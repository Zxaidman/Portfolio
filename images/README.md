# Images

Drop your files here using these exact names — the page picks them up automatically.
Until a file exists, the card falls back to a coloured gradient (nothing breaks).

```
images/
├── profile.jpg              ← your profile photo (square crop, ~600×600)
└── projects/
    ├── project-1.jpg
    ├── project-2.jpg
    ├── project-3.jpg
    ├── project-4.jpg
    ├── project-5.jpg
    └── project-6.jpg        ← empty slot, waiting for your next render
```

## Which render goes where

The card text in `index.html` was written to match these specific renders — save each
one under the matching filename:


| File            | The render it expects                                                                                                                    |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| `project-1.jpg` | Colour isometric cutaway — piles/raft at the bottom, podium amenity deck with pool and jogging track, tower above, exposed roof framing |
| `project-2.jpg` | Grey + blue structural frame of the tall tower with the blue basement/podium box                                                         |
| `project-3.jpg` | Triangular wedge floor plate, cutaway showing partitions, ceilings and the glazed facade                                                 |
| `project-4.jpg` | Finished cream/beige architectural tower with balconies, stilt level and footings                                                        |
| `project-5.jpg` | Monochrome twin towers over the curved podium parking                                                                                    |

Prefer landscape crops around 1200×900 (4:3). The cards crop to 4:3, so anything
wildly tall will get trimmed top and bottom.

## Editing project details

Everything is in the `projects` array near the bottom of `index.html`:

```js
{ name:"Project name",
  location:"Area, City",
  tag:"Short label",          // shown top-left on hover
  scope:"One line of detail", // shown under the location on hover
  img:"images/projects/project-1.jpg" }
```

Add more objects for more cards — the grid stays 3 per row and renumbers itself.
An entry with an empty `name` renders as a dashed "add render here" slot.
