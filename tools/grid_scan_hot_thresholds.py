import argparse
import json
from pathlib import Path

import pandas as pd


def load_price_data(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    df["date"] = pd.to_datetime(df["date"])
    df["code"] = df["code"].astype(str)
    for col in ["close"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df.sort_values(["code", "date"]).reset_index(drop=True)


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    out = []
    for code, g in df.groupby("code", sort=True):
        g = g.sort_values("date").copy()
        g["ret1"] = g["close"].pct_change(1)
        g["ret3"] = g["close"].pct_change(3)
        g["ret5"] = g["close"].pct_change(5)
        g["ret10"] = g["close"].pct_change(10)
        g["ret20"] = g["close"].pct_change(20)
        g["ma5"] = g["close"].rolling(5).mean()
        g["bias5"] = g["close"] / g["ma5"] - 1
        g["fwd1"] = g["close"].shift(-1) / g["close"] - 1
        g["fwd3"] = g["close"].shift(-3) / g["close"] - 1
        g["fwd5"] = g["close"].shift(-5) / g["close"] - 1
        g["fwd10"] = g["close"].shift(-10) / g["close"] - 1
        out.append(g)
    return pd.concat(out, ignore_index=True)


def summarize_subset(sub: pd.DataFrame, t3: float, t20: float) -> dict:
    result = {
        "ret3_threshold_pct": round(t3 * 100, 2),
        "ret20_threshold_pct": round(t20 * 100, 2),
        "samples": int(len(sub)),
        "codes": int(sub["code"].nunique()) if len(sub) else 0,
    }
    if len(sub) == 0:
        return result

    result["date_min"] = sub["date"].min().strftime("%Y-%m-%d")
    result["date_max"] = sub["date"].max().strftime("%Y-%m-%d")
    result["avg_ret1_pct"] = round(float(sub["ret1"].mean() * 100), 3)
    result["avg_ret3_pct"] = round(float(sub["ret3"].mean() * 100), 3)
    result["avg_ret20_pct"] = round(float(sub["ret20"].mean() * 100), 3)
    result["avg_bias5_pct"] = round(float(sub["bias5"].mean() * 100), 3)
    for col in ["fwd1", "fwd3", "fwd5", "fwd10"]:
        valid = sub[col].dropna()
        if valid.empty:
            continue
        result["avg_%s_pct" % col] = round(float(valid.mean() * 100), 3)
        result["median_%s_pct" % col] = round(float(valid.median() * 100), 3)
        result["down_%s_ratio" % col] = round(float((valid < 0).mean()), 4)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="对 ret3/ret20 阈值做网格扫描")
    parser.add_argument("--data", required=True, help="历史数据 csv")
    parser.add_argument("--outdir", default="validator_output/grid_scan", help="输出目录")
    args = parser.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    df = load_price_data(Path(args.data))
    features = build_features(df)
    features = features.dropna(subset=["ret3", "ret20", "fwd1", "fwd3", "fwd5", "fwd10"])

    ret20_thresholds = [0.08, 0.10, 0.12, 0.15, 0.18]
    ret3_thresholds = [0.04, 0.05, 0.06, 0.07]

    gt_rows = []
    low20_rows = []

    for t3 in ret3_thresholds:
        for t20 in ret20_thresholds:
            hot = features[(features["ret3"] > t3) & (features["ret20"] > t20)].copy()
            low20 = features[(features["ret3"] > t3) & (features["ret20"] <= t20)].copy()
            gt_rows.append(summarize_subset(hot, t3, t20))
            low20_rows.append(summarize_subset(low20, t3, t20))

    gt_df = pd.DataFrame(gt_rows).sort_values(["ret3_threshold_pct", "ret20_threshold_pct"]).reset_index(drop=True)
    low20_df = pd.DataFrame(low20_rows).sort_values(["ret3_threshold_pct", "ret20_threshold_pct"]).reset_index(drop=True)

    gt_df.to_csv(outdir / "ret3_gt_ret20_gt.csv", index=False, encoding="utf-8-sig")
    low20_df.to_csv(outdir / "ret3_gt_ret20_le.csv", index=False, encoding="utf-8-sig")

    summary = {
        "data_rows": int(len(df)),
        "feature_rows": int(len(features)),
        "ret3_thresholds_pct": [x * 100 for x in ret3_thresholds],
        "ret20_thresholds_pct": [x * 100 for x in ret20_thresholds],
        "hot_table": gt_df.to_dict(orient="records"),
        "low20_table": low20_df.to_dict(orient="records"),
    }
    (outdir / "grid_scan_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    lines = []
    lines.append("# 热度阈值网格扫描")
    lines.append("")
    lines.append("## 条件一")
    lines.append("")
    lines.append("- 热门过热组：`ret3 > 阈值 and ret20 > 阈值`")
    lines.append("- 对照组：`ret3 > 阈值 and ret20 <= 阈值`")
    lines.append("")
    lines.append("## 热门过热组结果")
    lines.append("")
    for _, row in gt_df.iterrows():
        lines.append(
            "- ret3>%s%% 且 ret20>%s%%: 样本%s, avg_fwd3=%s%%, avg_fwd5=%s%%, down_fwd5=%s"
            % (
                row["ret3_threshold_pct"],
                row["ret20_threshold_pct"],
                int(row["samples"]),
                row.get("avg_fwd3_pct", ""),
                row.get("avg_fwd5_pct", ""),
                row.get("down_fwd5_ratio", ""),
            )
        )
    lines.append("")
    lines.append("## 对照组结果")
    lines.append("")
    for _, row in low20_df.iterrows():
        lines.append(
            "- ret3>%s%% 且 ret20<=%s%%: 样本%s, avg_fwd3=%s%%, avg_fwd5=%s%%, down_fwd5=%s"
            % (
                row["ret3_threshold_pct"],
                row["ret20_threshold_pct"],
                int(row["samples"]),
                row.get("avg_fwd3_pct", ""),
                row.get("avg_fwd5_pct", ""),
                row.get("down_fwd5_ratio", ""),
            )
        )

    (outdir / "grid_scan_report.md").write_text("\n".join(lines), encoding="utf-8")
    print("done")
    print("outdir:", outdir)


if __name__ == "__main__":
    main()
