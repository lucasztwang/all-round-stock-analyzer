#!/usr/bin/env python3
"""
止盈止损模块
融合图片中的五大止盈方法 + 投资者类型推荐 + 心理误区提示
"""

import numpy as np
from typing import Dict, List, Optional

# ── 1. 固定比例止盈法 ─────────────────────────────────────────
def fixed_ratio_take_profit(current_price: float, cost_price: float = None,
                            targets: List[float] = None) -> dict:
    """
    固定比例止盈法
    - 设定 20%/30%/50% 目标，达到即卖
    """
    if targets is None:
        targets = [0.20, 0.30, 0.50]
    if cost_price is None:
        cost_price = current_price

    if cost_price <= 0:
        return {"方法": "固定比例止盈", "说明": "缺少成本价，无法计算"}

    current_return = (current_price - cost_price) / cost_price
    target_prices = []
    triggered = []

    for t in targets:
        tp = cost_price * (1 + t)
        target_prices.append({
            "涨幅目标": f"{t*100:.0f}%",
            "目标价": round(tp, 2),
            "是否触发": current_return >= t,
        })
        if current_return >= t:
            triggered.append(f"{t*100:.0f}%")

    advice = "未达到任何止盈目标，继续持有" if not triggered else (
        f"已达到 {' / '.join(triggered)} 止盈目标，建议按固定比例法分批或全部卖出锁定利润"
    )

    return {
        "方法": "固定比例止盈法",
        "成本价": cost_price,
        "当前价": current_price,
        "当前涨幅": round(current_return * 100, 2),
        "目标清单": target_prices,
        "已触发": triggered,
        "建议": advice,
        "适合人群": "投资新手、上班族、性格保守者",
        "优点": "简单易懂、执行方便、避免贪婪",
        "缺点": "可能卖飞、牛市初期易过早离场、不够灵活",
    }


# ── 2. 移动止盈法（追踪止损） ─────────────────────────────────
def trailing_stop_take_profit(kline_data: list, cost_price: float = None,
                              pullback_ratio: float = 0.10) -> dict:
    """
    移动止盈法：以最高点回撤一定比例作为止盈位
    - 默认回撤 10%（可根据波动调整 8%~20%）
    """
    if not kline_data or len(kline_data) < 5:
        return {"方法": "移动止盈法", "说明": "K线数据不足"}

    closes = np.array([d["收盘"] for d in kline_data], dtype=float)
    highs = np.array([d["最高"] for d in kline_data], dtype=float)
    current = closes[-1]
    recent_high = float(np.max(highs[-20:]))  # 近20日最高价

    if cost_price is None:
        cost_price = current

    stop_price = recent_high * (1 - pullback_ratio)
    triggered = current <= stop_price
    profit_ratio = (current - cost_price) / cost_price * 100

    return {
        "方法": "移动止盈法（追踪止损）",
        "成本价": cost_price,
        "当前价": round(current, 2),
        "近20日最高价": round(recent_high, 2),
        "回撤比例": f"{pullback_ratio*100:.0f}%",
        "移动止盈位": round(stop_price, 2),
        "是否触发止盈": bool(triggered),
        "当前浮盈": round(profit_ratio, 2),
        "建议": (
            f"⚠️ 价格已跌破移动止盈位 {stop_price:.2f}，建议卖出锁定利润" if triggered
            else f"📌 止盈位上移至 {stop_price:.2f}，未跌破则继续持有"
        ),
        "适合人群": "有经验股民、有时间盯盘、追求吃鱼身",
        "优点": "能吃主升浪、回撤即锁定利润、无需预测顶部",
        "缺点": "波动大时频繁触发、需盯盘、回撤比例难设定",
    }


# ── 3. 基本面止盈法 ───────────────────────────────────────────
def fundamental_take_profit(quote: dict, cost_pe: float = None,
                            current_pe: float = None,
                            pe_overvalued_threshold: float = 50) -> dict:
    """
    基本面止盈法：估值过高或行业拐点时卖出
    """
    if current_pe is None:
        current_pe = quote.get("市盈率(动)", 0)

    if current_pe <= 0 or cost_pe is None or cost_pe <= 0:
        return {
            "方法": "基本面止盈法",
            "说明": "缺少买入PE或当前亏损，需人工判断业绩/估值/行业前景",
            "适合人群": "价值投资者、有财务分析能力者、长期投资者",
        }

    pe_expansion = (current_pe - cost_pe) / cost_pe * 100
    overvalued = current_pe >= pe_overvalued_threshold

    if overvalued:
        advice = f"⚠️ 当前PE {current_pe:.1f} 已达估值高位（阈值{pe_overvalued_threshold:.0f}），且较买入PE {cost_pe:.1f} 扩张 {pe_expansion:.1f}%，基本面投资者应考虑止盈"
    else:
        advice = f"📌 当前PE {current_pe:.1f} 较买入PE {cost_pe:.1f} 扩张 {pe_expansion:.1f}%，尚未达到估值高位，可继续持有观察业绩能否跟上"

    return {
        "方法": "基本面止盈法",
        "买入PE": cost_pe,
        "当前PE": current_pe,
        "PE扩张幅度": round(pe_expansion, 2),
        "是否高估": overvalued,
        "建议": advice,
        "适合人群": "价值投资者、有财务分析能力者、长期投资者",
        "优点": "立足长期、逻辑清晰",
        "缺点": "可能错过泡沫、可能卖太晚、需专业能力",
    }


