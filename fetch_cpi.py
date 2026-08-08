"""
Sync the state-wise CPI dataset from the MoSPI eSankhyiki API into a local
parquet file that ind_eco.py reads. Supports two series:

  base_year 2024 ("current")  -- division/group/class/sub_class/item hierarchy,
                                  Jan 2025 onward, updated monthly.
  base_year 2012 ("old")      -- group/subgroup hierarchy, Jan 2013-Dec 2025,
                                  frozen: MoSPI stopped publishing it once the
                                  2024-base series took over, so it only needs
                                  a one-time backfill, not ongoing syncs.

Neither API endpoint has a way to request top-level rows only -- filtering by
division/group also returns every row beneath it in the hierarchy, and pages
are capped at 100 rows. So instead of downloading the full item-level
hierarchy on every run, this script pages through whichever (year, month)
slice is requested and keeps just the top-level rows (no child category)
client-side. Both series normalize into the same schema, with the old
series' "group" (its top level) stored in the "division" column so
ind_eco.py's existing division-based filtering works for both unmodified.

Usage:
    python fetch_cpi.py --seed-from-excel cpi_6.xlsx        # one-off: adopt existing export as history (base 2024)
    python fetch_cpi.py --recent-months 2                    # incremental sync (used by CI, base 2024)
    python fetch_cpi.py --year 2026 --month 6                 # backfill one specific month (base 2024)
    python fetch_cpi.py --base-year 2012 --recent-months 156  # one-time backfill of the old series
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

API_ROOT = "https://api.mospi.gov.in/api/cpi"
HEADERS = {"User-Agent": "Mozilla/5.0"}
PAGE_SIZE = 100
REQUEST_DELAY = 0.2

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

# How to talk to each base year's endpoint, and how to recognize a top-level
# (division/group) row versus one that belongs to a finer child category.
SERIES_CONFIG = {
    "2024": {
        "endpoint": f"{API_ROOT}/getCPIData",
        # division-level rows simply have no group/class/sub_class/item set.
        "is_top_level": lambda row: row.get("group") is None,
        "division_field": "division",
        "code_field": "code",
    },
    "2012": {
        "endpoint": f"{API_ROOT}/getCPIIndex",
        # every row has a non-null "subgroup" -- the group-level aggregate is
        # the row whose subgroup is literally "<Group>-Overall".
        "is_top_level": lambda row: row.get("subgroup") == f"{row.get('group')}-Overall",
        "division_field": "group",
        "code_field": None,
    },
}


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


def _fetch_page(base_year, page, year=None, month_code=None):
    cfg = SERIES_CONFIG[base_year]
    params = {
        "base_year": base_year,
        "series": "Current",
        "Format": "JSON",
        "limit": PAGE_SIZE,
        "page": page,
    }
    if year:
        params["year"] = year
    if month_code:
        params["month_code"] = month_code
    resp = SESSION.get(cfg["endpoint"], params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def fetch_top_level(base_year, year=None, month_code=None):
    """Page through the given series' endpoint for one year/month and keep
    only rows with no child category (i.e. division-level for 2024, group-level for 2012)."""
    cfg = SERIES_CONFIG[base_year]
    records = []
    page = 1
    total_pages = 1
    while page <= total_pages:
        payload = _fetch_page(base_year, page, year=year, month_code=month_code)
        meta = payload.get("meta_data", {})
        total_pages = meta.get("totalPages", 1)
        for row in payload.get("data", []):
            if cfg["is_top_level"](row):
                records.append(row)
        print(f"  page {page}/{total_pages} -> {len(records)} top-level rows so far", end="\r")
        page += 1
        if page <= total_pages:
            time.sleep(REQUEST_DELAY)
    print()
    return _to_frame(base_year, records)


def _to_frame(base_year, records):
    cfg = SERIES_CONFIG[base_year]
    df = pd.DataFrame.from_records(records)
    if df.empty:
        return pd.DataFrame(columns=COLUMNS)

    out = pd.DataFrame(index=df.index)
    out["base_year"] = int(base_year)
    out["series"] = "Current"
    out["year"] = pd.to_numeric(df["year"], errors="coerce").astype("int64")
    out["month"] = df["month"]
    out["state"] = df["state"]
    out["sector"] = df["sector"]
    out["division"] = df[cfg["division_field"]]
    out["group"] = float("nan")
    out["class"] = float("nan")
    out["sub_class"] = float("nan")
    out["item"] = float("nan")
    out["code"] = pd.to_numeric(df[cfg["code_field"]], errors="coerce") if cfg["code_field"] else float("nan")
    out["index"] = pd.to_numeric(df["index"], errors="coerce")
    out["inflation"] = pd.to_numeric(df["inflation"], errors="coerce")
    out["imputation"] = float("nan")

    return out[COLUMNS]


def load_existing():
    if DATA_PATH.exists():
        return pd.read_parquet(DATA_PATH)
    return pd.DataFrame(columns=COLUMNS)


def upsert(existing, new):
    if new.empty:
        return existing
    combined = pd.concat([existing, new], ignore_index=True)
    combined = combined.drop_duplicates(subset=KEY_COLUMNS, keep="last")
    combined = combined.sort_values(by=["base_year", "state", "division", "sector", "year", "month"])
    return combined.reset_index(drop=True)


def seed_from_excel(xlsx_path):
    print(f"Seeding {DATA_PATH.name} from {xlsx_path} ...")
    df = pd.read_excel(xlsx_path)
    df = df[COLUMNS]
    existing = load_existing()
    combined = upsert(existing, df)
    combined.to_parquet(DATA_PATH, index=False)
    print(f"Wrote {len(combined)} total rows ({len(df)} from {xlsx_path}).")


def sync_months(base_year, year_month_pairs):
    existing = load_existing()
    for year, month_code in year_month_pairs:
        label = f"{MONTH_NAMES[month_code - 1]} {year}"
        print(f"Fetching {label}, base_year={base_year} (year={year}, month_code={month_code}) ...")
        new = fetch_top_level(base_year, year=str(year), month_code=str(month_code))
        print(f"  -> {len(new)} top-level rows fetched")
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
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base-year", choices=sorted(SERIES_CONFIG), default="2024", help="Which CPI series to fetch (default: 2024)")
    parser.add_argument("--seed-from-excel", metavar="PATH", help="One-off: adopt an existing cpi_6.xlsx export as history (base 2024 only)")
    parser.add_argument("--recent-months", type=int, help="Fetch/refresh the last N months from the API")
    parser.add_argument("--year", type=int, help="Fetch a specific year (pairs with --month)")
    parser.add_argument("--month", type=int, help="Month number 1-12 (pairs with --year)")
    args = parser.parse_args()

    if args.seed_from_excel:
        seed_from_excel(args.seed_from_excel)
        return

    if args.year and args.month:
        sync_months(args.base_year, [(args.year, args.month)])
        return

    if args.recent_months:
        sync_months(args.base_year, recent_year_month_pairs(args.recent_months))
        return

    parser.error("Specify one of --seed-from-excel, --recent-months, or --year/--month")


if __name__ == "__main__":
    main()
