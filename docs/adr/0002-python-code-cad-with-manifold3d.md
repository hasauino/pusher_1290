# Python code-CAD on manifold3d

Geometry is built in plain Python on manifold3d (mesh booleans, lofts and extrusions) instead of a GUI CAD tool, OpenSCAD or CadQuery. Code-CAD makes every dimension a parameter that an agent can change and regenerate end to end. manifold3d installs as a small wheel, guarantees watertight results and is fast enough to rebuild all 26 parts in seconds. CadQuery would add STEP export but needs the much heavier OpenCascade stack.

## Consequences

- The outputs are meshes, not B-rep solids: there is no STEP export, and curved surfaces are faceted at the resolution chosen in `cad/geom.py`.
- Lofts are hand-built from rings of points (`geom.loft`), so every section in a loft must have the same point count and winding. That is why airfoils are resampled onto a common grid in `cad/airfoils.py`.
