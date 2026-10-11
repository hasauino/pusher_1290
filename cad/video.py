"""Assembly video from the builder's seat: every printed part and component
starts laid out on a workbench and moves into place, step by step.

    .venv/bin/python cad/video.py                      # video/pusher_1290_assembly.mp4
    .venv/bin/python cad/video.py --stills 4,30,95     # PNG frames at those seconds, for checking
    .venv/bin/python cad/video.py --web-only           # just remake the manual's web copy and poster

GPU-rendered with moderngl (shadow-mapped key light, 4x MSAA), encoded with ffmpeg.
"""
import argparse
import math
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

import imageio_ffmpeg
import moderngl
import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).parent))

import fuselage  # noqa: E402
import hardware  # noqa: E402
import tail  # noqa: E402
import wing  # noqa: E402
from geom import mesh_arrays  # noqa: E402
from params import MOTOR_HOLES  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
W, H, FPS = 1920, 1080, 30
FONT = "/System/Library/Fonts/Avenir Next.ttc"
PRINT_COLOR = (0.86, 0.86, 0.83)          # light grey PLA Aero
SURFACE_COLOR = (0.70, 0.72, 0.75)
TABLE = (-720.0, 1180.0, -1300.0, 1300.0)  # x0, x1, y0, y1 (mm); the builder sits at -x
MAT = (-60.0, 920.0, -700.0, 700.0)


# --- Scene items -----------------------------------------------------------------

@dataclass
class Item:
    name: str
    tris: np.ndarray       # (n, 3, 3) triangle vertices in the aircraft frame
    color: tuple
    material: int = 0      # 0 plastic, 1 carbon/metal (shinier)
    rest: np.ndarray = field(default_factory=lambda: np.zeros(3))   # offset when lying on the table
    vao: object = None
    shadow_vao: object = None


def item_from(name, man, color, material=0):
    v, t = mesh_arrays(man)
    return Item(name, v[t].astype("f4"), color, material)


def load_items():
    items = []
    for p in wing.parts() + fuselage.parts() + tail.parts():
        surface = p.name.startswith(("aileron", "tail_elevator", "tail_rudder"))
        color = (0.32, 0.32, 0.35) if p.material == "PETG" else SURFACE_COLOR if surface else PRINT_COLOR
        items.append(item_from(p.name, p.assembly, color))
    for c in hardware.components():
        items.append(item_from(c.name, c.shape, c.color, 1 if c.category in ("Carbon", "Fasteners") else 0))
    return {i.name: i for i in items}


# Free table areas around the build area, nearest the builder first: (x0, x1, y0, y1).
ZONES = [(-690.0, -90.0, -1250.0, 1250.0), (-60.0, 1150.0, 720.0, 1250.0),
         (-60.0, 1150.0, -1250.0, -720.0), (950.0, 1150.0, -700.0, 700.0)]


def lay_out(items, names):
    """Knolling: every item lies on the table in its assembled orientation,
    packed in shelves (biggest first) into the free zones around the build area."""
    gap = 26.0
    shelves = {z: [] for z in range(len(ZONES))}      # per zone: [x_top, depth, y_cursor]

    def size(n):
        p = items[n].tris.reshape(-1, 3)
        return p.min(0), p.max(0)

    for name in sorted(names, key=lambda n: -np.prod((size(n)[1] - size(n)[0])[:2])):
        lo, hi = size(name)
        sx, sy = hi[0] - lo[0], hi[1] - lo[1]
        placed = False
        for z, (x0, x1, y0, y1) in enumerate(ZONES):
            for shelf in shelves[z]:                    # an existing shelf with room
                if sx <= shelf[1] and shelf[2] + sy <= y1:
                    items[name].rest = np.array([shelf[0] - hi[0], shelf[2] - lo[1], -lo[2]])
                    shelf[2] += sy + gap
                    placed = True
                    break
            if placed:
                break
            top = shelves[z][-1][0] - shelves[z][-1][1] - gap if shelves[z] else x1
            if top - sx >= x0 and y0 + sy <= y1:        # open a new shelf
                shelves[z].append([top, sx, y0 + sy + gap])
                items[name].rest = np.array([top - hi[0], y0 - lo[1], -lo[2]])
                placed = True
                break
        if not placed:
            raise SystemExit(f"{name} ({sx:.0f} x {sy:.0f} mm) does not fit on the table")


