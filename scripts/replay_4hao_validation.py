from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


ROOT = Path(r"C:\Users\mengx\Desktop\量化策略\策略源码")
DATA_FILE = ROOT / "data" / "4hao_focused" / "derived_features.csv"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--min-open-gap", type=float, default=-0.09)
    parser.add_argument("--max-open-gap", type=float, default=0.003)
    parser.add_argument("--require-pullback", action="store_true", default=True)
    parser.add_argument("--allow-strong-exception", action="store_true")
    parser.add_argument("--strong-exception-max-gap", type=float, default=0.01)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    df = pd.read_csv(DATA_FILE)

    valid = df[df["buy_gap_vs_prev_close"].notna()].copy()
    main_board_mask = valid["code"].astype(str).str.zfill(6).str.startswith(
        ("600", "601", "603", "605", "000", "001", "002", "003")
    )
    valid = valid[main_board_mask].copy()

    valid["rule_limit_memory"] = valid["had_limit_prev5"].fillna(0) == 1
    valid["rule_open_gap"] = (valid["buy_gap_vs_prev_close"] >= args.min_open_gap) & (
        valid["buy_gap_vs_prev_close"] <= args.max_open_gap
    )
    valid["rule_pullback"] = valid["prev_pullback"].fillna(0) == 1

    if args.allow_strong_exception:
        valid["rule_pullback_or_exception"] = valid["rule_pullback"] | (
            (valid["buy_gap_vs_prev_close"] <= args.strong_exception_max_gap)
            & (valid["had_limit_prev5"].fillna(0) == 1)
        )
    else:
        valid["rule_pullback_or_exception"] = valid["rule_pullback"]

    valid["final_match"] = (
        valid["rule_limit_memory"] & valid["rule_open_gap"] & valid["rule_pullback_or_exception"]
    )

    print("样本数:", len(valid))
    print("涨停记忆命中:", int(valid["rule_limit_memory"].sum()), "/", len(valid))
    print("开盘缺口命中:", int(valid["rule_open_gap"].sum()), "/", len(valid))
    print("昨日回调命中:", int(valid["rule_pullback"].sum()), "/", len(valid))
    print("最终规则命中:", int(valid["final_match"].sum()), "/", len(valid))

    print("\n未命中样本:")
    miss = valid.loc[
        ~valid["final_match"],
        [
            "trade_id",
            "code",
            "name",
            "buy_date",
            "prev_pullback",
            "had_limit_prev5",
            "buy_gap_vs_prev_close",
        ],
    ]
    if miss.empty:
        print("无")
    else:
        print(miss.to_string(index=False))


if __name__ == "__main__":
    main()
