#!/usr/bin/env python3
"""Generate data/catalog.json for the Vault configurator from the parts/ tree.

Everything here is derived from file names/paths plus the quantities printed in the
USSA manual (hardware list pp.17-19, assembly pp. in 02-04 PDFs). Where the manual gives
no quantity the part carries qty=None and is reported as 'qty not in manual'.
Run:  python3 tools/build_catalog.py
"""
import json, os, re, sys, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARTS = os.path.join(ROOT, "parts")
OUT = os.path.join(ROOT, "data", "catalog.json")

ALL = []
for dp, dn, fn in os.walk(PARTS):
    for f in fn:
        if f.lower().endswith(".stl"):
            ALL.append(os.path.relpath(os.path.join(dp, f), PARTS))
ALL.sort()

SUP = re.compile(r"\s*\(turn on supports\)", re.I)


def stem(p):
    return os.path.splitext(os.path.basename(p))[0]


def label(p):
    s = SUP.sub("", stem(p))
    return re.sub(r"\s+", " ", s).strip()


def F(p, q=None, n=None):
    d = {"p": p, "l": label(p)}
    if q is not None:
        d["q"] = q
    notes = []
    if n:
        notes.append(n)
    if SUP.search(stem(p)) or "turn on supports" in stem(p).lower():
        notes.append("slicer: turn ON supports")
    if notes:
        d["n"] = "; ".join(notes)
    return d


def under(prefix):
    return [p for p in ALL if p.startswith(prefix)]


def hw(item, qty, per=None, src=None, byh=None):
    d = {"item": item, "qty": qty}
    if per:
        d["per"] = per
    if src:
        d["src"] = src
    if byh:
        d["byh"] = byh
    return d


def height_of(p):
    m = re.search(r"(?<![0-9A-Za-z])(1|2|4)\s?F", os.path.basename(p), re.I)
    if m:
        return m.group(1) + "F"
    m = re.search(r"[A-Z]+(1|2|4)F", os.path.basename(p))
    return m.group(1) + "F" if m else None


def split_family(code):
    m = re.match(r"^(XL|L|M|S)(\d)(²?)$", code)
    return m.group(1), int(m.group(2)), bool(m.group(3))


# ---------------------------------------------------------------- variants
D_ROOTS = {"S": "01. DRAWERS/01. S Families", "M": "01. DRAWERS/02. M Families",
           "L": "01. DRAWERS/03. L Families", "L²": "01. DRAWERS/04. L² Families",
           "XL": "01. DRAWERS/05. XL Families", "XL²": "01. DRAWERS/06. XL² Families"}
S_ROOTS = {"S": "02. SUSTAINERS/01. S Families", "M": "02. SUSTAINERS/02. M Families",
           "L": "02. SUSTAINERS/03. L Families", "XL": "02. SUSTAINERS/04. XL Families"}

MODES = [
    {"id": "mounted", "label": "Mounted", "img": "use_mounted",
     "desc": "Wall mount, pegboard (USSA / IKEA Skadis) or backbone"},
    {"id": "stationary", "label": "Stationary", "img": "use_stationary",
     "desc": "Base, feet and stationary handle on a backbone"},
    {"id": "mobile", "label": "Mobile", "img": "use_mobile",
     "desc": "Wheel kit (bushing, disks, TPU tyres, cover), base, feet"},
    {"id": "portable", "label": "Portable", "img": "use_portable",
     "desc": "Pull-out handle with lock, backbone and M16 rods"},
    {"id": "undertable", "label": "Under table", "img": "use_under_table",
     "desc": "Under Table Mount Roof screwed to the underside of a table"},
]

ROD_LEN = {"S": 248, "M": 338, "L": 414, "XL": 504}


def groups(files):
    """group files by name with ' Part N' stripped -> list of (key, [files])"""
    g = collections.OrderedDict()
    for p in files:
        k = re.sub(r"\s*Part\s*\d", "", stem(p))
        k = re.sub(r"\s+", " ", k).strip()
        g.setdefault(k, []).append(p)
    return g


def choice(cid, lab, files, img=None, sub=None, hwl=None, when=None, thumb=None, default=False):
    c = {"id": cid, "label": lab, "files": files}
    if sub:
        c["sub"] = sub
    if img:
        c["img"] = img
    if hwl:
        c["hw"] = hwl
    if when:
        c["when"] = when
    if thumb is not None:
        c["thumb"] = thumb
    if default:
        c["default"] = True
    return c