# --- Script ----------------------------------------------------------------------

STEPS = [
    ("Fuselage", (-860, -150, 430), (230, 0, 70), 34, [
        ("Glue the front and rear segments together on their 10 mm sleeve",
         [[("fuse_2_front", (0, 0, 40))], [("fuse_3_rear", (70, 0, 0))]]),
        ("Add the motor cone and the boom-socket tail",
         [[("fuse_4_tail_motor_cone", (60, 0, 0))], [("fuse_4_tail_boom_socket", (60, 0, 0))]]),
        ("Melt the two M3 heat-set inserts into the saddle bosses",
         [[("Heat-set insert front", (0, 0, 70)), ("Heat-set insert rear", (0, 0, 70))]]),
    ]),
    ("Electronics", (-820, -170, 520), (190, 0, 50), 30, [
        ("Elevator and rudder servos upright between the floor rails",
         [[("Elevator servo", (0, 0, 110)), ("Rudder servo", (0, 0, 110))]]),
        ("Flight controller, then the ESC on top of it",
         [[("Flight controller", (0, 0, 150))], [("ESC", (0, 0, 150))]]),
        ("Slide the 4S LiPo in along the floor from the front",
         [[("Battery", (-160, 0, 0))]]),
        ("VTX, receiver and GPS on top of the battery",
         [[("VTX", (-90, 0, 30))], [("Receiver", (0, 0, 80))], [("GPS", (0, 0, 80))]]),
        ("About 92 g of lead in the nose, then the camera, then slide the nose on",
         [[("Nose weight", (-90, 0, 0))], [("FPV camera", (-80, 0, 0)), ("fuse_1_nose", (-80, 0, 0))]]),
        ("Close the hatch: front tab under the skin first",
         [[("fuse_hatch", (35, 0, 55))]]),
    ]),
    ("Motor", (-700, -560, 480), (450, 0, 110), 26, [
        ("Glue in the motor mount with its four M3 × 14 screws",
         [[("motor_mount", (70, 0, 0))] + [(f"Motor screw {dy:+.1f}/{dz:+.1f}", (70, 0, 0))
                                           for dy, dz in MOTOR_HOLES]]),
        ("Mount the motor, then the 7-inch prop",
         [[("Motor", (90, 0, 0))], [("Propeller", (90, 0, 0))]]),
    ]),
    ("Boom and tail", (-650, -700, 560), (700, 0, 40), 27, [
        ("Slide the 12 mm boom 160 mm into the fuselage socket",
         [[("Boom", (230, 0, 0))]]),
        ("Push the tail hub onto the boom, fin square to the table",
         [[("tail_fin_hub", (130, 0, 0))]]),
        ("Thread the two Bowden cables from the servos through the boom",
         [[("Elevator Bowden cable", (0, 0, 60)), ("Rudder Bowden cable", (0, 0, 60))]]),
        ("Stab spar and pin through the hub",
         [[("Stab spar", (0, 160, 0))], [("Stab pin", (0, 130, 0))]]),
        ("Slide on both stab halves",
         [[("tail_stab_R", (0, 100, 0)), ("tail_stab_L", (0, -100, 0))]]),
        ("Elevators, joined by the 2 mm wire through the hub",
         [[("Elevator joiner", (0, 130, 0))], [("tail_elevator_R", (0, 80, 0)), ("tail_elevator_L", (0, -80, 0))]]),
        ("Hinge the rudder",
         [[("tail_rudder", (60, 0, 0))]]),
        ("Horns on the elevator and rudder, Z-bend the pushrods into them",
         [[("Elevator horn", (0, 0, -40)), ("Rudder horn", (0, 40, 0))],
          [("Elevator pushrod ends", (0, -40, 0)), ("Rudder pushrod ends", (0, 40, 0))]]),
    ]),
    ("Wing", (-930, -90, 600), (300, 0, 110), 44, [
        ("Seat the centre section in the saddle",
         [[("wing_center", (0, 0, 160))]]),
        ("Bolt it down: M3 × 20 at the front, M3 × 14 at the back",
         [[("Wing bolt front", (0, 0, 60)), ("Wing bolt rear", (0, 0, 60))]]),
        ("Slide the 10 mm main spar and both 6 mm rear spars through",
         [[("Main spar", (0, 540, 0))], [("Rear spar R", (0, 330, 0)), ("Rear spar L", (0, -330, 0))]]),
        ("Glue panel S1 onto the spars on each side",
         [[("wing_s1_R", (0, 150, 0)), ("wing_s1_L", (0, -150, 0))]]),
        ("Panel S2, then a 9 g servo flat in each pocket",
         [[("wing_s2_R", (0, 150, 0)), ("wing_s2_L", (0, -150, 0))],
          [("Aileron servo R", (0, 0, -70)), ("Aileron servo L", (0, 0, -70))]]),
        ("Panel S3",
         [[("wing_s3_R", (0, 150, 0)), ("wing_s3_L", (0, -150, 0))]]),
        ("Glue on the upswept tips",
         [[("wing_tip_R", (0, 110, 0)), ("wing_tip_L", (0, -110, 0))]]),
        ("Ailerons: 3 mm joiner rod, then hinge them on",
         [[("Aileron joiner R", (0, 120, 0)), ("Aileron joiner L", (0, -120, 0))],
          [("aileron_inner_R", (60, 0, 0)), ("aileron_outer_R", (60, 0, 0)),
           ("aileron_inner_L", (60, 0, 0)), ("aileron_outer_L", (60, 0, 0))]]),
        ("Aileron horns and pushrods to the servos",
         [[("Aileron horn R", (0, 0, -40)), ("Aileron horn L", (0, 0, -40)),
           ("Aileron pushrod R", (0, 0, -40)), ("Aileron pushrod L", (0, 0, -40))]]),
    ]),
]
INTRO, MOVE, OVERLAP, HOLD, OUTRO = 6.0, 1.9, 0.45, 0.8, 7.0
SHOT_INTRO = ((-1100, 0, 700), (-150, 0, 0), 60)
SHOT_OUTRO = ((-860, -330, 470), (390, 0, 100), 40)


