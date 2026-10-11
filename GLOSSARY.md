# Pusher 1290

A 1290 mm pusher RC plane designed to be printed in parts on a 180 mm printer and glued around carbon tubes.

## Airframe

**Wing**:
The whole lifting surface, tip to tip: centre section, three panels and a tip per side, plus ailerons.

**Centre section**:
The middle 160 mm of the wing that bolts onto the pod's saddle.
_Avoid_: Wing root piece, middle panel

**Panel**:
One 160 mm span-wise slice of the wing outboard of the centre section, named S1, S2, S3 from root to tip.
_Avoid_: Wing segment, section (except "centre section")

**Tip**:
The upswept outermost piece of each wing half.
_Avoid_: Winglet, wingtip panel

**Main spar**:
The 10 mm carbon tube running span-wise through the wing at a quarter of the chord.

**Rear spar**:
The 6 mm carbon tube running span-wise behind the main spar.

**Pod**:
The fuselage body that carries the battery, electronics, camera and motor.
_Avoid_: Fuselage (when the boom is excluded), body

**Segment**:
One printed slice of the pod along its length: nose, front, rear, tail cone.
_Avoid_: Fuselage part, section

**Lip**:
The sleeve on a segment's front face that slides into the segment ahead and carries the glue joint.
_Avoid_: Collar, joiner

**Saddle**:
The wing-shaped seat on top of the pod that the centre section sits in.

**Hatch**:
The removable top cover over the battery bay.

**Motor cone**:
The rear end of the pod that carries the motor mount.

**Boom**:
The 12 mm carbon tube from the pod to the tail.
_Avoid_: Tail tube, tail boom (fine in prose, but not as a part name)

**Boom socket**:
The fairing under the pod's rear that the boom slides into.

**Bowden cable**:
A steel pushrod sliding inside a plastic tube, running through the boom from a tail servo in the pod to its control horn.
_Avoid_: Pull-pull, cable, linkage (for this specific part)

**Nose weight**:
Lead fixed low in the nose to bring the CG onto its target.
_Avoid_: Ballast (fine in prose), counterweight

**Tail hub**:
The flat-sided block at the end of the boom that carries the fin and both stab halves.
_Avoid_: Tail block, empennage mount

**Stab**:
The horizontal tail surface, two halves on the tail hub.
_Avoid_: Tailplane, horizontal stabiliser (fine in prose)

**Fin**:
The vertical tail surface rising from the tail hub.
_Avoid_: Vertical stabiliser, tail

## Control surfaces

**Control surface**:
Any moving surface: aileron, elevator or rudder.

**Hinge line**:
The span-wise line where a control surface meets its fixed surface.

**Bevel**:
The V-shaped leading edge of a control surface whose half-angle sets the maximum throw.

## Printing

**Part**:
One printable piece, exactly one STL file.
_Avoid_: Component, piece (when a file is meant)

**Bed**:
The 180 × 180 × 180 mm build volume of the Bambu Lab A1 mini.
_Avoid_: Plate, build plate, print bed

**Print frame**:
A part's orientation and position as it sits on the bed, chosen so it prints without supports.

**Aircraft frame**:
A part's position on the assembled plane: X aft from the nose tip, Y toward the right wing, Z up.
_Avoid_: World frame, model coordinates

## Flight and aerodynamics

**Design point**:
The flight condition the analysis is quoted at: all-up mass, CG and sea-level air.

**CG**:
The balance point, quoted in millimetres behind the wing's leading edge at the root.
_Avoid_: Centre of mass, balance point (fine in prose)

**Neutral point**:
The CG position at which the plane has no pitch stability.

**Static margin**:
The distance from CG to neutral point as a fraction of the mean wing chord.

**Best-glide speed**:
The airspeed of maximum lift-to-drag ratio, used for range.
_Avoid_: Cruise speed

**Minimum-power speed**:
The airspeed that needs the least power to stay level, used for endurance.
_Avoid_: Loiter speed, endurance speed

**Before / After**:
The original design (E193 wing, stab at 0°, CG 62 mm) versus the current one, as compared in the aerodynamic analysis.
