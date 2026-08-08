"""
Sync the state-wise CPI dataset (base year 2024) from the MoSPI eSankhyiki API
into a local parquet file that ind_eco.py reads.

The API (https://api.mospi.gov.in/api/cpi/getCPIData) has no way to request
division-level rows only -- filtering by division_code also returns every
group/class/sub_class/item row beneath it, and pages are capped at 100 rows.
So instead of re-downloading the full item-level hierarchy on every run, this
script only pages through whichever (year, month) slices are requested and
keeps the division-level rows (group is null) client-side.

Usage:
    python fetch_cpi.py --seed-from-excel cpi_6.xlsx   # one-off: adopt existing export as history
    python fetch_cpi.py --recent-months 2              # incremental sync (used by CI)
    python fetch_cpi.py --year 2026 --month 6           # backfill one specific month
"""

import argparse
import datetime as dt
import ssl
import time
from pathlib import Path

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3 import PoolManager

API_URL = "https://api.mospi.gov.in/api/cpi/getCPIData"
HEADERS = {"User-Agent": "Mozilla/5.0"}
BASE_YEAR = "2024"
SERIES = "Current"
PAGE_SIZE = 100
REQUEST_DELAY = 0.2


class _LegacyRenegotiationAdapter(HTTPAdapter):
    """MoSPI's server requires legacy TLS renegotiation, which OpenSSL 3.x
    disables by default. Cert/hostname verification stays on -- only the
    renegotiation option is relaxed."""

    def __init__(self, ssl_context, **kwargs):
        self.ssl_context = ssl_context
        super().__init__(**kwargs)

    def init_poolmanager(self, connections, maxsize, block=False, **pool_kwargs):
        pool_kwargs["ssl_context"] = self.ssl_context
        self.poolmanager = PoolManager(num_pools=connections, maxsize=maxsize, block=block, **pool_kwargs)


def _make_session():
    ctx = ssl.create_default_context()
    ctx.options |= getattr(ssl, "OP_LEGACY_SERVER_CONNECT", 0x4)
    session = requests.Session()
    session.headers.update(HEADERS)
    session.mount("https://", _LegacyRenegotiationAdapter(ctx))
    return session


SESSION = _make_session()

DATA_PATH = Path(__file__).parent / "cpi_data.parquet"

COLUMNS = [
    "base_year", "series", "year", "month", "state", "sector", "division",
    "group", "class", "sub_class", "item", "code", "index", "inflation", "imputation",
]

KEY_COLUMNS = ["base_year", "series", "year", "month", "state", "sector", "division"]

MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


def _fetch_page(page, year=None, month_code=None):
    params = {
        "base_year": BASE_YEAR,
        "series": SERIES,
        "Format": "JSON",
        "limit": PAGE_SIZE,
        "page": page,
    }
    if year:
        params["year"] = year
    if month_code:
        params["month_code"] = month_code
    resp = SESSION.get(API_URL, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def fetch_division_level(year=None, month_code=None):
    """Page through getCPIData for the given year/month and keep division-level rows only."""
    records = []
    page = 1
    total_pages = 1
    while page <= total_pages:
        payload = _fetch_page(page, year=year, month_code=month_code)
        meta = payload.get("meta_data", {})
        total_pages = meta.get("totalPages", 1)
        for row in payload.get("data", []):
            if row.get("group") is None:
                records.append(row)
        print(f"  page {page}/{total_pages} -> {len(records)} division rows so far", end="\r")
        page += 1
        if page <= total_pages:
            time.sleep(REQUEST_DELAY)
    print()
    return _to_frame(records)


def _to_frame(records):
    df = pd.DataFrame(records, columns=[
        "base_year", "series", "year", "month", "state", "sector", "division",
        "group", "class", "sub_class", "item", "code", "index", "inflation", "imputation",
    ])
    if df.empty:
        return df.reindex(columns=COLUMNS)

    df["base_year"] = pd.to_numeric(df["base_year"], errors="coerce").astype("int64")
    df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("int64")
    df["index"] = pd.to_numeric(df["index"], errors="coerce")
    df["inflation"] = pd.to_numeric(df["inflation"], errors="coerce")
    # division-level "code" is the division_code itself ("01".."12"), null for CPI (General)
    df["code"] = pd.to_numeric(df["code"], errors="coerce")
    for col in ["group", "class", "sub_class", "item", "imputation"]:
        df[col] = float("nan")

    return df[COLUMNS]


def load_existing():
    if DATA_PATH.exists():
        return pd.read_parquet(DATA_PATH)
    return pd.DataFrame(columns=COLUMNS)


def upsert(existing, new):
    if new.empty:
        return existing
    combined = pd.concat([existing, new], ignore_index=True)
    combined = combined.drop_duplicates(subset=KEY_COLUMNS, keep="last")
    combined = combined.sort_values(by=["state", "division", "sector", "year", "month"])
    return combined.reset_index(drop=True)


def seed_from_excel(xlsx_path):
    print(f"Seeding {DATA_PATH.name} from {xlsx_path} ...")
    df = pd.read_excel(xlsx_path)
    df = df[COLUMNS]
    df.to_parquet(DATA_PATH, index=False)
    print(f"Wrote {len(df)} rows.")


def sync_months(year_month_pairs):
    existing = load_existing()
    for year, month_code in year_month_pairs:
        label = f"{MONTH_NAMES[month_code - 1]} {year}"
        print(f"Fetching {label} (year={year}, month_code={month_code}) ...")
        new = fetch_division_level(year=str(year), month_code=str(month_code))
        print(f"  -> {len(new)} division-level rows fetched")
        existing = upsert(existing, new)
    existing.to_parquet(DATA_PATH, index=False)
    print(f"Saved {len(existing)} total rows to {DATA_PATH}")


def recent_year_month_pairs(n_months):
    today = dt.date.today().replace(day=1)
    pairs = []
    cursor = today
    for _ in range(n_months):
        cursor = cursor.replace(day=1)
        prev = (cursor - dt.timedelta(days=1)).replace(day=1)
        pairs.append((cursor.year, cursor.month))
        cursor = prev
    return pairs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed-from-excel", metavar="PATH", help="One-off: adopt an existing cpi_6.xlsx export as history")
    parser.add_argument("--recent-months", type=int, help="Fetch/refresh the last N months from the API")
    parser.add_argument("--year", type=int, help="Fetch a specific year (pairs with --month)")
    parser.add_argument("--month", type=int, help="Month number 1-12 (pairs with --year)")
    args = parser.parse_args()

    if args.seed_from_excel:
        seed_from_excel(args.seed_from_excel)
        return

    if args.year and args.month:
        sync_months([(args.year, args.month)])
        return

    if args.recent_months:
        sync_months(recent_year_month_pairs(args.recent_months))
        return

    parser.error("Specify one of --seed-from-excel, --recent-months, or --year/--month")


if __name__ == "__main__":
    main()
