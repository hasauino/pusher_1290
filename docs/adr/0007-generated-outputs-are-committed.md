# Generated outputs are committed

The STLs, assembly model, renders, manual and aerodynamics report are all generated from `cad/params.py` but are committed anyway. Builders download STLs from GitHub and open the manual without installing Python. The Pages workflow regenerates the manual from the CAD on every push, so a stale committed copy would quietly disagree with the live site. The cost is that a geometry change is only complete once the whole regeneration chain in AGENTS.md has run and its outputs are committed with the source change.
