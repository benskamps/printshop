"""Source document -> HTML. Front matter is the whole control surface."""
from __future__ import annotations

import datetime as _dt
import html
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

PAPERS = {
    "letter": "letter", "legal": "legal", "a4": "A4", "a5": "A5",
    "letter-landscape": "letter landscape", "a4-landscape": "A4 landscape",
    "index-4x6": "6in 4in", "index-3x5": "5in 3in", "card": "3.5in 2in",
}

_FM = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.S)


def _coerce(v: str):
    s = v.strip().strip('"').strip("'")
    low = s.lower()
    if low in ("true", "yes", "on"):
        return True
    if low in ("false", "no", "off"):
        return False
    if low in ("null", "none", ""):
        return None
    if re.fullmatch(r"-?\d+", s):
        return int(s)
    if re.fullmatch(r"-?\d*\.\d+", s):
        return float(s)
    return s


def split_front_matter(text: str) -> tuple[dict, str]:
    """Minimal flat YAML front matter — flat `key: value`, plus `key: |` block
    scalars (which `css:` needs). Deliberately not a YAML parser: staying flat
    keeps the control surface obvious and the failure modes boring."""
    m = _FM.match(text)
    if not m:
        return {}, text

    meta: dict = {}
    lines = m.group(1).splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        i += 1
        if not line.strip() or line.strip().startswith("#") or ":" not in line:
            continue
        k, v = line.split(":", 1)
        key = k.strip().lower().replace("_", "-")

        if v.strip() in ("|", "|-", ">", ">-"):
            # Block scalar: consume every following line indented past the key.
            indent = len(k) - len(k.lstrip())
            block = []
            while i < len(lines):
                nxt = lines[i]
                if nxt.strip() and (len(nxt) - len(nxt.lstrip())) <= indent:
                    break
                block.append(nxt)
                i += 1
            # strip the common leading indent
            pads = [len(b) - len(b.lstrip()) for b in block if b.strip()]
            cut = min(pads) if pads else 0
            joiner = "\n" if v.strip().startswith("|") else " "
            meta[key] = joiner.join(b[cut:] if len(b) >= cut else b for b in block).strip()
        else:
            meta[key] = _coerce(v)
    return meta, text[m.end():]


def md_to_html(md: str) -> str:
    from markdown_it import MarkdownIt

    parser = MarkdownIt("commonmark", {"typographer": True})
    parser.enable(["table", "strikethrough", "smartquotes", "replacements"])
    return parser.render(md)


def _sugar(body: str) -> str:
    """Author shorthands that survive plain markdown.

    A blockquote whose first line is NOTE:/WARN:/GO: becomes the matching
    callout, so a doc stays readable as markdown and still prints as design.
    """
    def repl(m: str) -> str:
        return m

    for kind, cls in (("NOTE", "ps-note"), ("WARN", "ps-warn"), ("GO", "ps-go"),
                      ("TIP", "ps-go"), ("STOP", "ps-warn")):
        body = re.sub(
            rf"<blockquote>\s*<p>{kind}:\s*(.*?)</p>",
            rf'<div class="{cls}"><span class="ps-label">{kind.lower()}</span><p>\1</p>',
            body, flags=re.S,
        )
    # close the divs we opened
    out, depth = [], 0
    for chunk in re.split(r"(</?blockquote>)", body):
        if chunk == "<blockquote>":
            out.append(chunk)
        elif chunk == "</blockquote>":
            out.append(chunk)
        else:
            out.append(chunk)
    body = "".join(out)
    body = re.sub(r'(<div class="ps-(?:note|warn|go)">.*?)</blockquote>', r"\1</div>",
                  body, flags=re.S)

    # `<!--steps-->` on the line before an ordered list opts that list into the
    # numbered-pill treatment. markdown-it emits the comment as its own HTML
    # block *before* the <ol>, so match in that order — matching the other way
    # round is how this silently did nothing on first write.
    body = re.sub(r"<!--\s*steps\s*-->\s*<ol>", '<ol class="ps-steps">', body)

    # In a steps list the bold lead-in becomes its own line (see base.css), which
    # strands the "— " the author wrote to separate it from the body. Eat the
    # separator so the source still reads naturally as markdown.
    def _destrand(m):
        return re.sub(r"(</strong>)\s*(?:—|–|-{1,2})\s+", r"\1 ", m.group(0))

    body = re.sub(r'<ol class="ps-steps">.*?</ol>', _destrand, body, flags=re.S)
    return body


