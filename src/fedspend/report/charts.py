"""Hand-built inline SVG charts.

No plotting library is used on purpose. The dashboard has to be a single
self-contained HTML file that renders offline, respects the reader's light/dark
theme, and stays small enough to commit to a repository. Emitting SVG directly
gets all three: colours come from CSS custom properties so a theme switch needs
no re-render, and the whole page is well under a megabyte.

Every chart here follows the same rules: one value axis (never two scales),
recessive grid lines, thin marks with rounded data-ends, direct labels rather
than a number on every point, and a legend whenever more than one series is
plotted.
"""

from __future__ import annotations

import html
from dataclasses import dataclass

# Categorical slots 1-3, validated all-pairs in both light and dark modes.
SERIES = ("var(--series-1)", "var(--series-2)", "var(--series-3)")
POS = "var(--diverge-pos)"
NEG = "var(--diverge-neg)"


def esc(text: object) -> str:
    return html.escape(str(text), quote=True)


def fmt_money_bn(value: float, decimals: int = 1) -> str:
    return f"${value / 1e9:,.{decimals}f}B"


def fmt_pct(value: float, decimals: int = 1) -> str:
    return f"{value:.{decimals}f}%"


def fmt_signed(value: float, decimals: int = 1, suffix: str = "") -> str:
    return f"{value:+.{decimals}f}{suffix}"


@dataclass
class Box:
    """Plot geometry in user units."""

    width: int
    height: int
    left: int = 56
    right: int = 24
    top: int = 20
    bottom: int = 38

    @property
    def plot_w(self) -> int:
        return self.width - self.left - self.right

    @property
    def plot_h(self) -> int:
        return self.height - self.top - self.bottom


