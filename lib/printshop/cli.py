"""printshop — write a page, fit it, look at it, print it."""
from __future__ import annotations

import argparse
import io
import re
import shutil
import subprocess
import sys
from pathlib import Path

from . import doc as _doc
from .fit import solve

ROOT = Path(__file__).resolve().parents[2]


# ── rendering ──────────────────────────────────────────────────────────────
SOLO_CSS = """
/* A single-sheet handout has no business saying "page 1 of 1". */
@page { @bottom-right { content: ""; } }
"""


def _render(html_tpl: str, scale: float, columns: int, out: Path | None, solo: bool = False):
    from weasyprint import HTML

    src = html_tpl.replace("__PS_SCALE__", f"{scale:.4f}")
    src = re.sub(r"--ps-cols:\s*[^;]+;", f"--ps-cols: {columns};", src, count=1)
    if solo:
        src = src.replace("</style>", SOLO_CSS + "</style>")
    d = HTML(string=src, base_url=str(ROOT / "css") + "/").render()
    if out is not None:
        d.write_pdf(target=str(out))
    return len(d.pages)


def _page_count(pdf: Path) -> int:
    try:
        r = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True, timeout=30)
        m = re.search(r"^Pages:\s+(\d+)", r.stdout, re.M)
        if m:
            return int(m.group(1))
    except Exception:
        pass
    return 0


# ── verbs ──────────────────────────────────────────────────────────────────
def cmd_render(a) -> int:
    src = Path(a.input).expanduser().resolve()
    if not src.exists():
        print(f"printshop: no such file: {src}", file=sys.stderr)
        return 2

    overrides = {k: v for k, v in dict(
        theme=a.theme, paper=a.paper, profile=a.profile, margin=a.margin,
        columns=a.columns if a.columns != "auto" else None,
    ).items() if v is not None}

    html_tpl, meta = _doc.build_html(src, overrides)

    out = Path(a.output).expanduser() if a.output else src.with_suffix(".pdf")
    out.parent.mkdir(parents=True, exist_ok=True)

    target = a.fit if a.fit is not None else meta.get("fit")
    target = int(target) if target not in (None, False, "none") else None
    columns = a.columns if a.columns is not None else meta.get("columns", "auto" if target else 1)
    if isinstance(columns, str) and columns.isdigit():
        columns = int(columns)
    fill = a.fill or bool(meta.get("fill", False))

    say = (lambda s: print(s)) if a.verbose else (lambda s: None)
    if target:
        say(f"printshop: fitting {src.name} to {target} page(s)")

    res = solve(lambda s, c: _render(html_tpl, s, c, None),
                target, columns, fill=fill, verbose=say)

    _render(html_tpl, res.scale, res.columns, out, solo=(res.pages == 1))

    print(f"✓ {out}  —  {res.summary()}")
    if res.note:
        print(f"  ! {res.note}")
    if not res.ok:
        print("  → try: shorter copy, --fill, paper: letter-landscape, or accept the page count")
    return 0


def cmd_preview(a) -> int:
    pdf = Path(a.input).expanduser().resolve()
    if not pdf.exists():
        print(f"printshop: no such file: {pdf}", file=sys.stderr)
        return 2
    outdir = Path(a.outdir).expanduser() if a.outdir else pdf.parent / f"{pdf.stem}-preview"
    outdir.mkdir(parents=True, exist_ok=True)
    for f in outdir.glob(f"{pdf.stem}-*.png"):
        f.unlink()
    cmd = ["pdftoppm", "-r", str(a.dpi), "-png", str(pdf), str(outdir / pdf.stem)]
    subprocess.run(cmd, check=True)
    pngs = sorted(outdir.glob(f"{pdf.stem}-*.png"))
    print(f"✓ {len(pngs)} page image(s) at {a.dpi}dpi:")
    for p in pngs:
        print(f"  {p}")

    # A multi-page doc costs one Read per page to inspect, which is how an agent
    # ends up shipping page 4 unseen. Tile them into one sheet instead.
    if getattr(a, "contact", False) and len(pngs) > 1:
        sheet = _contact_sheet(pngs, outdir / f"{pdf.stem}-contact.png")
        print(f"  → contact sheet: {sheet}")
    return 0


