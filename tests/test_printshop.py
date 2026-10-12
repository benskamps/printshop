"""Regression tests. Each one pins a bug that actually happened during the build."""
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))

from printshop import doc as D          # noqa: E402
from printshop.cli import _render       # noqa: E402
from printshop.fit import solve         # noqa: E402


# ── front matter ───────────────────────────────────────────────────────────
def test_flat_front_matter():
    meta, body = D.split_front_matter("---\ntitle: Hi\nfit: 2\nfill: true\n---\n# Body\n")
    assert meta == {"title": "Hi", "fit": 2, "fill": True}
    assert body.strip() == "# Body"


def test_block_scalar_front_matter():
    """`css: |` used to be parsed as the literal string "|", and every line of
    the block then got misread as its own key."""
    meta, _ = D.split_front_matter(
        "---\ntheme: ihd\ncss: |\n  .a { color: red; }\n  .b { color: blue; }\nfit: 1\n---\nx\n")
    assert meta["theme"] == "ihd"
    assert meta["fit"] == 1
    assert meta["css"] == ".a { color: red; }\n.b { color: blue; }"


def test_no_front_matter_is_fine():
    meta, body = D.split_front_matter("# Just a doc\n")
    assert meta == {} and body.startswith("# Just")


# ── authoring sugar ────────────────────────────────────────────────────────
def test_steps_comment_becomes_pill_list(tmp_path):
    """The comment lands BEFORE the <ol> in markdown-it output. Matching the
    other way round made this silently do nothing."""
    src = tmp_path / "s.md"
    src.write_text("---\ntitle: T\n---\n<!--steps-->\n1. **One** — do a thing\n2. **Two** — do another\n")
    html, _ = D.build_html(src)
    assert 'class="ps-steps"' in html


def test_steps_separator_dash_is_eaten(tmp_path):
    """The bold lead-in becomes its own line, which stranded the author's dash."""
    src = tmp_path / "s.md"
    src.write_text("---\ntitle: T\n---\n<!--steps-->\n1. **One** — do a thing\n")
    html, _ = D.build_html(src)
    assert "</strong> —" not in html
    assert "do a thing" in html


def test_plain_ordered_list_is_untouched(tmp_path):
    src = tmp_path / "s.md"
    src.write_text("---\ntitle: T\n---\n1. one\n2. two\n")
    html, _ = D.build_html(src)
    assert 'class="ps-steps"' not in html


@pytest.mark.parametrize("kind,cls", [("NOTE", "ps-note"), ("WARN", "ps-warn"), ("GO", "ps-go")])
def test_callout_sugar(tmp_path, kind, cls):
    src = tmp_path / "s.md"
    src.write_text(f"---\ntitle: T\n---\n> {kind}: careful now\n")
    html, _ = D.build_html(src)
    assert f'class="{cls}"' in html
    assert "careful now" in html


# ── the solver ─────────────────────────────────────────────────────────────
def test_solver_prefers_bigger_type_over_fewer_columns():
    """1 col only fits when tiny; 2 cols fits at a comfortable size. Take 2 cols."""
    def fake(scale, cols):
        return 1 if scale <= (0.62 if cols == 1 else 0.86) else 2

    r = solve(fake, target=1, columns="auto")
    assert r.ok and r.columns == 2 and r.scale > 0.8


def test_solver_keeps_one_column_on_a_near_tie():
    def fake(scale, cols):
        return 1 if scale <= 0.90 else 2

    r = solve(fake, target=1, columns="auto")
    assert r.ok and r.columns == 1


def test_solver_reports_failure_instead_of_shipping_tiny_type():
    r = solve(lambda s, c: 3, target=1, columns="auto")
    assert not r.ok
    assert r.pages == 3
    assert "will not fit" in r.note


def test_solver_does_not_grow_past_100_percent_without_fill():
    r = solve(lambda s, c: 1, target=1, columns=1)
    assert r.ok and r.scale == pytest.approx(1.00)


def test_fill_lets_type_grow_to_fill_the_sheet():
    r = solve(lambda s, c: 1 if s <= 1.2 else 2, target=1, columns=1, fill=True)
    assert r.ok and r.scale > 1.0


def test_no_target_renders_once_at_full_size():
    r = solve(lambda s, c: 4, target=None, columns=1)
    assert r.scale == 1.0 and r.attempts == 1 and r.pages == 4


