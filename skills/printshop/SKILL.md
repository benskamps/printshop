---
name: printshop
description: Make something to print — a one-page field guide, cheat sheet, handout, form, index card, label, or reference sheet — and optionally send it to the laser or inkjet. Use whenever the user says print, printout, handout, cheat sheet, field guide, one-pager, tape it to the wall, or asks for a PDF meant for paper rather than a screen. Also use to shrink an existing multi-page document onto fewer pages.
---

# printshop

Paper is not a screen. It has a hard edge, no scrolling, and a fixed cost per
sheet. This skill turns a markdown file into a PDF that is *measured* against
that edge, then prints it.

**The core move: never guess density.** Write the content, declare the page
count you want, and let the fit solver find the type size and column count that
lands on it. A four-page handout that should have been one page is almost never
too much content — it is one unmeasured guess about type size, repeated.

## Run it

```bash
~/projects/printshop/bin/printshop <verb> …
```

| verb | does |
|---|---|
| `render IN.md -o OUT.pdf` | source → fitted PDF |
| `check IN.md` | lint for the traps that cost paper — **run this first** |
| `preview OUT.pdf --contact` | → PNG page images (+ one tiled contact sheet). **Look at them.** |
| `send OUT.pdf` | → printer via CUPS |
| `go IN.md` | render + preview in one move (`--print` to also send) |
| `printers` / `themes` | what's available |

`check` catches what the solver cannot: custom CSS that quietly opted out of
fitting, `<img>` paths that resolve to nothing, a fit target that can't be met,
and type that fell below the readable floor. It exits non-zero on errors.

`preview --contact` tiles every page into one image, so a multi-page document
costs one Read to inspect instead of one per page. That is how a page nobody
looked at ends up on paper.

## The workflow that actually works

1. **Write the markdown** with front matter (below). Put the content first;
   don't pre-shrink it by hand.
2. **`render` with a `fit:` target.** Read the summary line it prints — it tells
   you the scale and column count it landed on.
3. **`preview` and actually Read the PNG.** This is not optional. The solver
   guarantees the page *count*; only your eyes catch a stranded heading, a table
   that wrapped badly, or a column that broke mid-callout.
4. **`send`** — but see "Before you print" below.

## Front matter

```yaml
---
title:    Telegram Bots          # masthead headline (or use a leading # H1)
kicker:   broken branch · field guide   # small mono line above the title
dek:      everything BotFather won't tell you twice   # italic subtitle
theme:    field-guide            # field-guide | ihd | plain
paper:    letter                 # letter | a4 | letter-landscape | index-4x6 | index-3x5 | card
profile:  laser                  # laser | inkjet | mono
fit:      1                      # target page count — THE important knob
columns:  auto                   # auto | 1 | 2 | 3
fill:     false                  # allow type to grow past 100% to fill a short page
margin:   13mm
footer:   Broken Branch          # or `false` for none
masthead: true
---
```

Any front-matter key is overridable on the command line (`--fit`, `--theme`,
`--paper`, `--profile`, `--columns`, `--margin`, `--fill`).

## Authoring vocabulary

Plain markdown works. These add design without leaving markdown:

- `> NOTE:` / `> GO:` / `> TIP:` / `> WARN:` / `> STOP:` at the head of a
  blockquote → a labelled callout panel.
- `<!--steps-->` on the line *before* an ordered list → numbered pills. Write
  each item as `**Title** — body`; the separator dash is removed automatically.
- Tables are dense and cheap. Prefer a table over a bulleted list of pairs.
- Raw HTML with these classes: `ps-note` `ps-warn` `ps-go` `ps-specs`
  `ps-cut` `ps-keep` `ps-break` `ps-fence`.
  IHD theme adds `ps-field` `ps-rule-line` `ps-approval` `ps-seal`.

### Card sheets — use `ps-cards`, not a grid

