import argparse
import json
from pathlib import Path

import pandas as pd


REQUIRED_COLUMNS = ["date", "code", "close"]
OPTIONAL_NUMERIC_COLUMNS = ["open", "high", "low", "volume", "amount"]


def load_price_data(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError("missing required columns: %s" % ",".join(missing))

    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df["code"] = df["code"].astype(str)
    for col in ["close"] + [c for c in OPTIONAL_NUMERIC_COLUMNS if c in df.columns]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.sort_values(["code", "date"]).reset_index(drop=True)
    return df


def audit_data_quality(df: pd.DataFrame) -> dict:
    report = {}
    report["rows"] = int(len(df))
    report["codes"] = int(df["code"].nunique())
    report["date_min"] = df["date"].min().strftime("%Y-%m-%d")
    report["date_max"] = df["date"].max().strftime("%Y-%m-%d")
    report["duplicate_code_date_rows"] = int(df.duplicated(["code", "date"]).sum())
    report["non_positive_close_rows"] = int((df["close"] <= 0).fillna(False).sum())
    report["null_close_rows"] = int(df["close"].isna().sum())

    code_reports = []
    for code, g in df.groupby("code", sort=True):
        g = g.sort_values("date")
        row = {
            "code": code,
            "rows": int(len(g)),
            "date_min": g["date"].min().strftime("%Y-%m-%d"),
            "date_max": g["date"].max().strftime("%Y-%m-%d"),
            "duplicate_rows": int(g.duplicated(["date"]).sum()),
            "null_close_rows": int(g["close"].isna().sum()),
            "non_positive_close_rows": int((g["close"] <= 0).fillna(False).sum()),
        }

        if len(g) >= 2:
            date_diff = g["date"].diff().dt.days.dropna()
            row["max_calendar_gap_days"] = int(date_diff.max()) if not date_diff.empty else 0
            ret1 = g["close"].pct_change(1)
            row["max_abs_day_return_pct"] = round(float(ret1.abs().max() * 100), 2) if not ret1.dropna().empty else 0.0
        else:
            row["max_calendar_gap_days"] = 0
            row["max_abs_day_return_pct"] = 0.0
        code_reports.append(row)

    report["per_code"] = code_reports
    return report


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    out = []
    for code, g in df.groupby("code", sort=True):
        g = g.sort_values("date").copy()
        g["ret1"] = g["close"].pct_change(1)
        g["ret3"] = g["close"].pct_change(3)
        g["ret5"] = g["close"].pct_change(5)
        g["ret10"] = g["close"].pct_change(10)
        g["ret20"] = g["close"].pct_change(20)
        g["ret60"] = g["close"].pct_change(60)
        g["ma5"] = g["close"].rolling(5).mean()
        g["ma10"] = g["close"].rolling(10).mean()
        g["ma20"] = g["close"].rolling(20).mean()
        g["bias5"] = g["close"] / g["ma5"] - 1
        g["bias10"] = g["close"] / g["ma10"] - 1
        g["bias20"] = g["close"] / g["ma20"] - 1
        g["fwd1"] = g["close"].shift(-1) / g["close"] - 1
        g["fwd3"] = g["close"].shift(-3) / g["close"] - 1
        g["fwd5"] = g["close"].shift(-5) / g["close"] - 1
        g["fwd10"] = g["close"].shift(-10) / g["close"] - 1
        out.append(g)
    features = pd.concat(out, ignore_index=True)
    return features


def evaluate_rule(features: pd.DataFrame, rule: dict) -> dict:
    name = rule["name"]
    expr = rule["filter"]
    min_samples = int(rule.get("min_samples", 1))
    subset = features.query(expr, engine="python").copy()

    result = {
        "name": name,
        "filter": expr,
        "samples": int(len(subset)),
        "min_samples": min_samples,
    }

    if len(subset) < min_samples:
        result["status"] = "insufficient_samples"
        return result

    result["status"] = "ok"
    result["codes"] = int(subset["code"].nunique())
    result["date_min"] = subset["date"].min().strftime("%Y-%m-%d")
    result["date_max"] = subset["date"].max().strftime("%Y-%m-%d")

    for col in ["ret1", "ret3", "ret5", "ret10", "ret20", "bias5", "bias10", "bias20", "fwd1", "fwd3", "fwd5", "fwd10"]:
        if col in subset.columns and subset[col].notna().any():
            result["avg_%s_pct" % col] = round(float(subset[col].mean() * 100), 3)

    for col in ["fwd1", "fwd3", "fwd5", "fwd10"]:
        valid = subset[col].dropna()
        if valid.empty:
            continue
        result["down_%s_ratio" % col] = round(float((valid < 0).mean()), 4)
        result["up_%s_ratio" % col] = round(float((valid > 0).mean()), 4)
        result["median_%s_pct" % col] = round(float(valid.median() * 100), 3)

    examples = subset[["date", "code", "close", "ret1", "ret3", "ret20", "fwd1", "fwd3", "fwd5"]].tail(10).copy()
    examples["date"] = examples["date"].dt.strftime("%Y-%m-%d")
    result["recent_examples"] = examples.to_dict(orient="records")
    return result


def load_rules(rule_path: Path) -> list[dict]:
    config = json.loads(rule_path.read_text(encoding="utf-8"))
    rules = config.get("rules", [])
    if not rules:
        raise ValueError("no rules found in %s" % rule_path)
    return rules


def write_markdown_report(output_path: Path, data_report: dict, rule_results: list[dict]) -> None:
    lines = []
    lines.append("# 策略数据验证报告")
    lines.append("")
    lines.append("## 数据质量概览")
    lines.append("")
    lines.append("- 总行数：%s" % data_report["rows"])
    lines.append("- 标的数量：%s" % data_report["codes"])
    lines.append("- 起始日期：%s" % data_report["date_min"])
    lines.append("- 结束日期：%s" % data_report["date_max"])
    lines.append("- 重复记录：%s" % data_report["duplicate_code_date_rows"])
    lines.append("- 空收盘价：%s" % data_report["null_close_rows"])
    lines.append("- 非正收盘价：%s" % data_report["non_positive_close_rows"])
    lines.append("")
    lines.append("## 规则验证结果")
    lines.append("")

    for item in rule_results:
        lines.append("### %s" % item["name"])
        lines.append("")
        lines.append("- 过滤条件：`%s`" % item["filter"])
        lines.append("- 样本数：%s" % item["samples"])
        lines.append("- 状态：%s" % item["status"])
        if item["status"] == "ok":
            lines.append("- 标的数：%s" % item["codes"])
            lines.append("- 覆盖区间：%s ~ %s" % (item["date_min"], item["date_max"]))
            for key in ["avg_fwd1_pct", "avg_fwd3_pct", "avg_fwd5_pct", "avg_fwd10_pct"]:
                if key in item:
                    lines.append("- %s：%s%%" % (key, item[key]))
            for key in ["down_fwd1_ratio", "down_fwd3_ratio", "down_fwd5_ratio", "down_fwd10_ratio"]:
                if key in item:
                    lines.append("- %s：%s" % (key, item[key]))
        lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="验证策略数据质量与规则效果")
    parser.add_argument("--data", required=True, help="历史数据 csv 路径")
    parser.add_argument("--rules", required=True, help="规则配置 json 路径")
    parser.add_argument("--outdir", default="validator_output", help="输出目录")
    args = parser.parse_args()

    data_path = Path(args.data)
    rules_path = Path(args.rules)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    df = load_price_data(data_path)
    data_report = audit_data_quality(df)
    features = build_features(df)
    rules = load_rules(rules_path)
    rule_results = [evaluate_rule(features, rule) for rule in rules]

    (outdir / "data_quality.json").write_text(
        json.dumps(data_report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (outdir / "rule_results.json").write_text(
        json.dumps(rule_results, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    write_markdown_report(outdir / "report.md", data_report, rule_results)

    print("done")
    print("data_quality:", outdir / "data_quality.json")
    print("rule_results:", outdir / "rule_results.json")
    print("report:", outdir / "report.md")


if __name__ == "__main__":
    main()