# ── end to end ─────────────────────────────────────────────────────────────
def test_examples_render_to_their_declared_page_count():
    for name in ("telegram-bots", "ihd-inventory-tags"):
        src = ROOT / "examples" / f"{name}.md"
        html, meta = D.build_html(src)
        target = int(meta["fit"])
        r = solve(lambda s, c: _render(html, s, c, None), target,
                  meta.get("columns", "auto"), fill=bool(meta.get("fill", False)))
        assert r.ok, f"{name}: {r.note}"
        assert r.pages == target, f"{name} landed on {r.pages}pp, wanted {target}"


def test_solo_sheet_drops_the_page_counter(tmp_path):
    """"page 1 of 1" on a one-page handout is noise."""
    src = tmp_path / "s.md"
    src.write_text("---\ntitle: T\nfooter: BB\n---\nshort\n")
    html, _ = D.build_html(src)
    out = tmp_path / "s.pdf"
    _render(html, 1.0, 1, out, solo=True)
    import subprocess
    txt = subprocess.run(["pdftotext", str(out), "-"], capture_output=True, text=True).stdout
    assert "page 1 of 1" not in txt.lower()


# ── card sheets ────────────────────────────────────────────────────────────
def _cards_doc(n, per):
    cards = "".join(f'<div class="ps-card"><div class="inner">{i}</div></div>' for i in range(n))
    return (f'---\ntitle: T\n---\n<div class="ps-cards" data-per="{per}">'
            f"{cards}</div>\n<!--/ps-cards-->\n")


def test_cards_are_chunked_into_rows(tmp_path):
    """WeasyPrint fragments neither grids nor long inline-block runs, so the
    engine builds explicit rows. Blocks break between each other; rows don't."""
    src = tmp_path / "c.md"
    src.write_text(_cards_doc(5, 3))
    html, _ = D.build_html(src)
    assert 'class="ps-cards ps-per-3"' in html
    assert html.count('<div class="ps-row">') == 2      # 3 + 2
    assert html.count('class="ps-card"') == 5


def test_card_chunking_respects_nested_divs(tmp_path):
    """A naive regex split would cut cards open at their inner </div>."""
    src = tmp_path / "c.md"
    src.write_text(_cards_doc(4, 2))
    html, _ = D.build_html(src)
    assert html.count('<div class="ps-row">') == 2
    for i in range(4):
        assert f'<div class="ps-card"><div class="inner">{i}</div></div>' in html


def test_exact_multiple_makes_no_ragged_row(tmp_path):
    src = tmp_path / "c.md"
    src.write_text(_cards_doc(6, 3))
    html, _ = D.build_html(src)
    assert html.count('<div class="ps-row">') == 2


# ── the checker ────────────────────────────────────────────────────────────
def test_check_flags_fixed_length_that_opts_out_of_fitting():
    from printshop.check import lint_css
    bad = lint_css(".a { height: 30mm; }", "css")
    assert any("fixed length" in m for _, m in bad)


def test_check_accepts_scale_aware_length():
    from printshop.check import lint_css
    assert lint_css(".a { height: calc(30mm * var(--ps-scale)); }", "css") == []


def test_check_ignores_hairlines_and_tracking():
    """Borders and letter-spacing don't drive density; flagging them is noise."""
    from printshop.check import lint_css
    css = ".a { border: 0.4pt solid #000; letter-spacing: 0.16em; border-radius: 2pt; }"
    assert lint_css(css, "css") == []


def test_check_warns_on_grid():
    from printshop.check import lint_css
    out = lint_css(".a { display: grid; }", "css")
    assert any("fragment a grid" in m for _, m in out)


def test_check_catches_a_missing_image(tmp_path):
    from printshop.check import check
    src = tmp_path / "s.md"
    src.write_text('---\ntitle: T\n---\n<img src="nope-does-not-exist.png">\n')
    html, meta = D.build_html(src)
    problems, _ = check(src, meta, html, None)
    assert any(l == "ERROR" and "image not found" in m for l, m in problems)


def test_check_errors_when_the_fit_target_is_unreachable():
    from printshop.check import check
    from printshop.fit import solve
    r = solve(lambda s, c: 3, target=1, columns=1)
    problems, _ = check(Path("x.md"), {}, "", r)
    assert any(l == "ERROR" for l, _ in problems)


def test_check_warns_when_type_gets_too_small():
    from printshop.check import check
    from printshop.fit import solve
    r = solve(lambda s, c: 1 if s <= 0.60 else 2, target=1, columns=1)
    problems, _ = check(Path("x.md"), {}, "", r)
    assert any("below the comfortable floor" in m for _, m in problems)


def test_contact_sheet_tiles_every_page(tmp_path):
    from printshop.cli import _contact_sheet
    from PIL import Image
    pages = []
    for i in range(4):
        p = tmp_path / f"p-{i}.png"
        Image.new("RGB", (60, 80), "white").save(p)
        pages.append(p)
    out = _contact_sheet(pages, tmp_path / "contact.png", cols=3)
    assert out.exists()
    im = Image.open(out)
    assert im.width > 60 and im.height > 80 * 2      # 2 rows for 4 pages at 3 cols


