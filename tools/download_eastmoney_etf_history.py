import argparse
import json
from pathlib import Path

import pandas as pd
import requests


ETF12 = [
    {"code": "563300.SS", "name": "中证2000ETF"},
    {"code": "159611.SZ", "name": "电力ETF"},
    {"code": "159681.SZ", "name": "算力ETF"},
    {"code": "588000.SS", "name": "科创50ETF"},
    {"code": "513100.SS", "name": "纳指ETF"},
    {"code": "513180.SS", "name": "恒生科技ETF"},
    {"code": "515980.SS", "name": "人工智能ETF"},
    {"code": "518880.SS", "name": "黄金ETF"},
    {"code": "162411.SZ", "name": "华宝油气"},
    {"code": "512890.SS", "name": "红利低波ETF"},
    {"code": "515880.SS", "name": "通信ETF"},
    {"code": "159992.SZ", "name": "创新药ETF"},
]


def em_secid(symbol: str) -> str:
    code, suffix = symbol.split(".")
    if suffix.upper() == "SZ":
        return "0.%s" % code
    if suffix.upper() == "SS":
        return "1.%s" % code
    raise ValueError("unsupported suffix: %s" % symbol)


def fetch_etf_history(symbol: str, start_date: str, end_date: str, adjust: str = "1") -> pd.DataFrame:
    params = {
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f116",
        "ut": "7eea3edcaed734bea9cbfc24409ed989",
        "klt": "101",
        "fqt": adjust,
        "beg": start_date,
        "end": end_date,
        "secid": em_secid(symbol),
    }
    session = requests.Session()
    session.trust_env = False
    resp = session.get("https://push2his.eastmoney.com/api/qt/stock/kline/get", params=params, timeout=20)
    resp.raise_for_status()
    payload = resp.json()
    data = payload.get("data") or {}
    klines = data.get("klines") or []
    if not klines:
        return pd.DataFrame()

    rows = []
    for item in klines:
        parts = item.split(",")
        if len(parts) < 11:
            continue
        rows.append(
            {
                "date": parts[0],
                "open": parts[1],
                "close": parts[2],
                "high": parts[3],
                "low": parts[4],
                "volume": parts[5],
                "amount": parts[6],
                "amplitude_pct": parts[7],
                "pct_change_pct": parts[8],
                "change": parts[9],
                "turnover_pct": parts[10],
            }
        )

    df = pd.DataFrame(rows)
    numeric_cols = [col for col in df.columns if col != "date"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["date"] = pd.to_datetime(df["date"])
    df["code"] = symbol
    df["code6"] = symbol[:6]
    df["data_source"] = "eastmoney"
    return df


def main() -> None:
    parser = argparse.ArgumentParser(description="下载东方财富 ETF 历史日线")
    parser.add_argument("--start", default="20140101")
    parser.add_argument("--end", default="20260401")
    parser.add_argument("--outdir", default="data/etf12_history")
    args = parser.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    all_frames = []
    meta = []

    for item in ETF12:
        symbol = item["code"]
        name = item["name"]
        df = fetch_etf_history(symbol, args.start, args.end, adjust="1")
        if df.empty:
            meta.append({"code": symbol, "name": name, "rows": 0})
            print("empty", symbol, name)
            continue
        df["name"] = name
        one_path = outdir / ("%s.csv" % symbol.replace(".", "_"))
        df.to_csv(one_path, index=False, encoding="utf-8-sig")
        all_frames.append(df)
        meta.append(
            {
                "code": symbol,
                "name": name,
                "rows": int(len(df)),
                "date_min": df["date"].min().strftime("%Y-%m-%d"),
                "date_max": df["date"].max().strftime("%Y-%m-%d"),
            }
        )
        print(symbol, name, len(df), meta[-1]["date_min"], meta[-1]["date_max"])

    if all_frames:
        full_df = pd.concat(all_frames, ignore_index=True)
        full_df = full_df.sort_values(["code", "date"]).reset_index(drop=True)
        full_df.to_csv(outdir / "etf12_history_all.csv", index=False, encoding="utf-8-sig")

    (outdir / "download_meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print("done", outdir)


if __name__ == "__main__":
    main()