def _nice_ticks(lo: float, hi: float, target: int = 5) -> list[float]:
    """Human-readable tick positions spanning [lo, hi]."""
    if hi == lo:
        return [lo]
    raw = (hi - lo) / target
    mag = 10 ** (len(str(int(abs(raw)))) - 1) if abs(raw) >= 1 else 10 ** -3
    for m in (1, 2, 2.5, 5, 10):
        step = mag * m
        if raw <= step:
            break
    start = step * (lo // step)
    ticks = []
    v = start
    while v <= hi + step * 0.5:
        ticks.append(round(v, 6))
        v += step
    return ticks


def _svg_open(box: Box, title: str, desc: str) -> str:
    return (
        f'<svg viewBox="0 0 {box.width} {box.height}" class="chart" '
        f'preserveAspectRatio="xMidYMid meet" role="img" '
        f'aria-label="{esc(title)}">'
        f"<title>{esc(title)}</title><desc>{esc(desc)}</desc>"
    )


def _axis_and_grid(
    box: Box, ticks: list[float], y_of, label_fmt, *, zero_line: bool = False
) -> str:
    parts = []
    for t in ticks:
        y = y_of(t)
        parts.append(
            f'<line class="grid" x1="{box.left}" y1="{y:.1f}" '
            f'x2="{box.left + box.plot_w}" y2="{y:.1f}" />'
        )
        parts.append(
            f'<text class="tick" x="{box.left - 8}" y="{y + 4:.1f}" '
            f'text-anchor="end">{esc(label_fmt(t))}</text>'
        )
    if zero_line:
        y0 = y_of(0)
        parts.append(
            f'<line class="zero" x1="{box.left}" y1="{y0:.1f}" '
            f'x2="{box.left + box.plot_w}" y2="{y0:.1f}" />'
        )
    return "".join(parts)


# ---------------------------------------------------------------------------
def line_chart(
    x_labels: list[str],
    series: list[dict],
    *,
    title: str,
    desc: str,
    y_label_fmt=lambda v: f"{v:,.0f}",
    width: int = 720,
    height: int = 300,
    y_min: float | None = None,
    y_max: float | None = None,
    value_fmt=None,
) -> str:
    """Multi-series line chart with a crosshair hover layer.

    ``series`` items are ``{"name": str, "values": list[float]}``.
    """
    box = Box(width, height)
    value_fmt = value_fmt or y_label_fmt

    all_values = [v for s in series for v in s["values"] if v is not None]
    lo = y_min if y_min is not None else min(all_values)
    hi = y_max if y_max is not None else max(all_values)
    pad = (hi - lo) * 0.12 or 1.0
    lo, hi = lo - pad, hi + pad
    ticks = _nice_ticks(lo, hi)
    lo, hi = min(lo, ticks[0]), max(hi, ticks[-1])

    def y_of(v: float) -> float:
        return box.top + box.plot_h - (v - lo) / (hi - lo) * box.plot_h

    n = len(x_labels)
    step = box.plot_w / max(n - 1, 1)

    def x_of(i: int) -> float:
        return box.left + i * step

    out = [_svg_open(box, title, desc)]
    out.append(_axis_and_grid(box, ticks, y_of, y_label_fmt))

    for i, label in enumerate(x_labels):
        out.append(
            f'<text class="tick" x="{x_of(i):.1f}" y="{box.top + box.plot_h + 22}" '
            f'text-anchor="middle">{esc(label)}</text>'
        )

    for si, s in enumerate(series):
        colour = SERIES[si % len(SERIES)]
        pts = [
            (x_of(i), y_of(v)) for i, v in enumerate(s["values"]) if v is not None
        ]
        path = " ".join(
            ("M" if k == 0 else "L") + f"{x:.1f} {y:.1f}" for k, (x, y) in enumerate(pts)
        )
        out.append(f'<path class="line" d="{path}" style="stroke:{colour}" />')
        for x, y in pts:
            out.append(
                f'<circle class="marker" cx="{x:.1f}" cy="{y:.1f}" r="4.5" '
                f'style="fill:{colour}" />'
            )
        # Direct label on the final point rather than a number on every point.
        if pts:
            lx, ly = pts[-1]
            out.append(
                f'<text class="direct-label" x="{lx:.1f}" y="{ly - 12:.1f}" '
                f'text-anchor="end" style="fill:{colour}">'
                f"{esc(value_fmt(s['values'][-1]))}</text>"
            )

    # hover layer: one transparent column per x position
    for i, label in enumerate(x_labels):
        rows = "".join(
            f"<span class='tt-row'><i style='background:{SERIES[si % len(SERIES)]}'></i>"
            f"{esc(s['name'])}: <b>{esc(value_fmt(s['values'][i]))}</b></span>"
            for si, s in enumerate(series)
            if s["values"][i] is not None
        )
        # Clamp the hit column to the plot area so the end columns do not extend
        # under the axis labels or past the viewBox.
        col_left = max(x_of(i) - step / 2, box.left)
        col_right = min(x_of(i) + step / 2, box.left + box.plot_w)
        out.append(
            f'<rect class="hover-col" x="{col_left:.1f}" y="{box.top}" '
            f'width="{col_right - col_left:.1f}" height="{box.plot_h}" '
            f'data-tip="&lt;strong&gt;{esc(label)}&lt;/strong&gt;{esc(rows)}" />'
        )
        out.append(
            f'<line class="crosshair" x1="{x_of(i):.1f}" y1="{box.top}" '
            f'x2="{x_of(i):.1f}" y2="{box.top + box.plot_h}" />'
        )

    out.append("</svg>")
    return "".join(out)


def diverging_bar_chart(
    labels: list[str],
    values: list[float],
    *,
    title: str,
    desc: str,
    value_fmt=lambda v: f"{v:+,.1f}",
    width: int = 720,
    row_height: int = 26,
    label_width: int = 210,
) -> str:
    """Horizontal bars diverging from zero: blue for gains, red for losses."""
    height = len(labels) * row_height + 44
    box = Box(width, height, left=label_width, right=64, top=16, bottom=28)

    span = max(abs(min(values)), abs(max(values))) or 1.0
    mid = box.left + box.plot_w / 2

    def x_of(v: float) -> float:
        return mid + (v / span) * (box.plot_w / 2)

    out = [_svg_open(box, title, desc)]
    out.append(
        f'<line class="zero" x1="{mid:.1f}" y1="{box.top}" x2="{mid:.1f}" '
        f'y2="{box.top + len(labels) * row_height:.1f}" />'
    )

    for i, (label, value) in enumerate(zip(labels, values, strict=True)):
        y = box.top + i * row_height + 4
        h = row_height - 10
        colour = POS if value >= 0 else NEG
        x0, x1 = (mid, x_of(value)) if value >= 0 else (x_of(value), mid)
        bar_w = max(abs(x1 - x0), 1.5)
        # 2px surface gap keeps the bar from touching the zero rule.
        bx = x0 + 1 if value >= 0 else x0
        out.append(
            f'<rect class="bar" x="{bx:.1f}" y="{y:.1f}" width="{max(bar_w - 1, 1):.1f}" '
            f'height="{h}" rx="4" style="fill:{colour}" '
            f'data-tip="&lt;strong&gt;{esc(label)}&lt;/strong&gt;&lt;span class=\'tt-row\'&gt;'
            f'{esc(value_fmt(value))}&lt;/span&gt;" />'
        )
        out.append(
            f'<text class="row-label" x="{box.left - 10}" y="{y + h / 2 + 4:.1f}" '
            f'text-anchor="end">{esc(label)}</text>'
        )
        lx = (x1 + 6) if value >= 0 else (x0 - 6)
        anchor = "start" if value >= 0 else "end"
        out.append(
            f'<text class="value-label" x="{lx:.1f}" y="{y + h / 2 + 4:.1f}" '
            f'text-anchor="{anchor}">{esc(value_fmt(value))}</text>'
        )

    out.append("</svg>")
    return "".join(out)


def column_chart(
    labels: list[str],
    values: list[float],
    *,
    title: str,
    desc: str,
    highlight_index: int | None = None,
    reference: float | None = None,
    reference_label: str = "",
    value_fmt=lambda v: f"{v:,.0f}",
    y_label_fmt=lambda v: f"{v:,.0f}",
    width: int = 720,
    height: int = 300,
) -> str:
    """Vertical columns with an optional highlighted bar and reference line."""
    box = Box(width, height)
    hi = max(values + ([reference] if reference is not None else []))
    lo = min(0.0, min(values))
    ticks = _nice_ticks(lo, hi)
    hi = max(hi, ticks[-1])

    def y_of(v: float) -> float:
        return box.top + box.plot_h - (v - lo) / (hi - lo) * box.plot_h

    n = len(labels)
    slot = box.plot_w / n
    bar_w = min(slot * 0.62, 46)

    out = [_svg_open(box, title, desc)]
    out.append(_axis_and_grid(box, ticks, y_of, y_label_fmt))

    for i, (label, value) in enumerate(zip(labels, values, strict=True)):
        cx = box.left + slot * i + slot / 2
        y = y_of(value)
        h = max(y_of(lo) - y, 1.5)
        is_hl = highlight_index is not None and i == highlight_index
        colour = SERIES[1] if is_hl else SERIES[0]
        opacity = "1" if is_hl or highlight_index is None else "0.55"
        out.append(
            f'<rect class="bar" x="{cx - bar_w / 2:.1f}" y="{y:.1f}" '
            f'width="{bar_w:.1f}" height="{h:.1f}" rx="4" '
            f'style="fill:{colour};opacity:{opacity}" '
            f'data-tip="&lt;strong&gt;{esc(label)}&lt;/strong&gt;&lt;span class=\'tt-row\'&gt;'
            f'{esc(value_fmt(value))}&lt;/span&gt;" />'
        )
        if is_hl:
            out.append(
                f'<text class="direct-label" x="{cx:.1f}" y="{y - 8:.1f}" '
                f'text-anchor="middle" style="fill:{colour}">'
                f"{esc(value_fmt(value))}</text>"
            )
        out.append(
            f'<text class="tick" x="{cx:.1f}" y="{box.top + box.plot_h + 20}" '
            f'text-anchor="middle">{esc(label)}</text>'
        )

    if reference is not None:
        ry = y_of(reference)
        out.append(
            f'<line class="reference" x1="{box.left}" y1="{ry:.1f}" '
            f'x2="{box.left + box.plot_w}" y2="{ry:.1f}" />'
        )
        out.append(
            f'<text class="reference-label" x="{box.left + box.plot_w}" '
            f'y="{ry - 7:.1f}" text-anchor="end">{esc(reference_label)}</text>'
        )

    out.append("</svg>")
    return "".join(out)


def ranked_bar_with_range(
    labels: list[str],
    values: list[float],
    low: list[float],
    high: list[float],
    *,
    title: str,
    desc: str,
    value_fmt=lambda v: f"{v:,.1f}",
    width: int = 720,
    row_height: int = 26,
    label_width: int = 230,
) -> str:
    """Ranked horizontal bars, each overlaid with an uncertainty range.

    Used for the efficiency index: the bar is the configured score and the
    whisker is the 5th-95th percentile of scores across 2,000 random weightings,
    so a reader can see immediately which gaps between agencies survive and which
    are an artefact of the chosen weights.
    """
    height = len(labels) * row_height + 46
    box = Box(width, height, left=label_width, right=74, top=16, bottom=30)

    hi = max(max(high), max(values))
    lo = min(min(low), min(values), 0)
    span = hi - lo or 1.0

    def x_of(v: float) -> float:
        return box.left + (v - lo) / span * box.plot_w

    out = [_svg_open(box, title, desc)]
    for i, label in enumerate(labels):
        y = box.top + i * row_height + 4
        h = row_height - 10
        out.append(
            f'<rect class="bar" x="{box.left}" y="{y:.1f}" '
            f'width="{max(x_of(values[i]) - box.left, 1.5):.1f}" height="{h}" rx="4" '
            f'style="fill:{SERIES[0]}" '
            f'data-tip="&lt;strong&gt;{esc(label)}&lt;/strong&gt;'
            f'&lt;span class=\'tt-row\'&gt;score {esc(value_fmt(values[i]))}&lt;/span&gt;'
            f'&lt;span class=\'tt-row\'&gt;90% of weightings: {esc(value_fmt(low[i]))}'
            f'&ndash;{esc(value_fmt(high[i]))}&lt;/span&gt;" />'
        )
        cy = y + h / 2
        out.append(
            f'<line class="range" x1="{x_of(low[i]):.1f}" y1="{cy:.1f}" '
            f'x2="{x_of(high[i]):.1f}" y2="{cy:.1f}" />'
        )
        for v in (low[i], high[i]):
            out.append(
                f'<line class="range-cap" x1="{x_of(v):.1f}" y1="{cy - 4:.1f}" '
                f'x2="{x_of(v):.1f}" y2="{cy + 4:.1f}" />'
            )
        out.append(
            f'<text class="row-label" x="{box.left - 10}" y="{cy + 4:.1f}" '
            f'text-anchor="end">{esc(label)}</text>'
        )
        out.append(
            f'<text class="value-label" x="{box.left + box.plot_w + 8}" '
            f'y="{cy + 4:.1f}" text-anchor="start">{esc(value_fmt(values[i]))}</text>'
        )

    out.append("</svg>")
    return "".join(out)


def legend(names: list[str]) -> str:
    """Legend swatches. Always emitted for two or more series."""
    items = "".join(
        f'<span class="legend-item"><i style="background:{SERIES[i % len(SERIES)]}"></i>'
        f"{esc(n)}</span>"
        for i, n in enumerate(names)
    )
    return f'<div class="legend">{items}</div>'


def dumbbell_chart(
    labels: list[str],
    left_values: list[float],
    right_values: list[float],
    *,
    title: str,
    desc: str,
    left_name: str,
    right_name: str,
    value_fmt=lambda v: f"{v:.1f}%",
    width: int = 720,
    row_height: int = 26,
    label_width: int = 230,
) -> str:
    """Paired-dot rows connected by a rule.

    The right form for "same subject, two measures" - here an agency's observed
    competition rate against its portfolio-adjusted rate. A grouped bar chart
    would encode the same numbers but bury the thing that matters, which is the
    length and direction of the gap between the pair.
    """
    height = len(labels) * row_height + 46
    box = Box(width, height, left=label_width, right=76, top=16, bottom=30)

    everything = [v for v in (*left_values, *right_values)]
    lo, hi = min(everything), max(everything)
    pad = (hi - lo) * 0.10 or 1.0
    lo, hi = lo - pad, hi + pad

    def x_of(v: float) -> float:
        return box.left + (v - lo) / (hi - lo) * box.plot_w

    out = [_svg_open(box, title, desc)]
    for i, (label, a, b) in enumerate(zip(labels, left_values, right_values, strict=True)):
        y = box.top + i * row_height + (row_height - 10) / 2 + 5
        xa, xb = x_of(a), x_of(b)
        out.append(
            f'<line class="dumbbell" x1="{xa:.1f}" y1="{y:.1f}" x2="{xb:.1f}" y2="{y:.1f}" />'
        )
        out.append(
            f'<circle class="dot" cx="{xa:.1f}" cy="{y:.1f}" r="5" '
            f'style="fill:{SERIES[0]}" '
            f'data-tip="&lt;strong&gt;{esc(label)}&lt;/strong&gt;'
            f'&lt;span class=\'tt-row\'&gt;{esc(left_name)}: &lt;b&gt;{esc(value_fmt(a))}'
            f'&lt;/b&gt;&lt;/span&gt;&lt;span class=\'tt-row\'&gt;{esc(right_name)}: '
            f'&lt;b&gt;{esc(value_fmt(b))}&lt;/b&gt;&lt;/span&gt;" />'
        )
        out.append(
            f'<circle class="dot" cx="{xb:.1f}" cy="{y:.1f}" r="5" '
            f'style="fill:{SERIES[1]}" '
            f'data-tip="&lt;strong&gt;{esc(label)}&lt;/strong&gt;'
            f'&lt;span class=\'tt-row\'&gt;{esc(left_name)}: &lt;b&gt;{esc(value_fmt(a))}'
            f'&lt;/b&gt;&lt;/span&gt;&lt;span class=\'tt-row\'&gt;{esc(right_name)}: '
            f'&lt;b&gt;{esc(value_fmt(b))}&lt;/b&gt;&lt;/span&gt;" />'
        )
        out.append(
            f'<text class="row-label" x="{box.left - 10}" y="{y + 4:.1f}" '
            f'text-anchor="end">{esc(label)}</text>'
        )
        out.append(
            f'<text class="value-label" x="{box.left + box.plot_w + 8}" y="{y + 4:.1f}" '
            f'text-anchor="start">{esc(value_fmt(b))}</text>'
        )
    out.append("</svg>")
    return "".join(out)
