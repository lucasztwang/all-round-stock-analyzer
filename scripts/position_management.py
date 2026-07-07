#!/usr/bin/env python3
"""
仓位管理模块 — “三层仓位法则”
观察仓 → 确认仓 → 进攻仓
核心：不轻易满仓，留备用现金流，大跌有补仓余地
"""

import numpy as np
from typing import Dict, List, Optional


def _detect_trend_status(kline_data: list) -> dict:
    """判断趋势状态：启动/回踩/震荡/下跌"""
    if not kline_data or len(kline_data) < 20:
        return {"状态": "数据不足", "强度": 0}

    closes = np.array([d["收盘"] for d in kline_data], dtype=float)
    volumes = np.array([d["成交量"] for d in kline_data], dtype=float)
    n = len(closes)

    ma5 = np.mean(closes[-5:]) if n >= 5 else closes[-1]
    ma10 = np.mean(closes[-10:]) if n >= 10 else closes[-1]
    ma20 = np.mean(closes[-20:]) if n >= 20 else closes[-1]
    ma60 = np.mean(closes[-60:]) if n >= 60 else closes[-1]

    # 价格在均线上的数量
    above_mas = sum([
        closes[-1] > ma5,
        closes[-1] > ma10,
        closes[-1] > ma20,
        closes[-1] > ma60 if n >= 60 else False,
    ])

    # 均线排列
    ma_bull = ma5 > ma10 > ma20
    ma_bear = ma5 < ma10 < ma20

    # 近期涨跌幅
    ret_5 = (closes[-1] - closes[-6]) / closes[-6] * 100 if n >= 6 else 0
    ret_20 = (closes[-1] - closes[-21]) / closes[-21] * 100 if n >= 21 else 0

    # 量能
    avg_vol_5 = np.mean(volumes[-5:])
    avg_vol_20 = np.mean(volumes[-20:])
    volume_expanding = avg_vol_5 > avg_vol_20 * 1.2

    status = "震荡"
    strength = 50

    if ma_bull and ret_20 > 10 and volume_expanding:
        status = "趋势启动"
        strength = 85
    elif ma_bull and ret_5 > 0:
        status = "上升趋势"
        strength = 70
    elif above_mas >= 2 and ret_5 > -3:
        status = "回踩企稳"
        strength = 60
    elif ma_bear:
        status = "下跌趋势"
        strength = 20
    elif ret_20 < -15:
        status = "超跌"
        strength = 30

    return {
        "状态": status,
        "强度": strength,
        "均线多头排列": bool(ma_bull),
        "均线空头排列": bool(ma_bear),
        "5日涨幅": round(ret_5, 2),
        "20日涨幅": round(ret_20, 2),
        "放量": bool(volume_expanding),
    }


def _evaluate_support_level(kline_data: list, technical_data: dict = None) -> dict:
    """评估当前价格与支撑位关系"""
    if not kline_data:
        return {"状态": "数据不足"}

    current = kline_data[-1]["收盘"]
    supports = []
    if technical_data and "支撑压力" in technical_data:
        supports = technical_data["支撑压力"].get("支撑位", [])

    if not supports:
        # 用近期低点估算
        lows = [d["最低"] for d in kline_data[-20:]]
        recent_low = min(lows) if lows else current * 0.95
        supports = [{"点位": recent_low, "类型": "20日低点"}]

    nearest_support = supports[0]
    distance_to_support = (current - nearest_support["点位"]) / current * 100

    near_support = distance_to_support < 3  # 距离支撑位3%以内
    above_support = current > nearest_support["点位"]

    return {
        "最近支撑位": round(nearest_support["点位"], 2),
        "支撑类型": nearest_support.get("类型", ""),
        "距支撑距离": round(distance_to_support, 2),
        "贴近支撑": bool(near_support and above_support),
        "跌破支撑": bool(not above_support),
    }


def _evaluate_fundamental_signal(selection_data: dict) -> dict:
    """从选股框架中提取基本面确认信号"""
    if not selection_data:
        return {"得分": 0, "状态": "无数据"}

    score = selection_data.get("选股总分", 0)
    grade = selection_data.get("选股评级", "")

    if score >= 80:
        return {"得分": score, "状态": "基本面优秀", "确认": True}
    elif score >= 65:
        return {"得分": score, "状态": "基本面良好", "确认": True}
    elif score >= 50:
        return {"得分": score, "状态": "基本面一般", "确认": False}
    else:
        return {"得分": score, "状态": "基本面较弱", "确认": False}


