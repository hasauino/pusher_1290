# Lark-style pusher RC plane for the Bambu Lab A1 mini

This is an original parametric airframe with the same layout as the Flightory Lark: a pod fuselage, a pusher motor behind the wing, a carbon tail boom, a conventional tail, and a wing with an SD7037 airfoil (chosen for low drag; see [AERODYNAMICS.md](AERODYNAMICS.md)). It is the same size: 1290 mm span and 865 mm length. None of Flightory's geometry is used. Every printed part fits a 180 × 180 × 180 mm bed with 2 mm to spare on each side.

![iso](renders/iso_front.png)

| | |
|---|---|
| Wingspan / length | 1290 mm / 865 mm |
| Wing | SD7037, 200 mm chord, 1.5° incidence, 0.25 m² |
| Tail | NACA 0009 stab at −1° incidence (376 mm span), NACA 0012 fin, tail volume 0.50 (H) / 0.030 (V) |
| Printed parts | 26 STLs (13 wing, 7 fuselage, 6 tail) |
| Est. printed mass | ~700 g in LW-PLA, before carbon and electronics |
| Centre of gravity | **start at 66 mm behind the wing LE** (range 57–77). The neutral point is at 93 mm. |
| Performance (model, 2.3 kg) | best L/D 15.7 at 17 m/s (61 km/h); minimum power 43 W at 13.5 m/s. See [AERODYNAMICS.md](AERODYNAMICS.md). |

> **Not flight-tested.** The geometry was checked for fit, printability and clearances. The aerodynamic numbers come from AeroSandbox models (see [AERODYNAMICS.md](AERODYNAMICS.md)), not wind-tunnel or flight data. Do range checks, a CG check and a few gentle hand-launch glides before the first powered flight.

## Files