@dataclass
class Move:
    name: str
    t0: float
    t1: float
    approach: np.ndarray


@dataclass
class Caption:
    t0: float
    t1: float
    step: str
    index: int
    text: str


def build_timeline():
    moves, captions, shots = [], [], [(0.0,) + SHOT_INTRO]
    t = INTRO
    for si, (step, eye, target, fov, actions) in enumerate(STEPS):
        shots.append((t, eye, target, fov))
        t += 1.2                                   # let the head turn before the hands start
        for text, groups in actions:
            start = t
            for group in groups:
                for name, approach in group:
                    moves.append(Move(name, t, t + MOVE, np.array(approach, float)))
                t += MOVE - OVERLAP
            t += OVERLAP + HOLD
            captions.append(Caption(start - 0.3, t - 0.2, step, si + 1, text))
    shots.append((t,) + SHOT_OUTRO)
    end = t + OUTRO
    captions.append(Caption(t, end, "Done", len(STEPS) + 1,
                            "Balance at 66 mm behind the leading edge with lead in the nose, then range-check"))
    return moves, captions, shots, end


def smooth(u):
    u = min(max(u, 0.0), 1.0)
    return u * u * (3 - 2 * u)


def offset_at(it, mv, t):
    """Translation of an item at time t: resting, travelling, or in place."""
    if mv is None or t <= mv.t0:
        return it.rest
    if t >= mv.t1:
        return np.zeros(3)
    u = (t - mv.t0) / (mv.t1 - mv.t0)
    hover = mv.approach
    if u < 0.62:                                    # lift off the table and carry it over
        k = smooth(u / 0.62)
        p = it.rest * (1 - k) + hover * k
        dist = np.linalg.norm(it.rest[:2] - hover[:2])
        return p + np.array([0, 0, math.sin(math.pi * k) * min(90 + 0.08 * dist, 190)])
    k = smooth((u - 0.62) / 0.38)                    # slide home along the approach
    return hover * (1 - k)


