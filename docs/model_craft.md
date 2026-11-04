# How good low-poly models are built

Measured on 511 FBX models from CC0 packs (Kenney: watercraft, pirate, holiday, platformer, building, blaster, mini forest),
plus KayKit Adventurers and the Kenney road tiles. No file from these packs is in this repo: only the numbers and methods below.
`pazl/core/vehicles/` applies them.

## Colour

- One 512 px atlas and one material for a whole pack. There are no pictures in it: about 16 hues, each as a pair of strips,
  one flat and one running from light at the top to dark at the bottom.
- 60-85 % of the faces of a vehicle span a gradient strip. That is the shading baked in for free: a hull goes darker towards
  the water. A flat fill looks dead next to it.
- Shade goes cooler as it darkens, it does not only lose brightness.
- A vehicle uses 15-30 atlas colours, the big liner about 50. Three or four carry most of the surface.

## Shape

- Chunky over exact. Corners are cut: 25-35 % of edges on vehicles are soft angles (15-60 degrees), the rest are hard.
- Boats get a thick bright rim that wraps the hull, and the hull narrows to the keel. The rim is what makes them read.
- Round things stay very low: a wheel is about 60 triangles with its hub, a funnel is open at the top with a dark inside.
- Big wheels are exaggerated: a locomotive driver is 21 % of the engine length.

## Triangle budgets

| Model | Triangles | Parts |
|---|---|---|
| Speedboat | 136-265 | 2-7 |
| Rowboat | 170 | 4 |
| Container | 160 | 11 |
| Tug | 200-470 | 4-8 |
| Train wagon | 660-930 | 9 |
| Locomotive | 740 | 7 |
| Sailing ship | 1400-1900 | 25-37 |
| Cargo ship | 360-1060 | 7-43 |
| Ocean liner | 2800 | 97 |

Triangles go where the eye goes: 58 of the liner's 97 parts are smaller than 8 % of its length.

## Small details and decals

- There are no see-through overlay decals in these packs. Everything that looks like a decal is one of two things:
  1. Colour cut into the surface. Waterlines, gold lines and stripes are extra edges on the hull, with faces mapped to another
     strip. They cannot flicker or float.
  2. A thin separate solid sunk into the surface. A container has 6 ribs (1.8 % thick, a quarter of its length) and 4 door bars.
     A porthole is a 28-triangle ring, 1.2 % of the ship's length, repeated.
- Small parts are not welded to the body. They overlap it, which costs nothing and keeps the body mesh simple.
- Windows have depth: a frame around an inset pane, never a flat rectangle.
- Repeats are exact copies, which is why a long row of portholes stays cheap.

## What the kit does with this

| Lesson | In `pazl/core/vehicles/kit.py` |
|---|---|
| One atlas, flat or gradient | `atlas()`, `Piece.grad`, one strip per colour, flat = a point on the strip |
| Colour cut into the surface | `Kit.paint()`, `Kit.bands()`: planes split the triangles, nothing is added on top |
| Thin parts for detail | `Kit.add(small solid, grad=False)`, gated by `detail` |
| Inset windows | a smaller glass core inside a body with holes, so every window is framed at once (`glasshouse`) |
| Cut corners cheaply | three views intersected: `side() ^ plan() ^ front()` |
| Boat rim and keel | `hull_shape()`, `open_hull()` in `water.py` |

Added on top of the references, because games need them:

- Text and patterns: plate numbers, route boards, hazard stripes and side lettering are atlas cells on thin plates (`Kit.decal`).
  The packs have no text at all.
- Wheels, propellers and rotors are separate nodes with their pivot at the axle.

## Keeping the weight down

- `merge_coplanar` rebuilds each flat patch from its outline after painting. Without it, door lines alone cost 700 triangles on a car.
- The wheel is built by hand with no inside faces: 62 triangles at 8 sides, the same as the reference wheels.
- Size decides the method. A window on a 120 m ship is a painted patch, on a car it is a real inset. A porthole is a 16-triangle `stud`.
- Thin parts use 3-sided rods and 6-sided cylinders.

| Model | Reference | `detail: 1` | `detail: 2` | `detail: 3` |
|---|---|---|---|---|
| Sedan | none in the packs | 830 | 1140 | 1610 |
| Speedboat | 136-265 | 510 | 590 | 630 |
| Rowboat | 170 | 270 | 420 | 480 |
| Tug | 200-470 | 750 | 1400 | 1820 |
| Train wagon | 660-930 | 850 | 1180 | 1540 |
| Locomotive | 740 | 1360 | 1600 | 2340 |
| Cargo ship | 360-1060 | 1130 | 2240 | 4700 |
| Sailing ship | 1400-1900 | 630 | 1340 | 1490 |
| Ocean liner | 2800 | 830 | 2680 | 4390 |

`detail: 1` is the level to use for traffic and crowds. Small boats, the tug and the locomotive are still above the references even there.
