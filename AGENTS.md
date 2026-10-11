# Pusher 1290

Code-CAD for a 1290 mm 3D-printed pusher RC plane, split into parts that fit a Bambu Lab A1 mini (180 × 180 × 180 mm). Domain language lives in [GLOSSARY.md](GLOSSARY.md); decisions and their reasons live in [docs/adr/](docs/adr/). Read the relevant ADR before changing airfoil, planform, CAD toolchain, or anything Flightory-related.

## Change a dimension, then regenerate

`cad/params.py` is the single source of truth for geometry. Every output in the repo is generated from it and committed, so a geometry change is only done when the whole chain has run, in order:

1. `.venv/bin/python cad/build.py`: STLs, printed-parts assembly, renders. Exits non-zero if any part outgrows the bed.
2. `.venv/bin/python cad/assembly.py`: full assembly with every bought component (`cad/hardware.py`). Exits non-zero if a component collides with a printed part.
3. `.venv/bin/python cad/check_print.py`: overhang report. Exits non-zero on a printability regression.
4. `.venv/bin/python cad/export_web.py`: `manual/index.html` and `manual/models.json`.
5. `.venv/bin/python aero/report.py`: `AERODYNAMICS.md` and `aero/figures/` (~1 min). Needed when the wing, tail, mass or CG changes.
6. `.venv/bin/python cad/video.py`: `video/pusher_1290_assembly.mp4` (~1 min). The assembly order and captions live in `STEPS` in that file; a part or component missing from `STEPS` fails the render. Check a few frames first with `--stills 10,50,90`.

Done means all six ran clean and `git status` shows the regenerated outputs alongside the source change. Prose numbers in `README.md` (CG, L/D, masses) are hand-copied from these outputs; update them when they move.

## Invariants

- **Fit**: every part ≤ 176 × 176 mm footprint and ≤ 180 mm tall, in its print frame. Split oversized parts by design (new panel, new segment with a lip), never by an after-the-fact cut.
- **Hardware fits**: every bought component (carbon, bolts, servos, linkages, motor, battery, avionics) is a common Amazon part, modelled at true size, mass and position in `cad/hardware.py`. Bolt, spar and Bowden lengths are derived from the geometry. The bill of materials in `README.md` and `manual/template.html` quotes those derived values; `assembly.py` prints them.
- **Balance**: the PLA build must balance at the 66 mm CG target (±3 mm). `assembly.py` checks it with a full weight budget (`cad/mass.py`) and prints the nose weight that would restore it. Anything that moves mass aft (a heavier tail, a component moved back) shows up here first (see ADR 0009).
- **Print frame is deliberate**: each part's `printed` mesh is oriented for support-free printing. Horizontal holes are teardrops pointing up, downward faces get 45° chamfers, wing panels stand on their root. Keep new features within these rules and confirm with `check_print.py`.
- **Two frames**: the aircraft frame is millimetres, +X aft from the nose tip, +Y right wing, +Z up. `aero/` works in SI metres. The CG is quoted in mm behind the wing LE at the root.
- **Original design only**: no Flightory geometry, files, branding or product images. The plane is named Pusher 1290. The Flightory renders in the project root are local reference only and stay out of git (see ADR 0001).

## Gotchas

- `manual/template.html` is the manual's source; `index.html` is generated. The template has no `<!doctype>`/`<head>`, because the Claude Artifact host adds them. `export_web.py --site DIR` wraps it into a full document for GitHub Pages.
- AeroSandbox's VLM goes singular on the upswept tips above `spanwise_resolution=6`. Keep it at 6; `analysis.stability()` asserts a plausible lift slope to catch this.
- Pushing over HTTPS fails for `.github/workflows/` changes (the `gh` token lacks `workflow` scope). Push over SSH: `git push git@github.com:hasauino/pusher_1290.git main`.
- Every push to `main` republishes the manual to https://hassan.umari.dev/pusher_1290/ via `.github/workflows/pages.yml`.
- The Claude Artifact copy of the manual is https://claude.ai/artifact/D5UTsCGfX7Q4rfTPNguRrU. Republish it from `manual/index.html` with `models.json`, `assembly.mp4` and `assembly-poster.jpg` after regenerating. That host caps each supporting file at 15 MB, which is why the manual uses a 720p copy of the video (`cad/video.py` makes it and fails if it grows past the cap).
