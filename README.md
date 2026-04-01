# IB Statement Dashboard

A local web dashboard for visualising Interactive Brokers account statements. Upload a CSV export from IB and instantly get a structured, interactive view of your portfolio performance.

![Finance Green theme — light background, forest green accents](https://img.shields.io/badge/theme-Finance%20Green-166534)
![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)
![Flask](https://img.shields.io/badge/flask-3.x-lightgrey)

---

## Features

| Section | Details |
|---------|---------|
| **總覽 Overview** | NAV reconciliation — every P&L source itemised and summed to equal the net change |
| **資產結構 NAV Detail** | Per-asset-class breakdown (Cash, Stock, Options, Accruals) with prior / current / change |
| **股票持倉 Stocks** | Open and closed positions separated, with sortable columns (qty, price, market value, P&L) |
| **期權持倉 Options** | Open and closed contracts separated, full column set, sortable |
| **外匯 FX** | Currency balances with prior / current qty, rate, market value, and P&L |
| **股息 / 利息 Income** | Dividend and interest line items with currency tags |
| **費用 Fees** | Market data fees, other charges |
| **存提款 Withdrawals** | Deposit and withdrawal history (shown only when data present) |

**P&L Reconciliation** — the Overview card breaks down:
- Stock open position P&L
- Stock closed position P&L
- Option open position P&L
- Option closed position P&L
- Dividends, withholding tax, interest, fees, commissions, FX translation, deposits/withdrawals

All items sum to equal **淨變動合計 (Net Change in NAV)**.

---

## Supported Statement Formats

| Format | Language |
|--------|----------|
| MTM Performance Summary | Traditional Chinese |
| MTM Performance Summary | English |
| Activity Statement | English |

Export from IB: **Reports → Statements → Activity** or **MTM Summary**, format **CSV**.

---

## Requirements

- Python 3.11+
- Flask 3.x

---

## Installation

```bash
# Clone the repository
git clone https://github.com/<your-username>/ib-statement.git
cd ib-statement

# Install dependencies
pip install -r requirements.txt
```

---

## Usage

```bash
python app.py
```

Open **http://localhost:5000** in your browser, then drag-and-drop or click to upload your IB CSV statement.

To switch statements, drag a new CSV onto the upload bar at the top of the dashboard — no page reload needed.

---

## Project Structure

```
ib-statement/
├── app.py                # Flask routes and landing page
├── parser.py             # CSV parser (MTM Summary + Activity Statement)
├── templates_builder.py  # HTML dashboard generator (Tailwind CSS)
├── requirements.txt
└── README.md
```

---

## Tech Stack

- **Backend** — Python / Flask (zero database, stateless)
- **Frontend** — Tailwind CSS (CDN), Chart.js, IBM Plex Sans / Mono, Libre Baskerville
- **Parsing** — Pure Python `csv` module, no pandas dependency

---

## Notes

- All processing is done locally — no data leaves your machine
- The dashboard is regenerated on every upload; no state is stored server-side
- P&L figures use `pos_pnl + trd_pnl` when `total_pnl` is zero (common in MTM Summary exports)

---

## License

MIT
