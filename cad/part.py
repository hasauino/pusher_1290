from dataclasses import dataclass

from geom import Manifold


@dataclass
class Part:
    name: str
    printed: Manifold    # oriented for printing: +Z is "up" on the bed
    assembly: Manifold   # in the aircraft frame
    material: str
    color: tuple
    note: str = ""
