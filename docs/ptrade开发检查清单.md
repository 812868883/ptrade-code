# PTrade开发检查清单

## 使用方法

每开发完一个新策略，按此清单逐项检查：

---

## 一、必须检查的API规范（来自官方文档）

### 1.1 run_daily/run_interval 数量限制
- [ ] run_daily + run_interval 总数 ≤ 5
- [ ] 超出部分会静默不触发

### 1.2 set_parameters 位置
- [ ] 只在 `initialize()` 中调用
- [ ] `not_restart_trade`、`server_restart_not_do_before` 必须在initialize中设置

### 1.3 order返回值
- [ ] `order()` 返回 order_id 或 None，**不代表成交**
- [ ] 不能把返回值当成交确认

### 1.4 order_target / order_target_value
- [ ] 文档明确警告：交易场景持仓同步有延迟（约6秒）
- [ ] 交易场景慎用，可能重复下单

### 1.5 get_open_orders()
- [ ] 返回 `list[Order]`，不是字符串列表
- [ ] 遍历时用 `order.symbol` 或 `order.get('symbol')`

### 1.6 check_limit()
- [ ] 返回字典：`{code: flag}`
- [ ] 不能直接跟整数比较
- [ ] 正确用法：`check_limit(code)[code]` 或遍历取

### 1.7 价格精度
- [ ] ETF/LOF/可转债：3位小数 `round(price, 3)`
- [ ] 股票：2位小数 `round(price, 2)`
- [ ] 不按精度报单会废单

### 1.8 limit_price 参数
- [ ] 快照失败返回空dict
- [ ] 必须检查快照结果再下单
- [ ] 不传limit_price则用快照last_px，但快照失败会废单

### 1.9 持仓同步延迟
- [ ] 交易场景持仓同步约6秒延迟
- [ ] 连续下单要加防重
- [ ] 要结合 pending_order + 回调确认

---

## 二、必须维护的状态

### 2.1 pending_order 状态
- [ ] 买单提交后标记 `{'code': xxx, 'side': 'buy', 'order_id': xxx}`
- [ ] 卖单提交后标记 `{'code': xxx, 'side': 'sell', 'order_id': xxx}`
- [ ] 回调确认后清空
- [ ] 查询未完成订单后重建

### 2.2 highest_price 持久化
- [ ] 持仓期间必须持久化到硬盘
- [ ] 卖空后必须清空
- [ ] 不能只靠内存（ptrade每日重启会丢失）

### 2.3 sold_today_codes 持久化
- [ ] 当日卖出的标的不能当日买回
- [ ] 重启后sold_today_codes会丢失
- [ ] 需要持久化到硬盘

---

## 三、回调函数检查

### 3.1 on_trade_response
- [ ] 终结态判断：`status in ['5', '6', '8', '9']`（部撤/已撤/已成/废单）
- [ ] 买入后更新持仓 + highest_price
- [ ] 卖出后清空状态（无论全成还是部分成）
- [ ] 添加原始数据日志便于调试

### 3.2 on_order_response
- [ ] 记录error_info和status=9的废单
- [ ] 终结态刷新pending_order

### 3.3 回调中下单
- [ ] 官方警告：回调里下单可能死循环
- [ ] 必须加防重入标志

---

## 四、before_trading_start 必须做

- [ ] 同步真实持仓（不是只信内存）
- [ ] 读取硬盘持久化状态
- [ ] 过滤停牌/退市标的
- [ ] 重建pending_order状态
- [ ] 清理空仓残留状态

---

## 五、交易时间与频率

### 5.1 handle_data 执行时间
- [ ] 日线级别：每天一次（回测15:00，实盘14:50）
- [ ] 分钟级别：每分钟执行
- [ ] **如果需要分钟级风控，必须用分钟级策略**

### 5.2 run_daily 可设置范围
- [ ] 回测日线：time只能在9:31~11:30和13:00~15:00
- [ ] 回测分钟：time只能在9:31~11:30和13:00~15:00
- [ ] 实盘不受限制

---

## 六、实盘特有检查

### 6.1 其他策略隔离
- [ ] 获取持仓时只识别本策略标的池
- [ ] 买入前检查账户是否有其他策略持有的本策略ETF

### 6.2 部分成交处理
- [ ] 记录目标买入股数
- [ ] 回调中检查已成交数量
- [ ] 未满额则继续追买

### 6.3 涨跌停检查
- [ ] 买入前检查涨停（flag=1不能买）
- [ ] 卖出前检查跌停（flag=-1不能卖）

---

## 七、防重复下单

### 7.1 卖出防重
- [ ] 有pending sell单时不再重复报卖单
- [ ] 有持仓时不报卖空单

### 7.2 买入防重
- [ ] 有pending buy单时不再重复报买单
- [ ] 已有持仓时不重复买入

---

## 八、每条检查的执行命令

```bash
# 检查run_daily数量
grep -c "run_daily" strategy.py

# 检查是否有order_target
grep "order_target" strategy.py

# 检查价格精度（ETF应该是3位）
grep "round.*3" strategy.py

# 检查是否有持久化
grep "json.dump\|pickle.dump" strategy.py
```
