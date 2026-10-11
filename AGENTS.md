# Pusher 1290

Code-CAD for a 1290 mm 3D-printed pusher RC plane, split into parts that fit a Bambu Lab A1 mini (180 × 180 × 180 mm). Domain language lives in [GLOSSARY.md](GLOSSARY.md); decisions and their reasons live in [docs/adr/](docs/adr/). Read the relevant ADR before changing airfoil, planform, CAD toolchain, or anything Flightory-related.

## Change a dimension, then regenerate

`cad/params.py` is the single source of truth for geometry. Every output in the repo is generated from it and committed, so a geometry change is only done when the whole chain has run, in order:

1. `.venv/bin/python cad/build.py`: STLs, printed-parts assembly, renders. Exits non-zero if any part outgrows the bed.
2. `.venv/bin/python cad/assembly.py`: full assembly with every bought component (`cad/hardware.py`). Exits non-zero if a component collides with a printed part.
3. `.venv/bin/python cad/check_print.py`: overhang report. Exits non-zero on a printability regression.
4. `.venv/bin/python cad/export_web.py`: `manual/index.html` and `manual/models.json`.
5. `.venv/bin/python aero/report.py`: `AERODYNAMICS.md` and `aero/figures/` (~1 min). Needed when the wing, tail, mass or CG changes.

Done means all five ran clean and `git status` shows the regenerated outputs alongside the source change. Prose numbers in `README.md` (CG, L/D, masses) are hand-copied from these outputs; update them when they move.

## Invariants

- **Fit**: every part ≤ 176 × 176 mm footprint and ≤ 180 mm tall, in its print frame. Split oversized parts by design (new panel, new segment with a lip), never by an after-the-fact cut.
- **Hardware fits**: every bought component (carbon, bolts, servos, motor, battery, avionics) is modelled at true size and position in `cad/hardware.py`, with bolt lengths and spar lengths derived from the geometry. The bill of materials in `README.md` and `manual/template.html` quotes those derived values; `assembly.py` prints them.
- **Print frame is deliberate**: each part's `printed` mesh is oriented for support-free printing. Horizontal holes are teardrops pointing up, downward faces get 45° chamfers, wing panels stand on their root. Keep new features within these rules and confirm with `check_print.py`.
- **Two frames**: the aircraft frame is millimetres, +X aft from the nose tip, +Y right wing, +Z up. `aero/` works in SI metres. The CG is quoted in mm behind the wing LE at the root.
- **Original design only**: no Flightory geometry, files, branding or product images. The plane is named Pusher 1290. The Flightory renders in the project root are local reference only and stay out of git (see ADR 0001).

## Gotchas

- `manual/template.html` is the manual's source; `index.html` is generated. The template has no `<!doctype>`/`<head>`, because the Claude Artifact host adds them. `export_web.py --site DIR` wraps it into a full document for GitHub Pages.
- AeroSandbox's VLM goes singular on the upswept tips above `spanwise_resolution=6`. Keep it at 6; `analysis.stability()` asserts a plausible lift slope to catch this.
- Pushing over HTTPS fails for `.github/workflows/` changes (the `gh` token lacks `workflow` scope). Push over SSH: `git push git@github.com:hasauino/pusher_1290.git main`.
- Every push to `main` republishes the manual to https://hassan.umari.dev/pusher_1290/ via `.github/workflows/pages.yml`.
- The Claude Artifact copy of the manual is https://claude.ai/artifact/D5UTsCGfX7Q4rfTPNguRrU. Republish it from `manual/index.html` with `models.json` after regenerating.
