# 修复建议:在买入前增加更严格的持仓检查

def _has_any_strategy_position(context):
    """检查是否持有策略池内的任何ETF"""
    try:
        positions = context.portfolio.positions
        for code in positions:
            if positions[code].amount > 0 and _is_strategy_security(code):
                return True
    except Exception:
        pass
    return False

def step2_buy(context):
    if g.buy_done:
        return
    g.buy_done = True
    
    if is_trade():
        # 1. 先撤单
        cancelled = _cancel_open_orders()
        if cancelled > 0:
            log.warning('[买前清障] 已撤销%d笔未完成委托' % cancelled)
        
        # 2. 再次同步持仓状态
        _sync_holding_state(context)
        
        # 3. 检查是否有未完成委托
        remaining_orders = _refresh_pending_order_from_open_orders()
        if remaining_orders:
            log.warning('[买前阻断] 仍存在%d笔未完成委托,暂不买入' % len(remaining_orders))
            return
        
        # ★ 4. 新增:再次确认是否真的空仓
        if _has_any_strategy_position(context):
            log.warning('[买前阻断] 检测到策略池内仍有持仓,拒绝买入')
            return
    
    # 原有买入逻辑...
