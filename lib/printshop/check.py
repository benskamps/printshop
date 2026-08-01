"""`printshop check` — catch the traps before they cost a sheet of paper.

Every rule here corresponds to a mistake that actually happened while building
this tool. The solver guarantees a page *count*; it cannot tell you that your
custom CSS quietly opted out of being fitted, or that an <img> points at
nothing, or that 0.58 scale means nobody will read it.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# A length literal that is NOT wrapped in a calc() touching --ps-scale.
LEN = re.compile(r"(?<![\w-])(\d*\.?\d+)(mm|cm|in|pt|pc|px)(?![\w-])")
# Properties where a fixed length is fine — these do not drive density.
EXEMPT_PROP = re.compile(
    r"^\s*(border[a-z-]*|outline[a-z-]*|box-shadow|text-shadow|letter-spacing|"
    r"word-spacing|border-radius|column-rule[a-z-]*|text-underline-offset|"
    r"text-decoration[a-z-]*|stroke[a-z-]*|flex-basis)\s*:", re.I)


def _scale_aware(decl: str) -> bool:
    """True if every length in the declaration sits inside a --ps-scale calc()."""
    for m in re.finditer(r"calc\(([^()]*(?:\([^()]*\)[^()]*)*)\)", decl):
        if "--ps-scale" in m.group(1):
            decl = decl.replace(m.group(0), " ")
    return not LEN.search(decl)


def lint_css(css: str, where: str) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    if not css.strip():
        return out

    body = re.sub(r"/\*.*?\*/", " ", css, flags=re.S)

    for decl in re.split(r"[;{}]", body):
        if ":" not in decl or EXEMPT_PROP.match(decl):
            continue
        prop = decl.split(":", 1)[0].strip().lower()
        if not re.fullmatch(r"[a-z-]+", prop or ""):
            continue
        if not _scale_aware(decl):
            out.append(("WARN",
                        f"{where}: `{decl.strip()[:64]}` uses a fixed length. The fit "
                        f"solver only moves --ps-scale, so this element opts out of "
                        f"fitting. Write calc(X * var(--ps-scale))."))

    if re.search(r"display\s*:\s*grid", body, re.I):
        out.append(("WARN",
                    f"{where}: `display: grid` — WeasyPrint will not fragment a grid "
                    f"across a page. Fine for a single sheet; use "
                    f'<div class="ps-cards" data-per="N"> if it may overflow.'))
    return out


def check(src: Path, meta: dict, html: str, fit_result=None) -> tuple[list, list]:
    """Returns (problems, notes). A problem is ('ERROR'|'WARN', message)."""
    problems: list[tuple[str, str]] = []
    notes: list[str] = []

    problems += lint_css(str(meta.get("css", "")), "front-matter css")

    # Images that resolve to nothing print as a blank box and nobody notices
    # until it is on paper.
    base = ROOT / "css"
    for m in re.finditer(r'<img[^>]+src=["\']([^"\']+)["\']', html, re.I):
        ref = m.group(1)
        if ref.startswith(("http://", "https://", "data:")):
            notes.append(f"remote image (will fail under WeasyPrint's offline base): {ref}")
            continue
        if not (base / ref).resolve().exists():
            problems.append(("ERROR", f"image not found: {ref}"))

    # ps-cards without the closing marker silently never chunks.
    opens = len(re.findall(r'<div class="ps-cards"', html))
    if opens:
        problems.append(("WARN", "ps-cards block was not chunked — did you forget the "
                                 "`<!--/ps-cards-->` marker after the closing </div>?"))

    if fit_result is not None:
        r = fit_result
        if not r.ok:
            problems.append(("ERROR", r.note or f"cannot reach {r.target} page(s)"))
        elif r.scale < 0.70:
            problems.append(("WARN", f"scale {r.scale:.2f} is below the comfortable floor "
                                     f"(0.70). Readable at arm's length? Consider cutting "
                                     f"copy, --paper letter-landscape, or one more page."))
        elif r.scale < 0.85:
            notes.append(f"scale {r.scale:.2f} — dense but fine for a reference sheet")
        if r.target and r.pages == r.target and r.scale >= 0.99 and not meta.get("fill"):
            notes.append("landed at full scale with room to spare — `fill: true` would "
                         "grow the type to fill the sheet")

    return problems, notes