def _split_top_level_divs(inner: str) -> list[str]:
    """Split a fragment into its top-level <div>…</div> children, depth-aware.

    Regex alone can't do this — cards nest divs — so walk the tags and track
    depth. Anything outside a top-level div (stray whitespace) is dropped.
    """
    out, depth, start = [], 0, None
    for m in re.finditer(r"<(/?)div\b[^>]*>", inner, re.I):
        closing = bool(m.group(1))
        if not closing:
            if depth == 0:
                start = m.start()
            depth += 1
        else:
            depth -= 1
            if depth == 0 and start is not None:
                out.append(inner[start:m.end()])
                start = None
    return out


def _chunk_cards(body: str) -> str:
    """`<div class="ps-cards" data-per="N">` → flat cards wrapped in N-wide rows.

    WeasyPrint fragments neither a CSS grid nor a long run of inline-blocks
    cleanly across pages, but it does break between sibling blocks. So the
    author writes flat `.ps-card` children and the engine builds the rows.
    See the long note in css/base.css.
    """
    pat = re.compile(r'<div class="ps-cards"([^>]*)>(.*?)</div>\s*<!--/ps-cards-->',
                     re.S | re.I)

    def repl(m: re.Match) -> str:
        attrs, inner = m.group(1), m.group(2)
        per_m = re.search(r'data-per=["\']?(\d+)', attrs)
        per = max(1, int(per_m.group(1))) if per_m else 2
        cards = _split_top_level_divs(inner)
        if not cards:
            return m.group(0)
        rows = ["".join(cards[i:i + per]) for i in range(0, len(cards), per)]
        body = "".join(f'<div class="ps-row">{r}</div>' for r in rows)
        return f'<div class="ps-cards ps-per-{per}">{body}</div>'

    return pat.sub(repl, body)


def build_html(src: Path, overrides: dict | None = None) -> tuple[str, dict]:
    raw = src.read_text(encoding="utf-8")
    meta, body_src = split_front_matter(raw)
    meta.update({k: v for k, v in (overrides or {}).items() if v is not None})

    if src.suffix.lower() in (".html", ".htm"):
        body = body_src
    else:
        body = _sugar(md_to_html(body_src))
    body = _chunk_cards(body)

    theme = str(meta.get("theme", "field-guide"))
    paper = PAPERS.get(str(meta.get("paper", "letter")).lower(), str(meta.get("paper", "letter")))
    profile = str(meta.get("profile", "laser")).lower()
    cols = meta.get("columns", 1)
    margin = meta.get("margin", "13mm")
    title = str(meta.get("title", src.stem.replace("-", " ").title()))

    classes = ["ps-" + profile]
    if meta.get("mono") or profile == "mono":
        classes.append("ps-mono")

    footer = meta.get("footer")
    if footer is None:
        footer = f"Broken Branch  ·  {_dt.date.today().isoformat()}"
    footer_css = "none" if footer is False else f'"{str(footer)}"'

    masthead = ""
    if meta.get("masthead", True) and not src.suffix.lower().startswith(".htm"):
        kicker = meta.get("kicker")
        dek = meta.get("dek") or meta.get("subtitle")
        # If the body already opens with an <h1>, promote it into the masthead
        m = re.match(r"\s*<h1>(.*?)</h1>\s*", body, re.S)
        h1 = m.group(1) if m else html.escape(title)
        if m:
            body = body[m.end():]
        parts = ['<header class="ps-masthead">']
        if kicker:
            parts.append(f'<div class="ps-kicker">{html.escape(str(kicker))}</div>')
        parts.append(f"<h1>{h1}</h1>")
        if dek:
            parts.append(f'<div class="ps-dek">{html.escape(str(dek))}</div>')
        parts.append('<div class="ps-bar"></div></header>')
        masthead = "".join(parts)

    base_css = (ROOT / "css" / "base.css").read_text(encoding="utf-8")
    theme_path = ROOT / "themes" / f"{theme}.css"
    theme_css = theme_path.read_text(encoding="utf-8") if theme_path.exists() else ""

    doc = f"""<!DOCTYPE html>
<html class="{' '.join(classes)}" lang="en">
<head><meta charset="utf-8"><title>{html.escape(title)}</title>
<style>
{base_css}
{theme_css}
:root {{
  --ps-paper: {paper};
  --ps-margin: {margin};
  --ps-footer: {footer_css};
  --ps-cols: {cols};
  --ps-scale: __PS_SCALE__;
}}
{meta.get('css', '')}
</style></head>
<body>{masthead}<main class="ps-flow">{body}</main></body></html>"""

    meta.setdefault("title", title)
    meta["_theme"] = theme
    meta["_cols"] = cols
    return doc, meta
