"""Generates the full HTML dashboard string from parsed data."""

def fmt_usd(v, show_plus=False):
    s = f"${abs(v):,.2f}"
    if v < 0: return f"-{s}"
    if show_plus and v > 0: return f"+{s}"
    return s

def pnl_class(v):
    if v > 0: return "pos"
    if v < 0: return "neg"
    return "neu"

def pnl_fmt(v):
    sign = "+" if v > 0 else ""
    return f"{sign}{fmt_usd(v)}"

def _dash(v, fmt=None):
    """Return formatted value or em-dash if zero."""
    if v == 0: return "—"
    return fmt(v) if fmt else str(v)

def build_html(data: dict) -> str:
    meta      = data['meta']
    nav       = data['nav']
    chg       = data['nav_change']
    stocks    = data['stocks']
    opts      = data['options']
    stk_det   = data.get('stock_details', [])
    opt_det   = data.get('option_details', [])
    fx        = data['fx']
    divs      = data['dividends']
    fees      = data['fees']
    int_items = data['interest_items']
    wdrs      = data.get('withdrawals', [])

    period   = meta['period']
    acc_name = meta['account_name']
    acc_id   = meta['account_id']
    twr      = nav['twr']

    start_nav = nav['start']
    end_nav   = nav['end']
    nav_chg   = nav['change']

    mtm        = chg.get('mtm', 0)
    divid      = chg.get('dividends', data['div_total'])
    withh      = chg.get('withholding', data['wh_total'])
    intst      = chg.get('interest', data['int_total_usd'])
    ofees      = chg.get('other_fees', data['fee_total'])
    comms      = chg.get('commissions', 0)
    fx_tr      = chg.get('fx', 0)
    wdraw      = chg.get('withdrawals', 0)
    div_accr   = chg.get('div_accruals', 0)
    int_accr   = chg.get('int_accruals', 0)

    twr_display = twr if isinstance(twr, str) else f"{twr:.2f}%"
    nav_chg_cls = "pos" if nav_chg > 0 else ("neg" if nav_chg < 0 else "neu")
    mtm_cls     = "pos" if mtm > 0 else ("neg" if mtm < 0 else "neu")

    # 用 pos_pnl + trd_pnl 作為實際盈虧（total_pnl 在 MTM 結單常為 0）
    def _effective_pnl(item):
        return item['pos_pnl'] + item['trd_pnl'] if item['total_pnl'] == 0 else item['total_pnl']

    # Build details lookup: (ticker/contract, summary_idx) -> [detail rows]
    from collections import defaultdict
    stk_det_map = defaultdict(list)
    for d in stk_det:
        key = (d['ticker'], d.get('_summary_idx', 0))
        stk_det_map[key].append(d)
    opt_det_map = defaultdict(list)
    for d in opt_det:
        key = (d['contract'], d.get('_summary_idx', 0))
        opt_det_map[key].append(d)

    def _contract_badge(contract):
        parts = contract.strip().split()
        if len(parts) < 4:
            return f'<span class="ticker-chip" style="font-size:10px;">{contract}</span>'
        underlying, expiry, strike, cp = parts[0], parts[1], parts[2], parts[3].upper()
        cp_style = ('background:#dcfce7;color:#166534;border:1px solid #bbddbf;'
                    if cp == 'C' else
                    'background:#fee2e2;color:#991b1b;border:1px solid #fca5a5;')
        return (
            f'<span class="ticker-chip" style="font-size:10px;">{underlying}</span>'
            f' <span style="font-size:9px;font-family:\'IBM Plex Mono\',monospace;color:#5a6e5c;">{expiry}</span>'
            f' <span style="font-size:10px;font-family:\'IBM Plex Mono\',monospace;font-weight:600;color:#374840;">${strike}</span>'
            f' <span style="font-size:9px;padding:1px 5px;border-radius:3px;font-family:\'IBM Plex Mono\',monospace;font-weight:700;{cp_style}">{cp}</span>'
        )

    def _stock_row(s):
        eff_pnl = _effective_pnl(s)
        pc = pnl_class(eff_pnl)
        cc = pnl_class(s['comm'])
        tid = s['ticker'].replace(' ','_').replace('/','_').replace('.','_') + f"_{s.get('_idx',0)}"
        details = stk_det_map.get((s['ticker'], s.get('_idx', 0)), [])
        has_det = len(details) > 1
        arrow = (f'<svg id="sarr-{tid}" width="10" height="10" viewBox="0 0 10 10" fill="none" '
                 f'style="display:inline;margin-right:4px;transition:transform .2s;cursor:pointer;" '
                 f"onclick=\"toggleDet('s{tid}',this)\">"
                 f'<path d="M2 3.5l3 3 3-3" stroke="#5a6e5c" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/></svg>') if has_det else ''
        summary_row = (
            f'<tr>'
            f'<td class="px-3 py-2.5" data-val="{s["ticker"]}">{arrow}<span class="ticker-chip">{s["ticker"]}</span></td>'
            f'<td class="px-3 py-2.5 text-xs text-stone-500 max-w-[140px] truncate" data-val="{s["name"]}">{s["name"]}</td>'
            f'<td class="px-3 py-2.5 text-right font-mono text-xs text-stone-400" data-val="{s["prev_qty"]}">{_dash(s["prev_qty"], lambda v: f"{v:g}")}</td>'
            f'<td class="px-3 py-2.5 text-right font-mono text-sm font-medium text-stone-800" data-val="{s["qty"]}">{_dash(s["qty"], lambda v: f"{v:g}")}</td>'
            f'<td class="px-3 py-2.5 text-right font-mono text-xs text-stone-400" data-val="{s["prev_px"]}">{_dash(s["prev_px"], lambda v: f"${v:,.2f}")}</td>'
            f'<td class="px-3 py-2.5 text-right font-mono text-sm font-medium text-stone-800" data-val="{s["px"]}">{_dash(s["px"], lambda v: f"${v:,.2f}")}</td>'
            f'<td class="px-3 py-2.5 text-right font-mono text-xs text-stone-400" data-val="{s["prev_mv"]}">{_dash(s["prev_mv"], fmt_usd)}</td>'
            f'<td class="px-3 py-2.5 text-right font-mono text-sm" data-val="{s["mv"]}">{_dash(s["mv"], fmt_usd)}</td>'
            f'<td class="px-3 py-2.5 text-right font-mono text-sm {pnl_class(s["pos_pnl"])}" data-val="{s["pos_pnl"]}">{_dash(s["pos_pnl"], pnl_fmt)}</td>'
            f'<td class="px-3 py-2.5 text-right font-mono text-sm {pnl_class(s["trd_pnl"])}" data-val="{s["trd_pnl"]}">{_dash(s["trd_pnl"], pnl_fmt)}</td>'
            f'<td class="px-3 py-2.5 text-right font-mono text-sm {cc}" data-val="{s["comm"]}">{_dash(s["comm"], pnl_fmt)}</td>'
            f'<td class="px-3 py-2.5 text-right font-mono text-sm font-semibold {pc}" data-val="{eff_pnl}">{pnl_fmt(eff_pnl)}</td>'
            f'</tr>'
        )
        detail_rows = ""
        if has_det:
            for d in details:
                # Cash flow: buying costs money (negative), selling gains money (positive)
                cash_flow = -d['mv']
                cfp = pnl_class(cash_flow)
                dcc = pnl_class(d['comm'])
                carryover_badge = (' <span style="font-size:9px;padding:1px 5px;border-radius:3px;background:#fef9c3;color:#854d0e;border:1px solid #fde68a;font-family:\'IBM Plex Mono\',monospace;white-space:nowrap;">持倉轉入</span>'
                                   if d['prev_qty'] != 0 else '')
                detail_rows += (
                    f'<tr class="det-s{tid}" style="display:none;background:#f8fcf8;">'
                    f'<td class="px-3 py-1.5 text-xs text-stone-400" style="padding-left:28px;">↳ {_dash(d["prev_qty"], lambda v: f"{v:g}")} → {_dash(d["qty"], lambda v: f"{v:g}")}{carryover_badge}</td>'
                    f'<td class="px-3 py-1.5 text-xs text-stone-400"></td>'
                    f'<td class="px-3 py-1.5 text-right font-mono text-xs text-stone-300">{_dash(d["prev_qty"], lambda v: f"{v:g}")}</td>'
                    f'<td class="px-3 py-1.5 text-right font-mono text-xs">{_dash(d["qty"], lambda v: f"{v:g}")}</td>'
                    f'<td class="px-3 py-1.5 text-right font-mono text-xs text-stone-300">{_dash(d["prev_px"], lambda v: f"${v:,.2f}")}</td>'
                    f'<td class="px-3 py-1.5 text-right font-mono text-xs">{_dash(d["px"], lambda v: f"${v:,.2f}")}</td>'
                    f'<td class="px-3 py-1.5 text-right font-mono text-xs text-stone-300">{_dash(d["prev_mv"], fmt_usd)}</td>'
                    f'<td class="px-3 py-1.5 text-right font-mono text-xs">{_dash(d["mv"], fmt_usd)}</td>'
                    f'<td class="px-3 py-1.5 text-right font-mono text-xs {pnl_class(d["pos_pnl"])}">{_dash(d["pos_pnl"], pnl_fmt)}</td>'
                    f'<td class="px-3 py-1.5 text-right font-mono text-xs {pnl_class(d["trd_pnl"])}">{_dash(d["trd_pnl"], pnl_fmt)}</td>'
                    f'<td class="px-3 py-1.5 text-right font-mono text-xs {dcc}">{_dash(d["comm"], pnl_fmt)}</td>'
                    f'<td class="px-3 py-1.5 text-right font-mono text-xs font-semibold {cfp}">{pnl_fmt(cash_flow)}</td>'
                    f'</tr>'
                )
        return summary_row + detail_rows

    def _opt_row(o):
        eff_pnl = _effective_pnl(o)
        pc = pnl_class(eff_pnl)
        cc = pnl_class(o['comm'])
        status = "持有" if o['qty'] != 0 else "已平倉"
        if o['qty'] < 0: status = "空頭"
        status_cls = "badge-hold" if o['qty'] > 0 else ("badge-short" if o['qty'] < 0 else "badge-closed")
        tid = o['contract'].replace(' ','_').replace('/','_').replace('.','_') + f"_{o.get('_idx',0)}"
        details = opt_det_map.get((o['contract'], o.get('_idx', 0)), [])
        has_det = len(details) > 1
        arrow = (f'<svg id="oarr-{tid}" width="10" height="10" viewBox="0 0 10 10" fill="none" '
                 f'style="display:inline;margin-right:4px;transition:transform .2s;cursor:pointer;" '
                 f"onclick=\"toggleDet('o{tid}',this)\">"
                 f'<path d="M2 3.5l3 3 3-3" stroke="#5a6e5c" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/></svg>') if has_det else ''
        summary_row = (
            f'<tr>'
            f'<td class="px-3 py-2.5" data-val="{o["contract"]}">{arrow}{_contract_badge(o["contract"])}</td>'
            f'<td class="px-3 py-2.5 text-xs text-stone-500 max-w-[160px] truncate" data-val="{o["desc"]}">{o["desc"]}</td>'
            f'<td class="px-3 py-2.5 text-right font-mono text-xs text-stone-400" data-val="{o["prev_qty"]}">{_dash(o["prev_qty"], lambda v: f"{v:g}")}</td>'
            f'<td class="px-3 py-2.5 text-right font-mono text-sm font-medium text-stone-800" data-val="{o["qty"]}">{_dash(o["qty"], lambda v: f"{v:g}")}</td>'
            f'<td class="px-3 py-2.5 text-right font-mono text-xs text-stone-400" data-val="{o["prev_px"]}">{_dash(o["prev_px"], lambda v: f"${v:,.4f}")}</td>'
            f'<td class="px-3 py-2.5 text-right font-mono text-sm font-medium text-stone-800" data-val="{o["px"]}">{_dash(o["px"], lambda v: f"${v:,.4f}")}</td>'
            f'<td class="px-3 py-2.5 text-right font-mono text-xs text-stone-400" data-val="{o["prev_mv"]}">{_dash(o["prev_mv"], fmt_usd)}</td>'
            f'<td class="px-3 py-2.5 text-right font-mono text-sm" data-val="{o["mv"]}">{_dash(o["mv"], fmt_usd)}</td>'
            f'<td class="px-3 py-2.5 text-right font-mono text-sm {pnl_class(o["pos_pnl"])}" data-val="{o["pos_pnl"]}">{_dash(o["pos_pnl"], pnl_fmt)}</td>'
            f'<td class="px-3 py-2.5 text-right font-mono text-sm {pnl_class(o["trd_pnl"])}" data-val="{o["trd_pnl"]}">{_dash(o["trd_pnl"], pnl_fmt)}</td>'
            f'<td class="px-3 py-2.5 text-right font-mono text-sm {cc}" data-val="{o["comm"]}">{_dash(o["comm"], pnl_fmt)}</td>'
            f'<td class="px-3 py-2.5 text-right font-mono text-sm font-semibold {pc}" data-val="{eff_pnl}">{pnl_fmt(eff_pnl)}</td>'
            f'<td class="px-3 py-2.5 text-right"><span class="badge {status_cls}">{status}</span></td>'
            f'</tr>'
        )
        detail_rows = ""
        if has_det:
            for d in details:
                cash_flow = -d['mv']
                cfp = pnl_class(cash_flow)
                dcc = pnl_class(d['comm'])
                carryover_badge = (' <span style="font-size:9px;padding:1px 5px;border-radius:3px;background:#fef9c3;color:#854d0e;border:1px solid #fde68a;font-family:\'IBM Plex Mono\',monospace;white-space:nowrap;">持倉轉入</span>'
                                   if d['prev_qty'] != 0 else '')
                detail_rows += (
                    f'<tr class="det-o{tid}" style="display:none;background:#f8fcf8;">'
                    f'<td class="px-3 py-1.5" style="padding-left:28px;">↳ <span style="font-size:10px;color:#8a9e8c;font-family:\'IBM Plex Mono\',monospace;">{_dash(d["prev_qty"], lambda v: f"{v:g}")} → {_dash(d["qty"], lambda v: f"{v:g}")}</span>{carryover_badge} {_contract_badge(d["contract"])}</td>'
                    f'<td class="px-3 py-1.5 text-xs text-stone-400"></td>'
                    f'<td class="px-3 py-1.5 text-right font-mono text-xs text-stone-300">{_dash(d["prev_qty"], lambda v: f"{v:g}")}</td>'
                    f'<td class="px-3 py-1.5 text-right font-mono text-xs">{_dash(d["qty"], lambda v: f"{v:g}")}</td>'
                    f'<td class="px-3 py-1.5 text-right font-mono text-xs text-stone-300">{_dash(d["prev_px"], lambda v: f"${v:,.4f}")}</td>'
                    f'<td class="px-3 py-1.5 text-right font-mono text-xs">{_dash(d["px"], lambda v: f"${v:,.4f}")}</td>'
                    f'<td class="px-3 py-1.5 text-right font-mono text-xs text-stone-300">{_dash(d["prev_mv"], fmt_usd)}</td>'
                    f'<td class="px-3 py-1.5 text-right font-mono text-xs">{_dash(d["mv"], fmt_usd)}</td>'
                    f'<td class="px-3 py-1.5 text-right font-mono text-xs {pnl_class(d["pos_pnl"])}">{_dash(d["pos_pnl"], pnl_fmt)}</td>'
                    f'<td class="px-3 py-1.5 text-right font-mono text-xs {pnl_class(d["trd_pnl"])}">{_dash(d["trd_pnl"], pnl_fmt)}</td>'
                    f'<td class="px-3 py-1.5 text-right font-mono text-xs {dcc}">{_dash(d["comm"], pnl_fmt)}</td>'
                    f'<td class="px-3 py-1.5 text-right font-mono text-xs font-semibold {cfp}">{pnl_fmt(cash_flow)}</td>'
                    f'<td></td>'
                    f'</tr>'
                )
        return summary_row + detail_rows

    # ── Split open / closed ──
    stocks_open   = sorted([s for s in stocks if s['qty'] != 0],  key=lambda x: abs(_effective_pnl(x)), reverse=True)
    stocks_closed = sorted([s for s in stocks if s['qty'] == 0],  key=lambda x: abs(_effective_pnl(x)), reverse=True)
    opts_open     = sorted([o for o in opts   if o['qty'] != 0],  key=lambda x: abs(_effective_pnl(x)), reverse=True)
    opts_closed   = sorted([o for o in opts   if o['qty'] == 0],  key=lambda x: abs(_effective_pnl(x)), reverse=True)
    stk_open_pnl   = sum(_effective_pnl(s) for s in stocks_open)
    stk_closed_pnl = sum(_effective_pnl(s) for s in stocks_closed)
    opt_open_pnl   = sum(_effective_pnl(o) for o in opts_open)
    opt_closed_pnl = sum(_effective_pnl(o) for o in opts_closed)

    stock_open_rows   = "".join(_stock_row(s) for s in stocks_open)
    stock_closed_rows = "".join(_stock_row(s) for s in stocks_closed)
    opt_open_rows     = "".join(_opt_row(o)   for o in opts_open)
    opt_closed_rows   = "".join(_opt_row(o)   for o in opts_closed)

    def _total_row(group, cols=12):
        """Generate a totals footer row for a group of stock/option items."""
        if not group: return ""
        t_prev_mv  = sum(s['prev_mv']            for s in group)
        t_mv       = sum(s['mv']                 for s in group)
        t_pos_pnl  = sum(s['pos_pnl']            for s in group)
        t_trd_pnl  = sum(s['trd_pnl']            for s in group)
        t_comm     = sum(s['comm']               for s in group)
        t_eff_pnl  = sum(_effective_pnl(s)       for s in group)
        pc = pnl_class(t_eff_pnl)
        pp = pnl_class(t_pos_pnl)
        tp = pnl_class(t_trd_pnl)
        cp = pnl_class(t_comm)
        # cols=12 for stock (no status), cols=13 for option (has status)
        status_td = '<td class="px-3 py-2.5"></td>' if cols == 13 else ''
        return f"""<tr class="total-row">
          <td class="px-3 py-2.5 text-xs font-semibold text-stone-500" colspan="2">合計 ({len(group)} 個)</td>
          <td class="px-3 py-2.5"></td>
          <td class="px-3 py-2.5"></td>
          <td class="px-3 py-2.5"></td>
          <td class="px-3 py-2.5"></td>
          <td class="px-3 py-2.5 text-right font-mono text-xs text-stone-400">{fmt_usd(t_prev_mv)}</td>
          <td class="px-3 py-2.5 text-right font-mono text-sm font-semibold text-stone-700">{fmt_usd(t_mv)}</td>
          <td class="px-3 py-2.5 text-right font-mono text-sm font-semibold {pp}">{pnl_fmt(t_pos_pnl)}</td>
          <td class="px-3 py-2.5 text-right font-mono text-sm font-semibold {tp}">{pnl_fmt(t_trd_pnl)}</td>
          <td class="px-3 py-2.5 text-right font-mono text-sm font-semibold {cp}">{pnl_fmt(t_comm)}</td>
          <td class="px-3 py-2.5 text-right font-mono text-sm font-bold {pc}">{pnl_fmt(t_eff_pnl)}</td>
          {status_td}
        </tr>"""

    stock_open_total   = _total_row(stocks_open,   cols=12)
    stock_closed_total = _total_row(stocks_closed, cols=12)
    opt_open_total     = _total_row(opts_open,     cols=13)
    opt_closed_total   = _total_row(opts_closed,   cols=13)

    # ────────────────────────────────────────────
    # FX ROWS — all columns
    # ────────────────────────────────────────────
    fx_rows = ""
    for f in fx:
        pc = pnl_class(f['total_pnl'])
        chg_qty  = f['qty'] - f['prev_qty']
        chg_rate = f['rate'] - f['prev_rate'] if f['prev_rate'] else 0
        chg_mv   = f['mv']  - f['prev_mv']
        fx_rows += f"""
        <tr>
          <td class="px-3 py-2.5"><span class="ticker-chip">{f['ccy']}</span></td>
          <td class="px-3 py-2.5 text-right font-mono text-xs text-stone-500">{_dash(f['prev_qty'], lambda v: f"{v:,.0f}")}</td>
          <td class="px-3 py-2.5 text-right font-mono text-sm font-medium text-stone-800">{_dash(f['qty'], lambda v: f"{v:,.0f}")}</td>
          <td class="px-3 py-2.5 text-right font-mono text-xs {pnl_class(chg_qty)}">{_dash(chg_qty, lambda v: f"{v:+,.0f}")}</td>
          <td class="px-3 py-2.5 text-right font-mono text-xs text-stone-500">{_dash(f['prev_rate'], lambda v: f"{v:.5f}")}</td>
          <td class="px-3 py-2.5 text-right font-mono text-sm font-medium text-stone-800">{_dash(f['rate'], lambda v: f"{v:.5f}")}</td>
          <td class="px-3 py-2.5 text-right font-mono text-xs text-stone-500">{_dash(f['prev_mv'], fmt_usd)}</td>
          <td class="px-3 py-2.5 text-right font-mono text-sm">{_dash(f['mv'], fmt_usd)}</td>
          <td class="px-3 py-2.5 text-right font-mono text-sm {pnl_class(chg_mv)}">{_dash(chg_mv, pnl_fmt)}</td>
          <td class="px-3 py-2.5 text-right font-mono text-sm font-semibold {pc}">{pnl_fmt(f['total_pnl'])}</td>
        </tr>"""

    # ────────────────────────────────────────────
    # DIVIDEND ROWS
    # ────────────────────────────────────────────
    div_rows_html = ""
    for d in sorted(divs, key=lambda x: x['date']):
        div_rows_html += f"""
        <tr>
          <td class="px-3 py-2.5 font-mono text-xs text-stone-500">{d['date']}</td>
          <td class="px-3 py-2.5"><span class="badge badge-ccy">{d['currency']}</span></td>
          <td class="px-3 py-2.5 text-sm text-stone-600 max-w-xs truncate">{d['desc']}</td>
          <td class="px-3 py-2.5 text-right font-mono text-sm pos font-medium">+{fmt_usd(d['amount'])}</td>
        </tr>"""

    # ────────────────────────────────────────────
    # INTEREST ROWS
    # ────────────────────────────────────────────
    int_rows_html = ""
    for item in int_items:
        pc = pnl_class(item['amount'])
        int_rows_html += f"""
        <tr>
          <td class="px-3 py-2.5 font-mono text-xs text-stone-500">{item['date']}</td>
          <td class="px-3 py-2.5"><span class="badge badge-ccy">{item['currency']}</span></td>
          <td class="px-3 py-2.5 text-sm text-stone-600 max-w-xs truncate">{item['desc']}</td>
          <td class="px-3 py-2.5 text-right font-mono text-sm {pc} font-medium">{pnl_fmt(item['amount'])}</td>
        </tr>"""

    # ────────────────────────────────────────────
    # FEE ROWS
    # ────────────────────────────────────────────
    fee_rows_html = ""
    for f in fees:
        fee_rows_html += f"""
        <tr>
          <td class="px-3 py-2.5 font-mono text-xs text-stone-500">{f['date']}</td>
          <td class="px-3 py-2.5 text-sm text-stone-600">{f['desc']}</td>
          <td class="px-3 py-2.5 text-right font-mono text-sm neg font-medium">{pnl_fmt(f['amount'])}</td>
        </tr>"""

    # ────────────────────────────────────────────
    # WITHDRAWAL ROWS
    # ────────────────────────────────────────────
    wdr_rows_html = ""
    for w in wdrs:
        pc = pnl_class(w['amount'])
        wdr_rows_html += f"""
        <tr>
          <td class="px-3 py-2.5 font-mono text-xs text-stone-500">{w['date']}</td>
          <td class="px-3 py-2.5"><span class="badge badge-ccy">{w['currency']}</span></td>
          <td class="px-3 py-2.5 text-sm text-stone-600">{w['desc']}</td>
          <td class="px-3 py-2.5 text-right font-mono text-sm {pc} font-medium">{pnl_fmt(w['amount'])}</td>
        </tr>"""

    # ────────────────────────────────────────────
    # NEW PANEL DATA PREP
    # ────────────────────────────────────────────
    wh_items      = data.get('wh_items', [])
    div_accr_items = data.get('div_accrual_items', [])
    int_accr_items = data.get('int_accrual_items', [])

    def _detail_row(item):
        pc = pnl_class(item['amount'])
        return (f'<tr><td class="px-3 py-2.5 font-mono text-xs text-stone-500">{item["date"]}</td>'
                f'<td class="px-3 py-2.5"><span class="badge badge-ccy">{item["currency"]}</span></td>'
                f'<td class="px-3 py-2.5 text-sm text-stone-600">{item["desc"]}</td>'
                f'<td class="px-3 py-2.5 text-right font-mono text-sm {pc} font-medium">{pnl_fmt(item["amount"])}</td></tr>')

    def _div_accr_row(item):
        pc = pnl_class(item['amount'])
        return (f'<tr><td class="px-3 py-2.5 font-mono text-sm font-medium">{item["ticker"]}</td>'
                f'<td class="px-3 py-2.5"><span class="badge badge-ccy">{item["currency"]}</span></td>'
                f'<td class="px-3 py-2.5 text-right font-mono text-sm {pc} font-medium">{pnl_fmt(item["amount"])}</td></tr>')

    wh_rows_html       = "".join(_detail_row(i) for i in wh_items)
    div_accr_rows_html = "".join(_div_accr_row(i) for i in div_accr_items)
    int_accr_rows_html = "".join(_detail_row(i) for i in int_accr_items)
    wh_total_val       = sum(i['amount'] for i in wh_items) or data.get('wh_total', 0)

    # Commission rows from stocks + options + fx comm column
    # Group by symbol, support expandable rows when multiple entries exist
    from collections import defaultdict
    comm_groups = defaultdict(list)
    for s in stocks:
        if s['comm'] != 0:
            comm_groups[s['ticker']].append({'name': s['name'], 'amount': s['comm']})
    for o in opts:
        if o['comm'] != 0:
            comm_groups[o['contract']].append({'name': o['desc'], 'amount': o['comm']})
    for f in fx:
        if f.get('comm', 0) != 0:
            comm_groups[f['ccy']].append({'name': f['ccy'], 'amount': f['comm']})

    comm_rows_html = ""
    comm_total_val = 0
    for sym in sorted(comm_groups.keys()):
        entries = comm_groups[sym]
        total_c = sum(e['amount'] for e in entries)
        comm_total_val += total_c
        pc = pnl_class(total_c)
        if len(entries) == 1:
            comm_rows_html += (
                f'<tr><td class="px-3 py-2.5 font-mono text-sm font-medium">{sym}</td>'
                f'<td class="px-3 py-2.5 text-sm text-stone-500">{entries[0]["name"]}</td>'
                f'<td class="px-3 py-2.5 text-right font-mono text-sm {pc} font-medium">{pnl_fmt(total_c)}</td></tr>'
            )
        else:
            uid = sym.replace(" ","_").replace("/","_")
            comm_rows_html += (
                f"<tr class='comm-group-header' onclick=\"toggleComm('{uid}')\" style='cursor:pointer;'>"
                f'<td class="px-3 py-2.5 font-mono text-sm font-medium">'
                f'<svg id="arr-{uid}" width="10" height="10" viewBox="0 0 10 10" fill="none" style="display:inline;margin-right:5px;transition:transform .2s;">'
                f'<path d="M2 3.5l3 3 3-3" stroke="#5a6e5c" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/></svg>'
                f'{sym}</td>'
                f'<td class="px-3 py-2.5 text-sm text-stone-400">{len(entries)} 筆</td>'
                f'<td class="px-3 py-2.5 text-right font-mono text-sm {pc} font-medium">{pnl_fmt(total_c)}</td></tr>'
            )
            for e in entries:
                epc = pnl_class(e['amount'])
                comm_rows_html += (
                    f'<tr class="comm-child-{uid}" style="display:none;background:#fafcfa;">'
                    f'<td class="px-3 py-2 text-xs text-stone-400" style="padding-left:28px;">— {e["name"]}</td>'
                    f'<td></td>'
                    f'<td class="px-3 py-2 text-right font-mono text-xs {epc}">{pnl_fmt(e["amount"])}</td></tr>'
                )

    # ────────────────────────────────────────────
    # RECONCILIATION BREAKDOWN
    # Use nav_change_rows from parser (CSV order, original labels)
    # ────────────────────────────────────────────

    # Map CSV label → tab_id (for hyperlinks); special 'mtm' = expandable
    CHG_TAB = {
        # Chinese labels
        '按市值計價':     'mtm',
        '存款和取款':     'tab-withdrawals',
        '股息':           'tab-dividends',
        '代扣稅款':       'tab-withholding',
        '應計股息的變化': 'tab-div-accruals',
        '利息':           'tab-interest',
        '應計利息變更':   'tab-int-accruals',
        '其它費用':       'tab-fees',
        '佣金':           'tab-commissions',
        # English labels
        'Mark-to-Market':              'mtm',
        'Deposits & Withdrawals':      'tab-withdrawals',
        'Dividends':                   'tab-dividends',
        'Withholding Tax':             'tab-withholding',
        'Change in Dividend Accruals': 'tab-div-accruals',
        'Interest':                    'tab-interest',
        'Change in Interest Accruals': 'tab-int-accruals',
        'Other Fees':                  'tab-fees',
        'Commissions':                 'tab-commissions',
    }

    raw_rows = data.get('nav_change_rows', [])
    recon_items = []
    for row in raw_rows:
        lbl = row['label']
        val = row['value']
        if val == 0:
            continue
        tab_id = CHG_TAB.get(lbl)
        is_mtm = (tab_id == 'mtm')
        recon_items.append((lbl, val, False, tab_id, is_mtm))

    # recon_total must equal nav_chg
    recon_total = sum(v for _, v, _, __, ___ in recon_items)
    chg_items = [(l, v, False) for l, v, _, __, ___ in recon_items]

    def _recon_row(label, val, is_sub, tab_id, is_mtm):
        pc = pnl_class(val)
        lbl_cls = "text-xs text-stone-400" if is_sub else "text-sm text-stone-600"
        if is_mtm:
            return (
                '<div class="summary-item recon-expandable" onclick="toggleMtm(this)" style="cursor:pointer;">' +
                f'<span class="{lbl_cls}" style="display:flex;align-items:center;gap:6px;">' +
                '<svg class="mtm-arrow" width="10" height="10" viewBox="0 0 10 10" fill="none" style="transition:transform .2s;flex-shrink:0;">' +
                '<path d="M2 3.5l3 3 3-3" stroke="#5a6e5c" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/></svg>' +
                f'{label}</span>' +
                f'<span class="font-mono text-sm font-medium {pc}">{pnl_fmt(val)}</span></div>' +
                '<div class="mtm-children" style="display:none;">' +
                f'<div class="summary-item" style="padding-left:24px;"><a onclick="showMain(\'mtm\',null);event.stopPropagation();" href="#" class="recon-link">股票持倉</a><span class="font-mono text-sm {pnl_class(stk_open_pnl)}">{pnl_fmt(stk_open_pnl)}</span></div>' +
                f'<div class="summary-item" style="padding-left:24px;"><a onclick="showMain(\'mtm\',null);event.stopPropagation();" href="#" class="recon-link">股票平倉</a><span class="font-mono text-sm {pnl_class(stk_closed_pnl)}">{pnl_fmt(stk_closed_pnl)}</span></div>' +
                f'<div class="summary-item" style="padding-left:24px;"><a onclick="showMain(\'mtm\',null);event.stopPropagation();" href="#" class="recon-link">期權持倉</a><span class="font-mono text-sm {pnl_class(opt_open_pnl)}">{pnl_fmt(opt_open_pnl)}</span></div>' +
                f'<div class="summary-item" style="padding-left:24px;"><a onclick="showMain(\'mtm\',null);event.stopPropagation();" href="#" class="recon-link">期權平倉</a><span class="font-mono text-sm {pnl_class(opt_closed_pnl)}">{pnl_fmt(opt_closed_pnl)}</span></div></div>'
            )
        elif tab_id:
            onclick_attr = "showMain('"+tab_id+"',null)"
            return (
                '<div class="summary-item">'
                f'<a onclick="{onclick_attr}" href="#" class="recon-link">{label}</a>'
                f'<span class="font-mono text-sm font-medium {pc}">{pnl_fmt(val)}</span></div>'
            )
        else:
            return (
                f'<div class="summary-item">' +
                f'<span class="{lbl_cls}">{label}</span>' +
                f'<span class="font-mono text-sm font-medium {pc}">{pnl_fmt(val)}</span></div>'
            )

    chg_rows_html = "".join(_recon_row(l, v, s, tid, mtm) for l, v, s, tid, mtm in recon_items)

    # ────────────────────────────────────────────
    # CHART DATA
    # ────────────────────────────────────────────
    chart_labels, chart_values, chart_colors = [], [], []
    for label, val, _ in chg_items:
        if val != 0:
            chart_labels.append(label.replace('（','(').replace('）',')'))
            chart_values.append(round(val, 2))
            chart_colors.append('#15803d' if val > 0 else '#dc2626')

    import json
    def _safe_js(obj):
        # Replace </ to prevent </script> injection; also escape < in strings
        s = json.dumps(obj, ensure_ascii=False)
        s = s.replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
        return s
    chart_data_js  = _safe_js({'labels': chart_labels, 'values': chart_values, 'colors': chart_colors})
    top_stocks     = sorted(stocks, key=lambda x: abs(_effective_pnl(x)), reverse=True)[:12]
    stock_chart_js = _safe_js({
        'labels': [s['ticker'] for s in top_stocks],
        'values': [round(_effective_pnl(s), 2) for s in top_stocks],
        'colors': ['#15803d' if _effective_pnl(s) >= 0 else '#dc2626' for s in top_stocks],
    })


    # ────────────────────────────────────────────
    # NAV detail breakdown (from nav['detail'])
    # ────────────────────────────────────────────
    nav_detail = nav.get('detail', {})
    nav_detail_rows = ""
    label_map = {
        'Cash':'現金', 'Stock':'股票', 'Options':'期權',
        'Collateral':'抵押品', 'SecLent':'借出證券',
        'IntAccruals':'應計利息', 'DivAccruals':'應計股息',
    }
    for key, row in nav_detail.items():
        if key in ('Total','twr'): continue
        if not isinstance(row, dict): continue
        prior = row.get('prior',0); total = row.get('total',0); change = row.get('change',0)
        if prior == 0 and total == 0: continue
        lbl = label_map.get(key, key)
        pc = pnl_class(change)
        nav_detail_rows += f"""
        <tr>
          <td class="px-3 py-2.5 text-sm text-stone-600">{lbl}</td>
          <td class="px-3 py-2.5 text-right font-mono text-sm text-stone-500">{fmt_usd(prior)}</td>
          <td class="px-3 py-2.5 text-right font-mono text-sm text-stone-800">{fmt_usd(total)}</td>
          <td class="px-3 py-2.5 text-right font-mono text-sm {pc}">{pnl_fmt(change)}</td>
        </tr>"""

    # Legacy vars
    fx_nav_btn = ""
    wdr_tab = ""

    # Conditional tab buttons (no backslash in f-string)
    _wdr_btn     = "<button class=\"nav-btn\" onclick=\"showMain('tab-withdrawals',this)\">存款和取款</button>" if wdrs else ""
    _divaccr_btn = "<button class=\"nav-btn\" onclick=\"showMain('tab-div-accruals',this)\">應計股息的變化</button>" if div_accr_items else ""
    _intaccr_btn = "<button class=\"nav-btn\" onclick=\"showMain('tab-int-accruals',this)\">應計利息變更</button>" if int_accr_items else ""

    html = f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>IB 結單 · {acc_id}</title>
