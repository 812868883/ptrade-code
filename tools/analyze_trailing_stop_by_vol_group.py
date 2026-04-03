import argparse
import json
from pathlib import Path

import pandas as pd


def load_price_data(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    df["date"] = pd.to_datetime(df["date"])
    df["code"] = df["code"].astype(str)
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    if "high" in df.columns:
        df["high"] = pd.to_numeric(df["high"], errors="coerce")
    if "low" in df.columns:
        df["low"] = pd.to_numeric(df["low"], errors="coerce")
    return df.sort_values(["code", "date"]).reset_index(drop=True)


def build_code_volatility_table(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for code, g in df.groupby("code", sort=True):
        g = g.sort_values("date").copy()
        ret1 = g["close"].pct_change(1)
        if "high" in g.columns and "low" in g.columns:
            amplitude = (g["high"] / g["low"] - 1).replace([pd.NA, pd.NaT], pd.NA)
        else:
            amplitude = pd.Series(index=g.index, dtype=float)
        rows.append(
            {
                "code": code,
                "rows": int(len(g)),
                "daily_vol_pct": float(ret1.std() * 100) if ret1.dropna().size else 0.0,
                "avg_abs_day_ret_pct": float(ret1.abs().mean() * 100) if ret1.dropna().size else 0.0,
                "avg_amplitude_pct": float(amplitude.mean() * 100) if amplitude.dropna().size else 0.0,
            }
        )
    vol_df = pd.DataFrame(rows).sort_values("daily_vol_pct").reset_index(drop=True)
    vol_df["vol_group"] = pd.qcut(
        vol_df["daily_vol_pct"],
        q=3,
        labels=["low_vol", "mid_vol", "high_vol"],
        duplicates="drop",
    )
    return vol_df


def simulate_trailing_stop(g: pd.DataFrame, stop_pct: float) -> list[dict]:
    trades = []
    g = g.sort_values("date").copy().reset_index(drop=True)
    g["ret20"] = g["close"] / g["close"].shift(20) - 1
    g["ret3"] = g["close"] / g["close"].shift(3) - 1

    for i in range(20, len(g) - 1):
        if pd.isna(g.loc[i, "ret20"]) or g.loc[i, "ret20"] < 0.12:
            continue
        entry_price = g.loc[i, "close"]
        peak_price = entry_price
        exit_price = None
        exit_idx = None
        for j in range(i + 1, min(i + 31, len(g))):
            price = g.loc[j, "close"]
            if price > peak_price:
                peak_price = price
            drawdown = price / peak_price - 1
            if drawdown <= -stop_pct:
                exit_price = price
                exit_idx = j
                break
        if exit_idx is None:
            exit_idx = min(i + 20, len(g) - 1)
            exit_price = g.loc[exit_idx, "close"]
        trades.append(
            {
                "code": g.loc[i, "code"],
                "entry_date": g.loc[i, "date"],
                "exit_date": g.loc[exit_idx, "date"],
                "entry_price": float(entry_price),
                "exit_price": float(exit_price),
                "peak_price": float(peak_price),
                "hold_days": int(exit_idx - i),
                "entry_ret20": float(g.loc[i, "ret20"]),
                "entry_ret3": float(g.loc[i, "ret3"]) if not pd.isna(g.loc[i, "ret3"]) else None,
                "exit_return": float(exit_price / entry_price - 1),
                "max_runup_after_entry": float(peak_price / entry_price - 1),
            }
        )
    return trades


def summarize_trades(trades_df: pd.DataFrame, stop_pct: float, group_name: str) -> dict:
    result = {
        "vol_group": group_name,
        "stop_pct": round(stop_pct * 100, 2),
        "samples": int(len(trades_df)),
    }
    if trades_df.empty:
        return result
    result["avg_exit_return_pct"] = round(float(trades_df["exit_return"].mean() * 100), 3)
    result["median_exit_return_pct"] = round(float(trades_df["exit_return"].median() * 100), 3)
    result["down_ratio"] = round(float((trades_df["exit_return"] < 0).mean()), 4)
    result["avg_hold_days"] = round(float(trades_df["hold_days"].mean()), 2)
    result["avg_max_runup_pct"] = round(float(trades_df["max_runup_after_entry"].mean() * 100), 3)
    result["profit_capture_ratio"] = round(
        float(
            trades_df["exit_return"].sum() / trades_df["max_runup_after_entry"].replace(0, pd.NA).sum()
        ),
        4,
    ) if trades_df["max_runup_after_entry"].replace(0, pd.NA).dropna().size else None
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="按波动分组测试移动止损宽度")
    parser.add_argument("--data", required=True, help="历史数据 csv")
    parser.add_argument("--outdir", default="validator_output/trailing_stop_groups", help="输出目录")
    args = parser.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    df = load_price_data(Path(args.data))
    vol_df = build_code_volatility_table(df)
    vol_df.to_csv(outdir / "volatility_groups.csv", index=False, encoding="utf-8-sig")

    stops = [0.04, 0.045, 0.05, 0.055, 0.06]
    summaries = []
    trade_detail_frames = []

    for group_name, group_codes in vol_df.groupby("vol_group"):
        codes = set(group_codes["code"].tolist())
        group_df = df[df["code"].isin(codes)].copy()
        for stop in stops:
            all_trades = []
            for code, g in group_df.groupby("code", sort=True):
                trades = simulate_trailing_stop(g, stop)
                all_trades.extend(trades)
            trades_df = pd.DataFrame(all_trades)
            if not trades_df.empty:
                trades_df["vol_group"] = str(group_name)
                trades_df["stop_pct"] = round(stop * 100, 2)
                trade_detail_frames.append(trades_df)
            summaries.append(summarize_trades(trades_df, stop, str(group_name)))

    summary_df = pd.DataFrame(summaries).sort_values(["vol_group", "stop_pct"]).reset_index(drop=True)
    summary_df.to_csv(outdir / "trailing_stop_group_summary.csv", index=False, encoding="utf-8-sig")
    if trade_detail_frames:
        pd.concat(trade_detail_frames, ignore_index=True).to_csv(
            outdir / "trailing_stop_trade_details.csv", index=False, encoding="utf-8-sig"
        )

    report_lines = []
    report_lines.append("# 按波动分组的移动止损测试")
    report_lines.append("")
    report_lines.append("## 波动分组")
    report_lines.append("")
    for _, row in vol_df.iterrows():
        report_lines.append(
            "- %s: vol_group=%s, daily_vol=%.3f%%, avg_abs_day_ret=%.3f%%"
            % (row["code"], row["vol_group"], row["daily_vol_pct"], row["avg_abs_day_ret_pct"])
        )
    report_lines.append("")
    report_lines.append("## 各组止损表现")
    report_lines.append("")
    for _, row in summary_df.iterrows():
        report_lines.append(
            "- %s | stop=%s%% | samples=%s | avg_exit=%s%% | median_exit=%s%% | down_ratio=%s | avg_hold_days=%s"
            % (
                row["vol_group"],
                row["stop_pct"],
                int(row["samples"]),
                row.get("avg_exit_return_pct", ""),
                row.get("median_exit_return_pct", ""),
                row.get("down_ratio", ""),
                row.get("avg_hold_days", ""),
            )
        )
    (outdir / "report.md").write_text("\n".join(report_lines), encoding="utf-8")

    (outdir / "summary.json").write_text(
        json.dumps(
            {
                "volatility_groups": vol_df.to_dict(orient="records"),
                "stop_summary": summary_df.to_dict(orient="records"),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print("done")
    print("outdir:", outdir)


if __name__ == "__main__":
    main()