def mode_steps(letter, depth, heights, has_utm, kind):
    """Steps that depend on the chosen usage mode; letter is S/M/L/XL."""
    steps = []
    L = letter
    rod = ROD_LEN[L]

    def base_files():
        out = [p for p in ALL if p.startswith("03. MODIFICATIONS/Base/%s/" % L) and os.path.basename(p).startswith("%s%d " % (L, depth))]
        return out

    bf = base_files()
    base_choices = [choice("none", "No base", [], default=True, thumb=False)]
    whole = [p for p in bf if "Whole" in p]
    parts = [p for p in bf if "Part" in p]
    single = [p for p in bf if "Whole" not in p and "Part" not in p]
    rodhw = hw("M16 rod, cut to %d mm" % rod, 1, "per %s base" % L, "manual p.3 hardware list")
    if single:
        base_choices.append(choice("base", "%s%d Base" % (L, depth), [F(p, 1) for p in single], hwl=[rodhw]))
    if whole:
        base_choices.append(choice("whole", "%s%d Base (whole)" % (L, depth), [F(p, 1) for p in whole],
                                   sub="One piece, needs a large printer bed", hwl=[rodhw]))
    if parts:
        base_choices.append(choice("split", "%s%d Base (2 parts)" % (L, depth), [F(p, 1) for p in sorted(parts)],
                                   sub="Split for smaller beds", hwl=[rodhw]))
    bc = [p for p in ALL if p == "03. MODIFICATIONS/Base/Base Connector.stl"]
    base_step = {"id": "base", "title": "Base (printed tower foot)", "kind": "radio",
                 "help": "Manual p.4-8: the base takes the M16 rod and the backbone. Manual note: use a 2F module right after the base and before the roof.",
                 "choices": base_choices, "when": {"mode": ["stationary", "mobile", "portable"]}}
    if bc and len(base_choices) > 1:
        for c in base_choices[1:]:
            c["files"] = c["files"] + [F(bc[0], None, "Base Connector; qty not in manual")]
    steps.append(base_step)

    # backbone ------------------------------------------------------------
    def bb(h):
        return [p for p in ALL if p.startswith("03. MODIFICATIONS/Backbone/")
                and os.path.basename(p) in ("%s%s Backbone.stl" % (L, h),)]
    ub = lambda h: [p for p in ALL if p == "03. MODIFICATIONS/Backbone/Universal %s Backbone.stl" % h]
    conn = lambda h: [p for p in ALL if p == "03. MODIFICATIONS/Backbone/Connector for Modules %s.stl" % h]
    bbchoices = [choice("none", "No backbone", [], default=True, thumb=False)]
    for h in ("1F", "2F"):
        if h not in heights and not (h == "1F" and "1F" in heights):
            pass
    for h in ("1F", "2F"):
        if h not in heights:
            continue
        sz = bb(h) if L != "L" else bb(h)
        if sz:
            bbchoices.append(choice("bb_" + h, "%s%s Backbone" % (L, h), [F(p, 1) for p in sz] + [F(p, None, "qty not in manual") for p in conn(h)],
                                    sub="Size-specific backbone",
                                    hwl=[hw("M4 60-100 mm bolt", 4, "per backbone board", "manual p.3")], when={"height": [h]}))
        u = ub(h)
        if u:
            bbchoices.append(choice("ubb_" + h, "Universal %s Backbone" % h, [F(p, 1) for p in u] + [F(p, None, "qty not in manual") for p in conn(h)],
                                    sub="Fits any size",
                                    hwl=[hw("M4 60-100 mm bolt", 4, "per backbone board", "manual p.3")], when={"height": [h]}))
    if len(bbchoices) > 1:
        steps.append({"id": "backbone", "title": "Backbone", "kind": "radio", "choices": bbchoices,
                      "help": "Manual p.9-11: the backbone joins modules and attaches to the base. Only 1F and 2F backbones exist (no 4F).",
                      "when": {"mode": ["mounted", "stationary", "portable"]}})

    # mounted ----------------------------------------------------------------
    wm = []
    for h in heights:
        w = [p for p in ALL if p == "03. MODIFICATIONS/Wall Mounts/%s%s Wall Mount.stl" % (L, h)]
        sec = [p for p in ALL if p == "03. MODIFICATIONS/Wall Mounts/Wall Mount Second Part.stl"]
        if w:
            wm.append(choice("wm_" + h, "%s%s Wall Mount" % (L, h), [F(w[0], 1)] + [F(sec[0], None, "Second part fixed to the wall; qty not in manual (one per mount)")] if sec else [F(w[0], 1)],
                             sub="Includes wall-side second part. Manual p.2: keep one full-size mount per module size as template; 1F mounts can't be used as templates",
                             when={"height": [h]},
                             hwl=[hw("Wall anchors / wood screws (not specified)", None, "per wall mount", "manual p.6 - size not in manual")]))
    mount_choices = [choice("none", "None", [], default=True, thumb=False)] + wm
    for style, folder in (("ussa", "USSA Pegboard"), ("ikea", "IKEA Skadis Pegboard")):
        for h in ("1F", "2F"):
            if h not in heights:
                continue
            p = "03. MODIFICATIONS/Pegboard Attachment/%s/%s%s.stl" % (folder, L, h)
            if p in ALL:
                mount_choices.append(choice("peg_%s_%s" % (style, h), "%s %s%s attachment" % ("USSA pegboard" if style == "ussa" else "IKEA Skadis pegboard", L, h),
                                            [F(p, 1)], sub="Mounts to a backbone (choose a backbone above)", when={"height": [h]},
                                            hwl=[hw("M4 40 mm bolt", 4, "per pegboard board", "manual p.3")]))
    steps.append({"id": "mount", "title": "Wall mount / pegboard", "kind": "radio", "choices": mount_choices,
                  "when": {"mode": ["mounted"]}})

    # stationary ----------------------------------------------------------------
    feet = [p for p in ALL if p == "03. MODIFICATIONS/Feet/%s Feet.stl" % L]
    if feet:
        steps.append({"id": "feet", "title": "Feet", "kind": "radio",
                      "help": "Foot count is not stated in the manual - set it to match your build.",
                      "choices": [choice("none", "No feet", [], default=True, thumb=False),
                                  choice("feet", "%s Feet" % L, [F(feet[0], 4, "qty set by you (manual: not stated)")],
                                         hwl=[hw("M6 90 mm bolt", 2, "per foot", "manual p.3 (x2 per foot)")])],
                      "when": {"mode": ["stationary", "mobile"]},
                      "qty": {"label": "Feet quantity", "default": 4, "min": 1, "max": 16}})
    sh = [p for p in ALL if p == "03. MODIFICATIONS/Stationary Handle/%s Stationary Handle.stl" % L]
    if sh:
        steps.append({"id": "shandle", "title": "Stationary handle", "kind": "radio",
                      "help": "Manual p.12: fit the stationary handle on the far side of the backbone before the backbone goes on the module.",
                      "choices": [choice("none", "No handle", [], default=True, thumb=False),
                                  choice("sh", "%s Stationary Handle" % L, [F(sh[0], 1)],
                                         hwl=[hw("M4 60 mm bolt", 8, "per static handle", "manual p.3")])],
                      "when": {"mode": ["stationary"]}})

    # mobile -----------------------------------------------------------------------
    wheel = {}
    for n in ("Bushing", "Disk", "Tyre (TPU)", "Cover", "Jig"):
        p = "03. MODIFICATIONS/Wheels/%s.stl" % n
        if p in ALL:
            wheel[n] = p
    if wheel:
        wf = []
        for n in ("Bushing", "Disk", "Tyre (TPU)", "Cover"):
            note = "qty per wheel not stated; scaled by wheel count" if n != "Tyre (TPU)" else "print in TPU (7H, bambulab TPU standard settings); qty per wheel not stated"
            wf.append(F(wheel[n], 1, note))
        wf.append(F(wheel["Jig"], 1, "print aid for pressing bushings onto the rod"))
        steps.append({"id": "wheels", "title": "Wheel kit", "kind": "radio",
                      "help": "Manual p.3-6, 17: bushings via jig, 6205ZZ bearings, SCSAW stoppers, TPU tyre, cover. Holes for casters are M8 - check casters before buying.",
                      "choices": [choice("none", "No wheels", [], default=True, thumb=False),
                                  choice("wheels", "Wheel kit (Bushing, Disk, Tyre, Cover + Jig)", wf, thumb=wheel["Disk"],
                                         hwl=[hw("M4 25 mm bolt", 6, "per wheel", "manual p.3"),
                                              hw("6205ZZ bearing (25d/52D/15 mm)", 1, "per wheel", "manual p.3 (diagram shows bearings on both sides - verify)"),
                                              hw("SCSAW stopper (16d/35D/10 mm)", 1, "per wheel", "manual p.3")]),
                                  choice("casters", "Use 4 bought casters instead", [], thumb=False,
                                         hwl=[hw("M8 bolt for casters (length not in manual)", 4, "casters mode", "manual p.17 'insert 4 casters with M8 bolts'")])],
                      "when": {"mode": ["mobile"]},
                      "qty": {"label": "Number of wheels", "default": 4, "min": 1, "max": 8,
                              "appliesTo": ["wheels"], "note": "Caster mode in the manual uses 4; wheel count is otherwise not stated"}})

    # portable --------------------------------------------------------------------
    po = [p for p in ALL if p == "03. MODIFICATIONS/Pull-out Handle/%s Pull-out Handle.stl" % L]
    lock = [p for p in ALL if p.startswith("03. MODIFICATIONS/Backbone/") and "Pull-out Handle Lock" in p
            and (os.path.basename(p).startswith(L + " ") or "Universal" in p)]
    knobs = [p for p in ALL if "Handle Lock Knob" in p]
    if po:
        c = []
        c.append(choice("none", "No pull-out handle", [], default=True, thumb=False))
        pf = [F(po[0], 1)]
        hwp = [hw("M6 30 mm flat bolt", 4, "per pull-out handle", "manual p.3"),
               hw("M6 35 mm hex bolt", 2, "per pull-out handle", "manual p.3 list (steps text says M4 35 - verify)"),
               hw("M6x8x8 heat insert", 2, "per pull-out handle", "manual p.3"),
               hw("M16 rod cut to tower height", 2, "per pull-out handle", "manual p.3 / p.14")]
        sized = [p for p in lock if "Universal" not in p]
        univ = [p for p in lock if "Universal" in p]
        if sized:
            c.append(choice("po_sized", "%s Pull-out Handle + %s lock" % (L, L), pf + [F(x, 1) for x in sized] + [F(k, 1) for k in knobs], thumb=po[0], hwl=hwp))
        if univ:
            c.append(choice("po_univ", "%s Pull-out Handle + Universal lock" % L, pf + [F(x, 1) for x in univ] + [F(k, 1) for k in knobs], thumb=po[0], hwl=hwp))
        steps.append({"id": "pullout", "title": "Pull-out handle", "kind": "radio",
                      "help": "Manual p.13-14: heat-insert in the knob, Hex bolts tighten the lock, M16 rods cut to tower height and tapped for M6.",
                      "choices": c, "when": {"mode": ["portable"]}})
    return steps