def three_layer_position_plan(quote: dict, kline_data: list,
                               technical_data: dict = None,
                               selection_data: dict = None) -> dict:
    """
    三层仓位法则：
    - 观察仓：2%-5%（看好但价位偏高，小资金试水）
    - 确认仓：30%-50%（回踩支撑守住 或 基本面落地）
    - 进攻仓：30%-50%（趋势正式启动，放量+形态走顺）

    返回当前建议的仓位分配和进入下一层的条件。
    """
    trend = _detect_trend_status(kline_data)
    support = _evaluate_support_level(kline_data, technical_data)
    fundamental = _evaluate_fundamental_signal(selection_data)

    current_price = quote.get("最新价", 0)

    # 基础判断逻辑
    observation = {"比例": "0%", "条件": "尚未识别到合适入场信号", "建议": "观望"}
    confirmation = {"比例": "0%", "条件": "等待确认信号", "建议": "暂不建仓"}
    offensive = {"比例": "0%", "条件": "等待趋势启动", "建议": "暂不建仓"}

    # 场景1：趋势正式启动 + 放量 → 进攻仓为主
    if trend["状态"] in ["趋势启动", "上升趋势"] and trend["放量"] and fundamental["确认"]:
        offensive = {"比例": "40%-50%", "条件": "趋势启动+放量+基本面确认", "建议": "重仓出击吃主升"}
        confirmation = {"比例": "20%-30%", "条件": "回踩关键支撑守住", "建议": "逢低加仓"}
        observation = {"比例": "2%-5%", "条件": "价位偏高或想试盘", "建议": "已有底仓可忽略"}
        total = "60%-80%"
        stage = "进攻阶段"
        action = "趋势明确，建议进攻仓+确认仓合计 60%-80%，保留 20% 备用现金"

    # 场景2：回踩支撑位企稳 + 基本面尚可 → 确认仓
    elif support["贴近支撑"] and not support["跌破支撑"] and fundamental["得分"] >= 50:
        observation = {"比例": "2%-5%", "条件": "已在支撑位附近", "建议": "可小仓位试水"}
        confirmation = {"比例": "30%-40%", "条件": "回踩支撑守住+基本面落地", "建议": "加仓至确认仓"}
        offensive = {"比例": "0%", "条件": "等待趋势放量启动", "建议": "暂不进攻"}
        total = "35%-50%"
        stage = "确认阶段"
        action = "回踩企稳，建议观察仓+确认仓合计 35%-50%，等待趋势确认再加进攻仓"

    # 场景3：价位偏高/趋势不明 → 只给观察仓
    elif trend["状态"] in ["震荡", "数据不足"] or fundamental["得分"] < 50:
        observation = {"比例": "2%-5%", "条件": "看好但价位偏高或信号不明", "建议": "小资金试水，治踏空焦虑"}
        confirmation = {"比例": "0%", "条件": "等待回踩支撑或基本面落地", "建议": "暂不建仓"}
        offensive = {"比例": "0%", "条件": "等待趋势正式启动", "建议": "暂不进攻"}
        total = "2%-5%"
        stage = "观察阶段"
        action = "信号不足或价格偏高，建议只建 2%-5% 观察仓，避免重仓被套"

    # 场景4：下跌趋势 → 空仓/极轻观察仓
    elif trend["状态"] in ["下跌趋势", "超跌"]:
        observation = {"比例": "0%-2%", "条件": "下跌趋势中仅可极轻仓关注", "建议": "谨慎"}
        confirmation = {"比例": "0%", "条件": "等待止跌企稳", "建议": "不加仓"}
        offensive = {"比例": "0%", "条件": "等待趋势反转", "建议": "不进攻"}
        total = "0%-2%"
        stage = "空仓/观察阶段"
        action = "下跌趋势，建议空仓或极轻观察仓，不轻易抄底"

    # 默认场景
    else:
        observation = {"比例": "2%-5%", "条件": "看好但信号未完全确认", "建议": "小仓位试水"}
        confirmation = {"比例": "0%", "条件": "等待回踩支撑或基本面落地", "建议": "观望"}
        offensive = {"比例": "0%", "条件": "等待趋势启动", "建议": "观望"}
        total = "2%-5%"
        stage = "观察阶段"
        action = "建议先建 2%-5% 观察仓，等待更明确信号再加确认仓"

    return {
        "法则名称": "三层仓位管理",
        "核心理念": "不轻易满仓，留备用现金流，大跌有补仓余地。稳住仓位=稳住账户大半收益。",
        "当前阶段": stage,
        "当前价格": current_price,
        "趋势状态": trend,
        "支撑状态": support,
        "基本面评分": fundamental,
        "仓位分配": {
            "观察仓 (2%-5%)": observation,
            "确认仓 (30%-50%)": confirmation,
            "进攻仓 (30%-50%)": offensive,
        },
        "建议总仓位": total,
        "操作建议": action,
        "升级条件": {
            "观察仓→确认仓": "股价回踩关键支撑并守住，或基本面落地（财报/订单/政策兑现）",
            "确认仓→进攻仓": "趋势正式启动，放量上涨，形态走顺",
        },
        "风险提醒": "散户亏钱根源大多是乱重仓、一次性梭哈。三层仓位法用于控制回撤、保留弹药。",
    }


# ── 与选股/止盈框架联动 ───────────────────────────────────────
def integrated_position_advice(selection_data: dict, stop_profit_data: dict = None) -> dict:
    """
    综合选股评分和止盈信号，给出最终仓位建议
    """
    if not selection_data:
        return {"建议": "无选股数据，建议空仓观望"}

    score = selection_data.get("选股总分", 0)
    grade = selection_data.get("选股评级", "")

    # 止盈信号数量
    sp_count = 0
    if stop_profit_data:
        sp_count = stop_profit_data.get("触发信号数", 0)

    base_position = "0%"
    if score >= 80:
        base_position = "60%-80%"
    elif score >= 65:
        base_position = "40%-60%"
    elif score >= 50:
        base_position = "20%-40%"
    else:
        base_position = "0%-10%"

    # 止盈信号多 → 减仓
    if sp_count >= 3:
        action = "⚠️ 选股虽好但止盈信号密集，建议先减仓至基础仓位的一半以下，锁定利润"
    elif sp_count >= 2:
        action = "📌 部分止盈信号出现，保持现有仓位或小幅减仓"
    else:
        action = f"✅ 按三层仓位法分批建仓，目标总仓位 {base_position}"

    return {
        "基于选股评分的基础仓位": base_position,
        "止盈信号数": sp_count,
        "综合操作建议": action,
        "原则": "选股决定上限，仓位决定生死；不符合条件时空仓也是操作。",
    }


if __name__ == "__main__":
    print("Position management module ready")
