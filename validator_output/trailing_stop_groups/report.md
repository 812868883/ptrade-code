# 按波动分组的移动止损测试

## 波动分组

- 518880.SS: vol_group=low_vol, daily_vol=0.937%, avg_abs_day_ret=0.617%
- 512890.SS: vol_group=low_vol, daily_vol=1.079%, avg_abs_day_ret=0.752%
- 159611.SZ: vol_group=low_vol, daily_vol=1.215%, avg_abs_day_ret=0.884%
- 513100.SS: vol_group=low_vol, daily_vol=1.357%, avg_abs_day_ret=0.946%
- 159992.SZ: vol_group=mid_vol, daily_vol=1.810%, avg_abs_day_ret=1.330%
- 588000.SS: vol_group=mid_vol, daily_vol=1.879%, avg_abs_day_ret=1.271%
- 563300.SS: vol_group=mid_vol, daily_vol=1.896%, avg_abs_day_ret=1.351%
- 515980.SS: vol_group=mid_vol, daily_vol=2.034%, avg_abs_day_ret=1.504%
- 159681.SZ: vol_group=high_vol, daily_vol=2.100%, avg_abs_day_ret=1.316%
- 513180.SS: vol_group=high_vol, daily_vol=2.144%, avg_abs_day_ret=1.611%
- 162411.SZ: vol_group=high_vol, daily_vol=2.163%, avg_abs_day_ret=1.511%
- 515880.SS: vol_group=high_vol, daily_vol=2.170%, avg_abs_day_ret=1.587%

## 各组止损表现

- high_vol | stop=4.0% | samples=668 | avg_exit=2.155% | median_exit=-1.064% | down_ratio=0.5704 | avg_hold_days=8.7
- high_vol | stop=4.5% | samples=668 | avg_exit=1.74% | median_exit=-1.156% | down_ratio=0.5674 | avg_hold_days=9.38
- high_vol | stop=5.0% | samples=668 | avg_exit=1.119% | median_exit=-1.896% | down_ratio=0.6003 | avg_hold_days=10.51
- high_vol | stop=5.5% | samples=668 | avg_exit=1.04% | median_exit=-1.797% | down_ratio=0.5928 | avg_hold_days=11.59
- high_vol | stop=6.0% | samples=668 | avg_exit=0.696% | median_exit=-1.77% | down_ratio=0.5823 | avg_hold_days=12.71
- low_vol | stop=4.0% | samples=147 | avg_exit=-1.334% | median_exit=-2.402% | down_ratio=0.6939 | avg_hold_days=8.9
- low_vol | stop=4.5% | samples=147 | avg_exit=-1.107% | median_exit=-1.915% | down_ratio=0.6122 | avg_hold_days=10.56
- low_vol | stop=5.0% | samples=147 | avg_exit=-0.564% | median_exit=-0.598% | down_ratio=0.5102 | avg_hold_days=12.28
- low_vol | stop=5.5% | samples=147 | avg_exit=-0.551% | median_exit=0.0% | down_ratio=0.483 | avg_hold_days=13.24
- low_vol | stop=6.0% | samples=147 | avg_exit=-0.747% | median_exit=0.0% | down_ratio=0.4966 | avg_hold_days=13.73
- mid_vol | stop=4.0% | samples=446 | avg_exit=0.68% | median_exit=-2.134% | down_ratio=0.6413 | avg_hold_days=8.5
- mid_vol | stop=4.5% | samples=446 | avg_exit=0.022% | median_exit=-2.24% | down_ratio=0.6345 | avg_hold_days=9.2
- mid_vol | stop=5.0% | samples=446 | avg_exit=0.146% | median_exit=-2.118% | down_ratio=0.6188 | avg_hold_days=10.71
- mid_vol | stop=5.5% | samples=446 | avg_exit=0.056% | median_exit=-2.126% | down_ratio=0.6166 | avg_hold_days=11.53
- mid_vol | stop=6.0% | samples=446 | avg_exit=-0.047% | median_exit=-2.148% | down_ratio=0.6009 | avg_hold_days=12.29