def _contact_sheet(pngs: list[Path], out: Path, cols: int = 3, pad: int = 14) -> Path:
    from PIL import Image, ImageDraw

    ims = [Image.open(p).convert("RGB") for p in pngs]
    w = max(i.width for i in ims)
    h = max(i.height for i in ims)
    rows = (len(ims) + cols - 1) // cols
    cols = min(cols, len(ims))
    sheet = Image.new("RGB", (cols * w + pad * (cols + 1),
                              rows * (h + 18) + pad * (rows + 1)), "#d8d8d8")
    d = ImageDraw.Draw(sheet)
    for n, im in enumerate(ims):
        r, c = divmod(n, cols)
        x = pad + c * (w + pad)
        y = pad + r * (h + 18 + pad)
        sheet.paste(im, (x, y))
        d.rectangle([x, y, x + im.width, y + im.height], outline="#9a9a9a")
        d.text((x + 2, y + im.height + 4), f"page {n + 1}", fill="#333")
    sheet.save(out, "PNG", optimize=True)
    return out


def cmd_check(a) -> int:
    from .check import check as run_check

    src = Path(a.input).expanduser().resolve()
    if not src.exists():
        print(f"printshop: no such file: {src}", file=sys.stderr)
        return 2

    html_tpl, meta = _doc.build_html(src)
    target = a.fit if a.fit is not None else meta.get("fit")
    target = int(target) if target not in (None, False, "none") else None

    res = None
    if target:
        cols = meta.get("columns", "auto")
        res = solve(lambda s, c: _render(html_tpl, s, c, None), target, cols,
                    fill=bool(meta.get("fill", False)))

    problems, notes = run_check(src, meta, html_tpl, res)

    if res:
        print(f"  fit: {res.summary()}")
    for n in notes:
        print(f"  · {n}")
    for level, msg in problems:
        print(f"  {'✗' if level == 'ERROR' else '!'} {level}: {msg}")

    errors = sum(1 for l, _ in problems if l == "ERROR")
    warns = len(problems) - errors
    if not problems:
        print(f"✓ {src.name} — clean")
    else:
        print(f"{'✗' if errors else '!'} {src.name} — {errors} error(s), {warns} warning(s)")
    return 1 if errors else 0


def cmd_send(a) -> int:
    pdf = Path(a.input).expanduser().resolve()
    if not pdf.exists():
        print(f"printshop: no such file: {pdf}", file=sys.stderr)
        return 2
    pages = _page_count(pdf)
    printer = a.printer or _default_printer()
    if not printer:
        print("printshop: no printer found (lpstat -p)", file=sys.stderr)
        return 2

    cmd = ["lp", "-d", printer, "-t", pdf.stem]
    cmd += ["-n", str(a.copies)]
    if a.duplex:
        cmd += ["-o", "sides=two-sided-long-edge"]
    else:
        cmd += ["-o", "sides=one-sided"]
    if a.media:
        cmd += ["-o", f"media={a.media}"]
    if a.pages:
        cmd += ["-o", f"page-ranges={a.pages}"]
    for opt in a.opt or []:
        cmd += ["-o", opt]
    cmd.append(str(pdf))

    if a.dry_run:
        print("would run: " + " ".join(cmd))
        return 0

    print(f"→ {pdf.name} ({pages}pp × {a.copies}) → {printer}")
    r = subprocess.run(cmd, capture_output=True, text=True)
    sys.stdout.write(r.stdout)
    sys.stderr.write(r.stderr)
    return r.returncode


def _default_printer() -> str | None:
    try:
        r = subprocess.run(["lpstat", "-d"], capture_output=True, text=True, timeout=10)
        m = re.search(r"destination:\s*(\S+)", r.stdout)
        if m:
            return m.group(1)
        r = subprocess.run(["lpstat", "-p"], capture_output=True, text=True, timeout=10)
        m = re.search(r"^printer\s+(\S+)", r.stdout, re.M)
        return m.group(1) if m else None
    except Exception:
        return None


