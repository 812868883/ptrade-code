from __future__ import annotations

import time
import argparse
from dataclasses import dataclass
from pathlib import Path

import akshare as ak
import baostock as bs
import pandas as pd


ROOT = Path(r"C:\Users\mengx\Desktop\量化策略\策略源码")
TRADE_XLSX = ROOT / "4号最近交割单327.xlsx"
DATA_ROOT = ROOT / "data" / "4hao_focused"
TRADE_DIR = DATA_ROOT / "trades"
DAILY_DIR = DATA_ROOT / "daily_windows"
MINUTE_DIR = DATA_ROOT / "minute"
LOG_DIR = DATA_ROOT / "logs"


@dataclass(frozen=True)
class MinuteTask:
    trade_id: str
    code: str
    day: str
    kind: str


def ensure_dirs() -> None:
    for path in [TRADE_DIR, DAILY_DIR, MINUTE_DIR, LOG_DIR]:
        path.mkdir(parents=True, exist_ok=True)


def normalize_trades(df: pd.DataFrame) -> pd.DataFrame:
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
    out["trade_id"] = [f"T{i + 1:03d}" for i in range(len(out))]
    return out


def fetch_with_retry(fetcher, *args, retries: int = 4, sleep_s: float = 1.2, **kwargs):
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


def fetch_daily_window(code: str, start: str, end: str) -> tuple[pd.DataFrame, str]:
    symbol = ("sh" if code.startswith(("60", "68")) else "sz") + code
    df = fetch_with_retry(
        ak.stock_zh_a_hist_tx,
        symbol=symbol,
        start_date=start,
        end_date=end,
        adjust="",
    )
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
    return df, "akshare_tx"


def fetch_minute_day(code: str, day: str) -> tuple[pd.DataFrame, str]:
    market_code = ("sh." if code.startswith(("60", "68")) else "sz.") + code
    login_result = bs.login()
    if login_result.error_code != "0":
        raise RuntimeError(login_result.error_msg)
    try:
        rs = bs.query_history_k_data_plus(
            market_code,
            "date,time,open,high,low,close,volume,amount",
            start_date=day,
            end_date=day,
            frequency="5",
            adjustflag="3",
        )
        rows = []
        while rs.error_code == "0" and rs.next():
            rows.append(rs.get_row_data())
        df = pd.DataFrame(rows, columns=rs.fields)
        if not df.empty:
            df["date"] = pd.to_datetime(df["date"])
        return df, "baostock_5m"
    finally:
        bs.logout()


def save_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")


def upsert_status(path: Path, row: dict, keys: list[str]) -> None:
    if path.exists():
        df = pd.read_csv(path)
        mask = pd.Series(True, index=df.index)
        for key in keys:
            mask &= df[key].astype(str) == str(row[key])
        df = df.loc[~mask].copy()
        df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    else:
        df = pd.DataFrame([row])
    save_csv(df, path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=1, help="1-based trade start index")
    parser.add_argument("--limit", type=int, default=0, help="how many trades to fetch; 0 means all")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    ensure_dirs()

    trades = normalize_trades(pd.read_excel(TRADE_XLSX))
    save_csv(trades, TRADE_DIR / "trades_clean.csv")
    begin = max(args.start - 1, 0)
    end = begin + args.limit if args.limit else len(trades)
    trades = trades.iloc[begin:end].copy()

    daily_status_path = LOG_DIR / "daily_window_status.csv"
    minute_status_path = LOG_DIR / "minute_status.csv"

    minute_tasks: list[MinuteTask] = []

    for _, row in trades.iterrows():
        trade_id = row["trade_id"]
        code = row["code"]
        buy_dt = row["买入时间_dt"]
        sell_dt = row["卖出时间_dt"] if pd.notna(row["卖出时间_dt"]) else pd.Timestamp("2026-04-01 15:00:00")

        start = (buy_dt.normalize() - pd.Timedelta(days=10)).strftime("%Y%m%d")
        end = sell_dt.normalize().strftime("%Y%m%d")
        daily_path = DAILY_DIR / f"{trade_id}_{code}.csv"
        if daily_path.exists():
            upsert_status(
                daily_status_path,
                {
                    "trade_id": trade_id,
                    "code": code,
                    "status": "cached",
                    "source": "local",
                    "rows": -1,
                    "path": str(daily_path),
                },
                ["trade_id"],
            )
        else:
            try:
                daily_df, source = fetch_daily_window(code, start, end)
                save_csv(daily_df, daily_path)
                upsert_status(
                    daily_status_path,
                    {
                        "trade_id": trade_id,
                        "code": code,
                        "status": "ok",
                        "source": source,
                        "rows": len(daily_df),
                        "path": str(daily_path),
                    },
                    ["trade_id"],
                )
            except Exception as exc:  # noqa: BLE001
                upsert_status(
                    daily_status_path,
                    {
                        "trade_id": trade_id,
                        "code": code,
                        "status": "error",
                        "source": "",
                        "rows": 0,
                        "path": str(daily_path),
                        "error": str(exc),
                    },
                    ["trade_id"],
                )

        minute_tasks.append(MinuteTask(trade_id=trade_id, code=code, day=row["buy_date"], kind="buy"))
        if pd.notna(row["卖出时间_dt"]) and row["卖出时间_dt"] >= row["买入时间_dt"]:
            minute_tasks.append(MinuteTask(trade_id=trade_id, code=code, day=row["sell_date"], kind="sell"))

    for task in minute_tasks:
        minute_path = MINUTE_DIR / f"{task.trade_id}_{task.code}_{task.day}_{task.kind}.csv"
        if minute_path.exists():
            upsert_status(
                minute_status_path,
                {
                    "trade_id": task.trade_id,
                    "code": task.code,
                    "day": task.day,
                    "kind": task.kind,
                    "status": "cached",
                    "source": "local",
                    "rows": -1,
                    "path": str(minute_path),
                },
                ["trade_id", "day", "kind"],
            )
        else:
            try:
                minute_df, source = fetch_minute_day(task.code, task.day)
                save_csv(minute_df, minute_path)
                upsert_status(
                    minute_status_path,
                    {
                        "trade_id": task.trade_id,
                        "code": task.code,
                        "day": task.day,
                        "kind": task.kind,
                        "status": "ok",
                        "source": source,
                        "rows": len(minute_df),
                        "path": str(minute_path),
                    },
                    ["trade_id", "day", "kind"],
                )
            except Exception as exc:  # noqa: BLE001
                upsert_status(
                    minute_status_path,
                    {
                        "trade_id": task.trade_id,
                        "code": task.code,
                        "day": task.day,
                        "kind": task.kind,
                        "status": "error",
                        "source": "",
                        "rows": 0,
                        "path": str(minute_path),
                        "error": str(exc),
                    },
                    ["trade_id", "day", "kind"],
                )


if __name__ == "__main__":
    main()