# ── 4. 技术止盈法 ────────────────────────────────────────────
def technical_take_profit(kline_data: list) -> dict:
    """
    技术止盈法：跌破20日线 / RSI>80 / MACD死叉
    """
    if not kline_data or len(kline_data) < 20:
        return {"方法": "技术止盈法", "说明": "K线数据不足"}

    closes = np.array([d["收盘"] for d in kline_data], dtype=float)
    current = float(closes[-1])
    ma20 = float(np.mean(closes[-20:]))
    below_ma20 = current < ma20

    # RSI
    def calc_rsi(data, period=14):
        deltas = np.diff(data)
        gain = np.where(deltas > 0, deltas, 0)
        loss = np.where(deltas < 0, -deltas, 0)
        avg_gain = np.mean(gain[:period])
        avg_loss = np.mean(loss[:period])
        if avg_loss == 0:
            return 100
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    rsi = calc_rsi(closes)
    rsi_overbought = rsi > 80

    # MACD
    def calc_macd(data, fast=12, slow=26, signal=9):
        n = len(data)
        def ema(arr, period):
            res = np.full(n, np.nan)
            if n >= period:
                res[period-1] = np.mean(arr[:period])
                for i in range(period, n):
                    res[i] = 2/(period+1)*arr[i] + (1-2/(period+1))*res[i-1]
            return res
        ema_fast = ema(data, fast)
        ema_slow = ema(data, slow)
        dif = ema_fast - ema_slow
        dea = ema(dif, signal)
        return dif, dea

    dif, dea = calc_macd(closes)
    macd_dead_cross = False
    for i in range(max(2, len(dif)-5), len(dif)):
        if dif[i] < dea[i] and dif[i-1] >= dea[i-1]:
            macd_dead_cross = True
            break

    signals = []
    if below_ma20:
        signals.append("跌破20日均线")
    if rsi_overbought:
        signals.append(f"RSI超买({rsi:.1f})")
    if macd_dead_cross:
        signals.append("MACD死叉")

    triggered = len(signals) > 0

    return {
        "方法": "技术止盈法",
        "当前价": round(current, 2),
        "MA20": round(ma20, 2),
        "跌破MA20": bool(below_ma20),
        "RSI": round(rsi, 2),
        "RSI超买": bool(rsi_overbought),
        "MACD死叉": bool(macd_dead_cross),
        "触发信号": signals,
        "建议": (
            f"⚠️ 技术卖出信号触发：{'、'.join(signals)}，建议止盈/减仓"
            if triggered else "📌 未触发技术卖出信号，可继续持有"
        ),
        "适合人群": "技术派、量化交易爱好者",
        "优点": "客观量化、不受情绪干扰",
        "缺点": "震荡市假信号多、有学习成本",
    }


# ── 5. 分批止盈法 ────────────────────────────────────────────
def batch_take_profit(cost_price: float, current_price: float) -> dict:
    """
    分批止盈法：涨10%卖1/3、涨20%卖1/3、剩余灵活处理
    """
    if cost_price <= 0:
        return {"方法": "分批止盈法", "说明": "缺少成本价"}

    gain = (current_price - cost_price) / cost_price
    batches = [
        {"涨幅": "10%", "卖出比例": "1/3", "目标价": round(cost_price * 1.10, 2), "是否触发": gain >= 0.10},
        {"涨幅": "20%", "卖出比例": "1/3", "目标价": round(cost_price * 1.20, 2), "是否触发": gain >= 0.20},
        {"涨幅": "30%+", "卖出比例": "剩余仓位灵活处理", "目标价": round(cost_price * 1.30, 2), "是否触发": gain >= 0.30},
    ]

    triggered = [b for b in batches if b["是否触发"]]

    return {
        "方法": "分批止盈法",
        "成本价": cost_price,
        "当前价": current_price,
        "当前涨幅": round(gain * 100, 2),
        "分批计划": batches,
        "已触发": [f'{b["涨幅"]}({b["卖出比例"]})' for b in triggered],
        "建议": (
            "📌 尚未达到第一批止盈点，继续持有" if not triggered
            else f"✅ 已触发 {' / '.join([b['涨幅'] for b in triggered])}，按计划分批卖出，剩余仓位灵活处理"
        ),
        "适合人群": "有经验股民、重仓某板块者、想平衡锁定利润与参与上涨",
        "优点": "降低风险、心理轻松、灵活调整",
        "缺点": "大涨时可能后悔卖早、需判断市场情绪",
    }