def cmd_printers(a) -> int:
    r = subprocess.run(["lpstat", "-p", "-d"], capture_output=True, text=True)
    sys.stdout.write(r.stdout or "(no printers)\n")
    return 0


def cmd_themes(a) -> int:
    for f in sorted((ROOT / "themes").glob("*.css")):
        head = f.read_text(encoding="utf-8").splitlines()[:3]
        desc = next((l.lstrip("/* ").rstrip("*/ ").strip()
                     for l in head if "—" in l or "--" in l), "")
        print(f"  {f.stem:<16} {desc}")
    return 0


def cmd_go(a) -> int:
    """render → preview → (optionally) print, in one move."""
    rc = cmd_render(a)
    if rc:
        return rc
    src = Path(a.input).expanduser().resolve()
    out = Path(a.output).expanduser() if a.output else src.with_suffix(".pdf")
    pa = argparse.Namespace(input=str(out), outdir=a.outdir, dpi=a.dpi,
                            contact=getattr(a, "contact", True))
    cmd_preview(pa)
    if a.print:
        sa = argparse.Namespace(input=str(out), printer=a.printer, copies=a.copies,
                                duplex=a.duplex, media=None, pages=None, opt=None,
                                dry_run=False)
        return cmd_send(sa)
    return 0


# ── argument surface ───────────────────────────────────────────────────────
def _add_render_args(p):
    p.add_argument("input")
    p.add_argument("-o", "--output")
    p.add_argument("--theme")
    p.add_argument("--paper", help="letter | a4 | letter-landscape | index-4x6 | ...")
    p.add_argument("--profile", choices=["laser", "inkjet", "mono"])
    p.add_argument("--margin")
    p.add_argument("--columns", help="1 | 2 | 3 | auto")
    p.add_argument("--fit", type=int, metavar="N", help="squeeze/grow to land on N pages")
    p.add_argument("--fill", action="store_true", help="allow type to grow past 100%% to fill")
    p.add_argument("-v", "--verbose", action="store_true")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="printshop",
                                 description="Write a page, fit it, look at it, print it.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("render", help="source -> PDF, fitted")
    _add_render_args(r)
    r.set_defaults(func=cmd_render)

    p = sub.add_parser("preview", help="PDF -> PNG page images you can actually look at")
    p.add_argument("input")
    p.add_argument("--outdir")
    p.add_argument("--dpi", type=int, default=80)
    p.add_argument("--contact", action="store_true",
                   help="also tile every page into one contact sheet")
    p.set_defaults(func=cmd_preview)

    c = sub.add_parser("check", help="lint a source doc for the traps that cost paper")
    c.add_argument("input")
    c.add_argument("--fit", type=int, default=None)
    c.set_defaults(func=cmd_check)

    s = sub.add_parser("send", help="PDF -> printer")
    s.add_argument("input")
    s.add_argument("-d", "--printer")
    s.add_argument("-n", "--copies", type=int, default=1)
    s.add_argument("--duplex", action="store_true")
    s.add_argument("--media")
    s.add_argument("--pages", help="e.g. 1 or 1-3")
    s.add_argument("--opt", action="append", help="raw -o passthrough, repeatable")
    s.add_argument("--dry-run", action="store_true")
    s.set_defaults(func=cmd_send)

    g = sub.add_parser("go", help="render + preview (+ --print) in one move")
    _add_render_args(g)
    g.add_argument("--outdir")
    g.add_argument("--dpi", type=int, default=80)
    g.add_argument("--contact", action="store_true", default=True)
    g.add_argument("--print", action="store_true")
    g.add_argument("-d", "--printer")
    g.add_argument("-n", "--copies", type=int, default=1)
    g.add_argument("--duplex", action="store_true")
    g.set_defaults(func=cmd_go)

    sub.add_parser("printers", help="list printers").set_defaults(func=cmd_printers)
    sub.add_parser("themes", help="list themes").set_defaults(func=cmd_themes)

    a = ap.parse_args(argv)
    return a.func(a)
