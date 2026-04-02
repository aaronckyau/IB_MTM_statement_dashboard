"""
IB MTM Summary CSV Parser
Supports both Chinese (MTM) and English (Activity) statement formats
"""
import csv
import re
from io import StringIO


def safe_float(val):
    try:
        return float(str(val).replace(',', '').strip())
    except:
        return 0.0


def parse_mtm_csv(content: str) -> dict:
    """Parse IB MTM Summary or Activity Statement CSV into structured dict."""
    if isinstance(content, bytes):
        content = content.decode('utf-8-sig')
    content = content.lstrip('\ufeff')

    reader = csv.reader(StringIO(content))
    rows = list(reader)

    # Detect language by checking section names
    section_names = set(r[0] for r in rows if r)
    is_chinese = '淨資産值' in section_names or '淨資产值' in section_names

    # Map Chinese → English section names
    CN = {
        '淨資産值': 'NAV', '淨資产值': 'NAV',
        '淨資産值變更': 'NAV_CHANGE', '淨資产值变更': 'NAV_CHANGE',
        '賬戶信息': 'ACCOUNT', '账户信息': 'ACCOUNT',
        '持倉與以市值計的盈虧': 'POSITIONS', '持仓与以市值计的盈亏': 'POSITIONS',
        '費用': 'FEES', '费用': 'FEES',
        '股息': 'DIVIDENDS',
        '代扣稅': 'WITHHOLDING', '代扣税': 'WITHHOLDING',
        '利息': 'INTEREST',
        '應計利息': 'INTEREST_ACCRUALS', '应计利息': 'INTEREST_ACCRUALS',
        '應計股息的變化': 'DIVIDEND_ACCRUALS',
        'Statement': 'STATEMENT',
        'Net Asset Value': 'NAV',
        'Change in NAV': 'NAV_CHANGE',
        'Account Information': 'ACCOUNT',
        'Mark-to-Market Performance Summary': 'POSITIONS',
        'Fees': 'FEES',
        'Dividends': 'DIVIDENDS',
        'Withholding Tax': 'WITHHOLDING',
        'Interest': 'INTEREST',
        'Interest Accruals': 'INTEREST_ACCRUALS',
        'Deposits & Withdrawals': 'WITHDRAWALS',
        '存款和取款': 'WITHDRAWALS',
        '存款和提款': 'WITHDRAWALS',
    }

    def sec(name):
        key = CN.get(name, name)
        return [r for r in rows if r and CN.get(r[0], r[0]) == key]

    # ── Statement info ──
    stmt_rows = sec('STATEMENT')
    period = next((r[3] for r in stmt_rows if r[1]=='Data' and r[2] in ('Period',)), '')
    title  = next((r[3] for r in stmt_rows if r[1]=='Data' and r[2] in ('Title',)), '')
    generated = next((r[3] for r in stmt_rows if r[1]=='Data' and r[2] in ('WhenGenerated',)), '')

    # ── Account info ──
    acct_rows = sec('ACCOUNT')
    def acct(keys):
        for r in acct_rows:
            if r[1]=='Data' and r[2] in keys:
                return r[3] if len(r)>3 else ''
        return ''
    account_name = acct(['名稱','Name'])
    account_id   = acct(['賬戶','Account','账户'])
    base_currency= acct(['基礎貨幣','Base Currency','基础货币'])

    # ── NAV ──
    nav_rows = sec('NAV')
    nav = {}
    for r in nav_rows:
        if r[1]!='Data': continue
        key = r[2]
        if key and len(r) >= 7:
            # prior_total, cur_long, cur_short, cur_total, change
            try:
                nav[key] = {
                    'prior': safe_float(r[3]),
                    'long':  safe_float(r[4]),
                    'short': safe_float(r[5]),
                    'total': safe_float(r[6]),
                    'change':safe_float(r[7]) if len(r)>7 else 0,
                }
            except:
                pass
        elif key and '%' in key:
            nav['twr'] = key.strip()

    # Normalise NAV keys
    NAV_MAP = {
        '總數':'Total','现金':'Cash','現金':'Cash','Cash ':'Cash','Cash':'Cash',
        '股票':'Stock','Stock':'Stock',
        '期權':'Options','Options':'Options',
        '抵押品價值':'Collateral','Collateral Value':'Collateral',
        '借出證券':'SecLent','Securities Lent':'SecLent',
        '應計利息':'IntAccruals','Interest Accruals':'IntAccruals',
        '應計股息':'DivAccruals','Dividend Accruals':'DivAccruals',
        'Time Weighted Rate of Return':'twr',
    }
    nav_clean = {}
    for k,v in nav.items():
        mapped = NAV_MAP.get(k, k)
        nav_clean[mapped] = v

    total_row = nav_clean.get('Total',{})
    start_nav = total_row.get('prior',0)
    end_nav   = total_row.get('total',0)
    twr = nav_clean.get('twr') or nav.get('twr','N/A')

    # ── NAV Change ──
    chg_rows = sec('NAV_CHANGE')
    nav_change = {}
    CHANGE_MAP = {
        '開始價值':'start','Starting Value':'start',
        '結束價值':'end','Ending Value':'end',
        '按市值計價':'mtm','Mark-to-Market':'mtm',
        '股息':'dividends','Dividends':'dividends',
        '代扣稅款':'withholding','Withholding Tax':'withholding',
        '利息':'interest','Interest':'interest',
        '其它費用':'other_fees','Other Fees':'other_fees',
        '佣金':'commissions','Commissions':'commissions',
        '其它外匯換算':'fx','Other FX Translations':'fx',
        '應計股息的變化':'div_accruals','Change in Dividend Accruals':'div_accruals',
        '應計利息變更':'int_accruals','Change in Interest Accruals':'int_accruals',
        'Deposits & Withdrawals':'withdrawals',
    }
    SKIP_CHG = {'開始價值','Starting Value','結束價值','Ending Value'}
    nav_change_rows = []  # [(label, value)] in CSV order, skipping start/end
    for r in chg_rows:
        if r[1]=='Data' and len(r)>=4:
            key = CHANGE_MAP.get(r[2], r[2])
            try:
                nav_change[key] = safe_float(r[3])
            except:
                pass
            if r[2] not in SKIP_CHG:
                try:
                    nav_change_rows.append({'label': r[2], 'value': safe_float(r[3])})
                except:
                    pass

    # ── Positions ──
    pos_rows = sec('POSITIONS')
    stocks, options, fx = [], [], []
    stock_details, option_details = [], []
    # Track current summary index per symbol to correctly bind Details to their Summary
    _cur_stk_idx = {}  # ticker -> current stock index
    _cur_opt_idx = {}  # contract -> current option index

    for r in pos_rows:
        if r[1] != 'Data': continue

        # Details rows — bind to the most recent Summary of same symbol
        if r[2] == 'Details' and len(r) >= 18:
            asset_type = r[3]
            if asset_type in ('股票','Stocks'):
                sym = r[5]
                idx = _cur_stk_idx.get(sym, 0)
                stock_details.append({
                    'ticker': sym, 'name': r[6], '_summary_idx': idx,
                    'prev_qty': safe_float(r[7]), 'qty': safe_float(r[8]),
                    'prev_px': safe_float(r[9]),  'px': safe_float(r[10]),
                    'prev_mv': safe_float(r[11]),  'mv': safe_float(r[12]),
                    'pos_pnl': safe_float(r[13]),  'trd_pnl': safe_float(r[14]),
                    'comm': safe_float(r[15]),      'other': safe_float(r[16]),
                    'total_pnl': safe_float(r[17]),
                })
            elif asset_type in ('股票和指數期權','Equity and Index Options'):
                sym = r[5]
                idx = _cur_opt_idx.get(sym, 0)
                option_details.append({
                    'contract': sym, 'desc': r[6], '_summary_idx': idx,
                    'prev_qty': safe_float(r[7]), 'qty': safe_float(r[8]),
                    'prev_px': safe_float(r[9]),  'px': safe_float(r[10]),
                    'prev_mv': safe_float(r[11]),  'mv': safe_float(r[12]),
                    'pos_pnl': safe_float(r[13]),  'trd_pnl': safe_float(r[14]),
                    'comm': safe_float(r[15]),      'other': safe_float(r[16]),
                    'total_pnl': safe_float(r[17]),
                })

        if r[2] != 'Summary': continue
        asset_type = r[3]
        # Chinese & English asset type detection
        is_stock  = asset_type in ('股票','Stocks')
        is_option = asset_type in ('股票和指數期權','Equity and Index Options')
        is_forex  = asset_type in ('外匯','Forex')

        if is_stock and len(r) >= 18:
            ticker = r[5]; name = r[6]
            prev_qty = safe_float(r[7]); qty = safe_float(r[8])
            prev_px = safe_float(r[9]); px = safe_float(r[10])
            prev_mv = safe_float(r[11]); mv = safe_float(r[12])
            pos_pnl = safe_float(r[13]); trd_pnl = safe_float(r[14])
            comm    = safe_float(r[15]); other   = safe_float(r[16])
            total_pnl = safe_float(r[17])
            idx = len(stocks)
            _cur_stk_idx[ticker] = idx
            stocks.append({'ticker':ticker,'name':name,'prev_qty':prev_qty,
                           'qty':qty,'prev_px':prev_px,'px':px,
                           'prev_mv':prev_mv,'mv':mv,
                           'pos_pnl':pos_pnl,'trd_pnl':trd_pnl,
                           'comm':comm,'other':other,'total_pnl':total_pnl,
                           '_idx':idx})

        elif is_option and len(r) >= 18:
            contract = r[5]; desc = r[6]
            prev_qty = safe_float(r[7]); qty = safe_float(r[8])
            prev_px = safe_float(r[9]); px = safe_float(r[10])
            prev_mv = safe_float(r[11]); mv = safe_float(r[12])
            pos_pnl = safe_float(r[13]); trd_pnl = safe_float(r[14])
            comm    = safe_float(r[15]); other   = safe_float(r[16])
            total_pnl = safe_float(r[17])
            idx = len(options)
            _cur_opt_idx[contract] = idx
            options.append({'contract':contract,'desc':desc,'prev_qty':prev_qty,
                            'qty':qty,'prev_px':prev_px,'px':px,
                            'prev_mv':prev_mv,'mv':mv,
                            'pos_pnl':pos_pnl,'trd_pnl':trd_pnl,
                            'comm':comm,'other':other,'total_pnl':total_pnl,
                            '_idx':idx})

        elif is_forex and len(r) >= 18:
            ccy = r[5]
            prev_qty = safe_float(r[7]); qty = safe_float(r[8])
            prev_rate= safe_float(r[9]); rate= safe_float(r[10])
            prev_mv = safe_float(r[11]); mv  = safe_float(r[12])
            comm      = safe_float(r[15])
            total_pnl = safe_float(r[17])
            fx.append({'ccy':ccy,'prev_qty':prev_qty,'qty':qty,
                       'prev_rate':prev_rate,'rate':rate,
                       'prev_mv':prev_mv,'mv':mv,'comm':comm,'total_pnl':total_pnl})

    # ── Dividends ──
    div_rows = sec('DIVIDENDS')
    dividends = []
    for r in div_rows:
        if r[1]=='Data' and len(r)>=4 and r[2]!='Total' and r[2] not in ('貨幣','Currency'):
            try:
                dividends.append({'currency':r[2],'date':r[3],'desc':r[4],'amount':safe_float(r[5])})
            except: pass
    div_total = sum(d['amount'] for d in dividends)

    # ── Withholding ──
    wh_rows = sec('WITHHOLDING')
    wh_total = 0
    for r in wh_rows:
        if r[1]=='Data' and r[2]=='Total' and len(r)>=4:
            try: wh_total = safe_float(r[3]); break
            except: pass

    # ── Fees ──
    fee_rows = sec('FEES')
    fees = []
    fee_total = 0
    for r in fee_rows:
        if r[1]=='Data' and r[2]!='Total' and len(r)>=7:
            try:
                fees.append({'date':r[4],'desc':r[5],'amount':safe_float(r[6])})
            except: pass
        if r[1] in ('Data','Total') and r[2]=='Total' and len(r)>=4:
            try: fee_total = safe_float(r[3])
            except: pass
    if not fee_total:
        fee_total = sum(f['amount'] for f in fees)

    # ── Interest ──
    int_rows = sec('INTEREST')
    interest_items = []
    int_total_usd = 0
    for r in int_rows:
        if r[1]=='Data' and r[2]=='Total in USD' and len(r)>=4:
            try: int_total_usd = safe_float(r[3])
            except: pass
        if r[1]=='Data' and r[2]=='Total Interest in USD' and len(r)>=4:
            try: int_total_usd = safe_float(r[3])
            except: pass
        if r[1]=='Data' and r[2] not in ('Total','Total in USD','Total Interest in USD') and len(r)>=5:
            try:
                interest_items.append({'currency':r[2],'date':r[3],'desc':r[4],'amount':safe_float(r[5])})
            except: pass

    # ── Withholding detail ──
    wh_items = []
    for r in wh_rows:
        if r[1]=='Data' and r[2] not in ('Total','貨幣','Currency') and len(r)>=5:
            try:
                wh_items.append({'currency':r[2],'date':r[3],'desc':r[4],'amount':safe_float(r[5])})
            except: pass

    # ── Dividend Accruals ──
    # Columns: A=section, B=Data, C=資產分類, D=貨幣, E=代碼, F=日期, G=除息日, H=支付日期,
    #          I=數量, J=稅, K=費用, L=總股息率, M=總額, N=淨額(index 13)
    div_accr_rows = sec('DIVIDEND_ACCRUALS')
    div_accrual_items = []
    for r in div_accr_rows:
        if r[1]=='Data' and r[2] not in ('總數','Total') and len(r)>=14:
            try:
                ticker = r[4]   # E=代碼
                net    = safe_float(r[13])  # N=淨額
                if ticker and ticker not in ('期初應計股息.USD','期初應計股息'):
                    div_accrual_items.append({'ticker':ticker,'currency':r[3],'amount':net})
            except: pass
    div_accrual_items.sort(key=lambda x: x['ticker'])

    # ── Interest Accruals ──
    int_accr_rows = sec('INTEREST_ACCRUALS')
    int_accrual_items = []
    for r in int_accr_rows:
        if r[1]=='Data' and r[2] not in ('Total','貨幣','Currency') and len(r)>=5:
            try:
                int_accrual_items.append({'currency':r[2],'date':r[3],'desc':r[4],'amount':safe_float(r[5])})
            except: pass

    # ── Withdrawals (Chinese + English) ──
    # Add Chinese section name to CN map lookup
    wdr_rows = sec('WITHDRAWALS')
    # Also try Chinese section name directly
    cn_wdr_rows = [r for r in rows if r and r[0] in ('存款和取款','存款和提款')]
    if cn_wdr_rows:
        wdr_rows = cn_wdr_rows
    withdrawals = []
    for r in wdr_rows:
        if r[1]=='Data' and r[2] not in ('Total','Total Deposits & Withdrawals in USD','貨幣','Currency') and len(r)>=5:
            if r[3] and r[4]:
                try:
                    withdrawals.append({'currency':r[2],'date':r[3],'desc':r[4],'amount':safe_float(r[5])})
                except: pass

    return {
        'meta': {'period':period,'title':title,'generated':generated,
                 'account_name':account_name,'account_id':account_id,
                 'base_currency':base_currency,'is_chinese':is_chinese},
        'nav': {'start':start_nav,'end':end_nav,'twr':twr,
                'change': end_nav - start_nav, 'detail': nav_clean},
        'nav_change': nav_change,
        'nav_change_rows': nav_change_rows,
        'stocks': stocks,
        'options': options,
        'stock_details': stock_details,
        'option_details': option_details,
        'fx': fx,
        'dividends': dividends,
        'div_total': div_total,
        'wh_total': wh_total,
        'fees': fees,
        'fee_total': fee_total,
        'interest_items': interest_items,
        'int_total_usd': int_total_usd,
        'withdrawals': withdrawals,
        'wh_items': wh_items,
        'div_accrual_items': div_accrual_items,
        'int_accrual_items': int_accrual_items,
    }


