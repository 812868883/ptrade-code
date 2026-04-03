"""
PTrade策略自动化检查脚本
使用方法: python check_strategy.py your_strategy.py
"""

import re
import sys

def check_strategy(filepath):
    """检查策略文件是否符合规范"""

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
        lines = content.split('\n')

    issues = []
    warnings = []

    # ========== 1. run_daily数量检查 ==========
    run_daily_count = len(re.findall(r'run_daily\s*\(', content))
    run_interval_count = len(re.findall(r'run_interval\s*\(', content))
    total_scheduled = run_daily_count + run_interval_count

    if total_scheduled > 5:
        issues.append(f"[CRITICAL] run_daily+run_interval总数={total_scheduled}，超过5个上限")
    elif total_scheduled == 5:
        warnings.append(f"[WARNING] run_daily+run_interval总数=5，达到上限")
    else:
        print(f"  [OK] run_daily+run_interval={total_scheduled} (≤5)")

    # ========== 2. order_target/order_target_value 检查 ==========
    if 'order_target(' in content:
        issues.append("[严重] 使用了order_target（交易场景慎用，有持仓延迟问题）")
    else:
        print("  ✅ 未使用order_target")

    if 'order_target_value(' in content:
        issues.append("[严重] 使用了order_target_value（交易场景慎用）")
    else:
        print("  ✅ 未使用order_target_value")

    # ========== 3. set_parameters位置检查 ==========
    in_initialize = False
    initialize_started = False
    for i, line in enumerate(lines):
        if 'def initialize(' in line:
            initialize_started = True
            in_initialize = True
        elif initialize_started and line.startswith('def '):
            in_initialize = False
        if 'set_parameters(' in line and not in_initialize:
            issues.append(f"[严重] set_parameters在initialize外调用（第{i+1}行）")

    if 'set_parameters(' in content:
        print("  ✅ set_parameters调用检查通过")

    # ========== 4. get_open_orders返回值处理 ==========
    if 'get_open_orders()' in content:
        # 检查是否直接用字符串比较
        if "get_open_orders()[0]['symbol']" in content or 'get_open_orders()[0]["symbol"]' in content:
            issues.append("[严重] get_open_orders返回list[Order]，不能直接用字符串下标")

        # 检查是否正确提取symbol
        if 'order.symbol' in content or 'order.get(' in content:
            print("  ✅ get_open_orders正确处理Order对象")
        else:
            warnings.append("[注意] get_open_orders返回的Order对象处理方式不明确")

    # ========== 5. check_limit返回值检查 ==========
    if 'check_limit(' in content:
        # 检查是否有dict处理
        if 'isinstance' in content and 'dict' in content:
            print("  ✅ check_limit正确处理dict返回值")
        else:
            warnings.append("[警告] check_limit返回dict，建议用isinstance检查")

    # ========== 6. 价格精度检查 ==========
    # 检查ETF相关的round调用
    etf_round_3 = len(re.findall(r'round\([^)]+,3\)', content))
    stock_round_2 = len(re.findall(r'round\([^)]+,2\)', content))

    if etf_round_3 > 0:
        print(f"  ✅ 发现{etf_round_3}处3位小数精度处理")
    if stock_round_2 > 0:
        print(f"  ✅ 发现{stock_round_2}处2位小数精度处理")

    # ========== 7. 持久化检查 ==========
    has_json_save = 'json.dump' in content or 'json.dumps' in content
    has_pickle_save = 'pickle.dump' in content or 'pickle.dumps' in content

    if has_json_save:
        print("  ✅ 使用json持久化")
    elif has_pickle_save:
        print("  ✅ 使用pickle持久化")
    else:
        issues.append("[严重] 未发现持久化代码（硬盘持久化是实盘必须）")

    # ========== 8. highest_price持久化检查 ==========
    if 'highest_price' in content:
        if 'highest_price' in content and ('_save_state' in content or '_save_json' in content):
            print("  ✅ highest_price有持久化")
        else:
            issues.append("[严重] highest_price没有持久化（每日重启会丢失）")

    # ========== 9. pending_order状态管理 ==========
    if 'pending_order' in content or 'g.pending' in content:
        if '_refresh_pending_order' in content:
            print("  ✅ pending_order有刷新机制")
        else:
            warnings.append("[警告] pending_order没有明确的刷新函数")

    # ========== 10. 回调函数检查 ==========
    has_on_trade = 'def on_trade_response(' in content
    has_on_order = 'def on_order_response(' in content

    if has_on_trade:
        print("  ✅ 有on_trade_response回调")

        # 检查是否有原始数据日志
        if 'entrust_bs' in content and 'log' in content:
            print("  ✅ 成交回调有原始数据日志（便于调试）")
    else:
        issues.append("[严重] 缺少on_trade_response回调（实盘必须有）")

    if has_on_order:
        print("  ✅ 有on_order_response回调")

    # ========== 11. before_trading_start检查 ==========
    has_before = 'def before_trading_start(' in content
    if has_before:
        before_section = content[content.find('def before_trading_start'):]
        before_section = before_section[:before_section.find('\ndef ', 1)] if '\ndef ' in before_section[1:] else before_section

        checks = [
            ('_sync_holding_state', '同步持仓'),
            ('_load_state', '读取持久化状态'),
            ('filter_stock_by_status', '过滤停牌'),
            ('_refresh_pending_order', '刷新pending状态')
        ]

        for func, desc in checks:
            if func in before_section:
                print(f"  ✅ before_trading_start有{desc}")
            else:
                warnings.append(f"[警告] before_trading_start缺少{desc}")
    else:
        issues.append("[严重] 缺少before_trading_start函数（盘前准备必须）")

    # ========== 12. 卖出时防重复检查 ==========
    if '_do_sell' in content or 'def _sell' in content:
        sell_func = content[content.find('def _do_sell') if '_do_sell' in content else content.find('def _sell'):]
        sell_func = sell_func[:sell_func.find('\ndef ', 1)] if '\ndef ' in sell_func[1:] else sell_func

        if 'pending_order' in sell_func and ('sell' in sell_func or 'Sell' in sell_func):
            print("  ✅ 卖出有pending_order防重检查")
        else:
            warnings.append("[警告] 卖出可能没有pending_order防重检查")

    # ========== 13. 涨跌停检查 ==========
    if '_get_limit_flag' in content or 'check_limit(' in content:
        print("  ✅ 有涨跌停检查")
    else:
        warnings.append("[警告] 没有涨跌停检查")

    # ========== 14. 日志输出检查 ==========
    log_count = len(re.findall(r'log\.(info|warning|error)', content))
    if log_count > 10:
        print(f"  ✅ 有{log_count}处日志输出")
    else:
        warnings.append(f"[注意] 日志输出较少({log_count}处)，实盘难以追踪")

    # ========== 15. 每分钟handle_data检查 ==========
    if 'def handle_data(' in content:
        handle_section = content[content.find('def handle_data'):]
        handle_section = handle_section[:handle_section.find('\ndef ', 1)] if '\ndef ' in handle_section[1:] else handle_section

        if '09:3' in handle_section or '09:4' in handle_section or '09:5' in handle_section:
            print("  ✅ handle_data有分钟级时间判断")
        else:
            warnings.append("[注意] handle_data没有明确的分钟级时间判断")

    # ========== 输出报告 ==========
    print("\n" + "=" * 60)
    print("检查报告")
    print("=" * 60)

    if issues:
        print(f"\n🔴 严重问题 ({len(issues)}项):")
        for issue in issues:
            print(f"  {issue}")

    if warnings:
        print(f"\n🟡 建议改进 ({len(warnings)}项):")
        for warning in warnings:
            print(f"  {warning}")

    if not issues and not warnings:
        print("\n✅ 所有检查通过！")
    elif not issues:
        print("\n✅ 无严重问题，可以继续测试")
    else:
        print("\n🔴 有严重问题，请修复后再测试")

    return len(issues) == 0

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("使用方法: python check_strategy.py <策略文件路径>")
        sys.exit(1)

    filepath = sys.argv[1]
    success = check_strategy(filepath)
    sys.exit(0 if success else 1)