def finish_steps(steps):
    return steps


HEIGHT_SUB = {"1F": "Single floor", "2F": "Double height (2 x 1F)", "4F": "Quad height (4 x 1F)"}


def height_thumb(own, h):
    """Preview for a height card: the module shell of that height (None -> no image)."""
    for p in own:
        if "Module" in os.path.basename(p) and height_of(p) == h:
            return p
    return False


def make_drawer(prefix, code, famroot):
    letter, depth, sq = split_family(code)
    fam_dir = "%s/%s" % (famroot, code)
    own = under(fam_dir + "/")
    L2 = sq
    note = None
    # compat source for ² families that only contain modules
    src_dir = fam_dir
    if sq:
        base_letter_root = D_ROOTS[letter]
        src_dir = "%s/%s%d" % (base_letter_root, letter, depth)
        note = ("The archive's %s folder contains modules only. Box, baseplate and roof choices are therefore taken from the "
                "matching %s%d family by letter+depth (inferred, please verify fit)." % (code, letter, depth))
    fam_files = under(src_dir + "/") if sq else own
    modules = [p for p in own if "/Modules/" in p or p.startswith(fam_dir + "/") and "Module" in os.path.basename(p)]
    boxes = [p for p in fam_files if "/Boxes/" in p]
    bases = [p for p in fam_files if "/Gridfinity Baseplate/" in p]
    roofs = [p for p in fam_files if "/Roofs/" in p]
    heights = sorted({height_of(p) for p in modules if height_of(p)})
    # Facades
    fac_root = D_ROOTS[letter] if not sq else D_ROOTS[letter]
    if letter == "XL":
        facades = [p for p in ALL if p == "01. DRAWERS/05. XL Families/XL Facade 1F.stl"]
    else:
        facades = under(D_ROOTS[letter] + "/Facades/")
    steps = []

    steps.append({"id": "height", "title": "Height", "kind": "radio",
                  "help": "1F, 2F and 4F only - no 3F, to avoid gaps (manual p.6).",
                  "choices": [choice(h, h, [], default=(h == heights[0]), thumb=height_thumb(own, h), sub=HEIGHT_SUB[h]) for h in heights]})

    # interior
    inter = [choice("empty", "Empty drawer", [], img="interior_empty_drawer", sub="Plain box, no insert", default=True, thumb=False)]
    gb = []
    if bases:
        gb = [choice("gb_%s" % i, label(p), [F(p, 1)], img="interior_gridfinity_base_drawer", sub="Gridfinity baseplate inside the box") for i, p in enumerate(bases)]
    gd = []
    for hh, folder in (("20mm", "20MM TALL"), ("34.5mm", "34.5MM TALL (full height of 1F drawers)"), ("82.5mm", "82.5MM TALL (full height of 2F drawers)")):
        fl = [p for p in ALL if p.startswith("01. DRAWERS/07. Universal/Grid Dividers/%s/" % folder)]
        gd.append((hh, fl))
    steps.append({"id": "interior", "title": "Interior", "kind": "radio",
                  "help": "Manual p.9: empty drawer, Gridfinity base, or Gridfinity base with grid dividers.",
                  "choices": inter + gb + [choice("gridwithdiv", "Gridfinity base + grid dividers", [], img="interior_grid_dividers",
                                                   sub="Pick a baseplate and divider set below", thumb=False)] if bases else inter})
    if bases:
        bg = [sorted(g) for g in groups(bases).values()]
        plain_i = next((i for i, g in enumerate(bg) if not re.search(r"handle", stem(g[0]), re.I) or re.search(r"no[_ ]handle", stem(g[0]), re.I)), 0)
        steps.append({"id": "gridbase", "title": "Gridfinity baseplate", "kind": "radio",
                      "choices": [choice("g%i" % i, re.sub(r"\s*Part \d", "", label(g[0])) + (" (2 parts)" if len(g) > 1 else ""), [F(p, 1) for p in g], img="interior_gridfinity_base_drawer", thumb=g[0], default=(i == plain_i), sub=("Plain, no handles" if i == plain_i else None)) for i, g in enumerate(bg)],
                      "when": {"interior": ["gridwithdiv"]}})
        # drop the per-baseplate choices from the main interior step (baseplate chosen in its own step)
        steps[1]["choices"] = inter + [choice("gridbase", "Gridfinity baseplate (no dividers)", [], img="interior_gridfinity_base_drawer", sub="Baseplate included; choose its handle variant below", thumb=False),
                                       choice("gridwithdiv", "Gridfinity baseplate + grid dividers", [], img="interior_grid_dividers", sub="Baseplate included (plain preselected) plus a divider set", thumb=False)]
        steps.pop(2)
        steps.append({"id": "gridbase", "title": "Gridfinity baseplate", "kind": "radio",
                      "help": "The baseplate is always included with this interior. The plain version (no handles) is preselected; choose a 1-handle or 2-handle version if you want one.",
                      "choices": [choice("g%i" % i, re.sub(r"\s*Part \d", "", label(g[0])) + (" (2 parts)" if len(g) > 1 else ""), [F(p, 1) for p in g], img="interior_gridfinity_base_drawer", thumb=g[0], default=(i == plain_i), sub=("Plain, no handles" if i == plain_i else None)) for i, g in enumerate(bg)],
                      "when": {"interior": ["gridbase", "gridwithdiv"]}})
        divchoices = []
        for hh, fl in gd:
            divchoices.append(choice("d" + hh.replace(".", "_"), "Grid dividers %s tall" % hh, [F(p, None, "grid divider piece; count per set not in manual (file name suffix x# is the size/qty as named)") for p in fl],
                                     img="interior_grid_dividers", sub="%d pieces. Full height: 34.5 mm for 1F, 82.5 mm for 2F" % len(fl),
                                     thumb=fl[0] if fl else False))
        steps.append({"id": "griddiv", "title": "Grid dividers", "kind": "radio", "choices": divchoices,
                      "when": {"interior": ["gridwithdiv"]}})

    # box
    for h in heights:
        pass
    bchoices = []
    for h in heights:
        bh = [p for p in boxes if height_of(p) == h]
        extras = [p for p in boxes if height_of(p) is None]
        for k, g in groups(bh).items():
            bchoices.append(choice("box_" + h, label(g[0]).replace(" Part 1", "") + (" (2 parts)" if len(g) > 1 else ""),
                                   [F(p, 1) for p in sorted(g)] + [F(e, 1, "companion part") for e in extras], when={"height": [h]},
                                   thumb=g[0]))
    # L2 fallback compat: box for letter+depth
    if bchoices:
        steps.append({"id": "box", "title": "Drawer box", "kind": "radio", "required": True, "choices": bchoices})
    mchoices = []
    for h in heights:
        mm = [p for p in modules if height_of(p) == h]
        if mm:
            mchoices.append(choice("mod_" + h, label(mm[0]), [F(p, 1) for p in sorted(mm)], when={"height": [h]}, thumb=mm[0]))
    steps.append({"id": "module", "title": "Module (outer shell)", "kind": "radio", "required": True, "choices": mchoices})

    # roofs
    rc = []
    seen = {}
    ROOFMAP = [("Grid Roof", "grid", "roof_gridfinity", "Gridfinity roof"), ("Table Roof", "table", "roof_table", "Table roof"),
               ("Heawyweight Roof", "heavy", "roof_heavyweight", "Heavyweight roof"), ("Bowl Roof", "bowl", "roof_bowl", "Bowl roof"),
               ("Under Table Mount Roof", "utm", "roof_under_table_mount", "Under table mount roof")]
    ins = [p for p in ALL if p.startswith("01. DRAWERS/07. Universal/Heawyweight Roof")]
    th = [p for p in ALL if p.startswith("01. DRAWERS/07. Universal/Top Handle")]
    for key, rid, img, lab in ROOFMAP:
        rf = [p for p in roofs if key in p]
        if not rf:
            continue
        extra = []
        hwl = []
        if rid == "heavy":
            extra = [F(p, 1) for p in ins]
            hwl = [hw("M6 50 mm bolt", 2, "per roof handle", "manual p.3 / p.18")]
        if rid == "grid":
            extra = [F(p, 1, "optional top handle") for p in th]
        rc.append(choice(rid, lab, [F(p, 1) for p in rf] + extra, img=img, hwl=hwl, thumb=rf[0],
                         when=({"mode": ["undertable"]} if rid == "utm" else {"mode": ["mounted", "stationary", "mobile", "portable"]})))
    steps.append({"id": "roof", "title": "Roof type", "kind": "radio", "required": True, "help": "Manual p.10: five roof types.", "choices": rc})

    # facade + lock
    fh = []
    for h in heights:
        ff = [p for p in facades if height_of(p) == h or (letter == "XL" and h == "1F")]
        if ff:
            fh.append(choice("fac_" + h, label(ff[0]), [F(p, 1) for p in ff], when={"height": [h]}, thumb=ff[0],
                             hwl=[hw("M4 14 mm bolt", 4 if h == "1F" else 6, "facade to box", "manual p.18 (4 for 1F, 6 for 2F/4F)")]))
    if fh:
        steps.append({"id": "facade", "title": "Facade", "kind": "radio", "required": True, "choices": fh,
                      "help": "Facade bolts to the box with M4 14 mm bolts (x4 for 1F, x6 for 2F/4F)."})

    U = "01. DRAWERS/07. Universal/"
    klhw = [hw("Key lock (cylinder, not printed; no model/size given in manual)", 1, "per drawer", "manual p.11 naming diagram")]
    keyc = [choice("key", "Key", [F(U + "Key (Turn On Supports).stl", 1), F(U + "Key Cap.stl", 1, "press onto key with a mallet")], thumb=U + "Key (Turn On Supports).stl", default=True, hwl=klhw),
            choice("hidden", "Hidden key", [F(U + "Hidden Key (Turn On Supports).stl", 1), F(U + "Hidden Key Part 2 (Turn on Supports).stl", 1), F(U + "Key Cap.stl", 1, "press onto key with a mallet")],
                   thumb=U + "Hidden Key (Turn On Supports).stl", hwl=klhw)]
    steps.append({"id": "keytype", "title": "Key lock", "kind": "radio", "choices": keyc, "help": "Key Lock is inserted in the facade; a Key Cap goes on the key (drawer assembly p.1)."})

    # fixed parts
    rg = [p for p in ALL if p == U + "Geared Rails/%s Rails.stl" % letter]
    rn = []
    pref = ("XL%d" % depth) if letter == "XL" else ("x%d" % depth)
    for suf in ("Runner Guides", "Runner Slides"):
        rn += [p for p in ALL if p == U + "Runners/%s %s.stl" % (pref, suf)]
    rn += [U + "Runners/Runner Stopper.stl"]
    fixed = []
    fixed += [F(p, 2, "top and bottom geared rail (drawer assembly p.4)") for p in rg]
    fixed += [F(p, None, "qty not in manual; one file as named x%d" % depth if p.endswith("Guides.stl") or p.endswith("Slides.stl") else "qty not in manual (manual says 'stoppers' plural)") for p in rn]
    fixed += [F(U + "Springs.stl", None, "qty not in manual"), F(U + "Latch.stl", 1, "pushed in last, assembly p.8"),
              F(U + "Facade Cap.stl", 1), F(U + "Label.stl", 1, "slide into facade; write text with your slicer text tool")]
    steps.append({"id": "fixed", "title": "Included automatically", "kind": "fixed",
                  "help": "These parts are needed on every drawer and are added to your build for you. Nothing to choose here: springs, latch, runner slides and guides, runner stopper, geared rails, facade cap and label.",
                  "files": fixed})
    if sq:
        acc = [p for p in ALL if p.startswith(U + "L² Accessories/x%d " % depth)]
        if acc:
            steps.append({"id": "acc", "title": "Included automatically: L² accessories", "kind": "fixed",
                          "help": "Accessory pair named for depth x%d in the Universal folder (inferred match by depth)." % depth,
                          "files": [F(p, None, "qty not in manual") for p in acc]})
    ms = [p for p in ALL if p == U + "Manual Supports/x%d.stl" % depth]
    if ms:
        steps.append({"id": "sup", "title": "Manual supports", "kind": "radio",
                      "help": "Manual p.20: optional manual supports for a more stable print of tall prints; remove before assembly.",
                      "choices": [choice("none", "No manual supports", [], default=True, thumb=False),
                                  choice("sup", "Manual supports x%d" % depth, [F(ms[0], None, "qty not in manual")], thumb=ms[0])]})
    steps += mode_steps(letter, depth, heights, any("utm" == c["id"] for c in rc), "drawer")
    return {"id": "D-" + code, "type": "drawer", "family": code, "letter": letter, "depth": depth, "sq": sq,
            "heights": heights, "steps": steps, "note": note, "sizeImg": "size_" + letter,
            "modes": ["mounted", "stationary", "mobile", "portable"] + (["undertable"] if any(c["id"] == "utm" for c in rc) else [])}


