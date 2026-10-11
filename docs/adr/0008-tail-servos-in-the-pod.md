# Tail servos in the pod, Bowden cables through the boom

The elevator and rudder servos sit upright in the pod, just behind the battery. Each drives its surface through a Bowden cable (a 2 mm tube with a 1 mm steel pushrod) that runs inside the hollow carbon boom and leaves the tail hub through a drilled channel next to its horn. The Lark mounts its servos in the fin, and so did this design at first.

The weight-and-balance check moved them. Everything at the tail acts on a lever of about half a metre, and the first PLA build balanced 54 mm behind its target, behind the neutral point. Moving the two servos forward was worth about 14 kg·mm, more than any other single change except the battery position. The cost is about 700 mm of Bowden cable per surface, which adds a little friction and play compared with a short direct linkage.

## Consequences

- The fin has no servo pockets, which makes it lighter and stronger.
- The Bowden exits in the hub are drilled channels, positioned in `tail.ELEV_BOWDEN` and `tail.RUDDER_BOWDEN`. The rudder's exit is in the top of the hub behind the fin, because the stab blocks the side.
