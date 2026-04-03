# PTrade开发经验教训记录

## 更新时间：2026-04-02

---

## 一、已发现的Bug及修复

### Bug 1: handle_data 在日线模式下不触发
**发现时间**: 2026-04-02
**影响版本**: etf实盘动态防守23半小时.txt

**问题描述**:
代码注释说要"每半小时执行风控"，但用 `handle_data` 实现。而日线级别策略时 `handle_data` 每天只执行一次（15:00），不是"每分钟"。

**教训**:
- `handle_data` 的执行频率取决于**策略频率设置**，不是代码决定的
- 日线级别 = 每天一次
- 分钟级别 = 每分钟一次
- 如果需要分钟级扫描，策略必须选择**分钟级频率**

**修复方案**:
```python
# 方案1: 注册多个run_daily（受≤5限制）
run_daily(context, step1_sell, time='14:30')
run_daily(context, step2_buy, time='14:40')

# 方案2: 分钟级策略用handle_data每分钟扫描
# 策略频率设置选择"分钟级"
```

---

### Bug 2: on_trade_response 部分卖出时 highest_price 未清空
**发现时间**: 2026-04-02
**影响版本**: etf实盘动态防守23半小时.txt

**问题描述**:
卖出成交后，只有在 `actual_holding is None`（真正空仓）时才清空 `highest_price`。如果部分卖出，`highest_price` 保留旧值，导致下次风控判断错误。

**教训**:
卖出时无论是否全部成交，highest_price都应该清空或重置，因为：
1. 部分卖出后，持仓成本已经改变
2. 旧最高价不再适用于新的持仓

**修复方案**:
```python
elif entrust_bs == '2':  # 卖出
    actual = _sync_holding_state(context)
    if actual is None:
        # 全成交，真正空仓
        g.highest_price = 0.0
        _save_state({})
    else:
        # 部分成交，highest_price也应该清空
        g.highest_price = 0.0
```

---

### Bug 3: sold_today_codes 重启后丢失
**发现时间**: 2026-04-02

**问题描述**:
`sold_today_codes` 存在内存中，每日重启后丢失，导致当日卖出的标的可以被再次买入（违反规则）。

**教训**:
任何影响交易决策的状态，如果内存重启会丢失，都必须持久化到硬盘。

**修复方案**:
```python
# 每日盘前从硬盘加载
state = _load_state()
g.sold_today_codes = set(state.get('sold_today', []))

# 卖出成交后更新
g.sold_today_codes.add(code6)
_save_state({'sold_today': list(g.sold_today_codes)})
```

---

### Bug 4: 配置文件不自动创建
**发现时间**: 2026-04-02

**问题描述**:
代码依赖外部配置文件 `etf12_config.json`，但如果文件不存在，策略会使用硬编码默认值，用户不知道可以修改配置。

**教训**:
如果策略依赖外部配置，应该提供**不存在时自动创建默认配置**的功能。

**修复方案**:
```python
def _load_config():
    data = _load_json('etf12_config.json')
    if data is None:
        return _create_default_config()  # 不存在则创建
    return data
```

---

### Bug 5: 部分成交不继续追买
**发现时间**: 2026-04-02

**问题描述**:
实盘买入ETF时可能部分成交，剩余股数不会自动补买，可能导致资金闲置或持仓不足。

**教训**:
实盘下单不等于全部成交，需要在回调中追踪实际成交数量，未满额时继续追买。

**修复方案**:
```python
# 买入时记录目标股数
g.target_buy_shares = shares

# 成交回调中检查
def _check_continue_buy(context, stock_code, filled_amount):
    positions = context.portfolio.positions
    current = positions[stock_code].amount
    remaining = g.target_buy_shares - current
    if remaining > 0:
        _do_buy(context, stock_code, remaining)  # 继续买
```

---

## 二、ptrade官方文档确认的坑

### 坑1: order_target/order_target_value 慎用
**官方文档明确警告**:
> 该接口的使用有场景限制，回测可以正常使用，交易谨慎使用。交易场景下持仓信息同步有时滞，一般在6秒左右...

**经验**: 实盘优先用 `order()` 自己算数量，不用这两个接口。

---

### 坑2: get_open_orders() 返回类型
**官方文档**:
> 返回 `list[Order]`，不是字符串列表

**经验**: 直接 `cancel_order(order_obj)`，不要传字符串order_id。

---

### 坑3: check_limit() 返回字典
**官方文档**:
> 返回字典 `{code: flag}`

**经验**:
```python
result = check_limit(code)
if isinstance(result, dict):
    flag = result.get(code, 0)
else:
    flag = result  # 兼容旧格式
```

---

### 坑4: 涨跌停价格精度
**官方文档**:
> ETF/LOF/可转债价格3位，股票2位

**经验**: 下单时必须 `round(price, 3)` for ETF，否则废单。

---

### 坑5: 回调里下单死循环
**官方文档警告**:
> 当在主推里调用委托接口时，需要进行判断处理避免无限迭代循环问题

**经验**: 回调里下单必须加防重入标志。

---

## 三、ETF实盘策略特殊要求

### 3.1 ETF池外的持仓不影响
**场景**: 账户可能有其他策略持有ETF，这些持仓不能被本策略误判为自己的持仓

**解决方案**:
```python
def _is_strategy_security(code):
    """判断是否属于本策略ETF池"""
    for pool_code in g.codes:
        if _same_security(code, pool_code):
            return True
    return False

def _sync_holding_state(context):
    """只识别本策略ETF池的持仓"""
    positions = context.portfolio.positions
    for code in positions:
        if positions[code].amount > 0 and _is_strategy_security(code):
            g.current_holding = code
            return code
    g.current_holding = None
    return None
```

---

### 3.2 买入前检查其他策略持仓
**场景**: 14:40买入前，要确认账户中没有其他策略持有本策略ETF池的股票

**解决方案**:
```python
def _find_other_strategy_holdings(context):
    """找出账户中其他策略持有的本策略ETF"""
    other = []
    for code in context.portfolio.positions:
        if positions[code].amount > 0 and not _is_strategy_security(code):
            other.append(code)
    return other
```

---

## 四、工作流建议

### 4.1 开发新策略流程
1. 写策略代码
2. 对照检查清单逐项检查
3. 回测验证
4. 观察日志输出是否正常
5. 小资金实盘验证
6. 发现问题更新教训文档

### 4.2 检查顺序
1. 先跑一遍检查清单
2. 再用ptrade文档核对API用法
3. 最后检查历史教训中类似问题的修复

---

## 五、下次开发记得

- [ ] 策略频率选择**分钟级**（如果需要每分钟扫描）
- [ ] 硬盘持久化任何影响交易的内存状态
- [ ] 所有卖出/买入都要打日志
- [ ] 回调中添加原始数据日志便于调试
- [ ] ETF价格3位小数，股票2位
- [ ] 先检查配置文件是否存在，不存在则创建默认