def make_sustainer(code, famroot):
    letter, depth, _ = split_family(code)
    fam_dir = "%s/%s" % (famroot, code)
    own = under(fam_dir + "/")
    modules = [p for p in own if "/Modules/" in p]
    roofs = [p for p in own if "/Roof" in p]
    heights = sorted({height_of(p) for p in modules if height_of(p)})
    U = "02. SUSTAINERS/05. Universal/"
    steps = []
    steps.append({"id": "height", "title": "Height", "kind": "radio",
                  "help": "1F, 2F and 4F only - no 3F, to avoid gaps (manual p.6).",
                  "choices": [choice(h, h, [], default=(h == heights[0]), thumb=height_thumb(own, h), sub=HEIGHT_SUB[h]) for h in heights]})

    # interior
    kinds = collections.OrderedDict()
    for p in modules:
        n = os.path.basename(p).lower()
        k = "flat" if "flat" in n else "dividers" if "divider" in n else "sealed" if "sealed" in n else "std"
        kinds.setdefault(k, []).append(p)
    ibase = []
    IN = []
    bp_folder = {"S": "01. S", "M": "02. M", "L": "03. L", "XL": "04. XL"}[letter]
    bps = [p for p in ALL if p.startswith(U + "Baseplates/%s/" % bp_folder) and ("%s%d " % (letter, depth) in os.path.basename(p))]
    if "std" in kinds:
        IN.append(choice("std", "Standard module (empty)", [], img="interior_flat_sustainer", default=True, thumb=False))
        if bps:
            IN.append(choice("grid", "Gridfinity base", [], img="interior_gridfinity_base_sustainer", sub="Module with Gridfinity baseplate", thumb=False))
        IN.append(choice("div", "Dividers", [], img="interior_dividers_sustainer", sub="Module plus divider pieces", thumb=False))
    else:
        if "flat" in kinds:
            IN.append(choice("flat", "Flat", [], img="interior_flat_sustainer", default=True, thumb=False))
            if bps:
                IN.append(choice("grid", "Gridfinity base", [], img="interior_gridfinity_base_sustainer", sub="Flat module + Gridfinity baseplate", thumb=False))
        if "dividers" in kinds:
            IN.append(choice("div", "Dividers", [], img="interior_dividers_sustainer", sub="Dividers module + divider pieces", thumb=False))
        if "sealed" in kinds:
            IN.append(choice("sealed", "Sealed", [], img="interior_sealed_sustainer", sub="Sealed module + seal dividers", thumb=False))
    steps.append({"id": "interior", "title": "Interior", "kind": "radio",
                  "help": "Manual p.9: flat, Gridfinity base, dividers or sealed.", "choices": IN})

    # module (depends on interior)
    mch = []
    for h in heights:
        for k, ps in kinds.items():
            sel = [p for p in ps if height_of(p) == h]
            if not sel:
                continue
            inter = {"std": ["std", "grid", "div"], "flat": ["flat", "grid"], "dividers": ["div"], "sealed": ["sealed"]}[k]
            mch.append(choice("mod_%s_%s" % (h, k), label(sel[0]).strip(), [F(p, 1) for p in sel], when={"height": [h], "interior": inter}, thumb=sel[0]))
    steps.append({"id": "module", "title": "Module (outer shell)", "kind": "radio", "required": True, "choices": mch})

    if bps:
        steps.append({"id": "baseplate", "title": "Gridfinity baseplate", "kind": "radio",
                      "choices": [choice("bp%d" % i, label(p), [F(p, 1)], thumb=p) for i, p in enumerate(bps)],
                      "when": {"interior": ["grid"]}})

    # dividers
    dv = []
    if letter in ("S", "M"):
        for h in heights:
            dp = [p for p in ALL if p == U + "Dividers/%s Dividers/%s%s Divider.stl" % (letter, letter, h)]
            if dp:
                dv.append(choice("dv_" + h, label(dp[0]), [F(p, None, "qty not in manual") for p in dp], when={"height": [h], "interior": ["div"]}, thumb=dp[0]))
    elif letter == "L":
        for h in heights:
            dep = [p for p in ALL if p == U + "Dividers/L Depth Dividers/L%d-%s Depth Divider.stl" % (depth, h)]
            wid = [p for p in ALL if p == U + "Dividers/L Width Dividers/L-%s Width Divider.stl" % h]
            if dep or wid:
                dv.append(choice("dv_" + h, "L%d-%s depth + L-%s width dividers" % (depth, h, h), [F(p, None, "qty not in manual") for p in dep + wid],
                                 when={"height": [h], "interior": ["div"]}, thumb=(dep + wid)[0]))
    else:
        dep = [p for p in ALL if p == U + "Dividers/XL Depth Dividers/XL%d Depth Divider.stl" % depth]
        wid = [p for p in ALL if p == U + "Dividers/XL Width Divider.stl"]
        if dep or wid:
            dv.append(choice("dv_xl", "XL%d depth + XL width dividers" % depth, [F(p, None, "qty not in manual") for p in dep + wid],
                             when={"interior": ["div"]}, thumb=(dep + wid)[0]))
    if dv:
        steps.append({"id": "dividers", "title": "Dividers", "kind": "radio", "choices": dv,
                      "help": "Insert dividers the way you need (assembly p.7). Remove manual supports before filling."})
    sd = []
    if letter == "L":
        for h in heights:
            sp = [p for p in ALL if p == U + "Dividers/L Seal Dividers/L-%s Seal Divider.stl" % h]
            if sp:
                sd.append(choice("sd_" + h, label(sp[0]), [F(p, None, "qty not in manual") for p in sp], when={"height": [h], "interior": ["sealed"]}, thumb=sp[0]))
    if letter == "XL":
        sp = [p for p in ALL if p.startswith(U + "Dividers/XL Seal Divider")]
        if sp:
            sd.append(choice("sd_xl", "XL seal dividers (centre + sides)", [F(p, None, "qty not in manual") for p in sp], when={"interior": ["sealed"]}, thumb=sp[0]))
    if sd:
        steps.append({"id": "seal", "title": "Seal dividers", "kind": "radio", "choices": sd, "required": True})

    # roof
    if roofs:
        whole = [p for p in roofs if "Whole" in p]
        parts = [p for p in roofs if "Part" in p or "Connector" in p]
        other = [p for p in roofs if p not in whole and p not in parts]
        rc = []
        if other:
            rc.append(choice("roof", "%s%d Roof" % (letter, depth), [F(p, 1) for p in other], img="roof_gridfinity" if False else None, thumb=other[0], default=True))
        if whole:
            rc.append(choice("whole", "%s%d Roof (whole)" % (letter, depth), [F(p, 1) for p in whole], thumb=whole[0], default=not other))
        if parts:
            rc.append(choice("split", "%s%d Roof (split in 2 + connector)" % (letter, depth), [F(p, 1) for p in sorted(parts)], thumb=parts[0],
                             sub="For smaller print beds"))
        steps.append({"id": "roof", "title": "Roof", "kind": "radio", "required": True, "choices": rc,
                      "help": "Sustainer roofs hinge on the module (manual p.12). Table, bowl, heavyweight and under-table roofs exist only for drawers."})

    # facade
    fac = []
    for h in heights:
        ff = [p for p in under(famroot + "/Facades/") if height_of(p) == h]
        if letter == "XL":
            ff = [p for p in ALL if p == "02. SUSTAINERS/04. XL Families/XL1F Facade.stl"]
        if ff:
            fac.append(choice("fac_" + h, label(ff[0]), [F(p, 1) for p in ff], when={"height": [h]}, thumb=ff[0]))
    if fac:
        steps.append({"id": "facade", "title": "Facade", "kind": "radio", "required": True, "choices": fac})

    # lock
    lk = U + "Locks/"
    lockA = [F(lk + "LOCK HOLDER.stl", 1), F(lk + "LOCK INNER PART.stl", 1), F(lk + "1 SET OF PINS FOR 1 LOCK.stl", 1, "small + big pins")]
    lc = []
    for h in heights:
        outer = lk + ("LOCK OUTER PART 1F.stl" if h == "1F" else "LOCK OUTER PART 2-4F.stl")
        lc.append(choice("lock_" + h, "Lock set (%s outer)" % ("1F" if h == "1F" else "2-4F"), lockA + [F(outer, 1)], when={"height": [h]}, thumb=outer))
    steps.append({"id": "lock", "title": "Lock", "kind": "radio", "required": True, "choices": lc,
                  "help": "Assembly p.1-2: lock inner part to holder with small pins, outer part with big pins, fix to facade with M4 14 mm bolts."})

    # hinges + rods + label (fixed)
    H = U + "Hinges/"
    fixed = []
    if letter in ("S", "M"):
        top = H + "%s Hinge Top.stl" % letter
        for h in heights:
            bot = H + ("S-M 1F Hinge.stl" if h == "1F" else "S-M 2-4F Hinge.stl")
            pass
        fixed.append(F(top, 1, "hinge on roof"))
        rods = U + "Rods/S-M Rods.stl"
    else:
        fixed.append(F(H + "L-XL Hinge Top.stl", 1, "hinge on roof"))
        rods = U + "Rods/L-XL Rods.stl"
    fixed.append(F(rods, None, "two rods per sustainer (assembly p.4); qty of files not stated"))
    fixed.append(F(U + "Label for Sustainers.stl", 1))
    steps.append({"id": "fixed", "title": "Included automatically", "kind": "fixed",
                  "help": "These parts are needed on every sustainer and are added to your build for you. Nothing to choose here: top hinge, rods and label. The bottom hinge follows the height you chose (next section).",
                  "files": fixed})
    hbc = []
    for h in heights:
        if letter in ("S", "M"):
            b = H + ("S-M 1F Hinge.stl" if h == "1F" else "S-M 2-4F Hinge.stl")
        else:
            b = H + ("L-XL 1F Hinge.stl" if h == "1F" else "L 2-4F Hinge.stl")
        if b in ALL:
            hbc.append(choice("hinge_" + h, label(b), [F(b, 1, "bottom hinge on module")], when={"height": [h]}, thumb=b, default=True))
    steps.append({"id": "hinge", "title": "Bottom hinge", "kind": "radio", "required": True, "choices": hbc})
    steps.append({"id": "hwfixed", "title": "Included automatically: fasteners", "kind": "hwonly",
                  "hw": [hw("M4 14 mm bolt", 16, "per module", "manual p.3 / p.17"),
                         hw("M4 10 mm bolt", 8, "per module", "manual p.3 / p.17"),
                         hw("M4 20 mm bolt", 7, "per module", "manual p.3 / p.17")]})
    steps += mode_steps(letter, depth, heights, False, "sustainer")
    return {"id": "S-" + code, "type": "sustainer", "family": code, "letter": letter, "depth": depth, "sq": False,
            "heights": heights, "steps": steps, "note": None, "sizeImg": "size_" + letter,
            "modes": ["mounted", "stationary", "mobile", "portable"]}


