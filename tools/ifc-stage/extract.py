"""Extract world-space triangle meshes from an IFC, keeping ONLY geometry.

Writes  <out>/geom.bin  (float32 positions + uint32 indices, concatenated)
        <out>/geom.json (per element: category, storey index, offsets, bbox)
No names, GUIDs, properties, addresses or authors are written.
"""
import json, sys, time, multiprocessing
from pathlib import Path
import numpy as np
import ifcopenshell, ifcopenshell.geom, ifcopenshell.util.element as ue

src, out = Path(sys.argv[1]), Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
f = ifcopenshell.open(str(src))

CATS = ["IfcColumn", "IfcBeam", "IfcSlab", "IfcWall", "IfcStair", "IfcStairFlight", "IfcRailing",
        "IfcMember", "IfcPlate", "IfcWindow", "IfcDoor", "IfcFooting", "IfcRoof", "IfcCovering"]
storeys = sorted(f.by_type("IfcBuildingStorey"), key=lambda s: s.Elevation or 0)
sidx = {s.id(): i for i, s in enumerate(storeys)}

s = ifcopenshell.geom.settings()
s.set("use-world-coords", True)
s.set("apply-default-materials", True)
elems = [e for c in CATS for e in f.by_type(c, include_subtypes=False)]
it = ifcopenshell.geom.iterator(s, f, multiprocessing.cpu_count(), include=elems)
t0 = time.time()
pos_chunks, idx_chunks, meta = [], [], []
voff = ioff = 0
if it.initialize():
    while True:
        sh = it.get()
        el = f.by_id(sh.id)
        v = np.asarray(sh.geometry.verts, dtype=np.float32).reshape(-1, 3)
        ix = np.asarray(sh.geometry.faces, dtype=np.uint32)
        if len(v) and len(ix):
            st = ue.get_container(el)
            si = sidx.get(st.id(), -1) if st else -1
            pos_chunks.append(v); idx_chunks.append(ix)
            meta.append({"c": el.is_a(), "s": si, "v": [voff, len(v)], "i": [ioff, len(ix)],
                         "lo": v.min(0).round(3).tolist(), "hi": v.max(0).round(3).tolist()})
            voff += len(v); ioff += len(ix)
        if not it.next():
            break
P = np.concatenate(pos_chunks); I = np.concatenate(idx_chunks)
(out / "geom.bin").write_bytes(P.tobytes() + I.tobytes())
json.dump({"storeys": [round(float(x.Elevation or 0) * 0.3048, 3) for x in storeys],
           "nverts": int(voff), "nidx": int(ioff), "elements": meta}, open(out / "geom.json", "w"))
from collections import Counter
print(f"{len(meta)} elements, {voff} verts, {ioff//3} tris in {time.time()-t0:.0f}s")
print(Counter(m["c"] for m in meta)); print(Counter(m["s"] for m in meta))
print("bbox", P.min(0), P.max(0))