def test_scale_actually_changes_the_rendered_size(tmp_path):
    """If a theme stops using var(--ps-scale) the solver becomes a no-op that
    still reports success. Guard the mechanism itself."""
    src = tmp_path / "s.md"
    src.write_text("---\ntitle: T\n---\n" + ("Lorem ipsum dolor sit amet. " * 400))
    html, _ = D.build_html(src)
    big = _render(html, 1.0, 1, None)
    small = _render(html, 0.6, 1, None)
    assert small < big, "--ps-scale had no effect on page count"


# ── margin plates ──────────────────────────────────────────────────────────
# Born from the Dead Head Blooms atlas (2026-10-09): eight hand-written
# `@page :nth(n) { @left-middle { content: url(...) } }` rules, absolute
# file:// paths, and a hand-computed image-resolution per plate. A relative
# path there resolved inside printshop's css/ dir and rendered NOTHING.
def test_inline_list_front_matter():
    meta, _ = D.split_front_matter("---\nplates: [a.png, 'b c.png', d.png]\nfit: 2\n---\nx\n")
    assert meta["plates"] == ["a.png", "b c.png", "d.png"]
    assert meta["fit"] == 2


def test_block_list_front_matter():
    meta, _ = D.split_front_matter("---\nplates:\n  - a.png\n  - b.png\nfit: 2\n---\nx\n")
    assert meta["plates"] == ["a.png", "b.png"]
    assert meta["fit"] == 2


def _plate(path, w=400, h=700):
    from PIL import Image
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (w, h), (79, 107, 58)).save(path)
    return path


def test_plates_resolve_relative_to_the_document(tmp_path):
    _plate(tmp_path / "art" / "a.png")
    _plate(tmp_path / "art" / "b.png")
    src = tmp_path / "s.md"
    src.write_text("---\ntitle: T\nplates: [art/a.png, art/b.png]\n---\nx\n")
    html, meta = D.build_html(src)
    assert (tmp_path / "art" / "a.png").as_uri() in html
    assert "@page :nth(2n+1)" in html and "@page :nth(2n+2)" in html
    assert D.missing_plates(meta) == []


def _pdfimages(pdf):
    import subprocess
    out = subprocess.run(["pdfimages", "-list", str(pdf)], capture_output=True, text=True).stdout
    rows = [l.split() for l in out.splitlines()[2:] if l.strip()]
    # page num type width height color comp bpc enc interp object ID x-ppi y-ppi ...
    return [(int(r[0]), int(r[3]), float(r[12])) for r in rows]


def test_plates_land_on_every_page_cycling_and_at_the_set_width(tmp_path):
    """Two plates, three+ pages: page 3 must get plate 1 again, and every plate
    must print 26mm wide no matter its pixel width."""
    _plate(tmp_path / "a.png", w=400, h=700)
    _plate(tmp_path / "b.png", w=900, h=1600)
    src = tmp_path / "s.md"
    src.write_text("---\ntitle: T\nplates: [a.png, b.png]\n---\n"
                   + ("Lorem ipsum dolor sit amet. " * 900))
    html, _ = D.build_html(src)
    out = tmp_path / "s.pdf"
    pages = _render(html, 1.0, 1, out)
    assert pages >= 3
    imgs = _pdfimages(out)
    assert sorted({p for p, _, _ in imgs}) == list(range(1, pages + 1))
    by_page = {p: w for p, w, _ in imgs}
    assert by_page[1] == 400 and by_page[2] == 900 and by_page[3] == 400
    for _, px, ppi in imgs:
        assert px / ppi * 25.4 == pytest.approx(26.0, abs=0.3)


def test_a_missing_plate_is_an_error_not_a_blank_margin(tmp_path):
    from printshop.check import check
    from printshop.cli import main
    src = tmp_path / "s.md"
    src.write_text("---\ntitle: T\nplates: [nope.png]\n---\nx\n")
    html, meta = D.build_html(src)
    problems, _ = check(src, meta, html, None)
    assert any(l == "ERROR" and "plate not found" in m for l, m in problems)
    assert main(["render", str(src), "-o", str(tmp_path / "s.pdf")]) != 0
    assert not (tmp_path / "s.pdf").exists()


def test_no_plates_means_no_plate_css(tmp_path):
    src = tmp_path / "s.md"
    src.write_text("---\ntitle: T\n---\nx\n")
    html, _ = D.build_html(src)
    assert "@left-middle" not in html