def camera_at(shots, t, focus):
    """Eye, target, fov of the seated builder: shots blend over 1.4 s, the gaze
    drifts toward the part in hand, and the head never sits perfectly still."""
    i = max(k for k, s in enumerate(shots) if s[0] <= t)
    _, e1, g1, f1 = shots[i]
    if i > 0 and t - shots[i][0] < 1.4:
        _, e0, g0, f0 = shots[i - 1]
        k = smooth((t - shots[i][0]) / 1.4)
        e1 = np.array(e0) * (1 - k) + np.array(e1) * k
        g1 = np.array(g0) * (1 - k) + np.array(g1) * k
        f1 = f0 * (1 - k) + f1 * k
    eye, target = np.array(e1, float), np.array(g1, float)
    if focus is not None:
        target = target * 0.72 + focus * 0.28
    eye += np.array([math.sin(0.61 * t) * 7, math.sin(0.43 * t + 1.3) * 6, math.sin(0.87 * t + 2.1) * 4])
    return eye, target, f1


# --- Rendering -------------------------------------------------------------------

VERT = """
#version 330
uniform mat4 vp; uniform mat4 light_vp; uniform vec3 offset;
in vec3 in_pos; in vec3 in_nrm;
out vec3 v_pos; out vec3 v_nrm; out vec4 v_light;
void main() {
    vec3 p = in_pos + offset;
    v_pos = p; v_nrm = in_nrm; v_light = light_vp * vec4(p, 1.0);
    gl_Position = vp * vec4(p, 1.0);
}
"""
FRAG = """
#version 330
uniform vec3 color; uniform int material; uniform vec3 eye; uniform vec3 light_dir;
uniform sampler2D shadow_map;
in vec3 v_pos; in vec3 v_nrm; in vec4 v_light;
out vec4 f_color;
float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float noise(vec2 p) {
    vec2 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f);
    return mix(mix(hash(i), hash(i + vec2(1, 0)), f.x), mix(hash(i + vec2(0, 1)), hash(i + vec2(1, 1)), f.x), f.y);
}
float grid(float x, float step, float width) {
    float d = abs(fract(x / step + 0.5) - 0.5) * step;
    return 1.0 - smoothstep(width - fwidth(x), width + fwidth(x), d);
}
void main() {
    vec3 base = pow(color, vec3(2.2));
    vec3 n = normalize(v_nrm);
    if (!gl_FrontFacing) n = -n;
    float shine = 0.12, power = 24.0;
    if (material == 1) { shine = 0.35; power = 60.0; }
    if (material == 2) {               // oak workbench
        float rings = noise(vec2(v_pos.x * 0.05, v_pos.y * 0.003)) * 0.65 + noise(v_pos.xy * vec2(0.012, 0.0015)) * 0.35;
        base = pow(mix(vec3(0.60, 0.43, 0.27), vec3(0.70, 0.52, 0.33), rings), vec3(2.2));
        shine = 0.08;
    }
    if (material == 3) {               // self-healing cutting mat with a 10 / 50 mm grid
        base = pow(vec3(0.13, 0.33, 0.25), vec3(2.2));
        float minor = max(grid(v_pos.x, 10.0, 0.35), grid(v_pos.y, 10.0, 0.35));
        float major = max(grid(v_pos.x, 50.0, 0.7), grid(v_pos.y, 50.0, 0.7));
        base = mix(base, pow(vec3(0.55, 0.75, 0.62), vec3(2.2)), max(minor * 0.35, major * 0.8));
        shine = 0.04;
    }
    vec3 l = normalize(-light_dir);
    vec3 proj = v_light.xyz / v_light.w * 0.5 + 0.5;
    float lit = 0.0;
    vec2 texel = 1.0 / vec2(textureSize(shadow_map, 0));
    for (int x = -2; x <= 2; x++) for (int y = -2; y <= 2; y++) {
        float d = texture(shadow_map, proj.xy + vec2(x, y) * texel * 1.5).r;
        lit += proj.z - 0.0012 <= d ? 1.0 : 0.0;
    }
    lit /= 25.0;
    float diff = max(dot(n, l), 0.0) * lit;
    vec3 v = normalize(eye - v_pos);
    float spec = pow(max(dot(n, normalize(l + v)), 0.0), power) * shine * lit;
    float hemi = 0.5 + 0.5 * n.z;
    vec3 ambient = base * mix(vec3(0.20, 0.19, 0.18), vec3(0.42, 0.42, 0.44), hemi);
    vec3 col = ambient + base * diff * vec3(1.0, 0.96, 0.9) * 1.05 + spec;
    f_color = vec4(pow(col, vec3(1.0 / 2.2)), 1.0);
}
"""
DEPTH_VERT = """
#version 330
uniform mat4 light_vp; uniform vec3 offset;
in vec3 in_pos;
void main() { gl_Position = light_vp * vec4(in_pos + offset, 1.0); }
"""
DEPTH_FRAG = "#version 330\nvoid main() {}\n"


