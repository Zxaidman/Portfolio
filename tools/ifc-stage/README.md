# IFC stage renderer

Turns an IFC model into the frames of the site's scroll stage: elements fly into place storey
by storey (columns grow, beams slide in, slabs drop, walls rise, facade flies in), the storeys
separate into an exploded view and close again, and the camera orbits the whole time. A faint
wireframe of the finished building shows before the build starts. Frames are neutral clay on a
transparent background; the page tints them to the current theme.

**The IFC never goes into this repository.** `extract.py` keeps only triangle geometry, the IFC
class and the storey index of each element. Names, GUIDs, properties, addresses and authors are
dropped. Keep the IFC and the extracted geometry outside the repo.

```bash
cd tools/ifc-stage && npm install            # three.js, pinned in package.json
pip install --break-system-packages ifcopenshell playwright

python3 extract.py /path/to/model.ifc /tmp/geo             # ~1-2 min for 5k elements
CHROMIUM=/path/to/chrome python3 drive.py /tmp/geo /tmp/frames --frames 168   # ~5 s/frame (software GL)
cd ../.. && python3 scripts/stage.py model /tmp/frames --phases /tmp/frames/phases.json --complete 0.6
python3 scripts/portfolio.py build
```

Options for `--query`: `az0` (start angle, degrees), `azspan` (orbit sweep), `fov`, `r` (fixed
camera distance), `w`/`h` (render size). The timing of the choreography is at the top of
`render.html` (`A0`, `A1`, `EX`, `EXGAP`, `PHASE`); `--complete` must match `A1` (when the
building is fully assembled).

Tips: export from Revit as IFC4 or IFC4x3, any model view; rebar and furniture are skipped.
A building of 3-30 storeys works best. Models over ~1.5 M triangles render slowly.
