# 策略数据验证报告

## 数据质量概览

- 总行数：20030
- 标的数量：12
- 起始日期：2014-01-02
- 结束日期：2026-04-01
- 重复记录：0
- 空收盘价：0
- 非正收盘价：0

## 规则验证结果

### 当天涨超5且20日涨超12

- 过滤条件：`ret1 > 0.05 and ret20 > 0.12`
- 样本数：90
- 状态：ok
- 标的数：11
- 覆盖区间：2016-12-01 ~ 2026-03-30
- avg_fwd1_pct：0.947%
- avg_fwd3_pct：-0.007%
- avg_fwd5_pct：-0.715%
- avg_fwd10_pct：0.72%
- down_fwd1_ratio：0.5556
- down_fwd3_ratio：0.5506
- down_fwd5_ratio：0.5114
- down_fwd10_ratio：0.4943

### 3日涨超6且20日涨超12

- 过滤条件：`ret3 > 0.06 and ret20 > 0.12`
- 样本数：249
- 状态：ok
- 标的数：11
- 覆盖区间：2014-06-23 ~ 2026-03-31
- avg_fwd1_pct：0.218%
- avg_fwd3_pct：-0.022%
- avg_fwd5_pct：-0.227%
- avg_fwd10_pct：0.632%
- down_fwd1_ratio：0.5221
- down_fwd3_ratio：0.5425
- down_fwd5_ratio：0.5366
- down_fwd10_ratio：0.498

### 3日涨超6但20日涨幅不高

- 过滤条件：`ret3 > 0.06 and ret20 <= 0.12`
- 样本数：290
- 状态：ok
- 标的数：12
- 覆盖区间：2014-05-22 ~ 2026-04-01
- avg_fwd1_pct：0.152%
- avg_fwd3_pct：0.991%
- avg_fwd5_pct：1.079%
- avg_fwd10_pct：1.678%
- down_fwd1_ratio：0.5121
- down_fwd3_ratio：0.474
- down_fwd5_ratio：0.4618
- down_fwd10_ratio：0.4375

### 20日涨超15且偏离5日均线超4

- 过滤条件：`ret20 > 0.15 and bias5 > 0.04`
- 样本数：182
- 状态：ok
- 标的数：11
- 覆盖区间：2014-06-23 ~ 2026-03-30
- avg_fwd1_pct：0.295%
- avg_fwd3_pct：-0.634%
- avg_fwd5_pct：-0.738%
- avg_fwd10_pct：0.631%
- down_fwd1_ratio：0.5385
- down_fwd3_ratio：0.558
- down_fwd5_ratio：0.5444
- down_fwd10_ratio：0.514