<script src="https://cdn.tailwindcss.com"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Libre+Baskerville:wght@400;700&family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap" rel="stylesheet">
<script>
tailwind.config = {{
  theme: {{
    extend: {{
      colors: {{
        cream: '#f8faf8',
        'green-forest': '#166534',
        'green-mid':    '#15803d',
        'green-light':  '#dcfce7',
        'green-border': '#d4e4d4',
        'green-muted':  '#bbddbf',
        'ink':          '#1c2b1e',
      }},
      fontFamily: {{
        serif: ['Libre Baskerville', 'Georgia', 'serif'],
        sans:  ['IBM Plex Sans', 'sans-serif'],
        mono:  ['IBM Plex Mono', 'monospace'],
      }}
    }}
  }}
}}
</script>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: 'IBM Plex Sans', sans-serif;
    background: #f8faf8;
    color: #1c2b1e;
    font-size: 14px;
    line-height: 1.6;
    min-height: 100vh;
  }}
  .font-mono {{ font-family: 'IBM Plex Mono', monospace; }}

  .pos {{ color: #15803d; }}
  .neg {{ color: #b91c1c; }}
  .neu {{ color: #1c2b1e; }}

  /* ── Header ── */
  .site-header {{
    background: #ffffff;
    border-bottom: 2px solid #166534;
    padding: 0 32px;
    display: flex;
    align-items: stretch;
    justify-content: space-between;
    gap: 16px;
    flex-wrap: wrap;
  }}
  .header-brand {{
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 16px 0;
  }}
  .header-logo {{
    width: 36px; height: 36px;
    background: #166534;
    border-radius: 6px;
    display: flex; align-items: center; justify-content: center;
    flex-shrink: 0;
  }}
  .header-title {{
    font-family: 'Libre Baskerville', serif;
    font-size: 16px;
    font-weight: 700;
    color: #166534;
  }}
  .header-sub {{
    font-size: 11px;
    color: #5a6e5c;
    margin-top: 1px;
    font-family: 'IBM Plex Mono', monospace;
  }}
  .header-meta {{
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    justify-content: center;
    gap: 5px;
    padding: 14px 0;
  }}
  .period-pill {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: #f0f7f1;
    border: 1px solid #d4e4d4;
    border-radius: 5px;
    padding: 4px 10px;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 11px;
    color: #166534;
    font-weight: 500;
  }}
  .twr-tag {{
    font-family: 'IBM Plex Mono', monospace;
    font-size: 11px;
    color: #5a6e5c;
  }}

  /* ── Metric tiles ── */
  .metric-tile {{
    background: #ffffff;
    border: 1px solid #d4e4d4;
    border-radius: 8px;
    padding: 16px 18px;
    border-top: 3px solid #d4e4d4;
  }}
  .metric-tile.t-pos {{ border-top-color: #15803d; }}
  .metric-tile.t-neg {{ border-top-color: #b91c1c; }}
  .metric-tile.t-neu {{ border-top-color: #166534; }}
  .metric-label {{
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #8a9e8c;
    margin-bottom: 8px;
  }}
  .metric-value {{
    font-family: 'IBM Plex Mono', monospace;
    font-size: 17px;
    font-weight: 500;
    line-height: 1.2;
  }}
  .metric-sub {{
    font-size: 11px;
    color: #8a9e8c;
    margin-top: 4px;
    font-family: 'IBM Plex Mono', monospace;
  }}

  /* ── Tab bar ── */
  .tab-bar {{
    display: flex;
    gap: 0;
    border-bottom: 2px solid #d4e4d4;
    margin-bottom: 20px;
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
  }}
  .nav-btn {{
    padding: 10px 18px;
    font-size: 13px;
    font-weight: 500;
    border: none;
    background: transparent;
    color: #8a9e8c;
    cursor: pointer;
    border-bottom: 2px solid transparent;
    margin-bottom: -2px;
    transition: color 0.15s, border-color 0.15s;
    font-family: 'IBM Plex Sans', sans-serif;
    white-space: nowrap;
  }}
  .nav-btn.active {{
    color: #166534;
    border-bottom-color: #166534;
    font-weight: 600;
  }}
  .nav-btn:hover:not(.active) {{ color: #374840; }}

  /* ── Data card ── */
  .data-card {{
    background: #ffffff;
    border: 1px solid #d4e4d4;
    border-radius: 8px;
    overflow: hidden;
  }}
  .data-card-header {{
    padding: 12px 18px;
    border-bottom: 1px solid #e8f0e8;
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: #f6fbf6;
  }}
  .card-title {{
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #374840;
  }}
  .card-badge {{
    font-size: 11px;
    padding: 2px 9px;
    border-radius: 4px;
    background: #dcfce7;
    color: #166534;
    font-family: 'IBM Plex Mono', monospace;
    font-weight: 500;
    border: 1px solid #bbddbf;
  }}
  .card-badge-red {{
    background: #fee2e2;
    color: #991b1b;
    border-color: #fca5a5;
  }}

  /* ── Tables ── */
  table {{ width: 100%; border-collapse: collapse; }}
  .table-head-row {{ border-bottom: 2px solid #e8f0e8; background: #f6fbf6; }}
  .th-l, .th-r {{
    padding: 9px 12px;
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    color: #8a9e8c;
    white-space: nowrap;
  }}
  .th-l {{ text-align: left; }}
  .th-r {{ text-align: right; }}
  /* sub-header for prev/current grouping */
  .th-group {{
    padding: 4px 12px;
    font-size: 9px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #a8b8a8;
    text-align: center;
    border-bottom: 1px solid #e8f0e8;
    background: #f9fcf9;
  }}
  tr {{ border-bottom: 1px solid #eef5ee; }}
  tr:last-child {{ border-bottom: none; }}
  tr:hover {{ background: #f6fbf6; }}

  /* ── Badges ── */
  .badge {{
    display: inline-block;
    font-size: 10px;
    font-weight: 600;
    padding: 2px 6px;
    border-radius: 3px;
    font-family: 'IBM Plex Mono', monospace;
    letter-spacing: 0.02em;
    border: 1px solid transparent;
    white-space: nowrap;
  }}
  .badge-hold   {{ background: #dcfce7; color: #166534; border-color: #bbddbf; }}
  .badge-closed {{ background: #f1f5f1; color: #8a9e8c; border-color: #d4e4d4; }}
  .badge-short  {{ background: #fee2e2; color: #991b1b; border-color: #fca5a5; }}
  .badge-ccy    {{ background: #f0fdf4; color: #166534; border-color: #bbddbf; }}

  .ticker-chip {{
    font-family: 'IBM Plex Mono', monospace;
    font-size: 11px;
    font-weight: 500;
    color: #166534;
    background: #f0f7f1;
    border: 1px solid #d4e4d4;
    border-radius: 4px;
    padding: 2px 7px;
    letter-spacing: 0.03em;
    white-space: nowrap;
  }}

  /* column divider */
  .col-sep {{ border-left: 1px solid #e8f0e8; }}

  /* ── Summary rows ── */
  .summary-item {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 9px 18px;
    border-bottom: 1px solid #eef5ee;
  }}
  .summary-item:last-child {{ border-bottom: none; }}
  .recon-link {{ color:#166534;text-decoration:none;font-size:13px; }}
  .recon-link:hover {{ text-decoration:underline; }}
  .recon-expandable:hover {{ background:#f6fbf6; }}
  .summary-total {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 18px;
    background: #f0f7f1;
    border-top: 2px solid #d4e4d4;
  }}

  /* ── Upload zone ── */
  .upload-zone {{
    border: 1.5px dashed #bbddbf;
    border-radius: 8px;
    cursor: pointer;
    transition: border-color 0.2s, background 0.2s;
    background: #ffffff;
  }}
  .upload-zone:hover, .upload-zone.drag {{
    border-color: #166534;
    background: #f0f7f1;
  }}
  .upload-zone input {{ display: none; }}

  /* chart */
  .chart-wrap {{ position: relative; width: 100%; height: 220px; padding: 14px 18px; }}

  @keyframes fadeUp {{
    from {{ opacity: 0; transform: translateY(5px); }}
    to   {{ opacity: 1; transform: translateY(0); }}
  }}
  .main-panel {{ animation: fadeUp 0.16s ease-out; }}
  .hidden {{ display: none !important; }}

  ::-webkit-scrollbar {{ width: 5px; height: 5px; }}
  ::-webkit-scrollbar-track {{ background: #f0f7f1; }}
  ::-webkit-scrollbar-thumb {{ background: #bbddbf; border-radius: 3px; }}

  .empty-state {{
    padding: 40px;
    text-align: center;
    color: #8a9e8c;
    font-size: 13px;
  }}
  tr.total-row {{
    background: #f0f7f1;
    border-top: 2px solid #d4e4d4 !important;
  }}
  tr.total-row td {{ padding-top: 10px; padding-bottom: 10px; }}
  tr.total-row:hover {{ background: #e8f5ea; }}

  /* ── Sortable table headers ── */
  .sortable {{
    cursor: pointer;
    user-select: none;
    white-space: nowrap;
  }}
  .sortable:hover {{ background: #eef5ee !important; }}
  .sort-icon {{
    display: inline-block;
    font-size: 9px;
    color: #bbddbf;
    margin-left: 3px;
    vertical-align: middle;
    transition: color 0.1s;
  }}
  .sortable:hover .sort-icon {{ color: #8a9e8c; }}
  .sort-asc  .sort-icon {{ color: #166534 !important; }}
  .sort-desc .sort-icon {{ color: #166534 !important; }}
  .sort-asc  .sort-icon::after {{ content: '↑'; }}
  .sort-desc .sort-icon::after {{ content: '↓'; }}
  .sort-asc  .sort-icon,
  .sort-desc .sort-icon {{ font-size: 0; }}
  .sort-asc  .sort-icon::after,
  .sort-desc .sort-icon::after {{ font-size: 10px; }}
</style>
</head>
<body>

<!-- ── HEADER ── -->
<header class="site-header">
  <div class="header-brand">
    <div class="header-logo">
      <svg width="18" height="18" viewBox="0 0 20 20" fill="none">
        <path d="M3 14l4-5 3 3 3-4 4 6" stroke="white" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
        <circle cx="16" cy="5" r="2" fill="white" opacity="0.7"/>
      </svg>
    </div>
    <div>
      <div class="header-title">IB 結單儀表板</div>
      <div class="header-sub">{acc_name} · {acc_id}</div>
    </div>
  </div>
  <div class="header-meta">
    <div class="period-pill">
      <svg width="11" height="11" viewBox="0 0 12 12" fill="none">
        <rect x="1" y="2" width="10" height="9" rx="1.5" stroke="#166534" stroke-width="1.3"/>
        <path d="M4 1v2M8 1v2M1 5h10" stroke="#166534" stroke-width="1.3" stroke-linecap="round"/>
      </svg>
      {period}
    </div>
    <div class="twr-tag">時間加權報酬 {twr_display}</div>
  </div>
</header>

<div style="max-width:1440px;margin:0 auto;padding:24px 32px;">

<!-- ── UPLOAD ── -->
<label class="upload-zone flex items-center gap-4 px-5 py-4 mb-6" id="dropZone">
  <input type="file" id="csvInput" accept=".csv">
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#8a9e8c" stroke-width="1.8" stroke-linecap="round">
    <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M17 8l-5-5-5 5M12 3v12"/>
  </svg>
  <div>
    <div style="font-size:13px;font-weight:500;color:#374840;">上載另一份結單</div>
    <div style="font-size:11px;color:#8a9e8c;margin-top:2px;">拖放或點擊 · 支援 IB MTM 摘要及活動結單（中英文）</div>
  </div>
</label>

<!-- ── METRIC TILES ── -->
<div style="display:grid;grid-template-columns:repeat(6,1fr);gap:12px;margin-bottom:24px;" class="grid-metrics">
  <div class="metric-tile t-neu">
    <div class="metric-label">期初 NAV</div>
    <div class="metric-value neu">{fmt_usd(start_nav)}</div>
    <div class="metric-sub">期間開始</div>
  </div>
  <div class="metric-tile t-neu">
    <div class="metric-label">期末 NAV</div>
    <div class="metric-value neu">{fmt_usd(end_nav)}</div>
    <div class="metric-sub">期間結束</div>
  </div>
  <div class="metric-tile {'t-pos' if nav_chg >= 0 else 't-neg'}">
    <div class="metric-label">期間變動</div>
    <div class="metric-value {nav_chg_cls}">{pnl_fmt(nav_chg)}</div>
    <div class="metric-sub {nav_chg_cls}">TWR {twr_display}</div>
  </div>
  <div class="metric-tile {'t-pos' if mtm >= 0 else 't-neg'}">
    <div class="metric-label">MTM 盈虧</div>
    <div class="metric-value {mtm_cls}">{pnl_fmt(mtm)}</div>
    <div class="metric-sub">按市值計價</div>
  </div>
  <div class="metric-tile t-pos">
    <div class="metric-label">股息（稅後）</div>
    <div class="metric-value pos">+{fmt_usd(divid + withh)}</div>
    <div class="metric-sub">預扣稅 {fmt_usd(abs(withh))}</div>
  </div>
  <div class="metric-tile t-neg">
    <div class="metric-label">總費用</div>
    <div class="metric-value neg">{pnl_fmt(intst + ofees + comms)}</div>
    <div class="metric-sub">息＋行情費＋佣金</div>
  </div>
</div>

<!-- ── TAB BAR ── -->
<div class="tab-bar">
  <button class="nav-btn active" onclick="showMain('overview',this)">總覽</button>
  <button class="nav-btn" onclick="showMain('mtm',this)">按市值計價</button>
  {_wdr_btn}
  <button class="nav-btn" onclick="showMain('tab-dividends',this)">股息</button>
  <button class="nav-btn" onclick="showMain('tab-withholding',this)">代扣稅款</button>
  {_divaccr_btn}
  <button class="nav-btn" onclick="showMain('tab-interest',this)">利息</button>
  {_intaccr_btn}
  <button class="nav-btn" onclick="showMain('tab-fees',this)">其它費用</button>
  <button class="nav-btn" onclick="showMain('tab-commissions',this)">佣金</button>
</div>

<!-- ══════════ OVERVIEW ══════════ -->
<div id="main-overview" class="main-panel">
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px;">
    <div class="data-card">
      <div class="data-card-header">
        <span class="card-title">淨資產值變動明細</span>
      </div>
      <div class="summary-total">
        <span style="font-size:12px;font-weight:600;color:#374840;">淨變動合計</span>
        <span class="font-mono" style="font-size:14px;font-weight:600;color:{'#15803d' if nav_chg>=0 else '#b91c1c'}">{pnl_fmt(nav_chg)}</span>
      </div>
      <div style="border-bottom:1px solid #e8f0e8;"></div>
      {chg_rows_html if chg_rows_html else '<div class="empty-state">無資料</div>'}
    </div>
    <div class="data-card">
      <div class="data-card-header"><span class="card-title">盈虧來源分析</span></div>
      <div class="chart-wrap"><canvas id="navChart"></canvas></div>
    </div>
  </div>
  <div class="data-card">
    <div class="data-card-header"><span class="card-title">持倉 MTM 盈虧（前 12 名）</span></div>
    <div class="chart-wrap" style="height:240px;"><canvas id="stockChart"></canvas></div>
  </div>
</div>

<!-- ══════════ 按市值計價 ══════════ -->
<div id="main-mtm" class="main-panel hidden">
  <div class="data-card" style="margin-bottom:16px;">
    <div class="data-card-header" id="mtm-stk-open"><span class="card-title">股票持倉</span><span class="card-badge">{len(stocks_open)} 個代碼</span></div>
    <div style="overflow-x:auto;"><table class="sortable-table" id="tbl-stock-open">
      <thead>
        <tr style="background:#f6fbf6;border-bottom:1px solid #e8f0e8;">
          <th class="th-group sortable" rowspan="2" data-col="0" data-type="str" style="text-align:left;vertical-align:bottom;padding:9px 12px;border-bottom:2px solid #e8f0e8;">代碼 <span class="sort-icon">↕</span></th>
          <th class="th-group sortable" rowspan="2" data-col="1" data-type="str" style="text-align:left;vertical-align:bottom;padding:9px 12px;border-bottom:2px solid #e8f0e8;">名稱 <span class="sort-icon">↕</span></th>
          <th class="th-group" colspan="2" style="border-left:1px solid #e8f0e8;">持倉數量</th>
          <th class="th-group" colspan="2" style="border-left:1px solid #e8f0e8;">價格</th>
          <th class="th-group" colspan="2" style="border-left:1px solid #e8f0e8;">市值</th>
          <th class="th-group" colspan="2" style="border-left:1px solid #e8f0e8;">持倉 / 交易盈虧</th>
          <th class="th-group sortable" rowspan="2" data-col="10" data-type="num" style="text-align:right;vertical-align:bottom;padding:9px 12px;border-bottom:2px solid #e8f0e8;border-left:1px solid #e8f0e8;">佣金 <span class="sort-icon">↕</span></th>
          <th class="th-group sortable" rowspan="2" data-col="11" data-type="num" style="text-align:right;vertical-align:bottom;padding:9px 12px;border-bottom:2px solid #e8f0e8;border-left:1px solid #e8f0e8;">總盈虧 <span class="sort-icon">↕</span></th>
        </tr>
        <tr class="table-head-row">
          <th class="th-r col-sep sortable" data-col="2" data-type="num" style="font-size:9px;color:#a8b8a8;">期初 <span class="sort-icon">↕</span></th>
          <th class="th-r sortable" data-col="3" data-type="num">期末 <span class="sort-icon">↕</span></th>
          <th class="th-r col-sep sortable" data-col="4" data-type="num" style="font-size:9px;color:#a8b8a8;">期初 <span class="sort-icon">↕</span></th>
          <th class="th-r sortable" data-col="5" data-type="num">期末 <span class="sort-icon">↕</span></th>
          <th class="th-r col-sep sortable" data-col="6" data-type="num" style="font-size:9px;color:#a8b8a8;">期初 <span class="sort-icon">↕</span></th>
          <th class="th-r sortable" data-col="7" data-type="num">期末 <span class="sort-icon">↕</span></th>
          <th class="th-r col-sep sortable" data-col="8" data-type="num" style="font-size:9px;color:#a8b8a8;">持倉 <span class="sort-icon">↕</span></th>
          <th class="th-r sortable" data-col="9" data-type="num">交易 <span class="sort-icon">↕</span></th>
        </tr>
      </thead>
      <tbody>{stock_open_rows if stock_open_rows else '<tr><td colspan="12" class="empty-state">無持倉股票</td></tr>'}{stock_open_total}</tbody>
    </table></div>
  </div>
  <div class="data-card" style="margin-bottom:16px;">
    <div class="data-card-header" id="mtm-stk-closed"><span class="card-title">股票平倉</span><span class="card-badge" style="background:#f1f5f1;color:#8a9e8c;border-color:#d4e4d4;">{len(stocks_closed)} 個代碼</span></div>
    <div style="overflow-x:auto;"><table class="sortable-table" id="tbl-stock-closed">
      <thead>
        <tr style="background:#f6fbf6;border-bottom:1px solid #e8f0e8;">
          <th class="th-group sortable" rowspan="2" data-col="0" data-type="str" style="text-align:left;vertical-align:bottom;padding:9px 12px;border-bottom:2px solid #e8f0e8;">代碼 <span class="sort-icon">↕</span></th>
          <th class="th-group sortable" rowspan="2" data-col="1" data-type="str" style="text-align:left;vertical-align:bottom;padding:9px 12px;border-bottom:2px solid #e8f0e8;">名稱 <span class="sort-icon">↕</span></th>
          <th class="th-group" colspan="2" style="border-left:1px solid #e8f0e8;">持倉數量</th>
          <th class="th-group" colspan="2" style="border-left:1px solid #e8f0e8;">價格</th>
          <th class="th-group" colspan="2" style="border-left:1px solid #e8f0e8;">市值</th>
          <th class="th-group" colspan="2" style="border-left:1px solid #e8f0e8;">持倉 / 交易盈虧</th>
          <th class="th-group sortable" rowspan="2" data-col="10" data-type="num" style="text-align:right;vertical-align:bottom;padding:9px 12px;border-bottom:2px solid #e8f0e8;border-left:1px solid #e8f0e8;">佣金 <span class="sort-icon">↕</span></th>
          <th class="th-group sortable" rowspan="2" data-col="11" data-type="num" style="text-align:right;vertical-align:bottom;padding:9px 12px;border-bottom:2px solid #e8f0e8;border-left:1px solid #e8f0e8;">總盈虧 <span class="sort-icon">↕</span></th>
        </tr>
        <tr class="table-head-row">
          <th class="th-r col-sep sortable" data-col="2" data-type="num" style="font-size:9px;color:#a8b8a8;">期初 <span class="sort-icon">↕</span></th>
          <th class="th-r sortable" data-col="3" data-type="num">期末 <span class="sort-icon">↕</span></th>
          <th class="th-r col-sep sortable" data-col="4" data-type="num" style="font-size:9px;color:#a8b8a8;">期初 <span class="sort-icon">↕</span></th>
          <th class="th-r sortable" data-col="5" data-type="num">期末 <span class="sort-icon">↕</span></th>
          <th class="th-r col-sep sortable" data-col="6" data-type="num" style="font-size:9px;color:#a8b8a8;">期初 <span class="sort-icon">↕</span></th>
          <th class="th-r sortable" data-col="7" data-type="num">期末 <span class="sort-icon">↕</span></th>
          <th class="th-r col-sep sortable" data-col="8" data-type="num" style="font-size:9px;color:#a8b8a8;">持倉 <span class="sort-icon">↕</span></th>
          <th class="th-r sortable" data-col="9" data-type="num">交易 <span class="sort-icon">↕</span></th>
        </tr>
      </thead>
      <tbody>{stock_closed_rows if stock_closed_rows else '<tr><td colspan="12" class="empty-state">無平倉股票</td></tr>'}{stock_closed_total}</tbody>
    </table></div>
  </div>
  <div class="data-card" style="margin-bottom:16px;">
    <div class="data-card-header" id="mtm-opt-open"><span class="card-title">期權持倉</span><span class="card-badge">{len(opts_open)} 張合約</span></div>
    <div style="overflow-x:auto;"><table class="sortable-table" id="tbl-opt-open">
      <thead>
        <tr style="background:#f6fbf6;border-bottom:1px solid #e8f0e8;">
          <th class="th-group sortable" rowspan="2" data-col="0" data-type="str" style="text-align:left;vertical-align:bottom;padding:9px 12px;border-bottom:2px solid #e8f0e8;">合約 <span class="sort-icon">↕</span></th>
          <th class="th-group sortable" rowspan="2" data-col="1" data-type="str" style="text-align:left;vertical-align:bottom;padding:9px 12px;border-bottom:2px solid #e8f0e8;">描述 <span class="sort-icon">↕</span></th>
          <th class="th-group" colspan="2" style="border-left:1px solid #e8f0e8;">數量</th>
          <th class="th-group" colspan="2" style="border-left:1px solid #e8f0e8;">價格</th>
          <th class="th-group" colspan="2" style="border-left:1px solid #e8f0e8;">市值</th>
          <th class="th-group" colspan="2" style="border-left:1px solid #e8f0e8;">盈虧</th>
          <th class="th-group sortable" rowspan="2" data-col="10" data-type="num" style="text-align:right;vertical-align:bottom;padding:9px 12px;border-bottom:2px solid #e8f0e8;border-left:1px solid #e8f0e8;">佣金 <span class="sort-icon">↕</span></th>
          <th class="th-group sortable" rowspan="2" data-col="11" data-type="num" style="text-align:right;vertical-align:bottom;padding:9px 12px;border-bottom:2px solid #e8f0e8;border-left:1px solid #e8f0e8;">總盈虧 <span class="sort-icon">↕</span></th>
        </tr>
        <tr class="table-head-row">
          <th class="th-r col-sep sortable" data-col="2" data-type="num" style="font-size:9px;color:#a8b8a8;">期初 <span class="sort-icon">↕</span></th>
          <th class="th-r sortable" data-col="3" data-type="num">期末 <span class="sort-icon">↕</span></th>
          <th class="th-r col-sep sortable" data-col="4" data-type="num" style="font-size:9px;color:#a8b8a8;">期初 <span class="sort-icon">↕</span></th>
          <th class="th-r sortable" data-col="5" data-type="num">期末 <span class="sort-icon">↕</span></th>
          <th class="th-r col-sep sortable" data-col="6" data-type="num" style="font-size:9px;color:#a8b8a8;">期初 <span class="sort-icon">↕</span></th>
          <th class="th-r sortable" data-col="7" data-type="num">期末 <span class="sort-icon">↕</span></th>
          <th class="th-r col-sep sortable" data-col="8" data-type="num" style="font-size:9px;color:#a8b8a8;">持倉 <span class="sort-icon">↕</span></th>
          <th class="th-r sortable" data-col="9" data-type="num">交易 <span class="sort-icon">↕</span></th>
        </tr>
      </thead>
      <tbody>{opt_open_rows if opt_open_rows else '<tr><td colspan="13" class="empty-state">無持倉期權</td></tr>'}{opt_open_total}</tbody>
    </table></div>
  </div>
  <div class="data-card">
    <div class="data-card-header" id="mtm-opt-closed"><span class="card-title">期權平倉</span><span class="card-badge" style="background:#f1f5f1;color:#8a9e8c;border-color:#d4e4d4;">{len(opts_closed)} 張合約</span></div>
    <div style="overflow-x:auto;"><table class="sortable-table" id="tbl-opt-closed">
      <thead>
        <tr style="background:#f6fbf6;border-bottom:1px solid #e8f0e8;">
          <th class="th-group sortable" rowspan="2" data-col="0" data-type="str" style="text-align:left;vertical-align:bottom;padding:9px 12px;border-bottom:2px solid #e8f0e8;">合約 <span class="sort-icon">↕</span></th>
          <th class="th-group sortable" rowspan="2" data-col="1" data-type="str" style="text-align:left;vertical-align:bottom;padding:9px 12px;border-bottom:2px solid #e8f0e8;">描述 <span class="sort-icon">↕</span></th>
          <th class="th-group" colspan="2" style="border-left:1px solid #e8f0e8;">數量</th>
          <th class="th-group" colspan="2" style="border-left:1px solid #e8f0e8;">價格</th>
          <th class="th-group" colspan="2" style="border-left:1px solid #e8f0e8;">市值</th>
          <th class="th-group" colspan="2" style="border-left:1px solid #e8f0e8;">盈虧</th>
          <th class="th-group sortable" rowspan="2" data-col="10" data-type="num" style="text-align:right;vertical-align:bottom;padding:9px 12px;border-bottom:2px solid #e8f0e8;border-left:1px solid #e8f0e8;">佣金 <span class="sort-icon">↕</span></th>
          <th class="th-group sortable" rowspan="2" data-col="11" data-type="num" style="text-align:right;vertical-align:bottom;padding:9px 12px;border-bottom:2px solid #e8f0e8;border-left:1px solid #e8f0e8;">總盈虧 <span class="sort-icon">↕</span></th>
        </tr>
        <tr class="table-head-row">
          <th class="th-r col-sep sortable" data-col="2" data-type="num" style="font-size:9px;color:#a8b8a8;">期初 <span class="sort-icon">↕</span></th>
          <th class="th-r sortable" data-col="3" data-type="num">期末 <span class="sort-icon">↕</span></th>
          <th class="th-r col-sep sortable" data-col="4" data-type="num" style="font-size:9px;color:#a8b8a8;">期初 <span class="sort-icon">↕</span></th>
          <th class="th-r sortable" data-col="5" data-type="num">期末 <span class="sort-icon">↕</span></th>
          <th class="th-r col-sep sortable" data-col="6" data-type="num" style="font-size:9px;color:#a8b8a8;">期初 <span class="sort-icon">↕</span></th>
          <th class="th-r sortable" data-col="7" data-type="num">期末 <span class="sort-icon">↕</span></th>
          <th class="th-r col-sep sortable" data-col="8" data-type="num" style="font-size:9px;color:#a8b8a8;">持倉 <span class="sort-icon">↕</span></th>
          <th class="th-r sortable" data-col="9" data-type="num">交易 <span class="sort-icon">↕</span></th>
        </tr>
      </thead>
      <tbody>{opt_closed_rows if opt_closed_rows else '<tr><td colspan="13" class="empty-state">無平倉期權</td></tr>'}{opt_closed_total}</tbody>
    </table></div>
  </div>
</div>

<!-- ══════════ 存款和取款 ══════════ -->
<div id="main-tab-withdrawals" class="main-panel hidden">
  <div class="data-card">
    <div class="data-card-header"><span class="card-title">存款和取款</span></div>
    <div style="overflow-x:auto;"><table><thead><tr class="table-head-row">
      <th class="th-l">日期</th><th class="th-l">幣別</th><th class="th-l">描述</th><th class="th-r">金額</th>
    </tr></thead>
    <tbody>{wdr_rows_html if wdr_rows_html else '<tr><td colspan="4" class="empty-state">無存款和取款記錄</td></tr>'}</tbody></table></div>
    {'<div class="summary-total"><span style="font-size:12px;font-weight:600;color:#374840;">合計</span><span class="font-mono ' + pnl_class(sum(w["amount"] for w in wdrs)) + '" style="font-size:13px;font-weight:600;">' + pnl_fmt(sum(w["amount"] for w in wdrs)) + '</span></div>' if wdrs else ''}
  </div>
</div>

<!-- ══════════ 股息 ══════════ -->
<div id="main-tab-dividends" class="main-panel hidden">
  <div class="data-card">
    <div class="data-card-header"><span class="card-title">股息收入</span><span class="card-badge">+{fmt_usd(divid)}</span></div>
    <div style="overflow-x:auto;"><table><thead><tr class="table-head-row">
      <th class="th-l">日期</th><th class="th-l">幣別</th><th class="th-l">描述</th><th class="th-r">金額</th>
    </tr></thead>
    <tbody>{div_rows_html if div_rows_html else '<tr><td colspan="4" class="empty-state">無股息記錄</td></tr>'}</tbody></table></div>
    {'<div class="summary-total"><span style="font-size:12px;font-weight:600;color:#374840;">合計</span><span class="font-mono pos" style="font-size:13px;font-weight:600;">+' + fmt_usd(divid) + '</span></div>' if divs else ''}
  </div>
</div>

<!-- ══════════ 代扣稅款 ══════════ -->
<div id="main-tab-withholding" class="main-panel hidden">
  <div class="data-card">
    <div class="data-card-header"><span class="card-title">代扣稅款</span><span class="card-badge card-badge-red">{pnl_fmt(wh_total_val)}</span></div>
    <div style="overflow-x:auto;"><table><thead><tr class="table-head-row">
      <th class="th-l">日期</th><th class="th-l">幣別</th><th class="th-l">描述</th><th class="th-r">金額</th>
    </tr></thead>
    <tbody>{wh_rows_html if wh_rows_html else '<tr><td colspan="4" class="empty-state">無代扣稅記錄</td></tr>'}</tbody></table></div>
  </div>
</div>

<!-- ══════════ 應計股息的變化 ══════════ -->
<div id="main-tab-div-accruals" class="main-panel hidden">
  <div class="data-card">
    <div class="data-card-header"><span class="card-title">應計股息的變化</span><span class="card-badge">{pnl_fmt(sum(i['amount'] for i in div_accr_items))}</span></div>
    <div style="overflow-x:auto;"><table><thead><tr class="table-head-row">
      <th class="th-l">代碼</th><th class="th-l">幣別</th><th class="th-r">淨額</th>
    </tr></thead>
    <tbody>{div_accr_rows_html if div_accr_rows_html else '<tr><td colspan="3" class="empty-state">無應計股息記錄</td></tr>'}</tbody></table></div>
    {'<div class="summary-total"><span style="font-size:12px;font-weight:600;color:#374840;">合計</span><span class="font-mono ' + pnl_class(sum(i["amount"] for i in div_accr_items)) + '" style="font-size:13px;font-weight:600;">' + pnl_fmt(sum(i["amount"] for i in div_accr_items)) + '</span></div>' if div_accr_items else ''}
  </div>
</div>

<!-- ══════════ 利息 ══════════ -->
<div id="main-tab-interest" class="main-panel hidden">
  <div class="data-card">
    <div class="data-card-header"><span class="card-title">利息明細</span><span class="card-badge {'card-badge-red' if intst < 0 else ''}">{pnl_fmt(intst)}</span></div>
    <div style="overflow-x:auto;"><table><thead><tr class="table-head-row">
      <th class="th-l">日期</th><th class="th-l">幣別</th><th class="th-l">描述</th><th class="th-r">金額</th>
    </tr></thead>
    <tbody>{int_rows_html if int_rows_html else '<tr><td colspan="4" class="empty-state">無利息記錄</td></tr>'}</tbody></table></div>
    {'<div class="summary-total"><span style="font-size:12px;font-weight:600;color:#374840;">合計</span><span class="font-mono ' + pnl_class(intst) + '" style="font-size:13px;font-weight:600;">' + pnl_fmt(intst) + '</span></div>' if int_items else ''}
  </div>
</div>

<!-- ══════════ 應計利息變更 ══════════ -->
<div id="main-tab-int-accruals" class="main-panel hidden">
  <div class="data-card">
    <div class="data-card-header"><span class="card-title">應計利息變更</span><span class="card-badge">{pnl_fmt(sum(i['amount'] for i in int_accr_items))}</span></div>
    <div style="overflow-x:auto;"><table><thead><tr class="table-head-row">
      <th class="th-l">日期</th><th class="th-l">幣別</th><th class="th-l">描述</th><th class="th-r">金額</th>
    </tr></thead>
    <tbody>{int_accr_rows_html if int_accr_rows_html else '<tr><td colspan="4" class="empty-state">無應計利息記錄</td></tr>'}</tbody></table></div>
    {'<div class="summary-total"><span style="font-size:12px;font-weight:600;color:#374840;">合計</span><span class="font-mono ' + pnl_class(sum(i["amount"] for i in int_accr_items)) + '" style="font-size:13px;font-weight:600;">' + pnl_fmt(sum(i["amount"] for i in int_accr_items)) + '</span></div>' if int_accr_items else ''}
  </div>
</div>

<!-- ══════════ 其它費用 ══════════ -->
<div id="main-tab-fees" class="main-panel hidden">
  <div class="data-card">
    <div class="data-card-header"><span class="card-title">其它費用明細</span><span class="card-badge card-badge-red">{pnl_fmt(ofees)}</span></div>
    <div style="overflow-x:auto;"><table><thead><tr class="table-head-row">
      <th class="th-l">日期</th><th class="th-l">描述</th><th class="th-r">金額</th>
    </tr></thead>
    <tbody>{fee_rows_html if fee_rows_html else '<tr><td colspan="3" class="empty-state">無費用記錄</td></tr>'}</tbody></table></div>
    {'<div class="summary-total"><span style="font-size:12px;font-weight:600;color:#374840;">合計</span><span class="font-mono neg" style="font-size:13px;font-weight:600;">' + pnl_fmt(ofees) + '</span></div>' if fees else ''}
  </div>
</div>

<!-- ══════════ 佣金 ══════════ -->
<div id="main-tab-commissions" class="main-panel hidden">
  <div class="data-card">
    <div class="data-card-header"><span class="card-title">佣金明細</span><span class="card-badge card-badge-red">{pnl_fmt(comm_total_val)}</span></div>
    <div style="overflow-x:auto;"><table><thead><tr class="table-head-row">
      <th class="th-l">代碼</th><th class="th-l">名稱 / 描述</th><th class="th-r">佣金</th>
    </tr></thead>
    <tbody>{comm_rows_html if comm_rows_html else '<tr><td colspan="3" class="empty-state">無佣金記錄</td></tr>'}</tbody></table></div>
    {'<div class="summary-total"><span style="font-size:12px;font-weight:600;color:#374840;">合計</span><span class="font-mono neg" style="font-size:13px;font-weight:600;">' + pnl_fmt(comm_total_val) + '</span></div>' if comm_rows_html else ''}
  </div>
</div>


</div><!-- end container -->

<footer style="text-align:center;padding:20px;font-size:11px;color:#8a9e8c;border-top:1px solid #e8f0e8;margin-top:8px;font-family:'IBM Plex Mono',monospace;">
  IB 結單儀表板 &nbsp;·&nbsp; 數據來自 Interactive Brokers &nbsp;·&nbsp; 僅供參考
</footer>

<script>
const NAV_DATA   = {chart_data_js};
const STOCK_DATA = {stock_chart_js};

const GRID   = 'rgba(166,208,170,0.35)';
const TICK   = '#8a9e8c';
const TT     = {{
  backgroundColor: '#ffffff',
  borderColor: '#d4e4d4',
  borderWidth: 1,
  titleColor: '#374840',
  bodyColor:  '#1c2b1e',
  padding: 10,
  cornerRadius: 5,
  callbacks: {{
    label: ctx => (ctx.raw >= 0 ? ' +' : ' ') + '$' + Math.abs(ctx.raw).toLocaleString('en-US', {{minimumFractionDigits:2}})
  }}
}};
const FONT = {{ family: 'IBM Plex Mono' }};

new Chart(document.getElementById('navChart'), {{
  type: 'bar',
  data: {{
    labels: NAV_DATA.labels,
    datasets: [{{ data: NAV_DATA.values, backgroundColor: NAV_DATA.colors, borderRadius: 4, borderSkipped: false }}]
  }},
  options: {{
    responsive: true, maintainAspectRatio: false,
    plugins: {{ legend: {{ display: false }}, tooltip: TT }},
    scales: {{
      x: {{ grid: {{ color: GRID }}, ticks: {{ color: TICK, font: {{ ...FONT, size: 10 }} }} }},
      y: {{ grid: {{ color: GRID }}, ticks: {{ color: TICK, font: {{ ...FONT, size: 10 }}, callback: v => '$' + (Math.abs(v)/1000).toFixed(1) + 'k' }} }}
    }}
  }}
}});

new Chart(document.getElementById('stockChart'), {{
  type: 'bar',
  data: {{
    labels: STOCK_DATA.labels,
    datasets: [{{ data: STOCK_DATA.values, backgroundColor: STOCK_DATA.colors, borderRadius: 4, borderSkipped: false }}]
  }},
  options: {{
    responsive: true, maintainAspectRatio: false,
    plugins: {{ legend: {{ display: false }}, tooltip: TT }},
    scales: {{
      x: {{ grid: {{ display: false }}, ticks: {{ color: TICK, font: {{ ...FONT, size: 11 }} }} }},
      y: {{ grid: {{ color: GRID }}, ticks: {{ color: TICK, font: {{ ...FONT, size: 10 }}, callback: v => '$' + Math.round(Math.abs(v)) }} }}
    }}
  }}
}});

// ── Table sorting ──
document.querySelectorAll('.sortable-table').forEach(function(table) {{
  var state = {{ col: null, asc: true }};
  table.querySelectorAll('th.sortable').forEach(function(th) {{
    th.addEventListener('click', function() {{
      var col  = parseInt(th.dataset.col);
      var type = th.dataset.type || 'str';
      if (state.col === col) {{
        state.asc = !state.asc;
      }} else {{
        state.col = col;
        state.asc = (type === 'str');
      }}
      table.querySelectorAll('th.sortable').forEach(function(h) {{
        h.classList.remove('sort-asc', 'sort-desc');
      }});
      th.classList.add(state.asc ? 'sort-asc' : 'sort-desc');
      var tbody = table.querySelector('tbody');
      // Build groups: each group = [summary row, ...detail rows]
      // Detail rows have class starting with "det-" or "comm-child-"
      var groups = [];
      var allRows = Array.from(tbody.querySelectorAll('tr'));
      allRows.forEach(function(r) {{
        var isChild = Array.from(r.classList).some(function(c) {{
          return c.startsWith('det-') || c.startsWith('comm-child-');
        }});
        if (!isChild) {{
          groups.push([r]);
        }} else if (groups.length > 0) {{
          groups[groups.length - 1].push(r);
        }}
      }});
      // Sort by the summary row (first row of each group)
      groups.sort(function(a, b) {{
        var aCell = a[0].querySelectorAll('td')[col];
        var bCell = b[0].querySelectorAll('td')[col];
        if (!aCell || !bCell) return 0;
        var aVal = aCell.dataset.val !== undefined ? aCell.dataset.val : aCell.textContent.trim();
        var bVal = bCell.dataset.val !== undefined ? bCell.dataset.val : bCell.textContent.trim();
        var cmp  = (type === 'num') ? ((parseFloat(aVal) || 0) - (parseFloat(bVal) || 0)) : aVal.localeCompare(bVal, 'zh-Hant');
        return state.asc ? cmp : -cmp;
      }});
      // Re-append groups in sorted order (keeping detail rows with their parent)
      groups.forEach(function(group) {{
        group.forEach(function(r) {{ tbody.appendChild(r); }});
      }});
    }});
  }});
}});

function showMain(id, btn) {{
  document.querySelectorAll('.main-panel').forEach(p => p.classList.add('hidden'));
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('main-' + id).classList.remove('hidden');
  if (btn) btn.classList.add('active');
  else {{
    document.querySelectorAll('.nav-btn').forEach(b => {{
      if (b.getAttribute('onclick') && b.getAttribute('onclick').includes("'" + id + "'")) b.classList.add('active');
    }});
  }}
}}

function toggleDet(uid, arrow) {{
  var rows = document.querySelectorAll('.det-' + uid);
  var open = rows.length > 0 && rows[0].style.display !== 'none';
  rows.forEach(function(r) {{ r.style.display = open ? 'none' : 'table-row'; }});
  if (arrow) arrow.style.transform = open ? '' : 'rotate(-90deg)';
}}

function toggleComm(uid) {{
  var rows = document.querySelectorAll('.comm-child-' + uid);
  var arrow = document.getElementById('arr-' + uid);
  var open = rows.length > 0 && rows[0].style.display !== 'none';
  rows.forEach(function(r) {{ r.style.display = open ? 'none' : 'table-row'; }});
  if (arrow) arrow.style.transform = open ? '' : 'rotate(-90deg)';
}}

function toggleMtm(row) {{
  var children = row.nextElementSibling;
  if (!children || !children.classList.contains('mtm-children')) return;
  var open = children.style.display !== 'none';
  children.style.display = open ? 'none' : 'block';
  var arrow = row.querySelector('.mtm-arrow');
  if (arrow) arrow.style.transform = open ? '' : 'rotate(-90deg)';
}}

const inp  = document.getElementById('csvInput');
const drop = document.getElementById('dropZone');
drop.addEventListener('dragover',  e => {{ e.preventDefault(); drop.classList.add('drag'); }});
drop.addEventListener('dragleave', () => drop.classList.remove('drag'));
drop.addEventListener('drop', e => {{
  e.preventDefault(); drop.classList.remove('drag');
  if (e.dataTransfer.files[0]) loadFile(e.dataTransfer.files[0]);
}});
inp.addEventListener('change', () => {{ if (inp.files[0]) loadFile(inp.files[0]); }});

function loadFile(file) {{
  const fd = new FormData();
  fd.append('file', file);
  fetch('/upload', {{ method: 'POST', body: fd }})
    .then(r => r.text())
    .then(html => {{ document.open(); document.write(html); document.close(); }})
    .catch(e => alert('上載失敗: ' + e));
}}


</script>
</body>
</html>"""
    return html
