# printshop

> Write a page, fit it, look at it, print it.

A Claude Code plugin for making things that go on paper. Markdown in, a
**measured** PDF out, then straight to the laser.

```bash
bin/printshop go examples/telegram-bots.md --print
```

---

## The problem it solves

On 2026-07-31 this box printed a four-page Telegram field guide. It should have
been one page. Nothing was wrong with the content — page one was 45% empty white
space, because the type size and column count had been picked by eye, once, and
never re-measured.

That is the whole bug, and it is not a writing bug. It is a *density* bug, and a
density bug is measurable.

```
✓ telegram-bots.pdf — 1pp @ scale 0.84, 2 cols — target 1pp: fits  (10 renders)
```

Same content. One page.

## How

Every size in `css/base.css` is `calc(<literal> * var(--ps-scale))`. That means a
single number controls the entire document's density. Declare the page count you
want and the solver binary-searches that number for the **largest** value that
still lands on it — largest, not smallest, because the goal is a page that is
full, not a page that is tiny.

Column count is the second lever, searched outside the scale search. More columns
buy density *without shrinking type*, which is almost always the better trade for
reference material, so the solver tries each column count, finds the best scale
for it, and keeps the candidate with the biggest type. In the example above:
1 column needed 0.61 scale; 2 columns fit at 0.84. It picked 2 columns.

When nothing fits above the legibility floor it says so and tells you the
smallest page count it could actually reach. It will not silently ship 6pt type.

## Verbs

| verb | does |
|---|---|
| `render IN.md -o OUT.pdf` | source → fitted PDF |
| `check IN.md` | lint for the traps that cost paper (run this first) |
| `preview OUT.pdf --contact` | → PNG page images + one tiled contact sheet |
| `send OUT.pdf` | → printer via CUPS |
| `go IN.md` | render + preview in one move; `--print` to also send |
| `printers`, `themes` | what's available |

## Front matter is the control surface

```yaml
---
title:   Telegram Bots
kicker:  broken branch · field guide
dek:     everything BotFather won't tell you twice
theme:   field-guide     # field-guide | ihd | plain
paper:   letter          # a4 | letter-landscape | index-4x6 | index-3x5 | card
profile: laser           # laser | inkjet | mono
fit:     1               # the important knob
columns: auto            # auto | 1 | 2 | 3
fill:    false           # let type grow past 100% to fill a short page
plates:  [art/ginkgo.png, art/rose.png]   # margin art, one per page, cycling
---
```

## Margin plates

`plates:` hangs one engraving per page in the side margin: plate 1 on page 1,
plate 2 on page 2, and round again (`@page :nth(Kn+i)`), so the list never has
to match the page count. Paths are relative to the document. A missing plate is
an `ERROR` in `check` and `render` refuses, because the old failure here was a
silently blank margin. Knobs: `plate-width: 26mm`, `plate-gap: 7mm` (margin =
width + gap), `plate-side: left | right`. Each plate is sized through
`image-resolution` from its own pixel width (a margin box cannot be sized any
other way), so mixed-resolution art all prints the same width. Tall, narrow,
single-ink art on white works best (9:16, ~1600px tall). The Dead Head Blooms
sourcing atlas (`~/projects/deadheadblooms-print/`) is the worked example.

## Authoring

Plain markdown, plus:

- `> NOTE:` / `> GO:` / `> WARN:` heading a blockquote → labelled callout panel
- `<!--steps-->` before an ordered list → numbered pills
- classes: `ps-note` `ps-warn` `ps-go` `ps-specs` `ps-cut` `ps-keep` `ps-break`
  `ps-fence`; IHD adds `ps-field` `ps-rule-line` `ps-approval` `ps-seal`
- **card sheets:** `<div class="ps-cards" data-per="3">` … `</div>` +
  `<!--/ps-cards-->`. Write flat cards; the engine chunks them into rows that
  break across pages. Do **not** reach for `display: grid` — WeasyPrint will not
  fragment a grid, and a long run of inline-blocks fragments badly too. Both
  mistakes cost this project half-blank pages before `ps-cards` existed.

**If you write custom CSS, express sizes as `calc(X * var(--ps-scale))`.**
Hard-coded `mm` opts that element out of fitting — see
`examples/ihd-inventory-tags.md`, which does it right and explains why.

## Themes

- **field-guide** — Broken Branch house voice on paper. The screen style is
  warm-bark-dark; a full-bleed dark page is 40 minutes of toner and a warped
  sheet, so the translation keeps the structure (serif = human voice, mono =
  machine voice, one ember accent) and moves the warmth into rules and panel
  tints. Paper stays paper.
- **ihd** — Inter-House Department. Typewriter caps, ruled lines, double-rule
  letterhead, ledger tables, laurel ring, no rounded cards. Mock-*official*,
  not playful-chaotic. Follows the template canon in the IHD repo.
- **plain** — no house voice, maximum density.

## Printer profiles are not decoration

Earned on this box: a large solid ink flood is the worst thing you can hand a
struggling inkjet — it soaks, cockles the sheet, bleeds into reversed-out type
and prints slowly. The laser eats it happily.

`inkjet` uses lighter fills and *darker* rules (thin grey inkjet ink prints
faint) and outlines step numerals instead of filling them. `mono` rebuilds
hierarchy from ink density and line weight rather than hue — deliberately not a
desaturation, because a desaturated accent lands on a mid-grey that reads as
faded, half-dead text.

## Install

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python weasyprint markdown-it-py pygments
```

Needs `poppler-utils` for `preview`/page counts and CUPS (`lp`) for `send`.
Fonts (JetBrains Mono, Fraunces) ship in `assets/fonts/`, so output is identical
regardless of what's installed system-wide.

## Tests

```bash
.venv/bin/python -m pytest tests/ -q      # or: tests/run.sh
```

## Layout

```
bin/printshop          launcher (uses the project venv)
lib/printshop/         doc.py (source→HTML) · fit.py (the solver) · cli.py
css/base.css           the paged foundation + density system
themes/*.css           field-guide · ihd · plain
assets/                fonts + IHD laurel monogram
examples/              telegram-bots.md · ihd-inventory-tags.md
skills/printshop/      the skill Claude reads
commands/print.md      /print
```
