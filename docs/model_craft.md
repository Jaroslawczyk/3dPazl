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

## Where we are heavier

`detail: 1` is the fair comparison with the packs. A car there is about 1300 triangles, and `detail: 2` about 2400, roughly three
times the budget above, mostly from wheels (150 each against 60) and from cuts for lamps and door lines. Use `detail: 1` for
traffic and crowds.
