# Neutral point from the vortex-lattice model, not AeroBuildup

Drag and performance come from AeroSandbox's AeroBuildup. Stability and trim come from its vortex-lattice method (VLM) plus AeroBuildup's body moments. AeroBuildup on its own ignores the wing's downwash on the tail and put the neutral point at 131 mm behind the LE, about 30 mm too far aft, which would have suggested a dangerously aft CG. The VLM result (93 mm) was checked for mesh convergence at spanwise resolutions 4 and 6, and agrees with a hand estimate.

## Consequences

The VLM goes singular on the upswept tips above `spanwise_resolution=6`, so it is pinned at 6, and `analysis.stability()` asserts a plausible lift slope to catch a bad mesh.