# ── 6. 投资者类型推荐 ─────────────────────────────────────────
def recommend_method(investor_type: str = "综合") -> dict:
    """
    根据投资者类型推荐止盈方法
    """
    mapping = {
        "投资新手": {"方法": "固定比例止盈法", "理由": "简单易懂容易执行"},
        "上班族": {"方法": "固定比例止盈法 + 基本面止盈法", "理由": "不需要频繁盯盘"},
        "技术派": {"方法": "技术止盈法 + 移动止盈法", "理由": "有客观标准不受情绪干扰"},
        "价值投资者": {"方法": "基本面止盈法", "理由": "立足长期不被短期波动干扰"},
        "重仓某一板块": {"方法": "分批止盈法", "理由": "降低风险灵活调整"},
        "追求吃鱼身": {"方法": "移动止盈法", "理由": "不预测顶部让市场告诉你"},
    }

    if investor_type in mapping:
        return {
            "投资者类型": investor_type,
            "推荐方法": mapping[investor_type]["方法"],
            "理由": mapping[investor_type]["理由"],
        }

    return {
        "投资者类型": "综合",
        "推荐方法": "技术止盈法 + 分批止盈法",
        "理由": "趋势走坏时技术止盈，上涨过程中分批锁定利润",
        "可选方法": list(mapping.keys()),
    }


# ── 7. 心理误区提示 ──────────────────────────────────────────
def psychology_reminders() -> dict:
    """止盈心理误区与正确心态"""
    return {
        "核心原则": "止盈的核心不是卖在最高点，而是锁定合理利润",
        "损失厌恶": "亏损100元的痛苦 ≈ 需要赚250元才能平衡，别让情绪左右决策",
        "常见误区": [
            {
                "误区": "想卖在最高点",
                "真相": "没人能每次都卖在最高点",
                "正确做法": "设定合理目标或用移动止盈法",
            },
            {
                "误区": "赚到钱就不想卖",
                "真相": "账面盈利不是真盈利，坐电梯比卖飞更痛苦",
                "正确做法": "保住利润比赚更多重要",
            },
            {
                "误区": "止盈后股票继续涨就觉得自己错了",
                "真相": "卖早了不代表做错了",
                "正确做法": "接受卖飞是止盈的一部分",
            },
        ],
        "心法": "会买的是徒弟，会卖的是师傅，会空仓的是祖师爷。好的止盈 = 在合理价位锁定利润 + 安心睡觉。",
    }


# ── 8. 综合止盈分析 ──────────────────────────────────────────
def full_stop_profit_analysis(quote: dict, kline_data: list,
                               cost_price: float = None, cost_pe: float = None,
                               investor_type: str = "综合") -> dict:
    """
    执行完整止盈分析，汇总五种方法
    """
    current_price = quote.get("最新价", 0)
    if cost_price is None:
        cost_price = current_price

    fixed = fixed_ratio_take_profit(current_price, cost_price)
    trailing = trailing_stop_take_profit(kline_data, cost_price)
    fundamental = fundamental_take_profit(quote, cost_pe)
    technical = technical_take_profit(kline_data)
    batch = batch_take_profit(cost_price, current_price)
    recommend = recommend_method(investor_type)
    psychology = psychology_reminders()

    # 综合判断：只要有2种以上方法触发止盈，就强化建议
    trigger_count = sum([
        len(fixed.get("已触发", [])) > 0,
        trailing.get("是否触发止盈", False),
        fundamental.get("是否高估", False),
        len(technical.get("触发信号", [])) > 0,
        len(batch.get("已触发", [])) > 0,
    ])

    if trigger_count >= 3:
        overall = "⚠️ 多重止盈信号共振，建议积极减仓/卖出，先锁定利润"
    elif trigger_count >= 2:
        overall = "📌 部分止盈信号出现，可考虑分批减仓"
    elif trigger_count >= 1:
        overall = "⏸️ 单一止盈信号，保持警惕，继续观察"
    else:
        overall = "✅ 暂未触发止盈信号，可继续持有"

    return {
        "综合建议": overall,
        "触发信号数": trigger_count,
        "推荐方法": recommend,
        "心理提示": psychology,
        "五种方法": [fixed, trailing, fundamental, technical, batch],
    }


if __name__ == "__main__":
    print("Stop-profit module ready")
