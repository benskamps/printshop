"""The fit solver — the reason this plugin exists.

A four-page handout that should have been one page is almost never a content
problem. It is a *density* problem: the author picked a type size and a column
count by eye, once, and then never re-measured. This module measures.

Every size in base.css is `calc(<literal> * var(--ps-scale))`. So one number
controls the whole document's density. The solver renders, counts pages, and
binary-searches that number for the LARGEST value that still lands on the page
count you asked for. Largest, not smallest — the goal is a page that is full,
not a page that is tiny.

Column count is the second lever, searched outside the scale search: more
columns buy density without shrinking type, which is almost always the better
trade for reference material. So for each candidate column count we find the
best scale, then prefer the candidate with the biggest type.
"""
from __future__ import annotations

from dataclasses import dataclass

SCALE_MIN = 0.55
SCALE_MAX_DEFAULT = 1.00
SCALE_MAX_FILL = 1.45
TOLERANCE = 0.012          # stop bisecting when the window is this narrow
NEAR_TIE = 0.04            # scales within this count as "same size" -> prefer fewer columns


@dataclass
class FitResult:
    scale: float
    columns: int
    pages: int
    target: int | None
    ok: bool
    attempts: int
    note: str = ""

    def summary(self) -> str:
        col = f"{self.columns} col" if self.columns == 1 else f"{self.columns} cols"
        head = f"{self.pages}pp @ scale {self.scale:.2f}, {col}"
        if self.target is None:
            return head + f"  ({self.attempts} renders)"
        verdict = "fits" if self.ok else "OVER TARGET"
        return f"{head} — target {self.target}pp: {verdict}  ({self.attempts} renders)"


def solve(render_fn, target: int | None, columns, fill: bool = False,
          scale_min: float = SCALE_MIN, scale_max: float | None = None,
          verbose=lambda s: None) -> FitResult:
    """`render_fn(scale, columns) -> page_count`. Returns the winning knobs.

    `columns` may be an int (locked) or "auto" (ladder searched).
    """
    scale_max = scale_max if scale_max is not None else (SCALE_MAX_FILL if fill else SCALE_MAX_DEFAULT)
    calls = {"n": 0}

    def pages(s: float, c: int) -> int:
        calls["n"] += 1
        n = render_fn(s, c)
        verbose(f"    probe scale={s:.3f} cols={c} -> {n}pp")
        return n

    if target is None:
        c = 1 if columns == "auto" else int(columns)
        return FitResult(1.0, c, pages(1.0, c), None, True, calls["n"])

    ladder = [1, 2] if columns == "auto" else [int(columns)]

    best: tuple[float, int, int] | None = None      # (scale, cols, pages)
    fallback: tuple[int, float, int] | None = None  # (pages, scale, cols) if nothing fits

    for c in ladder:
        verbose(f"  · trying {c} column(s)")
        hi_pages = pages(scale_max, c)
        if hi_pages <= target:
            # Already fits wide open — nothing to search, this is the best possible.
            cand = (scale_max, c, hi_pages)
            if best is None or cand[0] > best[0] + NEAR_TIE:
                best = cand
            continue

        lo_pages = pages(scale_min, c)
        if lo_pages > target:
            # Cannot fit at this column count at any legible size.
            if fallback is None or lo_pages < fallback[0]:
                fallback = (lo_pages, scale_min, c)
            verbose(f"    {c} col: cannot reach {target}pp (floor is {lo_pages}pp)")
            continue

        lo, hi = scale_min, scale_max      # lo fits, hi does not
        best_here = (scale_min, lo_pages)
        while hi - lo > TOLERANCE:
            mid = (lo + hi) / 2
            n = pages(mid, c)
            if n <= target:
                lo, best_here = mid, (mid, n)
            else:
                hi = mid
        cand = (best_here[0], c, best_here[1])
        verbose(f"    {c} col: best scale {cand[0]:.3f} -> {cand[2]}pp")

        if best is None:
            best = cand
        elif cand[0] > best[0] + NEAR_TIE:
            best = cand          # meaningfully bigger type wins
        # a near-tie leaves `best` alone, which is the earlier (fewer-column) entry

    if best is None:
        p, s, c = fallback if fallback else (0, scale_min, ladder[0])
        return FitResult(s, c, p, target, False, calls["n"],
                         note=f"content will not fit {target}pp above the {scale_min:.2f} "
                              f"legibility floor; smallest reachable is {p}pp")

    return FitResult(best[0], best[1], best[2], target, True, calls["n"])
