#!/usr/bin/env python3
"""Build an exhibition catalogue for the Den's gallery — The Mantel, on paper.

A worked example of the pattern printshop is really for: point a small script at
a real data source, emit printshop markdown, let the solver do the layout.

Village law applies, same as the Mantel itself: **only collected data, no
fiction.** Every plate here has a real file on disk, a real prompt from the
append-only transcript, a real timestamp and a real model string. Nothing is
invented — a plate whose file is missing is counted and reported, never
imagined into the catalogue.

    ./examples/den-exhibition.py            # writes examples/den-exhibition.md
    ./bin/printshop go examples/den-exhibition.md
"""
from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

DEN = Path.home() / "projects/personal-infra/den"
HERE = Path(__file__).resolve().parent
CACHE = HERE / ".den-plates"          # downsampled copies; the originals are 13MB
OUT = HERE / "den-exhibition.md"

PER_ROW = 3
PLATE_PX = 1100                        # ~78mm wide at 300dpi, with headroom

# Each artifact block in transcript.md looks like:
#   ## @claude → @nano-banana — <ts> [artifact <path>]
#   prompt: <text>
#   → saved <path> (model: <model>)
BLOCK = re.compile(
    r"^## @(?P<who>\S+) → @nano-banana — (?P<ts>\S+) \[artifact (?P<rel>.+?)\]\n+"
    r"prompt:\s*(?P<prompt>.*?)\n+→ saved \S+ \(model: (?P<model>.+?)\)",
    re.M | re.S,
)

# The exhibition's rooms, in the order they happened.
RUNS = [
    ("artifacts/2", "Opening night",
     "The first two things the room ever made, hours after it was built."),
    ("artifacts/promo-run", "The promo run",
     "Thirteen heroes and tiles, one per property, in a single 27-minute sitting."),
    ("hub/outputs", "The bench commission",
     "Ten reference plates cut for the Builders' Bench — CAD, joinery, fabrication."),
    ("artifacts/hearth", "Hearth moods",
     "Three candidate moods for the den's own face. The last thing hung."),
]


def room_for(rel: str) -> str:
    for prefix, name, _ in RUNS:
        if rel.startswith(prefix):
            return name
    return "Unfiled"


def collect():
    tp = DEN / "transcript.md"
    if not tp.exists():
        sys.exit(f"den-exhibition: no transcript at {tp}")
    rows, missing = [], []
    for m in BLOCK.finditer(tp.read_text(encoding="utf-8")):
        d = m.groupdict()
        src = DEN / d["rel"]
        if not src.exists():
            missing.append(d["rel"])
            continue
        d["src"] = src
        d["date"] = d["ts"][:10]
        d["prompt"] = " ".join(d["prompt"].split())
        d["room"] = room_for(d["rel"])
        rows.append(d)
    return rows, missing


def thumb(src: Path, idx: int) -> Path:
    """Downsample for print. 13MB of originals makes a PDF nobody wants to spool."""
    from PIL import Image

    CACHE.mkdir(exist_ok=True)
    out = CACHE / f"plate-{idx:02d}.jpg"
    if out.exists() and out.stat().st_mtime >= src.stat().st_mtime:
        return out
    im = Image.open(src)
    im = im.convert("RGB")
    if im.width > PLATE_PX:
        im = im.resize((PLATE_PX, round(im.height * PLATE_PX / im.width)), Image.LANCZOS)
    im.save(out, "JPEG", quality=84, optimize=True)
    return out


def title_of(d: dict) -> str:
    stem = Path(d["rel"]).stem
    stem = re.sub(r"^\d{8}-\d{6}-", "", stem)          # strip the timestamp prefix
    stem = re.sub(r"^\d{4}-\d{2}-\d{2}-bb-", "", stem)  # strip the bench run prefix
    return stem.replace("-", " ").strip().rstrip("-").title()


