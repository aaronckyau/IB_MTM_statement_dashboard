"""Prepares template context from parsed data, then renders via Jinja2."""

import json
from collections import defaultdict
from flask import render_template


# ── Formatting helpers (also used by template via filters) ──────────────────

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

def dash(v, fmt_fn=None):
    if v == 0: return "—"
    return fmt_fn(v) if fmt_fn else str(v)

def fmt_px2(v):
    return f"${v:,.2f}"

def fmt_px4(v):
    return f"${v:,.4f}"

def fmt_qty(v):
    return f"{v:g}"

def _effective_pnl(item):
    return item['pos_pnl'] + item['trd_pnl']


# ── Detail row helpers ───────────────────────────────────────────────────────

def _build_stk_det_map(stk_det):
    m = defaultdict(list)
    for d in stk_det:
        m[(d['ticker'], d.get('_summary_idx', 0))].append(d)
    return m

def _build_opt_det_map(opt_det):
    m = defaultdict(list)
    for d in opt_det:
        m[(d['contract'], d.get('_summary_idx', 0))].append(d)
    return m


# ── Reconciliation rows ──────────────────────────────────────────────────────

CHG_TAB = {
    '按市值計價':     'mtm',
    '存款和取款':     'tab-withdrawals',
    '股息':           'tab-dividends',
    '代扣稅款':       'tab-withholding',
    '應計股息的變化': 'tab-div-accruals',
    '利息':           'tab-interest',
    '應計利息變更':   'tab-int-accruals',
    '其它費用':       'tab-fees',
    '佣金':           'tab-commissions',
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


# ── Symbol lookup data ───────────────────────────────────────────────────────

def _build_sym_data(stocks, opts, fx=None):
    sym_data = {}
    for s in stocks:
        e = sym_data.setdefault(s['ticker'], {'stk_open': [], 'stk_closed': [], 'opt_open': [], 'opt_closed': [], 'fx': []})
        rec = {
            'ticker': s['ticker'], 'name': s['name'],
            'qty': s['qty'], 'px': s['px'], 'mv': s['mv'],
            'pos_pnl': s['pos_pnl'], 'trd_pnl': s['trd_pnl'],
            'comm': s['comm'], 'eff_pnl': round(_effective_pnl(s), 2),
        }
        e['stk_open' if s['qty'] != 0 else 'stk_closed'].append(rec)
    for o in opts:
        und = o['contract'].split()[0] if o['contract'] else o['contract']
        e = sym_data.setdefault(und, {'stk_open': [], 'stk_closed': [], 'opt_open': [], 'opt_closed': [], 'fx': []})
        rec = {
            'contract': o['contract'], 'desc': o['desc'],
            'qty': o['qty'], 'px': o['px'], 'mv': o['mv'],
            'pos_pnl': o['pos_pnl'], 'trd_pnl': o['trd_pnl'],
            'comm': o['comm'], 'eff_pnl': round(_effective_pnl(o), 2),
        }
        e['opt_open' if o['qty'] != 0 else 'opt_closed'].append(rec)
    for f in (fx or []):
        e = sym_data.setdefault(f['ccy'], {'stk_open': [], 'stk_closed': [], 'opt_open': [], 'opt_closed': [], 'fx': []})
        rec = {
            'ccy': f['ccy'], 'qty': f['qty'], 'prev_qty': f['prev_qty'],
            'rate': f['rate'], 'prev_rate': f['prev_rate'],
            'mv': f['mv'], 'prev_mv': f['prev_mv'],
            'pos_pnl': f['pos_pnl'], 'trd_pnl': f['trd_pnl'],
            'comm': f['comm'], 'eff_pnl': round(f['pos_pnl'] + f['trd_pnl'], 2),
        }
        e['fx'].append(rec)
    return sym_data


# ── Main context builder ─────────────────────────────────────────────────────

def build_context(data: dict) -> dict:
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

    start_nav = nav['start']
    end_nav   = nav['end']
    nav_chg   = nav['change']
    twr       = nav['twr']
    twr_display = twr if isinstance(twr, str) else f"{twr:.2f}%"

    mtm   = chg.get('mtm', 0)
    divid = chg.get('dividends', data['div_total'])
    withh = chg.get('withholding', data['wh_total'])
    intst = chg.get('interest', data['int_total_usd'])
    ofees = chg.get('other_fees', data['fee_total'])
    comms = chg.get('commissions', 0)

    # ── Stock / option groups ──
    stocks_open   = sorted([s for s in stocks if s['qty'] != 0],  key=lambda x: abs(_effective_pnl(x)), reverse=True)
    stocks_closed = sorted([s for s in stocks if s['qty'] == 0],  key=lambda x: abs(_effective_pnl(x)), reverse=True)
    opts_open     = sorted([o for o in opts   if o['qty'] != 0],  key=lambda x: abs(_effective_pnl(x)), reverse=True)
    opts_closed   = sorted([o for o in opts   if o['qty'] == 0],  key=lambda x: abs(_effective_pnl(x)), reverse=True)

    stk_open_pnl   = sum(_effective_pnl(s) for s in stocks_open)
    stk_closed_pnl = sum(_effective_pnl(s) for s in stocks_closed)
    opt_open_pnl   = sum(_effective_pnl(o) for o in opts_open)
    opt_closed_pnl = sum(_effective_pnl(o) for o in opts_closed)
    fx_pnl         = sum(f.get('pos_pnl', 0) + f.get('trd_pnl', 0) for f in fx)

    # ── Detail maps ──
    stk_det_map = _build_stk_det_map(stk_det)
    opt_det_map = _build_opt_det_map(opt_det)

    # Attach details + computed fields to each stock/option for template
    def enrich_stock(s):
        eff = _effective_pnl(s)
        tid = s['ticker'].replace(' ', '_').replace('/', '_').replace('.', '_') + f"_{s.get('_idx', 0)}"
        details = stk_det_map.get((s['ticker'], s.get('_idx', 0)), [])
        for d in details:
            d['cash_flow'] = -d['mv']
        return {**s, 'eff_pnl': eff, 'tid': tid, 'details': details if len(details) > 1 else []}

    def enrich_opt(o):
        eff = _effective_pnl(o)
        tid = o['contract'].replace(' ', '_').replace('/', '_').replace('.', '_') + f"_{o.get('_idx', 0)}"
        underlying = o['contract'].split()[0] if o['contract'] else o['contract']
        details = opt_det_map.get((o['contract'], o.get('_idx', 0)), [])
        for d in details:
            d['cash_flow'] = -d['mv']
        status = '持有' if o['qty'] > 0 else ('空頭' if o['qty'] < 0 else '已平倉')
        status_cls = 'badge-hold' if o['qty'] > 0 else ('badge-short' if o['qty'] < 0 else 'badge-closed')
        return {**o, 'eff_pnl': eff, 'tid': tid, 'underlying': underlying,
                'details': details if len(details) > 1 else [],
                'status': status, 'status_cls': status_cls}

    stocks_open_e   = [enrich_stock(s) for s in stocks_open]
    stocks_closed_e = [enrich_stock(s) for s in stocks_closed]
    opts_open_e     = [enrich_opt(o)   for o in opts_open]
    opts_closed_e   = [enrich_opt(o)   for o in opts_closed]

    # ── Totals ──
    def total_row(group):
        if not group: return None
        return {
            'count':    len(group),
            'prev_mv':  sum(s['prev_mv']      for s in group),
            'mv':       sum(s['mv']            for s in group),
            'pos_pnl':  sum(s['pos_pnl']       for s in group),
            'trd_pnl':  sum(s['trd_pnl']       for s in group),
            'comm':     sum(s['comm']           for s in group),
            'eff_pnl':  sum(s['eff_pnl']        for s in group),
        }

    # ── Chart data ──
    raw_rows   = data.get('nav_change_rows', [])
    chg_items  = [(r['label'], r['value']) for r in raw_rows if r['value'] != 0]
    recon_items = []
    for label, val in chg_items:
        tab_id = CHG_TAB.get(label)
        recon_items.append({'label': label, 'val': val, 'tab_id': tab_id, 'is_mtm': tab_id == 'mtm'})

    chart_labels = [l.replace('（', '(').replace('）', ')') for l, v in chg_items]
    chart_values = [round(v, 2) for l, v in chg_items]
    chart_colors = ['#15803d' if v > 0 else '#dc2626' for l, v in chg_items]

    top_stocks = sorted(stocks, key=lambda x: abs(_effective_pnl(x)), reverse=True)[:12]
    stock_chart = {
        'labels': [s['ticker'] for s in top_stocks],
        'values': [round(_effective_pnl(s), 2) for s in top_stocks],
        'colors': ['#15803d' if _effective_pnl(s) >= 0 else '#dc2626' for s in top_stocks],
    }

    # ── Commission groups ──
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

    comm_list = []
    comm_total_val = 0
    for sym in sorted(comm_groups.keys()):
        entries = comm_groups[sym]
        total_c = sum(e['amount'] for e in entries)
        comm_total_val += total_c
        comm_list.append({'sym': sym, 'entries': entries, 'total': total_c})

    # ── NAV detail ──
    nav_detail = nav.get('detail', {})
    label_map = {
        'Cash': '現金', 'Stock': '股票', 'Options': '期權',
        'Collateral': '抵押品', 'SecLent': '借出證券',
        'IntAccruals': '應計利息', 'DivAccruals': '應計股息',
    }
    nav_detail_rows = []
    for key, row in nav_detail.items():
        if key in ('Total', 'twr'): continue
        if not isinstance(row, dict): continue
        prior = row.get('prior', 0); total = row.get('total', 0); change = row.get('change', 0)
        if prior == 0 and total == 0: continue
        nav_detail_rows.append({'label': label_map.get(key, key), 'prior': prior, 'total': total, 'change': change})

    # ── Symbol lookup ──
    sym_data = _build_sym_data(stocks, opts, fx)

    # ── FX enriched ──
    fx_enriched = []
    for f in fx:
        fx_enriched.append({**f,
            'chg_qty':  f['qty'] - f['prev_qty'],
            'chg_rate': f['rate'] - f['prev_rate'] if f['prev_rate'] else 0,
            'chg_mv':   f['mv'] - f['prev_mv'],
        })

    # ── Conditional tab flags ──
    wh_items       = data.get('wh_items', [])
    div_accr_items = data.get('div_accrual_items', [])
    int_accr_items = data.get('int_accrual_items', [])
    wh_total_val   = sum(i['amount'] for i in wh_items) or data.get('wh_total', 0)

    return {
        # meta
        'period':       meta['period'],
        'acc_name':     meta['account_name'],
        'acc_id':       meta['account_id'],
        'twr_display':  twr_display,
        # nav
        'start_nav':    start_nav,
        'end_nav':      end_nav,
        'nav_chg':      nav_chg,
        'nav_chg_cls':  pnl_class(nav_chg),
        'mtm':          mtm,
        'mtm_cls':      pnl_class(mtm),
        'divid':        divid,
        'withh':        withh,
        'intst':        intst,
        'ofees':        ofees,
        'comms':        comms,
        # stocks / options
        'stocks_open':   stocks_open_e,
        'stocks_closed': stocks_closed_e,
        'opts_open':     opts_open_e,
        'opts_closed':   opts_closed_e,
        'stk_open_total':   total_row(stocks_open_e),
        'stk_closed_total': total_row(stocks_closed_e),
        'opt_open_total':   total_row(opts_open_e),
        'opt_closed_total': total_row(opts_closed_e),
        'stk_open_pnl':   stk_open_pnl,
        'stk_closed_pnl': stk_closed_pnl,
        'opt_open_pnl':   opt_open_pnl,
        'opt_closed_pnl': opt_closed_pnl,
        'fx_pnl':         fx_pnl,
        # fx / dividends / fees / interest
        'fx':           fx_enriched,
        'divs':         sorted(divs, key=lambda x: x['date']),
        'fees':         fees,
        'int_items':    int_items,
        'wdrs':         wdrs,
        'wdr_total':    sum(w['amount'] for w in wdrs),
        # income panels
        'wh_items':        wh_items,
        'wh_total_val':    wh_total_val,
        'div_accr_items':  div_accr_items,
        'int_accr_items':  int_accr_items,
        'div_total':       data['div_total'],
        'div_accr_total':  sum(i['amount'] for i in div_accr_items),
        'int_accr_total':  sum(i['amount'] for i in int_accr_items),
        # reconciliation
        'recon_items':  recon_items,
        'nav_chg_total': sum(r['val'] for r in recon_items),
        # chart
        'chart_data':   json.dumps({'labels': chart_labels, 'values': chart_values, 'colors': chart_colors}).replace('</', '<\\/'),
        'stock_chart':  json.dumps(stock_chart).replace('</', '<\\/'),
        # commission
        'comm_list':    comm_list,
        'comm_total':   comm_total_val,
        # nav detail
        'nav_detail_rows': nav_detail_rows,
        # symbol lookup
        'sym_data_json': json.dumps(sym_data).replace('</', '<\\/'),
        # helpers
        'fmt_usd':   fmt_usd,
        'pnl_fmt':   pnl_fmt,
        'pnl_class': pnl_class,
        'dash':      dash,
        'fmt_px2':   fmt_px2,
        'fmt_px4':   fmt_px4,
        'fmt_qty':   fmt_qty,
    }


def build_html(data: dict) -> str:
    ctx = build_context(data)
    return render_template('dashboard.html', **ctx)
