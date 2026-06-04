"""Index definitions and constituent lists.

Kite Connect does NOT expose index constituents, so they are configured here
and resolved against the live instrument master at sync time (symbols not found
are logged and skipped). These lists are a SNAPSHOT and must be refreshed from
NSE's official index CSVs periodically (constituents change ~semi-annually):
  Nifty 50:   https://www.niftyindices.com (ind_nifty50list.csv)
  Bank Nifty: https://www.niftyindices.com (ind_niftybanklist.csv)

The index instruments themselves (NIFTY 50 / NIFTY BANK) come from the
instrument master and are stored as INDEX-type instruments.
"""

# (index tradingsymbol as it appears in the NSE instrument master)
INDEX_DEFINITIONS: list[dict[str, str]] = [
    {"symbol": "NIFTY 50", "name": "NIFTY 50"},
    {"symbol": "NIFTY BANK", "name": "NIFTY BANK"},
]

NIFTY50_SYMBOLS: list[str] = [
    "ADANIENT", "ADANIPORTS", "APOLLOHOSP", "ASIANPAINT", "AXISBANK",
    "BAJAJ-AUTO", "BAJFINANCE", "BAJAJFINSV", "BEL", "BHARTIARTL",
    "BPCL", "BRITANNIA", "CIPLA", "COALINDIA", "DRREDDY",
    "EICHERMOT", "GRASIM", "HCLTECH", "HDFCBANK", "HDFCLIFE",
    "HEROMOTOCO", "HINDALCO", "HINDUNILVR", "ICICIBANK", "INDUSINDBK",
    "INFY", "ITC", "JSWSTEEL", "KOTAKBANK", "LT",
    "LTIM", "M&M", "MARUTI", "NESTLEIND", "NTPC",
    "ONGC", "POWERGRID", "RELIANCE", "SBILIFE", "SBIN",
    "SHRIRAMFIN", "SUNPHARMA", "TATACONSUM", "TATAMOTORS", "TATASTEEL",
    "TCS", "TECHM", "TITAN", "ULTRACEMCO", "WIPRO",
]

BANKNIFTY_SYMBOLS: list[str] = [
    "AUBANK", "AXISBANK", "BANKBARODA", "CANBK", "FEDERALBNK",
    "HDFCBANK", "ICICIBANK", "IDFCFIRSTB", "INDUSINDBK", "KOTAKBANK",
    "PNB", "SBIN",
]

CONSTITUENTS: dict[str, list[str]] = {
    "NIFTY 50": NIFTY50_SYMBOLS,
    "NIFTY BANK": BANKNIFTY_SYMBOLS,
}

# Selector keywords accepted by the historical-sync API.
SELECTOR_NIFTY50 = "NIFTY50"
SELECTOR_BANKNIFTY = "BANKNIFTY"
SELECTOR_ALL = "ALL"

SELECTOR_TO_INDEX = {
    SELECTOR_NIFTY50: "NIFTY 50",
    SELECTOR_BANKNIFTY: "NIFTY BANK",
}
