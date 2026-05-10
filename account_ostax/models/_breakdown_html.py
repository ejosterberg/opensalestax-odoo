# SPDX-License-Identifier: LGPL-3.0-or-later OR AGPL-3.0-or-later
"""Render the engine's per-jurisdiction breakdown JSON as a readable
HTML table. v0.3.4 — replaces the raw-JSON display in audit tabs.

Used by ``account.move``, ``sale.order``, and ``pos.order`` form
views via a computed ``ostax_breakdown_pretty`` Html field.

The function is pure (no env, no Odoo dependencies) so it tests
trivially and stays portable across the three models.
"""

from __future__ import annotations

import json
import logging
from html import escape

_logger = logging.getLogger(__name__)


def _fmt_amount(value: object) -> str:
    """Format a stringified Decimal-or-float as an aligned dollar
    figure with up to 4 decimal places. Pass-through for non-numeric
    values (returns the input as a stringified-and-escaped form)."""
    if value is None or value == "":
        return ""
    try:
        # The serializer stores str(Decimal); parse and reformat.
        f = float(value)
    except (TypeError, ValueError):
        return escape(str(value))
    # Display with 4 dp to preserve the engine's precision; the totals
    # area on the move uses 2dp via Odoo's Monetary widget — that's a
    # separate concern.
    return f"{f:,.4f}".rstrip("0").rstrip(".") or "0"


def _fmt_rate(value: object) -> str:
    """Format a stringified rate as a percent (e.g. ``6.875%``)."""
    if value is None or value == "":
        return ""
    try:
        f = float(value)
    except (TypeError, ValueError):
        return escape(str(value))
    return f"{f:g}%"


def breakdown_to_html(breakdown_json: str | None) -> str:
    """Convert the breakdown JSON string into a readable HTML table.

    Returns an HTML string suitable for an ``Html`` field. Empty
    string when input is empty / None / unparseable. Defensive against
    schema drift: missing keys render as blank cells, unexpected
    keys are ignored.
    """
    if not breakdown_json:
        return ""
    try:
        data = json.loads(breakdown_json)
    except (TypeError, ValueError) as e:
        _logger.debug("OST breakdown_to_html: unparseable JSON (%s)", e)
        # Fall back to a <pre> dump so the user still sees something
        # rather than a blank tab. Escape to avoid XSS via tampered
        # data.
        return f"<pre>{escape(breakdown_json)}</pre>"
    if not isinstance(data, dict):
        return f"<pre>{escape(json.dumps(data, indent=2))}</pre>"

    parts: list[str] = []

    # ------------------------------------------------------------------
    # Header summary (engine version + totals)
    # ------------------------------------------------------------------
    engine_v = data.get("engine_version") or "?"
    subtotal = data.get("subtotal")
    tax_total = data.get("tax_total")
    parts.append(
        '<div class="ostax-breakdown-header" style="margin-bottom:0.75em;">'
        f'<div><strong>Engine version:</strong> {escape(str(engine_v))}</div>'
    )
    if subtotal is not None:
        parts.append(
            f'<div><strong>Subtotal:</strong> {_fmt_amount(subtotal)}</div>'
        )
    if tax_total is not None:
        parts.append(
            f'<div><strong>Tax total:</strong> {_fmt_amount(tax_total)}</div>'
        )
    parts.append("</div>")

    # ------------------------------------------------------------------
    # Per-line breakdown — most invoices have one line, but POS orders
    # and multi-product carts can have many. Render each line as its
    # own subtable so jurisdictions stay grouped.
    # ------------------------------------------------------------------
    lines = data.get("lines") or []
    if not isinstance(lines, list):
        lines = []

    for idx, line in enumerate(lines, start=1):
        if not isinstance(line, dict):
            continue
        amount = line.get("amount")
        category = line.get("category") or "general"
        line_tax = line.get("tax")
        rate_pct = line.get("rate_pct")
        note = line.get("note")
        parts.append('<div class="ostax-breakdown-line" '
                     'style="margin-top:1em;border-top:1px solid #ddd;'
                     'padding-top:0.5em;">')
        parts.append(
            f'<div><strong>Line {idx}:</strong> {_fmt_amount(amount)} · '
            f'category {escape(str(category))} · '
            f'effective rate {_fmt_rate(rate_pct)} · '
            f'tax {_fmt_amount(line_tax)}'
            f'</div>'
        )
        if note:
            parts.append(
                f'<div style="font-style:italic;color:#666;">{escape(str(note))}</div>'
            )

        jurisdictions = line.get("jurisdictions") or []
        if not isinstance(jurisdictions, list) or not jurisdictions:
            parts.append('<div style="color:#888;">'
                         'No per-jurisdiction breakdown.</div>')
        else:
            parts.append(
                '<table class="o_list_table" '
                'style="width:auto;margin-top:0.5em;border-collapse:collapse;">'
                '<thead><tr>'
                '<th style="text-align:left;padding:2px 8px;">Jurisdiction</th>'
                '<th style="text-align:left;padding:2px 8px;">Type</th>'
                '<th style="text-align:right;padding:2px 8px;">Rate</th>'
                '<th style="text-align:right;padding:2px 8px;">Tax</th>'
                '</tr></thead><tbody>'
            )
            for j in jurisdictions:
                if not isinstance(j, dict):
                    continue
                parts.append(
                    "<tr>"
                    f'<td style="padding:2px 8px;">'
                    f'{escape(str(j.get("name") or ""))}</td>'
                    f'<td style="padding:2px 8px;">'
                    f'{escape(str(j.get("type") or ""))}</td>'
                    f'<td style="text-align:right;padding:2px 8px;'
                    f'font-variant-numeric:tabular-nums;">'
                    f'{_fmt_rate(j.get("rate_pct"))}</td>'
                    f'<td style="text-align:right;padding:2px 8px;'
                    f'font-variant-numeric:tabular-nums;">'
                    f'{_fmt_amount(j.get("tax"))}</td>'
                    f'</tr>'
                )
            parts.append("</tbody></table>")
        parts.append("</div>")

    if not lines:
        parts.append(
            '<div style="color:#888;">No lines in breakdown.</div>'
        )

    return "\n".join(parts)
