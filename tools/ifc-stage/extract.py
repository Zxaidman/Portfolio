"""Extract world-space triangle meshes from one or more IFCs (e.g. AR + ST of one project),
keeping ONLY geometry, the IFC class and a storey-group index per element.

Storeys at nearly the same height (A/B blocks of one level) are grouped together. Each group
gets a GENERIC label (Basement, Ground, Podium 1, Level 7, Terrace...) built from keywords and
numbers only; the model's own level names are never written.

usage: extract.py OUT_DIR model1.ifc [model2.ifc ...]
"""
import json, re, sys, time, multiprocessing
from collections import Counter
from pathlib import Path
import numpy as np
import ifcopenshell, ifcopenshell.geom, ifcopenshell.util.element as ue, ifcopenshell.util.unit as uu

CATS = ["IfcColumn", "IfcBeam", "IfcSlab", "IfcWall", "IfcStair", "IfcStairFlight", "IfcRailing",
        "IfcMember", "IfcPlate", "IfcWindow", "IfcDoor", "IfcFooting", "IfcRoof", "IfcCovering"]
GROUP_TOL = 1.6  # metres: storeys closer than this to a group's lowest level join that group


def generic_label(names: list[str]) -> str:
    n = " ".join(names).upper()
    num = re.search(r"\b(\d{1,3})(?:ST|ND|RD|TH)\b", n)
    for key, label in (("BASEMENT", "Basement"), ("FOUNDATION", "Foundation"), ("TERRACE", "Terrace"),
                       ("ROOF", "Roof"), ("OHT", "Water tank"), ("ROAD", "Ground"), ("SITE", "Ground"),
                       ("GROUND", "Ground"), ("STILT", "Stilt"), ("AMENITY", "Amenity"), ("PODIUM", "Podium")):
        if key in n:
            if label == "Podium":
                m = re.search(r"PODIUM\s*(\d+)", n)
                return f"Podium {m.group(1)}" if m else label
            return label
    return f"Level {num.group(1)}" if num else "Level"


def main():
    out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
    files = [ifcopenshell.open(p) for p in sys.argv[2:]]
    # storey groups across all files (same project => same shared coordinates)
    levels = []
    for f in files:
        k = uu.calculate_unit_scale(f)
        for s in f.by_type("IfcBuildingStorey"):
            levels.append(((s.Elevation or 0) * k, s.Name or ""))
    levels.sort()
    groups = []  # [z0, [names]]
    for z, name in levels:
        if groups and z - groups[-1][0] < GROUP_TOL:
            groups[-1][1].append(name)
        else:
            groups.append([z, [name]])
    def group_of(z):
        g = 0
        for i, (z0, _) in enumerate(groups):
            if z >= z0 - 1e-6: g = i
        return g
    labels = [generic_label(n) for _, n in groups]
    # make duplicate generic labels unique-ish (e.g. two "Ground" groups)
    seen = Counter()
    for i, l in enumerate(labels):
        seen[l] += 1
        if seen[l] > 1 and not re.search(r"\d", l): labels[i] = f"{l} {seen[l]}"

    s = ifcopenshell.geom.settings()
    s.set("use-world-coords", True)
    pos_chunks, idx_chunks, meta = [], [], []
    voff = ioff = 0
    t0 = time.time()
    for f in files:
        k = uu.calculate_unit_scale(f)
        elems = [e for c in CATS for e in f.by_type(c, include_subtypes=False)]
        if not elems: continue
        it = ifcopenshell.geom.iterator(s, f, multiprocessing.cpu_count(), include=elems)
        if not it.initialize(): continue
        while True:
            sh = it.get()
            el = f.by_id(sh.id)
            v = np.asarray(sh.geometry.verts, dtype=np.float32).reshape(-1, 3)
            ix = np.asarray(sh.geometry.faces, dtype=np.uint32)
            if len(v) and len(ix):
                st = ue.get_container(el)
                z = (st.Elevation or 0) * k if st is not None and st.is_a("IfcBuildingStorey") else float(v[:, 2].min())
                pos_chunks.append(v); idx_chunks.append(ix)
                meta.append({"c": el.is_a(), "s": group_of(z), "v": [voff, len(v)], "i": [ioff, len(ix)],
                             "lo": v.min(0).round(3).tolist(), "hi": v.max(0).round(3).tolist()})
                voff += len(v); ioff += len(ix)
            if not it.next(): break
    P = np.concatenate(pos_chunks); I = np.concatenate(idx_chunks)
    (out / "geom.bin").write_bytes(P.tobytes() + I.tobytes())
    json.dump({"storeys": [round(z, 3) for z, _ in groups], "labels": labels,
               "nverts": int(voff), "nidx": int(ioff), "elements": meta}, open(out / "geom.json", "w"))
    print(f"{len(meta)} elements, {voff} verts, {ioff // 3} tris in {time.time() - t0:.0f}s")
    print(Counter(m["c"] for m in meta))
    print(list(zip(labels, Counter(m["s"] for m in meta).most_common() and [Counter(m["s"] for m in meta)[i] for i in range(len(groups))])))
    print("bbox", P.min(0), P.max(0))


if __name__ == "__main__":
    main()