def main():
    variants = []
    for letter, root in D_ROOTS.items():
        for d in sorted(os.listdir(os.path.join(PARTS, root))):
            if re.match(r"^(XL|L|M|S)\d²?$", d):
                variants.append(make_drawer("D", d, root))
    for letter, root in S_ROOTS.items():
        for d in sorted(os.listdir(os.path.join(PARTS, root))):
            if re.match(r"^(XL|L|M|S)\d$", d):
                variants.append(make_sustainer(d, root))
    # drawer-specific hardware for the always-included drawer facade bolts is attached to the facade choices.
    for v in variants:
        mod = next((s for s in v["steps"] if s["id"] == "module"), None)
        v["hero"] = mod["choices"][0]["files"][0]["p"] if mod and mod["choices"] else None
        v["heroImg"] = "type_drawers" if v["type"] == "drawer" else "type_sustainers"
    data = {"modes": MODES, "variants": variants, "generated": "build_catalog.py",
            "partsCount": len(ALL)}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    # sanity: every referenced file exists
    missing = set()
    for v in variants:
        for s in v["steps"]:
            for c in s.get("choices", []):
                for f in c["files"]:
                    if f["p"] not in ALL:
                        missing.add(f["p"])
            for f in s.get("files", []):
                if f["p"] not in ALL:
                    missing.add(f["p"])
    if missing:
        print("MISSING referenced files:", len(missing))
        for m in sorted(missing):
            print("  ", m)
    json.dump(data, open(OUT, "w"), ensure_ascii=False, indent=1)
    print("variants:", len(variants), "->", OUT)


if __name__ == "__main__":
    main()
