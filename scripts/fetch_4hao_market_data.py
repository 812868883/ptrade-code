from __future__ import annotations

import argparse
import time
from dataclasses import dataclass
from pathlib import Path

import akshare as ak
import efinance as ef
import pandas as pd


ROOT = Path(r"C:\Users\mengx\Desktop\量化策略\策略源码")
TRADE_XLSX = ROOT / "4号最近交割单327.xlsx"
DATA_ROOT = ROOT / "data" / "4hao"
RAW_DAILY_DIR = DATA_ROOT / "raw" / "daily"
RAW_MINUTE_DIR = DATA_ROOT / "raw" / "minute"
DERIVED_DIR = DATA_ROOT / "derived"
LOG_DIR = DATA_ROOT / "logs"


@dataclass(frozen=True)
class MinuteTask:
    code: str
    day: str
    kind: str


def ensure_dirs() -> None:
    for path in [RAW_DAILY_DIR, RAW_MINUTE_DIR, DERIVED_DIR, LOG_DIR]:
        path.mkdir(parents=True, exist_ok=True)


def normalize_trade_sheet(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["code"] = out["股票代码"].apply(lambda x: str(int(x)).zfill(6))
    for col in ["买入时间", "卖出时间"]:
        text = (
            out[col]
            .astype(str)
            .str.replace("年", "-", regex=False)
            .str.replace("月", "-", regex=False)
            .str.replace("日", "", regex=False)
        )
        out[f"{col}_dt"] = pd.to_datetime(text, errors="coerce")
    out["buy_date"] = out["买入时间_dt"].dt.strftime("%Y-%m-%d")
    out["sell_date"] = out["卖出时间_dt"].dt.strftime("%Y-%m-%d")
    return out


def fetch_with_retry(fetcher, *args, retries: int = 4, sleep_s: float = 1.5, **kwargs):
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            df = fetcher(*args, **kwargs)
            if isinstance(df, pd.DataFrame) and not df.empty:
                return df
        except Exception as exc:  # noqa: BLE001
            last_error = exc
        time.sleep(sleep_s * attempt)
    if last_error:
        raise last_error
    return pd.DataFrame()


def fetch_daily_ak(code: str, start: str, end: str) -> pd.DataFrame:
    df = fetch_with_retry(
        ak.stock_zh_a_hist,
        symbol=code,
        period="daily",
        start_date=start,
        end_date=end,
        adjust="",
    )
    if not df.empty:
        df["日期"] = pd.to_datetime(df["日期"])
    return df


def fetch_daily_ef(code: str, start: str, end: str) -> pd.DataFrame:
    df = fetch_with_retry(ef.stock.get_quote_history, code, beg=start, end=end, klt=101)
    if not df.empty and "日期" in df.columns:
        df["日期"] = pd.to_datetime(df["日期"])
    return df


def fetch_daily(code: str, start: str, end: str) -> tuple[pd.DataFrame, str]:
    try:
        return fetch_daily_ak(code, start, end), "akshare"
    except Exception:  # noqa: BLE001
        return fetch_daily_ef(code, start, end), "efinance"


def fetch_minute_ak(code: str, day: str) -> pd.DataFrame:
    df = fetch_with_retry(
        ak.stock_zh_a_hist_min_em,
        symbol=code,
        start_date=f"{day} 09:30:00",
        end_date=f"{day} 15:00:00",
        period="1",
        adjust="",
    )
    if not df.empty:
        df["时间"] = pd.to_datetime(df["时间"])
    return df


def fetch_minute_ef(code: str, day: str) -> pd.DataFrame:
    beg = day.replace("-", "")
    df = fetch_with_retry(ef.stock.get_quote_history, code, beg=beg, end=beg, klt=1)
    if not df.empty:
        dt_col = "日期"
        if dt_col in df.columns:
            df[dt_col] = pd.to_datetime(df[dt_col])
    return df


def fetch_minute(code: str, day: str) -> tuple[pd.DataFrame, str]:
    try:
        return fetch_minute_ak(code, day), "akshare"
    except Exception:  # noqa: BLE001
        return fetch_minute_ef(code, day), "efinance"


def save_frame(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")


def load_existing_status(path: Path, key_cols: list[str]) -> dict[tuple, dict]:
    if not path.exists():
        return {}
    df = pd.read_csv(path)
    out: dict[tuple, dict] = {}
    for _, row in df.iterrows():
        key = tuple(row[col] for col in key_cols)
        out[key] = row.to_dict()
    return out


def persist_status(rows: list[dict], path: Path) -> None:
    if rows:
        save_frame(pd.DataFrame(rows), path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=["all", "daily", "minute"], default="all")
    parser.add_argument("--max-daily", type=int, default=0)
    parser.add_argument("--max-minute", type=int, default=0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    ensure_dirs()

    trades = pd.read_excel(TRADE_XLSX)
    trades = normalize_trade_sheet(trades)
    save_frame(trades, DERIVED_DIR / "trades_clean.csv")

    start = (trades["买入时间_dt"].min() - pd.Timedelta(days=90)).strftime("%Y%m%d")
    end = (pd.Timestamp("2026-04-01") + pd.Timedelta(days=5)).strftime("%Y%m%d")

    daily_status_path = LOG_DIR / "daily_fetch_status.csv"
    minute_status_path = LOG_DIR / "minute_fetch_status.csv"
    daily_status = load_existing_status(daily_status_path, ["code"])
    minute_status = load_existing_status(minute_status_path, ["code", "day", "kind"])

    daily_rows = list(daily_status.values())
    minute_rows = list(minute_status.values())

    if args.phase in {"all", "daily"}:
        processed_daily = 0
        for code in sorted(trades["code"].unique()):
            out_path = RAW_DAILY_DIR / f"{code}.csv"
            key = (code,)
            if out_path.exists() and out_path.stat().st_size > 0:
                daily_status[key] = {"code": code, "rows": -1, "source": "local", "status": "cached", "path": str(out_path)}
                continue
            try:
                df, source = fetch_daily(code, start, end)
                save_frame(df, out_path)
                daily_status[key] = {
                    "code": code,
                    "rows": len(df),
                    "source": source,
                    "status": "ok",
                    "path": str(out_path),
                }
            except Exception as exc:  # noqa: BLE001
                daily_status[key] = {
                    "code": code,
                    "rows": 0,
                    "source": "",
                    "status": "error",
                    "path": str(out_path),
                    "error": str(exc),
                }
            processed_daily += 1
            persist_status(list(daily_status.values()), daily_status_path)
            if args.max_daily and processed_daily >= args.max_daily:
                break

    minute_tasks: set[MinuteTask] = set()
    for _, row in trades.iterrows():
        if pd.notna(row["买入时间_dt"]):
            minute_tasks.add(MinuteTask(code=row["code"], day=row["buy_date"], kind="buy"))
        if pd.notna(row["卖出时间_dt"]) and row["卖出时间_dt"] >= row["买入时间_dt"]:
            minute_tasks.add(MinuteTask(code=row["code"], day=row["sell_date"], kind="sell"))

    if args.phase in {"all", "minute"}:
        processed_minute = 0
        for task in sorted(minute_tasks, key=lambda x: (x.day, x.code, x.kind)):
            out_path = RAW_MINUTE_DIR / f"{task.day}_{task.code}_{task.kind}.csv"
            key = (task.code, task.day, task.kind)
            if out_path.exists() and out_path.stat().st_size > 0:
                minute_status[key] = {
                    "code": task.code,
                    "day": task.day,
                    "kind": task.kind,
                    "rows": -1,
                    "source": "local",
                    "status": "cached",
                    "path": str(out_path),
                }
                continue
            try:
                df, source = fetch_minute(task.code, task.day)
                save_frame(df, out_path)
                minute_status[key] = {
                    "code": task.code,
                    "day": task.day,
                    "kind": task.kind,
                    "rows": len(df),
                    "source": source,
                    "status": "ok",
                    "path": str(out_path),
                }
            except Exception as exc:  # noqa: BLE001
                minute_status[key] = {
                    "code": task.code,
                    "day": task.day,
                    "kind": task.kind,
                    "rows": 0,
                    "source": "",
                    "status": "error",
                    "path": str(out_path),
                    "error": str(exc),
                }
            processed_minute += 1
            persist_status(list(minute_status.values()), minute_status_path)
            if args.max_minute and processed_minute >= args.max_minute:
                break

    persist_status(list(daily_status.values()), daily_status_path)
    persist_status(list(minute_status.values()), minute_status_path)


if __name__ == "__main__":
    main()
