from __future__ import annotations

import argparse
from pathlib import Path

import akshare as ak
import baostock as bs
import pandas as pd
from pandas.errors import EmptyDataError


ROOT = Path(r"C:\Users\mengx\Desktop\量化策略\策略源码")
TRADES_FILE = ROOT / "data" / "4hao_focused" / "trades" / "trades_clean.csv"
DATA_ROOT = ROOT / "data" / "4hao_cross_section"
LIMIT_POOL_DIR = DATA_ROOT / "limit_pool"
DAILY_DIR = DATA_ROOT / "daily_cache"
RESULT_DIR = DATA_ROOT / "results"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-date", default="2026-03-13")
    parser.add_argument("--end-date", default="2026-03-27")
    return parser.parse_args()


def ensure_dirs() -> None:
    for path in [LIMIT_POOL_DIR, DAILY_DIR, RESULT_DIR]:
        path.mkdir(parents=True, exist_ok=True)


def get_trade_rows(start_date: str, end_date: str) -> pd.DataFrame:
    trades = pd.read_csv(TRADES_FILE)
    trades["buy_dt"] = pd.to_datetime(trades["买入时间_dt"])
    trades["buy_date_only"] = trades["buy_dt"].dt.strftime("%Y-%m-%d")
    trades["code"] = trades["code"].astype(str).str.zfill(6)
    mask = (trades["buy_date_only"] >= start_date) & (trades["buy_date_only"] <= end_date)
    return trades.loc[mask].copy()


def get_prev_trade_days(target_date: str, n: int = 5) -> list[str]:
    start = (pd.Timestamp(target_date) - pd.Timedelta(days=20)).strftime("%Y-%m-%d")
    rs = bs.query_trade_dates(start_date=start, end_date=target_date)
    rows = []
    while rs.error_code == "0" and rs.next():
        rows.append(rs.get_row_data())
    df = pd.DataFrame(rows, columns=rs.fields)
    df = df[df["is_trading_day"] == "1"].copy()
    days = [x for x in df["calendar_date"].tolist() if x < target_date]
    return days[-n:]


def fetch_limit_pool(date_str: str) -> pd.DataFrame:
    cache = LIMIT_POOL_DIR / f"{date_str}.csv"
    if cache.exists():
        try:
            return pd.read_csv(cache)
        except Exception:
            return pd.DataFrame()
    df = ak.stock_zt_pool_em(date=date_str.replace("-", ""))
    df.to_csv(cache, index=False, encoding="utf-8-sig")
    return df


def fetch_daily_window(code: str, start: str, end: str) -> pd.DataFrame:
    cache = DAILY_DIR / f"{code}_{start}_{end}.csv"
    if cache.exists():
        return pd.read_csv(cache)

    symbol = ("sh" if code.startswith(("60", "68")) else "sz") + code
    df = ak.stock_zh_a_hist_tx(symbol=symbol, start_date=start.replace("-", ""), end_date=end.replace("-", ""), adjust="")
    df.to_csv(cache, index=False, encoding="utf-8-sig")
    return df


def is_main_board(code: str) -> bool:
    code = str(code).zfill(6)
    return code.startswith(("600", "601", "603", "605", "000", "001", "002", "003")) and not code.startswith(
        ("300", "301", "688")
    )


def score_candidate(open_gap: float, y_ret: float, y_body_ret: float, days_since_limit: int) -> float:
    target_open_gap = -0.012
    gap_penalty = abs(open_gap - target_open_gap)
    limit_recency_penalty = days_since_limit * 0.60
    pullback_penalty = abs(y_ret) * 8
    deep_gap_penalty = max(0, abs(open_gap) - 0.03) * 20
    positive_gap_penalty = max(0, open_gap) * 40
    body_penalty = max(0, abs(y_body_ret) - 0.08) * 20
    return gap_penalty * 100 + limit_recency_penalty + pullback_penalty + deep_gap_penalty + positive_gap_penalty + body_penalty