def parse_mtm_csv_v2(content: str) -> dict:
    """Enhanced parser: handles both MTM Summary AND Activity Statement formats."""
    base = parse_mtm_csv(content)

    if isinstance(content, bytes):
        content = content.decode('utf-8-sig')
    content = content.lstrip('\ufeff')

    import csv
    from io import StringIO
    rows = list(csv.reader(StringIO(content)))

    # If stocks/options are empty, try Open Positions (Activity Statement English)
    if not base['stocks']:
        for r in rows:
            if r and r[0] == 'Open Positions' and r[1] == 'Data' and r[2] == 'Summary':
                asset = r[3]
                if asset == 'Stocks' and len(r) >= 13:
                    ticker = r[5]; qty = safe_float(r[6])
                    cost_px = safe_float(r[8]); px = safe_float(r[10])
                    mv = safe_float(r[11]); upnl = safe_float(r[12])
                    # name from Financial Instrument Info if present
                    base['stocks'].append({
                        'ticker': ticker, 'name': ticker,
                        'prev_qty': qty, 'qty': qty,
                        'prev_px': cost_px, 'px': px,
                        'prev_mv': cost_px * qty, 'mv': mv,
                        'pos_pnl': upnl, 'trd_pnl': 0,
                        'comm': 0, 'other': 0, 'total_pnl': upnl
                    })
                elif asset == 'Equity and Index Options' and len(r) >= 13:
                    contract = r[5]; qty = safe_float(r[6])
                    cost_px = safe_float(r[8]); px = safe_float(r[10])
                    mv = safe_float(r[11]); upnl = safe_float(r[12])
                    base['options'].append({
                        'contract': contract, 'desc': contract,
                        'prev_qty': qty, 'qty': qty,
                        'prev_px': cost_px, 'px': px,
                        'prev_mv': cost_px * qty, 'mv': mv,
                        'pos_pnl': upnl, 'trd_pnl': 0,
                        'comm': 0, 'other': 0, 'total_pnl': upnl
                    })

    # Use stock names from Financial Instrument Information
    name_map = {}
    for r in rows:
        if r and r[0] == 'Financial Instrument Information' and r[1] == 'Data' and len(r) >= 4:
            if r[2] == 'Stocks' and len(r) >= 6:
                name_map[r[3]] = r[4]
    for s in base['stocks']:
        if s['ticker'] in name_map:
            s['name'] = name_map[s['ticker']]

    # Use MTM summary for total_pnl on Activity Statement (includes realized+unrealized)
    if name_map:  # only for English activity statement
        mtm_pnl = {}
        for r in rows:
            if r and r[0] == 'Mark-to-Market Performance Summary' and r[1] == 'Data':
                asset = r[2]
                if asset in ('Stocks', 'Equity and Index Options') and len(r) >= 14:
                    sym = r[3]
                    total = safe_float(r[13])
                    mtm_pnl[sym] = total
        for s in base['stocks']:
            if s['ticker'] in mtm_pnl:
                s['total_pnl'] = mtm_pnl[s['ticker']]
        for o in base['options']:
            contract_sym = o['contract'].split()[0] if o['contract'] else ''
            # Try full contract key first
            if o['contract'] in mtm_pnl:
                o['total_pnl'] = mtm_pnl[o['contract']]

    # Forex from Forex Balances
    if not base['fx']:
        for r in rows:
            if r and r[0] == 'Forex Balances' and r[1] == 'Data' and len(r) >= 11:
                ccy = r[2]; qty = safe_float(r[5])
                rate = safe_float(r[7]); mv = safe_float(r[9])
                upnl = safe_float(r[10])
                if ccy and ccy != 'USD':
                    base['fx'].append({
                        'ccy': ccy, 'prev_qty': qty, 'qty': qty,
                        'prev_rate': rate, 'rate': rate,
                        'prev_mv': mv, 'mv': mv, 'total_pnl': upnl
                    })

    return base