def look_at(eye, target, up):
    f = target - eye
    f /= np.linalg.norm(f)
    s = np.cross(f, up)
    s /= np.linalg.norm(s)
    u = np.cross(s, f)
    m = np.eye(4)
    m[0, :3], m[1, :3], m[2, :3] = s, u, -f
    m[:3, 3] = -m[:3, :3] @ eye
    return m


def perspective(fov, aspect, near, far):
    f = 1 / math.tan(math.radians(fov) / 2)
    m = np.zeros((4, 4))
    m[0, 0], m[1, 1] = f / aspect, f
    m[2, 2], m[2, 3] = (far + near) / (near - far), 2 * far * near / (near - far)
    m[3, 2] = -1
    return m


def ortho(half_w, half_h, near, far):
    m = np.eye(4)
    m[0, 0], m[1, 1] = 1 / half_w, 1 / half_h
    m[2, 2], m[2, 3] = -2 / (far - near), -(far + near) / (far - near)
    return m


def gl_mat(m):
    return m.T.astype("f4").tobytes()


def flat_normals(tris):
    n = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-9)
    return np.repeat(n[:, None, :], 3, axis=1).astype("f4")


def box_tris(x0, x1, y0, y1, z0, z1):
    import manifold3d as m3d
    b = m3d.Manifold.cube((x1 - x0, y1 - y0, z1 - z0)).translate((x0, y0, z0))
    v, t = mesh_arrays(b)
    return v[t].astype("f4")


def props():
    """The bench: oak top, cutting mat, a CA bottle and a soldering iron for the inserts."""
    from geom import cyl_x, cyl_z
    t = [Item("table", box_tris(TABLE[0], TABLE[1], TABLE[2], TABLE[3], -42, -2), (0.6, 0.45, 0.3), 2),
         Item("mat", box_tris(MAT[0], MAT[1], MAT[2], MAT[3], -2, 0), (0.15, 0.35, 0.27), 3)]
    bottle = cyl_z(0, 70, -560, 1150, 14, 32) + cyl_z(70, 92, -560, 1150, 5, 24)
    iron = cyl_x(-640, -500, 980, 14, 11, 24) + cyl_x(-500, -420, 980, 14, 3, 16)
    for name, man, color, mat in (("glue", bottle, (0.92, 0.92, 0.9), 0), ("iron", iron, (0.15, 0.15, 0.16), 1)):
        v, tr = mesh_arrays(man)
        t.append(Item(name, v[tr].astype("f4"), color, mat))
    return t