def analyze_date(buy_date: str, actual_code: str, actual_name: str) -> tuple[pd.DataFrame, dict]:
    prev_days = get_prev_trade_days(buy_date, 5)
    if len(prev_days) < 5:
        raise RuntimeError(f"{buy_date} 前置交易日不足")

    limit_day_map: dict[str, list[str]] = {}
    pool_codes: set[str] = set()
    for day in prev_days:
        pool = fetch_limit_pool(day)
        if "代码" not in pool.columns:
            continue
        codes = [str(x).zfill(6) for x in pool["代码"].tolist()]
        for code in codes:
            if not is_main_board(code):
                continue
            pool_codes.add(code)
            limit_day_map.setdefault(code, []).append(day)

    start = (pd.Timestamp(prev_days[0]) - pd.Timedelta(days=2)).strftime("%Y-%m-%d")
    candidates = []
    for code in sorted(pool_codes):
        try:
            ddf = fetch_daily_window(code, start, buy_date)
            if ddf.empty:
                continue
            ddf["date"] = pd.to_datetime(ddf["date"])
            ddf = ddf.sort_values("date").reset_index(drop=True)
            idx = ddf.index[ddf["date"] == pd.Timestamp(buy_date)]
            if len(idx) == 0 or idx[0] < 1:
                continue
            buy_idx = int(idx[0])
            prev = ddf.iloc[buy_idx - 1]
            prev2 = ddf.iloc[buy_idx - 2] if buy_idx >= 2 else None
            buybar = ddf.iloc[buy_idx]

            y_open = float(prev["open"])
            y_close = float(prev["close"])
            prev_close = float(prev2["close"]) if prev2 is not None else y_close
            buy_open = float(buybar["open"])

            if y_open <= 0 or y_close <= 0 or prev_close <= 0 or buy_open <= 0:
                continue

            y_ret = y_close / prev_close - 1
            y_body_ret = y_close / y_open - 1
            is_pullback = (y_close < y_open) or (y_close < prev_close)
            open_gap = buy_open / y_close - 1
            days_since_limit = len(prev_days) - prev_days.index(limit_day_map[code][-1])

            # 主规则过滤
            if open_gap < -0.09 or open_gap > 0.003:
                continue
            if not is_pullback:
                continue

            score = score_candidate(open_gap, y_ret, y_body_ret, days_since_limit)
            candidates.append(
                {
                    "buy_date": buy_date,
                    "code": code,
                    "actual_code": actual_code,
                    "actual_name": actual_name,
                    "days_since_limit": days_since_limit,
                    "is_pullback": int(is_pullback),
                    "y_ret": y_ret,
                    "y_body_ret": y_body_ret,
                    "open_gap": open_gap,
                    "score": score,
                }
            )
        except Exception:
            continue

    frame = pd.DataFrame(candidates)
    if not frame.empty:
        frame = frame.sort_values(["score", "open_gap"]).reset_index(drop=True)
        frame["rank"] = range(1, len(frame) + 1)

    if not frame.empty and actual_code in frame["code"].tolist():
        actual_row = frame.loc[frame["code"] == actual_code].iloc[0]
        summary = {
            "buy_date": buy_date,
            "actual_code": actual_code,
            "actual_name": actual_name,
            "candidate_count": len(frame),
            "actual_rank": int(actual_row["rank"]),
            "top1_code": frame.iloc[0]["code"],
            "top1_score": float(frame.iloc[0]["score"]),
            "actual_score": float(actual_row["score"]),
            "actual_open_gap": float(actual_row["open_gap"]),
        }
    else:
        summary = {
            "buy_date": buy_date,
            "actual_code": actual_code,
            "actual_name": actual_name,
            "candidate_count": len(frame),
            "actual_rank": None,
            "top1_code": frame.iloc[0]["code"] if len(frame) else None,
            "top1_score": float(frame.iloc[0]["score"]) if len(frame) else None,
            "actual_score": None,
            "actual_open_gap": None,
        }
    return frame, summary


def main() -> None:
    args = parse_args()
    ensure_dirs()

    trades = get_trade_rows(args.start_date, args.end_date)
    if trades.empty:
        print("没有可回放的交易日期")
        return

    lg = bs.login()
    if lg.error_code != "0":
        raise RuntimeError(lg.error_msg)

    summaries = []
    try:
        for _, trade in trades.iterrows():
            buy_date = trade["buy_date"]
            code = trade["code"]
            name = trade["股票名称"]
            frame, summary = analyze_date(buy_date, code, name)
            out = RESULT_DIR / f"{buy_date}_{code}.csv"
            frame.to_csv(out, index=False, encoding="utf-8-sig")
            summaries.append(summary)
            print(buy_date, code, name, "candidates=", summary["candidate_count"], "actual_rank=", summary["actual_rank"], "top1=", summary["top1_code"])
    finally:
        bs.logout()

    summary_rows = []
    for p in sorted(RESULT_DIR.glob("2026-*.csv")):
        actual_code = p.stem.split("_")[1].zfill(6)
        buy_date = p.stem.split("_")[0]
        try:
            df = pd.read_csv(p, dtype={"code": str, "actual_code": str})
        except EmptyDataError:
            df = pd.DataFrame()
        if df.empty:
            summary_rows.append(
                {
                    "buy_date": buy_date,
                    "actual_code": actual_code,
                    "candidate_count": 0,
                    "actual_rank": None,
                    "top1_code": None,
                    "top1_score": None,
                    "actual_score": None,
                }
            )
            continue
        df["code"] = df["code"].astype(str).str.zfill(6)
        actual = df[df["code"] == actual_code]
        summary_rows.append(
            {
                "buy_date": buy_date,
                "actual_code": actual_code,
                "candidate_count": len(df),
                "actual_rank": int(actual.iloc[0]["rank"]) if len(actual) else None,
                "top1_code": df.iloc[0]["code"],
                "top1_score": float(df.iloc[0]["score"]),
                "actual_score": float(actual.iloc[0]["score"]) if len(actual) else None,
            }
        )
    summary_df = pd.DataFrame(summary_rows).sort_values("buy_date")
    summary_path = RESULT_DIR / "summary.csv"
    summary_df.to_csv(summary_path, index=False, encoding="utf-8-sig")
    print("\nsummary saved:", summary_path)
    print(summary_df.to_string(index=False))


if __name__ == "__main__":
    main()