For a repeating sheet (tags, cards, plates, labels) write **flat cards** and let
the engine chunk them into rows:

```html
<div class="ps-cards" data-per="3">
<div class="ps-card">…</div>
<div class="ps-card">…</div>
…
</div>
<!--/ps-cards-->
```

The trailing `<!--/ps-cards-->` marker is **required** — without it nothing
chunks and `check` will tell you so.

Why it matters: WeasyPrint will **not fragment a CSS grid across a page**, and
will not reliably fragment a long run of inline-blocks either. A 13-item grid
becomes one unbreakable box that shunts half a blank sheet ahead of itself. The
engine emits explicit `.ps-row` blocks instead, because plain blocks *do* break
between each other. `.ps-grid` still exists but is safe **only** when the whole
sheet fits on one page.

Give cards a `ps-card-frame` (fixed height, `object-fit: contain`) when their
natural heights are ragged — uniform rows pack, ragged rows waste half a page.

## Reading the fit result

```
✓ out.pdf — 1pp @ scale 0.84, 2 cols — target 1pp: fits  (10 renders)
```

- **scale ≥ 0.85** — comfortable, ship it.
- **scale 0.70–0.85** — dense but fine for a reference sheet you'll scan, not read.
- **scale < 0.70** — genuinely small. Cut copy, go landscape, or accept 2 pages.
- **`OVER TARGET`** — it could not fit above the legibility floor. It tells you
  the smallest page count it *could* reach. Don't fight it; change the content
  or the target. Report this to the user honestly rather than shipping 6pt type.

The solver prefers **more columns over smaller type**, which is almost always
right for reference material. Lock it with `columns: 1` when the content is
prose that should read across the full measure.

## Choosing a theme

- **`field-guide`** (default) — Broken Branch house voice. Serif headings, mono
  for machine/system text, one ember accent. For guides, handouts, references.
- **`ihd`** — Inter-House Department: mock-corporate household paperwork.
  Typewriter caps, ruled lines, double-rule letterhead, ledger tables, no
  rounded cards. For forms, minutes, inventory tags, department reviews.
  Tone is mock-*official*, not playful-chaotic.
- **`plain`** — no house voice, maximum density. When the honest answer to "why
  is this four pages" is "because it was decorated."

## Printer profiles — this is not decoration

Earned on this box: **a large solid ink flood is the worst thing you can hand a
struggling inkjet.** It soaks, cockles the sheet, bleeds into reversed-out type,
and prints slowly. The laser eats it happily.

- `profile: laser` — full fills, reversed-out numerals, solid accent bars.
- `profile: inkjet` — light fills, *darker* rules (thin grey inkjet ink prints
  faint), outlined rather than filled step numerals.
- `profile: mono` — pure black; hierarchy rebuilt from ink density and line
  weight rather than hue. Do **not** just desaturate a colour build — a
  desaturated accent lands on a mid-grey that reads as faded, half-dead text.

## Before you print

Printing spends the user's paper and toner and cannot be undone.

- **Always `preview` and Read the image first.** Never send an unseen PDF.
- **Confirm with the user before `send`**, unless they already said to print
  this specific thing. "Make me a cheat sheet" is not authorisation to print it.
- Say the page count and printer in the confirmation: *"3 pages to
  BrotherLaser-Direct — go ahead?"*
- For anything over ~4 pages, offer `--duplex` first.
- Test on **one copy** before printing many.

`send` flags: `-d PRINTER` `-n COPIES` `--duplex` `--pages 1-3` `--media A4`
`--dry-run` (prints the `lp` command instead of running it).

## Printers on this box

- `BrotherLaser-Direct` — Brother HL-L3210CW colour laser. **Default.** Use for
  anything with fills, panels or heavy rules.
- `BrotherInkjet-Direct` / `Brother_MFC_J995DW` — inkjet. Use `profile: inkjet`.

Verify with `printshop printers` rather than trusting this list.