class Renderer:
    def __init__(self, items):
        self.ctx = moderngl.create_standalone_context()
        self.prog = self.ctx.program(vertex_shader=VERT, fragment_shader=FRAG)
        self.depth_prog = self.ctx.program(vertex_shader=DEPTH_VERT, fragment_shader=DEPTH_FRAG)
        for it in items:
            pos = it.tris.reshape(-1, 3)
            nrm = flat_normals(it.tris).reshape(-1, 3)
            vbo = self.ctx.buffer(np.hstack([pos, nrm]).astype("f4").tobytes())
            it.vao = self.ctx.vertex_array(self.prog, [(vbo, "3f 3f", "in_pos", "in_nrm")])
            it.shadow_vao = self.ctx.vertex_array(self.depth_prog, [(vbo, "3f 12x", "in_pos")])
        self.shadow_tex = self.ctx.depth_texture((4096, 4096))
        self.shadow_fbo = self.ctx.framebuffer(depth_attachment=self.shadow_tex)
        self.msaa = self.ctx.framebuffer(color_attachments=[self.ctx.renderbuffer((W, H), samples=4)],
                                         depth_attachment=self.ctx.depth_renderbuffer((W, H), samples=4))
        self.out = self.ctx.simple_framebuffer((W, H))
        self.light_dir = np.array([0.45, 0.55, -1.0])
        self.light_dir /= np.linalg.norm(self.light_dir)
        center = np.array([230.0, 0.0, 0.0])
        lv = look_at(center - self.light_dir * 3000, center, np.array([1.0, 0, 0]))
        self.light_vp = ortho(1500, 1500, 500, 5500) @ lv

    def frame(self, items, offsets, eye, target, fov):
        ctx = self.ctx
        ctx.enable(moderngl.DEPTH_TEST)
        self.shadow_fbo.use()
        self.shadow_fbo.clear(depth=1.0)
        self.depth_prog["light_vp"].write(gl_mat(self.light_vp))
        for it in items:
            self.depth_prog["offset"].value = tuple(offsets.get(it.name, (0, 0, 0)))
            it.shadow_vao.render()
        self.msaa.use()
        self.msaa.clear(0.80, 0.78, 0.74, 1.0)
        vp = perspective(fov, W / H, 20, 8000) @ look_at(eye, target, np.array([0.0, 0, 1]))
        p = self.prog
        p["vp"].write(gl_mat(vp))
        p["light_vp"].write(gl_mat(self.light_vp))
        p["eye"].value = tuple(eye)
        p["light_dir"].value = tuple(self.light_dir)
        self.shadow_tex.use(0)
        p["shadow_map"].value = 0
        for it in items:
            p["offset"].value = tuple(offsets.get(it.name, (0, 0, 0)))
            p["color"].value = tuple(it.color)
            p["material"].value = it.material
            it.vao.render()
        ctx.copy_framebuffer(self.out, self.msaa)
        img = np.frombuffer(self.out.read(components=3), np.uint8).reshape(H, W, 3)
        return img[::-1]


# --- Captions --------------------------------------------------------------------

class Overlay:
    def __init__(self):
        self.small = ImageFont.truetype(FONT, 22, index=2)
        self.big = ImageFont.truetype(FONT, 38, index=5)
        self.title = ImageFont.truetype(FONT, 84, index=0)
        self.sub = ImageFont.truetype(FONT, 32, index=5)

    def draw(self, img, t, captions, end):
        im = Image.fromarray(img).convert("RGBA")
        layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        if t < INTRO:
            a = smooth(min(t / 0.8, (INTRO - t) / 0.8))
            d.rectangle((0, 0, W, H), fill=(14, 16, 20, int(120 * a)))
            d.text((W / 2, H / 2 - 40), "Pusher 1290", font=self.title, anchor="mm", fill=(255, 255, 255, int(255 * a)))
            d.text((W / 2, H / 2 + 40), "Assembly, from the printed parts to a ready airframe", font=self.sub,
                   anchor="mm", fill=(225, 228, 232, int(255 * a)))
        for c in captions:
            if c.t0 <= t <= c.t1:
                a = smooth(min((t - c.t0) / 0.35, (c.t1 - t) / 0.35))
                label = f"STEP {c.index} OF {len(STEPS)}  ·  {c.step.upper()}" if c.index <= len(STEPS) else "DONE"
                tw = max(self.big.getlength(c.text), self.small.getlength(label))
                x0, y0 = 64, H - 170
                d.rounded_rectangle((x0, y0, x0 + tw + 64, y0 + 112), radius=14, fill=(14, 16, 20, int(175 * a)))
                d.text((x0 + 32, y0 + 22), label, font=self.small, fill=(150, 185, 255, int(255 * a)))
                d.text((x0 + 32, y0 + 52), c.text, font=self.big, fill=(255, 255, 255, int(255 * a)))
        if t > end - 3.0:
            a = smooth((t - (end - 3.0)) / 0.8)
            d.text((W - 64, 64), "hassan.umari.dev/pusher_1290", font=self.small, anchor="ra",
                   fill=(30, 32, 36, int(220 * a)))
        return np.asarray(Image.alpha_composite(im, layer).convert("RGB"))


