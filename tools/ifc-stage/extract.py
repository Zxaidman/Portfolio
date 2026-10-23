"""Extract world-space triangle meshes from one or more IFCs (e.g. AR + ST of one project),
keeping ONLY geometry, the IFC class and a storey-group index per element.

Storeys at nearly the same height (A/B blocks of one level) are grouped together. Each group
gets a GENERIC label (Basement, Ground, Podium 1, Level 7, Terrace...) built from keywords and
numbers only; the model's own level names are never written.

usage: extract.py OUT_DIR model1.ifc [model2.ifc ...]
       A file can be limited to some classes, e.g. to take only the architectural layer from an
       ARCH model whose structure is already in the ST model (avoids duplicate stairs/slabs):
       extract.py OUT ST.ifc "ARCH.ifc@IfcWall,IfcWallStandardCase,IfcWindow,IfcPlate,IfcMember"
"""
import json, re, sys, time, multiprocessing
from collections import Counter
from pathlib import Path
import numpy as np
import ifcopenshell, ifcopenshell.geom, ifcopenshell.util.element as ue, ifcopenshell.util.unit as uu

CATS = ["IfcColumn", "IfcBeam", "IfcSlab", "IfcWall", "IfcWallStandardCase", "IfcStair", "IfcStairFlight",
        "IfcRamp", "IfcRampFlight", "IfcRailing", "IfcMember", "IfcPlate", "IfcWindow", "IfcDoor",
        "IfcFooting", "IfcRoof", "IfcCovering"]
GROUP_TOL = 1.6  # metres: storeys closer than this to a group's lowest level join that group


def generic_label(names: list[str]) -> str:
    n = " ".join(names).upper()
    lvl = re.search(r"\bLEVEL\s*(\d{1,3})\b", n)          # a plain "Level 8" wins over odd "Level B8" tags
    b = re.search(r"\bB(\d)\b", n)                      # "Level B2" -> Basement 2
    if b and not lvl:
        return f"Basement {b.group(1)}"
    if "LOWER GROUND" in n or "UPPER GROUND" in n:
        return "Lower ground" if "LOWER" in n else "Upper ground"
    num = re.search(r"\b(\d{1,3})(?:ST|ND|RD|TH)\b", n) or re.search(r"\bLEVEL\s*(\d{1,3})\b", n)
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
    specs = [(a.split("@")[0], a.split("@")[1].split(",") if "@" in a else CATS) for a in sys.argv[2:]]
    files = [ifcopenshell.open(p) for p, _ in specs]
    cats_of = {id(f): cats for f, (_, cats) in zip(files, specs)}
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
    if labels and labels[0] == "Level":      # lowest group with no usable name (e.g. excavation)
        labels[0] = "Foundation"
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
        elems = [e for c in cats_of[id(f)] for e in f.by_type(c, include_subtypes=False)]
        if not elems: continue
        it = ifcopenshell.geom.iterator(s, f, multiprocessing.cpu_count(), include=elems)
        if not it.initialize(): continue
        while True:
            sh = it.get()
            el = f.by_id(sh.id)
            v = np.asarray(sh.geometry.verts, dtype=np.float64).reshape(-1, 3)  # float32 later, after re-origin
            ix = np.asarray(sh.geometry.faces, dtype=np.uint32)
            if len(v) and len(ix):
                st = ue.get_container(el)
                z = (st.Elevation or 0) * k if st is not None and st.is_a("IfcBuildingStorey") else float(v[:, 2].min())
                pos_chunks.append(v); idx_chunks.append(ix)
                meta.append({"c": el.is_a(), "s": group_of(z), "v": [voff, len(v)], "i": [ioff, len(ix)],
                             "lo": v.min(0), "hi": v.max(0)})
                voff += len(v); ioff += len(ix)
            if not it.next(): break
    # Drop strays: elements that sit entirely far below the rest of the model (e.g. a railing left
    # at an excavation datum). They would stretch the frame and float under the building.
    lows = np.array([m["lo"][2] for m in meta])
    floor = np.percentile(lows, 1) - 5.0
    keep = [k for k, m in enumerate(meta) if m["hi"][2] >= floor]
    if len(keep) < len(meta):
        print(f"dropped {len(meta) - len(keep)} stray element(s) below z={floor:.1f}")
        voff = ioff = 0
        meta2, pc, ic = [], [], []
        for k in keep:
            m = meta[k]; pc.append(pos_chunks[k]); ic.append(idx_chunks[k])
            m["v"] = [voff, len(pos_chunks[k])]; m["i"] = [ioff, len(idx_chunks[k])]
            voff += len(pos_chunks[k]); ioff += len(idx_chunks[k]); meta2.append(m)
        meta, pos_chunks, idx_chunks = meta2, pc, ic
    P = np.concatenate(pos_chunks); I = np.concatenate(idx_chunks)
    # Georeferenced models sit at site coordinates (millions of metres); float32 would round them
    # to ~0.25 m. Move the footprint to a local origin first (keeps z, so storey heights still match).
    origin = np.array([P[:, 0].min(), P[:, 1].min(), 0.0])
    P = (P - origin).astype(np.float32)
    for m in meta:
        m["lo"] = (m["lo"] - origin).round(3).tolist(); m["hi"] = (m["hi"] - origin).round(3).tolist()
    (out / "geom.bin").write_bytes(P.tobytes() + I.tobytes())
    json.dump({"storeys": [round(z, 3) for z, _ in groups], "labels": labels,
               "nverts": int(voff), "nidx": int(ioff), "elements": meta}, open(out / "geom.json", "w"))
    print(f"{len(meta)} elements, {voff} verts, {ioff // 3} tris in {time.time() - t0:.0f}s")
    print(Counter(m["c"] for m in meta))
    print(list(zip(labels, Counter(m["s"] for m in meta).most_common() and [Counter(m["s"] for m in meta)[i] for i in range(len(groups))])))
    print("bbox", P.min(0), P.max(0))


if __name__ == "__main__":
    main()