def main() -> int:
    rows, missing = collect()
    if not rows:
        sys.exit("den-exhibition: no artifacts with files on disk")

    for i, d in enumerate(rows, 1):
        d["plate"] = i
        d["thumb"] = thumb(d["src"], i)

    span = f"{min(r['date'] for r in rows)} – {max(r['date'] for r in rows)}"
    models = Counter(r["model"] for r in rows)
    callers = Counter(r["who"] for r in rows)
    model_line = ", ".join(f"{m} ({n})" for m, n in models.most_common())
    caller_line = ", ".join(f"{c} ({n})" for c, n in callers.most_common())

    L: list[str] = []
    A = L.append
    A("---")
    A("title: The Den")
    A("kicker: the mantel · an exhibition")
    A("dek: what the room made, on paper")
    A("theme: field-guide")
    A("profile: laser")
    A("paper: letter")
    A("footer: The Den · Broken Branch · exhibition catalogue")
    A("columns: 1")
    A("css: |")
    # NOT display:grid. WeasyPrint will not fragment a grid across a page, so a
    # 13-plate run became one unbreakable box and shunted a whole page of
    # whitespace ahead of itself — the exact failure this catalogue is about.
    # inline-block plates flow and break like text. font-size:0 on the container
    # eats the inter-block whitespace that would otherwise force a wrap.
    A("  .plates { font-size: 0; break-inside: avoid; }")
    A("  .plate { display: inline-block; width: 31.3%; vertical-align: top;")
    A("           font-size: var(--ps-fs); break-inside: avoid;")
    A("           margin: 0 0 calc(5mm * var(--ps-scale)) 0; }")
    A("  .plate:nth-child(3n+1), .plate:nth-child(3n+2) { margin-right: 3%; }")
    # A row of inline-blocks is one line box, and a line box cannot be split
    # across a page. So ragged plate heights meant 461pt rows and one row per
    # page. A fixed image box makes every plate the same height and the rows
    # pack. `contain`, not `cover` — this is a catalogue, so nothing gets cropped.
    A("  .plate .frame { height: calc(30mm * var(--ps-scale)); background: #f4efe6;")
    A("                  border: 0.4pt solid #cbc0b1; display: flex;")
    A("                  align-items: center; justify-content: center; overflow: hidden; }")
    A("  .plate img { max-width: 100%; max-height: 100%; display: block;")
    A("               object-fit: contain; }")
    A("  .plate .lab { margin-top: calc(1.6mm * var(--ps-scale)); }")
    A("  .plate .n { font-family: var(--ps-mono); font-size: calc(6pt * var(--ps-scale));")
    A("              letter-spacing: 0.16em; color: #9c4a1e; }")
    A("  .plate .t { font-family: var(--ps-serif); font-weight: 600;")
    A("              font-size: calc(8.2pt * var(--ps-scale)); line-height: 1.18; }")
    A("  .plate .m { font-family: var(--ps-mono); font-size: calc(5.2pt * var(--ps-scale));")
    A("              letter-spacing: 0.1em; color: #7d7367;")
    A("              margin-top: calc(0.6mm * var(--ps-scale)); }")
    A("  .plate .p { font-family: var(--ps-serif); font-style: italic;")
    A("              font-size: calc(6.6pt * var(--ps-scale)); line-height: 1.3;")
    A("              color: #4a3f33; margin-top: calc(1.2mm * var(--ps-scale)); }")
    A("  .room { break-before: auto; margin-top: calc(3mm * var(--ps-scale)); }")
    A("---")
    A("")
    A(f"**{len(rows)} works**, {span}. Every plate below has a file on disk, a prompt "
      f"in the room's append-only transcript, and a model that answered. "
      f"Called by {caller_line}. Rendered by {model_line}.")
    A("")
    A("> NOTE: Village law, same as the Mantel it comes from: this catalogue renders "
      "only collected data. No plate here was invented, retitled or improved. Titles "
      "are the filenames the room saved; the caption *is* the prompt, verbatim.")

    for _, room, blurb in RUNS:
        group = [r for r in rows if r["room"] == room]
        if not group:
            continue
        A("")
        A(f"## {room}")
        A("")
        A(f"{blurb} — {len(group)} work{'s' if len(group) != 1 else ''}, "
          f"{min(g['date'] for g in group)}.")
        A("")
        # Explicit rows of PER_ROW, rather than one long container of
        # inline-blocks. WeasyPrint will not reliably fragment a run of
        # inline-block line boxes across a page — it shunted the whole 13-plate
        # promo run to the next sheet and left half a page blank, which is
        # precisely the failure this catalogue is a demonstration against.
        # A row is a plain block, and blocks break between each other cleanly.
        for i in range(0, len(group), PER_ROW):
            A('<div class="plates">')
            for d in group[i:i + PER_ROW]:
                rel = Path("..") / "examples" / CACHE.name / d["thumb"].name
                prompt = d["prompt"]
                if len(prompt) > 150:
                    prompt = prompt[:147].rsplit(" ", 1)[0] + "…"
                A('<div class="plate">')
                A(f'<div class="frame"><img src="{rel.as_posix()}" alt=""></div>')
                A('<div class="lab">')
                A(f'<div class="n">PLATE {d["plate"]:02d}</div>')
                A(f'<div class="t">{title_of(d)}</div>')
                A(f'<div class="m">nano banana · {d["model"]} · {d["date"]}</div>')
                A(f'<div class="p">{prompt}</div>')
                A("</div></div>")
            A("</div>")

    if missing:
        A("")
        A(f"> WARN: {len(missing)} further artifact call{'s' if len(missing) != 1 else ''} "
          f"appear{'' if len(missing) != 1 else 's'} in the transcript with no file on "
          f"disk, and {'are' if len(missing) != 1 else 'is'} therefore not hung. "
          f"Counted, not imagined.")

    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"✓ {OUT}  —  {len(rows)} plates hung, {len(missing)} counted-but-missing")
    for _, room, _ in RUNS:
        n = sum(1 for r in rows if r["room"] == room)
        if n:
            print(f"    {room:<24} {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