# --- Web copy for the manual -------------------------------------------------------

WEB_VIDEO = ROOT / "manual" / "assembly.mp4"
WEB_POSTER = ROOT / "manual" / "assembly-poster.jpg"
WEB_MAX_MB = 15.0      # the Claude artifact host caps each supporting file at 15 MB


def web_copy(src):
    """720p copy and a poster frame (the finished plane) for the manual page."""
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    subprocess.run([ff, "-y", "-loglevel", "error", "-i", str(src), "-vf", "scale=1280:-2", "-c:v", "libx264",
                    "-crf", "28", "-preset", "slow", "-pix_fmt", "yuv420p", "-an", "-movflags", "+faststart",
                    str(WEB_VIDEO)], check=True)
    subprocess.run([ff, "-y", "-loglevel", "error", "-sseof", "-2.5", "-i", str(src), "-frames:v", "1",
                    "-vf", "scale=1280:-2", "-q:v", "3", str(WEB_POSTER)], check=True)
    mb = WEB_VIDEO.stat().st_size / 1e6
    if mb > WEB_MAX_MB:
        raise SystemExit(f"{WEB_VIDEO} is {mb:.1f} MB; raise its -crf until it is under {WEB_MAX_MB:.0f} MB")
    print(f"{WEB_VIDEO}: {mb:.1f} MB, poster {WEB_POSTER.name}")


# --- Main ------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stills", help="comma-separated seconds: write PNG frames instead of the video")
    ap.add_argument("--out", default=str(ROOT / "video" / "pusher_1290_assembly.mp4"))
    ap.add_argument("--web-only", action="store_true", help="only remake the manual's web copy and poster")
    args = ap.parse_args()
    if args.web_only:
        web_copy(args.out)
        return

    items = load_items()
    moves, captions, shots, end = build_timeline()
    order = [m.name for m in moves]
    missing = [n for n in items if n not in order]
    if missing:
        raise SystemExit(f"items never assembled in the video: {missing}")
    lay_out(items, order)
    by_item = {m.name: m for m in moves}
    scene = list(items.values()) + props()
    renderer, overlay = Renderer(scene), Overlay()

    def render_at(t):
        offsets = {n: offset_at(it, by_item.get(n), t) for n, it in items.items()}
        active = [m for m in moves if m.t0 <= t <= m.t1]
        focus = None
        if active:
            m = active[-1]
            c = items[m.name].tris.reshape(-1, 3).mean(0)
            focus = c + offsets[m.name]
        eye, target, fov = camera_at(shots, t, focus)
        return overlay.draw(renderer.frame(scene, offsets, eye, target, fov), t, captions, end)

    if args.stills:
        out = Path(args.out).parent
        out.mkdir(parents=True, exist_ok=True)
        for s in args.stills.split(","):
            Image.fromarray(render_at(float(s))).save(out / f"still_{float(s):05.1f}.png")
        print(f"stills in {out}")
        return

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    writer = imageio_ffmpeg.write_frames(args.out, (W, H), fps=FPS, codec="libx264", macro_block_size=8,
                                         output_params=["-crf", "26", "-preset", "slow", "-pix_fmt", "yuv420p",
                                                        "-movflags", "+faststart"])
    writer.send(None)
    frames = int(end * FPS)
    for f in range(frames):
        writer.send(np.ascontiguousarray(render_at(f / FPS)).tobytes())
        if f % (FPS * 10) == 0:
            print(f"  {f / FPS:5.1f} / {end:.1f} s", flush=True)
    writer.close()
    print(f"{args.out}: {end:.0f} s, {frames} frames at {W}x{H}")
    web_copy(args.out)


if __name__ == "__main__":
    main()
