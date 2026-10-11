# Wing panels print standing on their root, with internal walls modelled in

Each wing panel is a span-wise extrusion of a 2D section: a 0.8 mm skin, span-wise webs and spar sleeves, printed standing on its root with 0 % infill. The common alternative is a solid model sliced in "vase mode" or with slicer-generated internal ribs. Modelled walls keep the structure and its weight under version control and identical in every slicer, and standing panels have no overhangs at all because every wall is vertical. The cost is that panels are limited to 160 mm of span (bed height), so each wing half has three panels plus a tip.

## Consequences

- Anything that crosses the wing's thickness (servo pocket, bolt sleeves) needs 45° chamfers or teardrop shapes, because inside a standing panel it becomes an overhang.
- Wall thickness is sized for foamed LW-PLA. Printing in regular PLA works but roughly doubles the printed mass; thinner PLA walls (0.45 mm skin) are an open option.
