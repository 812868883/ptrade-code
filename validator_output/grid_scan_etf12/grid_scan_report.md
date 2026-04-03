# 热度阈值网格扫描

## 条件一

- 热门过热组：`ret3 > 阈值 and ret20 > 阈值`
- 对照组：`ret3 > 阈值 and ret20 <= 阈值`

## 热门过热组结果

- ret3>4.0% 且 ret20>8.0%: 样本623, avg_fwd3=0.439%, avg_fwd5=0.198%, down_fwd5=0.4992
- ret3>4.0% 且 ret20>10.0%: 样本513, avg_fwd3=0.287%, avg_fwd5=0.126%, down_fwd5=0.5166
- ret3>4.0% 且 ret20>12.0%: 样本423, avg_fwd3=0.206%, avg_fwd5=-0.031%, down_fwd5=0.5035
- ret3>4.0% 且 ret20>15.0%: 样本304, avg_fwd3=-0.436%, avg_fwd5=-0.58%, down_fwd5=0.5362
- ret3>4.0% 且 ret20>18.0%: 样本222, avg_fwd3=-0.788%, avg_fwd5=-1.057%, down_fwd5=0.536
- ret3>5.0% 且 ret20>8.0%: 样本447, avg_fwd3=0.459%, avg_fwd5=0.148%, down_fwd5=0.4944
- ret3>5.0% 且 ret20>10.0%: 样本384, avg_fwd3=0.372%, avg_fwd5=0.096%, down_fwd5=0.5104
- ret3>5.0% 且 ret20>12.0%: 样本327, avg_fwd3=0.231%, avg_fwd5=-0.094%, down_fwd5=0.5076
- ret3>5.0% 且 ret20>15.0%: 样本249, avg_fwd3=-0.398%, avg_fwd5=-0.57%, down_fwd5=0.5382
- ret3>5.0% 且 ret20>18.0%: 样本183, avg_fwd3=-0.881%, avg_fwd5=-1.24%, down_fwd5=0.5519
- ret3>6.0% 且 ret20>8.0%: 样本300, avg_fwd3=0.358%, avg_fwd5=0.14%, down_fwd5=0.5133
- ret3>6.0% 且 ret20>10.0%: 样本274, avg_fwd3=0.17%, avg_fwd5=0.071%, down_fwd5=0.5255
- ret3>6.0% 且 ret20>12.0%: 样本245, avg_fwd3=-0.009%, avg_fwd5=-0.294%, down_fwd5=0.5388
- ret3>6.0% 且 ret20>15.0%: 样本199, avg_fwd3=-0.727%, avg_fwd5=-0.821%, down_fwd5=0.5628
- ret3>6.0% 且 ret20>18.0%: 样本150, avg_fwd3=-1.34%, avg_fwd5=-1.64%, down_fwd5=0.5867
- ret3>7.0% 且 ret20>8.0%: 样本214, avg_fwd3=0.393%, avg_fwd5=-0.059%, down_fwd5=0.5467
- ret3>7.0% 且 ret20>10.0%: 样本198, avg_fwd3=0.168%, avg_fwd5=-0.137%, down_fwd5=0.5505
- ret3>7.0% 且 ret20>12.0%: 样本182, avg_fwd3=0.002%, avg_fwd5=-0.455%, down_fwd5=0.5604
- ret3>7.0% 且 ret20>15.0%: 样本156, avg_fwd3=-0.834%, avg_fwd5=-1.054%, down_fwd5=0.5897
- ret3>7.0% 且 ret20>18.0%: 样本121, avg_fwd3=-1.448%, avg_fwd5=-1.892%, down_fwd5=0.6198

## 对照组结果

- ret3>4.0% 且 ret20<=8.0%: 样本728, avg_fwd3=0.498%, avg_fwd5=0.696%, down_fwd5=0.4684
- ret3>4.0% 且 ret20<=10.0%: 样本838, avg_fwd3=0.583%, avg_fwd5=0.675%, down_fwd5=0.4618
- ret3>4.0% 且 ret20<=12.0%: 样本928, avg_fwd3=0.591%, avg_fwd5=0.693%, down_fwd5=0.4731
- ret3>4.0% 且 ret20<=15.0%: 样本1047, avg_fwd3=0.734%, avg_fwd5=0.77%, down_fwd5=0.467
- ret3>4.0% 且 ret20<=18.0%: 样本1129, avg_fwd3=0.718%, avg_fwd5=0.766%, down_fwd5=0.4721
- ret3>5.0% 且 ret20<=8.0%: 样本395, avg_fwd3=0.41%, avg_fwd5=0.642%, down_fwd5=0.4911
- ret3>5.0% 且 ret20<=10.0%: 样本458, avg_fwd3=0.49%, avg_fwd5=0.618%, down_fwd5=0.4782
- ret3>5.0% 且 ret20<=12.0%: 样本515, avg_fwd3=0.566%, avg_fwd5=0.681%, down_fwd5=0.4835
- ret3>5.0% 且 ret20<=15.0%: 样本593, avg_fwd3=0.786%, avg_fwd5=0.779%, down_fwd5=0.4739
- ret3>5.0% 且 ret20<=18.0%: 样本659, avg_fwd3=0.802%, avg_fwd5=0.83%, down_fwd5=0.4765
- ret3>6.0% 且 ret20<=8.0%: 样本233, avg_fwd3=0.79%, avg_fwd5=0.844%, down_fwd5=0.4764
- ret3>6.0% 且 ret20<=10.0%: 样本259, avg_fwd3=0.946%, avg_fwd5=0.846%, down_fwd5=0.4672
- ret3>6.0% 且 ret20<=12.0%: 样本288, avg_fwd3=1.02%, avg_fwd5=1.079%, down_fwd5=0.4618
- ret3>6.0% 且 ret20<=15.0%: 样本334, avg_fwd3=1.306%, avg_fwd5=1.204%, down_fwd5=0.4581
- ret3>6.0% 且 ret20<=18.0%: 样本383, avg_fwd3=1.286%, avg_fwd5=1.265%, down_fwd5=0.4621
- ret3>7.0% 且 ret20<=8.0%: 样本132, avg_fwd3=0.949%, avg_fwd5=0.861%, down_fwd5=0.4621
- ret3>7.0% 且 ret20<=10.0%: 样本148, avg_fwd3=1.19%, avg_fwd5=0.865%, down_fwd5=0.4662
- ret3>7.0% 且 ret20<=12.0%: 样本164, avg_fwd3=1.274%, avg_fwd5=1.121%, down_fwd5=0.4634
- ret3>7.0% 且 ret20<=15.0%: 样本190, avg_fwd3=1.787%, avg_fwd5=1.397%, down_fwd5=0.4526
- ret3>7.0% 且 ret20<=18.0%: 样本225, avg_fwd3=1.709%, avg_fwd5=1.466%, down_fwd5=0.4578