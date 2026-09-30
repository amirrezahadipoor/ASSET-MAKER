"""CLI: python -m assetmaker make|list|sheet (see README for full reference)."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .core import export
from .core.export import AssetResult, save_png, save_sheet
from .core.shapes import Canvas, dilate
from .qa import gates
from .recipes import catalog


def _composite_parts(parts: dict[str, Canvas]) -> Canvas:
    first = next(iter(parts.values()))
    out = Canvas(first.w, first.h)
    for _, p in parts.items():
        out.composite(p)
    return out


def build_asset(kind: str, seed: int, variant: int) -> tuple[AssetResult, dict]:
    """Generate one asset + its manifest dict (without qa attached)."""
    recipe = catalog.get(kind)
    res = recipe.fn(seed, variant)
    return res, {"recipe": recipe}


def export_asset(res: AssetResult, root: Path, run_qa: bool = True) -> dict:
    """Write all layers + manifest for one asset. Returns the manifest."""
    d = export.out_dir(root, res.category, res.kind, res.variant, res.seed)
    d.mkdir(parents=True, exist_ok=True)

    full = res.full()
    files: dict = {"full": None, "shadow": None, "parts": {}, "sheets": {}}

    def name(layer: str) -> str:
        return export.layer_filename(res.category, res.kind, res.variant,
                                     res.seed, layer)

    files["full"] = name("full")
    save_png(full, d / files["full"])
    files["shadow"] = name("shadow")
    save_png(res.shadow, d / files["shadow"])
    for pname, pc in res.parts.items():
        fn = name(f"part-{pname}")
        save_png(pc, d / fn)
        files["parts"][pname] = fn
    for anim_name, frames in res.sheets.items():
        fn = name(f"sheet-{anim_name}")
        save_sheet(frames, d / fn)
        files["sheets"][anim_name] = fn

    # rig recompose gate: rebuild full from SAVED part files + shadow file
    recomposed = Canvas(res.width, res.height)
    from PIL import Image
    import numpy as np

    sh_img = np.array(Image.open(d / files["shadow"]).convert("RGBA"))
    recomposed.buf = sh_img
    for pname in sorted(res.parts):
        p_img = np.array(Image.open(d / files["parts"][pname]).convert("RGBA"))
        m = p_img[..., 3] > 0
        recomposed.buf[m] = p_img[m]

    obj = _composite_parts(res.parts)
    obj_mask = obj.alpha_mask()

    qa = {"passed": True, "checks": {}}
    if run_qa:
        qa = gates.evaluate(res, full, obj_mask, recomposed=recomposed)

    palette = export.palette_for(res.colors_used)
    manifest = export.build_manifest(res, files, qa, palette)
    export.write_manifest(d / "manifest.json", manifest)
    return manifest


def cmd_make(args: argparse.Namespace) -> int:
    catalog.load_all()
    ok = True
    seeds = [args.seed] if args.seeds is None else list(
        range(args.seed, args.seed + args.seeds))
    for seed in seeds:
        res, _ = build_asset(args.kind, seed, args.variant)
        manifest = export_asset(res, Path(args.out), run_qa=not args.no_qa)
        qa = manifest["qa"]
        status = "PASS" if qa["passed"] else "FAIL"
        print(f"[{status}] {manifest['id']} -> {args.out}/{manifest['id']}/")
        if not qa["passed"]:
            ok = False
            for cname, c in qa["checks"].items():
                mark = "ok" if c["passed"] else "FAIL"
                print(f"    {mark:4} {cname}: {c['detail']}")
    return 0 if ok else 1


def cmd_list(_args: argparse.Namespace) -> int:
    catalog.load_all()
    for kind in sorted(catalog.REGISTRY):
        r = catalog.REGISTRY[kind]
        rig = "rigged" if r.has_rig else "static"
        print(f"{kind:12} {r.category:10} {rig:7} {r.doc}")
    return 0


def cmd_sheet(args: argparse.Namespace) -> int:
    """Contact sheet: N seeds side by side + a crop of the reference."""
    from PIL import Image

    catalog.load_all()
    recipe = catalog.get(args.kind)
    n = args.count
    thumbs: list[Image.Image] = []
    scale = 4
    cell = 0
    for i in range(n):
        res, _ = build_asset(args.kind, args.seed + i, args.variant)
        img = res.full().to_pil()
        img = img.resize((img.width * scale, img.height * scale),
                         Image.NEAREST)
        thumbs.append(img)
        cell = max(cell, img.width + 8)
    cell_h = max(t.height for t in thumbs) + 8

    ref_path = Path("reference/village.png")
    ref_crop = None
    if ref_path.exists():
        ref = Image.open(ref_path).convert("RGBA")
        # crop a nature/prop-rich corner of the reference for comparison
        cw, ch = min(360, ref.width), min(220, ref.height)
        ref_crop = ref.crop((130, 20, 130 + cw, 20 + ch))
        ref_crop = ref_crop.resize((ref_crop.width * 2, ref_crop.height * 2),
                                   Image.NEAREST)

    sheet_w = cell * n + (ref_crop.width + 12 if ref_crop else 0)
    sheet_h = max(cell_h, ref_crop.height if ref_crop else 0) + 8
    sheet = Image.new("RGBA", (sheet_w, sheet_h), (34, 30, 26, 255))
    for i, t in enumerate(thumbs):
        sheet.paste(t, (i * cell + 4, 4), t)
    if ref_crop:
        sheet.paste(ref_crop, (cell * n + 8, 4), ref_crop)

    out = Path(args.output or f"out/contact_sheet_{args.kind}.png")
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    print(f"contact sheet -> {out}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="assetmaker",
                                description="procedural pixel-art asset engine")
    sub = p.add_subparsers(dest="cmd", required=True)

    mk = sub.add_parser("make", help="generate one asset (all layers + manifest)")
    mk.add_argument("kind")
    mk.add_argument("--seed", type=int, default=42)
    mk.add_argument("--variant", type=int, default=1)
    mk.add_argument("--seeds", type=int, default=None,
                    help="render N consecutive seeds starting at --seed")
    mk.add_argument("--out", default="out")
    mk.add_argument("--no-qa", action="store_true")
    mk.set_defaults(fn=cmd_make)

    ls = sub.add_parser("list", help="list registered asset kinds")
    ls.set_defaults(fn=cmd_list)

    sh = sub.add_parser("sheet", help="render a contact sheet of N seeds")
    sh.add_argument("kind")
    sh.add_argument("--seed", type=int, default=42)
    sh.add_argument("--variant", type=int, default=1)
    sh.add_argument("--count", type=int, default=16)
    sh.add_argument("--output", default=None)
    sh.set_defaults(fn=cmd_sheet)

    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