- `stl/` – one STL per part, already oriented and centred for the A1 mini. Load them into Bambu Studio as they are. `stl/PARTS.md` lists each part's size on the bed, material and notes.
- `assembly/lark_assembly.stl` – the whole plane assembled, for reference.
- `renders/` – previews. `parts_sheet.png` shows every part as it sits on the bed.
- `cad/` – the Python source. Every dimension is in `cad/params.py`.
- `manual/` – the interactive build manual (3D viewer, bill of materials, steps), live at **[hassan.umari.dev/pusher_1290](https://hassan.umari.dev/pusher_1290/)**. `.venv/bin/python cad/export_web.py` regenerates it from the CAD; `.github/workflows/pages.yml` rebuilds and republishes it on every push to `main`.
- `aero/` – the aerodynamic model and analysis. `.venv/bin/python aero/report.py` regenerates [AERODYNAMICS.md](AERODYNAMICS.md) from the current parameters.

To rebuild after changing a parameter:

```sh
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python cad/build.py
```

The build fails, and names the parts, if any part stops fitting the bed.

## Printing (Bambu Studio, 0.4 nozzle, 0.2 mm layers)

Use **Bambu PLA Aero** (or another LW-PLA) unless the part is marked PETG.

| Parts | Wall loops | Sparse infill | Top/bottom layers | Notes |
|---|---|---|---|---|
| Wing centre, S1, S2, S3 | 2 | 0 % | 3 | The internal spars and webs are modelled in, so infill isn't needed. |
| Wing tips, ailerons, stab, elevators, rudder, fin hub | 2 | 8 % gyroid | 3 | Solid parts. Use a brim (5 mm) on the tall thin ones. |
| Fuselage segments, hatch | 3 | 10 % gyroid | 3 | The shell is modelled at 1.2 mm. Infill only fills the boom-socket walls. |
| `motor_mount`, `fuse_4_tail_motor_cone` | 4 | 40 % | 4 | **PETG.** These carry the motor and run warm. |

- No supports needed. Overhangs are held to 45° using chamfers and teardrop holes, with a few short exceptions: the servo-pocket ceilings in S2 and the fin hub (25–33 mm bridges) and the ring of ceiling around the camera hole at the nose tip. If your printer bridges poorly, turn on *Thick bridges*.
- `fuse_3_rear` stands on a small ring with a free-standing boom-socket column next to it, so give it a brim.
- Left and right wing parts are mirror images; print both.

## Hardware

| Item | Qty / size |
|---|---|
| Carbon tube 10 mm OD (main spar) | 1 × 1000 mm |
| Carbon tube 6 mm OD (rear spar) | 2 × 600 mm (meet at the centreline) |
| Carbon tube 12 mm OD (boom) | 1 × 490 mm |
| Carbon tube 6 mm OD (stab spar) | 1 × 130 mm |
| Carbon rod 3 mm (stab pin) | 1 × 80 mm |
| Carbon rod 3 mm (aileron joiners) | 2 × 80 mm |
| Piano wire or carbon rod 2 mm (elevator joiner) | 1 × 100 mm |
| M3 heat-set inserts + bolts (wing) | 2 inserts, 1 × M3×20 (front), 1 × M3×16 (rear) |
| Servos, EMAX ES08MA II or same size | 4: 2 ailerons, elevator, rudder (the rudder is optional) |
| Hinges (polyester/CA, or hinge tape) | ~14 |
| Control horns, 1.2 mm pushrods | 4 |
| Motor | 28xx class, e.g. T-Motor F90 1300KV, 7" prop (7×4 to 7×6) |
| ESC, FC, GPS, receiver, camera | e.g. 30–40 A ESC, F405 wing FC, 19 × 19 mm FPV camera |

**Check the motor mount before printing it.** `motor_mount.stl` has a 16 × 19 mm M3 cross pattern and a 10 mm centre hole. If your motor uses a different pattern, change the holes in `fuselage.motor_mount()`.

**Battery bay:** the flat floor is about 80 mm wide (100 mm higher up) and about 150 mm long, and the bay continues under the wing saddle. A 4S Li-ion pack about 75 × 56 × 130 mm (for example 4S6P 18650) fits.

## Assembly

1. **Wing.** Slide the 10 mm spar and the two 6 mm rear spars through the centre section, then S1, S2 and S3 on each side. Glue each joint with medium CA or 5-minute epoxy. Glue the tips on, with the rear spar ending 35 mm inside them. The aileron servo lies flat in the pocket under S2. Its lead runs inside the wing's middle cell and comes out through the hole in the centre section's bottom skin.
2. **Ailerons.** Glue a 3 mm rod through the inner and outer aileron so they move as one piece. Hinge them along the bevel's apex line (the centreline). The bevel allows ±30° of throw.
3. **Fuselage.** Glue the front segment to the rear segment, and the two tail-cone pieces to the rear, using the 10 mm sleeves at each joint. Leave the nose unglued and hold it with tape or a screw so the camera can be reached. Melt the two M3 inserts into the bosses under the wing saddle. Bolt the motor to `motor_mount` first, then glue the mount into the cone.
4. **Boom.** Glue the 12 mm tube into the fuselage socket (160 mm deep) and into the tail hub (110 mm deep). Check that the fin is square to the wing first. Servo leads from the tail run inside the boom, into the fuselage.
5. **Tail.** Put the stab halves on the 6 mm spar and 3 mm pin through the hub. Hinge the elevators and join them with the 2 mm rod through the slot in the hub. The elevator servo goes in the left fin pocket and the rudder servo in the right.
6. **Wing on.** The wing drops into the saddle and is held by the two M3 bolts. The saddle window gives access to wiring and the battery. To fit the battery hatch, hook its front tab under the fuselage skin, then press the back down onto the ledge. Hold it with a 6 × 3 mm magnet or tape.

Suggested first throws: ailerons ±12°, elevator ±10°, rudder ±15°. Seal the aileron and elevator hinge gaps with clear tape; it's free drag reduction.
