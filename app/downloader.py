from datetime import datetime
import httpx
import polars as pl
from pathlib import Path
import time


def get_kucoin_klines(symbol, interval, start, end):
    url = "https://api.kucoin.com/api/v1/market/candles"
    params = {
        "symbol": symbol,
        "type": interval.replace("m", "min")
        .replace("h", "hour")
        .replace("d", "day")
        .replace("w", "week"),
        "startAt": int(start / 1000),  # seconds
        "endAt": int(end / 1000),
    }

    with httpx.Client(timeout=30) as client:
        response = client.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        data["data"] = [[int(row[0]) * 1000] + row[1:] for row in data["data"]]
        return data["data"]


def get_binance_klines(symbol, interval, start, end):
    url = "https://api.binance.com/api/v3/klines"
    params = {
        "symbol": symbol.replace("-", ""),
        "interval": interval,
        "startTime": start,  # milliseconds
        "endTime": end,
        "limit": 1000,
    }
    with httpx.Client(timeout=30) as client:
        response = client.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        return data


def get_klines_batch_bitfinex(symbol: str, interval: str, end_ms: int) -> list:
    url = f"https://api-pub.bitfinex.com/v2/candles/trade:{interval}:{symbol}/hist"
    params = {"end": end_ms, "limit": 1000, "sort": -1}
    with httpx.Client() as client:
        resp = client.get(url, params=params)
    if resp.status_code != 200:
        print(f"[ERROR] API call failed: {resp.status_code}")
        return []
    return resp.json()


def to_polars_df(batch: list) -> pl.DataFrame:
    return pl.DataFrame(
        (
            (
                row[0],
                float(row[1]),
                float(row[2]),
                float(row[3]),
                float(row[4]),
                float(row[5]),
            )
            for row in batch
        ),
        schema=[
            ("timestamp", pl.Int64),
            ("open", pl.Float64),
            ("high", pl.Float64),
            ("low", pl.Float64),
            ("close", pl.Float64),
            ("volume", pl.Float64),
        ],
    )


def batch_download(
    start,
    end,
    symbol,
    get_klines,
    interval="1m",
    reverse=False,
):
    print(f"Downloading {symbol} {start} - {end}")
    dfs = []
    current_start = start
    current_end = end
    step = 60_000
    batch_count = 0

    while current_start < current_end:
        print(current_start, current_end)
        batch = get_klines(symbol, interval, current_start, current_end)
        print(len(batch))
        if not batch:
            break
        dfs.append(to_polars_df(batch))
        if reverse:
            current_end = batch[-1][0] - step
        else:
            current_start = batch[-1][0] + step
        batch_count += 1
        time.sleep(0.1)
    if not dfs:
        print(f"[ERROR] No data for {symbol} {start} - {end}")
        return
    final_df = pl.concat(dfs, rechunk=True)
    return final_df.sort("timestamp")


def download(symbol, year, month, interval="1m", out_dir="data/", update=False):

    symbol = symbol.upper()
    out_path = Path(f"{out_dir}/{symbol}/{interval}/{year}-{month:02d}.parquet")
    if out_path.exists() and not update:
        print(f"[INFO] File {out_path} already exists")
        return
    print(f"Downloading {symbol} {year}-{month:02d}")
    exchange = [
        {
            "exchange": "binance",
            "get_klines": get_binance_klines,
            "reverse": False,
        },
        {
            "exchange": "kucoin",
            "get_klines": get_kucoin_klines,
            "reverse": True,
        },
    ]
    start = datetime(year, month, 1)
    end = datetime(year + (month // 12), (month % 12) + 1, 1)
    start_ms, end_ms = int(start.timestamp() * 1000), int(end.timestamp() * 1000)
    for e in exchange:
        print(f"Downloading {symbol} from {e['exchange']}")
        final_df = batch_download(
            symbol=symbol,
            start=start_ms,
            end=end_ms,
            interval=interval,
            get_klines=e["get_klines"],
            reverse=e["reverse"],
        )
        if final_df is not None and not final_df.is_empty():
            break
    if final_df is None or final_df.is_empty():
        print(f"[ERROR] No data for {symbol} {year}-{month:02d}")
        return
    out_path.parent.mkdir(parents=True, exist_ok=True)
    final_df.write_parquet(str(out_path), compression="zstd")
    print(f"[OK] Wrote {len(final_df)} rows")
