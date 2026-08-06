#!/usr/bin/env python3
"""Resize and recompress the images that index.html actually uses.

The source photographs are print-resolution (up to 5668x4049) but are displayed
at a few hundred CSS pixels, so the page was shipping ~9.4 MB of images. This
downscales each one to roughly twice its largest on-screen size — enough for a
2x/retina display, including the product lightbox — and re-encodes it.

Safety rules, in order:
  * never upscale: an image already smaller than its target is left at its size
  * never write a larger file: if re-encoding does not help, the original stays
  * EXIF orientation is applied before resizing, then metadata is dropped, so
    rotated photos cannot end up sideways

Everything it touches is committed to git, so `git checkout -- images/ favicon.ico`
restores the originals.

    python3 tools/optimise-images.py --dry-run   # report only, write nothing
    python3 tools/optimise-images.py             # apply
"""

import argparse
import io
import re
import sys
from pathlib import Path

try:
    from PIL import Image, ImageOps
except ImportError:
    sys.exit("Pillow is required:  pip install Pillow")

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "index.html"

# Long-edge budget in pixels. Product shots peak in the lightbox at roughly
# 436x581 CSS px, so 1200 covers a 2x display with room to spare.
PRODUCT_EDGE = 1200
JPEG_QUALITY = 80

# Files needing something other than the product-photo defaults.
OVERRIDES = {
    "images/rk_soap.jpeg": dict(edge=1200, quality=80),        # hero / LCP
    "images/soap_tshirt.jpeg": dict(edge=1100, quality=82),    # already small
    "images/logo-removebg.png": dict(edge=400),                # nav + apple-touch-icon
    "images/14 -  - 5X7-removebg-preview.png": dict(edge=500),  # collage cut-out
}


def referenced_images() -> list[str]:
    """Only touch images the page actually loads."""
    src = PAGE.read_text(encoding="utf-8")
    found = set(re.findall(r'<img[^>]+src="(images/[^"]+)"', src))
    found |= set(re.findall(r'href="(images/[^"]+)"', src))
    return sorted(found)


def encode(im: Image.Image, fmt: str, quality: int) -> bytes:
    buf = io.BytesIO()
    if fmt == "JPEG":
        im.convert("RGB").save(buf, "JPEG", quality=quality,
                               optimize=True, progressive=True)
    else:
        # keep alpha; try palette too, since flat logo art shrinks a lot
        best = None
        for candidate in (im, ):
            b = io.BytesIO()
            candidate.save(b, "PNG", optimize=True)
            best = b.getvalue()
        if im.mode == "RGBA":
            b = io.BytesIO()
            try:
                im.quantize(colors=256, method=Image.FASTOCTREE).save(b, "PNG", optimize=True)
                if len(b.getvalue()) < len(best):
                    best = b.getvalue()
            except Exception:
                pass
        return best
    return buf.getvalue()


def process(rel: str, dry_run: bool):
    path = ROOT / rel
    before = path.stat().st_size
    opts = OVERRIDES.get(rel, {})
    edge = opts.get("edge", PRODUCT_EDGE)
    quality = opts.get("quality", JPEG_QUALITY)

    with Image.open(path) as raw:
        fmt = "JPEG" if raw.format == "JPEG" else "PNG"
        im = ImageOps.exif_transpose(raw)
        if fmt == "PNG" and im.mode not in ("RGBA", "P", "LA"):
            im = im.convert("RGBA")
        w, h = im.size
        scale = min(edge / max(w, h), 1.0)          # never upscale
        new_size = (max(1, round(w * scale)), max(1, round(h * scale)))
        if scale < 1.0:
            im = im.resize(new_size, Image.LANCZOS)
        data = encode(im, fmt, quality)

    if len(data) >= before:                          # never write a bigger file
        return dict(rel=rel, before=before, after=before, dims=(w, h),
                    new_dims=(w, h), action="kept (re-encode was not smaller)")

    if not dry_run:
        path.write_bytes(data)
    return dict(rel=rel, before=before, after=len(data), dims=(w, h),
                new_dims=new_size, action="optimised")


def rebuild_favicon(dry_run: bool):
    """The .ico holds one uncompressed 256x201 bitmap (~200 KB) and is fetched on
    every page load. Rebuild it square at the three sizes browsers actually use."""
    ico = ROOT / "favicon.ico"
    before = ico.stat().st_size
    with Image.open(ROOT / "images/logo-removebg.png") as raw:
        src = raw.convert("RGBA")
    side = max(src.size)
    square = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    square.paste(src, ((side - src.size[0]) // 2, (side - src.size[1]) // 2))
    buf = io.BytesIO()
    square.save(buf, "ICO", sizes=[(16, 16), (32, 32), (48, 48)])
    data = buf.getvalue()
    if len(data) >= before:
        return dict(rel="favicon.ico", before=before, after=before,
                    dims=(0, 0), new_dims=(0, 0), action="kept")
    if not dry_run:
        ico.write_bytes(data)
    return dict(rel="favicon.ico", before=before, after=len(data),
                dims=src.size, new_dims=(48, 48), action="rebuilt square 16/32/48")


def sync_dimensions() -> int:
    """Rewrite width/height attributes to the images' real pixel sizes.

    These attributes reserve layout space and are what stops the page shifting
    while images load (CLS). A stale value is worse than none, so this must run
    after any resize."""
    src = PAGE.read_text(encoding="utf-8")
    changed = 0

    def fix(m):
        nonlocal changed
        tag, rel = m.group(0), m.group(1)
        path = ROOT / rel
        if not path.exists():
            return tag
        with Image.open(path) as im:
            w, h = im.size
        new = tag
        if 'width="' in new:
            new = re.sub(r'width="\d+"', f'width="{w}"', new)
            new = re.sub(r'height="\d+"', f'height="{h}"', new)
        if new != tag:
            changed += 1
        return new

    src = re.sub(r'<img[^>]+src="(images/[^"]+)"[^>]*>', fix, src)
    PAGE.write_text(src, encoding="utf-8")
    return changed


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="report without writing")
    args = ap.parse_args()

    rows = [process(r, args.dry_run) for r in referenced_images()]
    rows.append(rebuild_favicon(args.dry_run))

    kb = lambda n: n / 1024
    print(f"{'file':<44}{'before':>10}{'after':>10}{'saved':>9}  dimensions")
    print("-" * 100)
    for r in rows:
        saved = 1 - r["after"] / r["before"] if r["before"] else 0
        dims = (f'{r["dims"][0]}x{r["dims"][1]}' if r["dims"] != r["new_dims"]
                else f'{r["dims"][0]}x{r["dims"][1]} (unchanged)')
        arrow = f' -> {r["new_dims"][0]}x{r["new_dims"][1]}' if r["dims"] != r["new_dims"] else ""
        print(f'{r["rel"][:43]:<44}{kb(r["before"]):9.0f}K{kb(r["after"]):9.0f}K'
              f'{saved:8.0%}  {dims}{arrow}')

    tb, ta = sum(r["before"] for r in rows), sum(r["after"] for r in rows)
    print("-" * 100)
    print(f'{"TOTAL":<44}{kb(tb):9.0f}K{kb(ta):9.0f}K{1 - ta / tb:8.0%}'
          f'   ({tb / 1024 / 1024:.1f} MB -> {ta / 1024 / 1024:.1f} MB)')
    if args.dry_run:
        print("\n(dry run — nothing written)")
    else:
        n = sync_dimensions()
        print(f"\nindex.html: refreshed width/height on {n} <img> tag(s) so CLS stays at 0")
        print("If any image alt text changed, also run:  python3 tools/seo-sync.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
