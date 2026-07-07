#!/usr/bin/env python3
"""
选股框架模块 — “老刘四步选股法”
排雷 → 估值 → 精选 → 量价验证

注意：部分硬指标（连续5年ROE、毛利率/净利率趋势、经营现金流）
      需要 F10 财务明细数据，免费 API 仅提供 PE/PB/市值，因此用
      可获得的指标 + 合理替代/标注缺失的方式实现。
"""

import numpy as np
from typing import List, Dict, Optional


# 导入技术指标计算（兼容相对/绝对导入）
def _import_technical():
    try:
        from . import technical
    except ImportError:
        import technical
    return technical


# ── 进阶策略：趋势动能系统（5/20日均线 + 周线MACD）────────────
def ma_cross_analysis(kline_data: list) -> dict:
    """
    5日均线金叉20日均线关注 + 5/10日线支撑
    """
    n = len(kline_data)
    if n < 20:
        return {"信号": "数据不足", "金叉": False, "支撑有效": False}

    closes = np.array([d["收盘"] for d in kline_data], dtype=float)
    ma5 = np.array([np.mean(closes[max(0, i - 4): i + 1]) for i in range(n)])
    ma10 = np.array([np.mean(closes[max(0, i - 9): i + 1]) for i in range(n)])
    ma20 = np.array([np.mean(closes[max(0, i - 19): i + 1]) for i in range(n)])

    # 金叉：昨日MA5<=MA20，今日MA5>MA20
    golden_cross = False
    for i in range(max(1, n - 5), n):
        if ma5[i] > ma20[i] and ma5[i - 1] <= ma20[i - 1]:
            golden_cross = True
            break

    # 死叉
    dead_cross = False
    for i in range(max(1, n - 5), n):
        if ma5[i] < ma20[i] and ma5[i - 1] >= ma20[i - 1]:
            dead_cross = True
            break

    # 当前价格是否紧贴5/10日线（不破）
    latest_close = closes[-1]
    support_5 = bool(latest_close >= ma5[-1] * 0.99)  # 允许1%以内虚破
    support_10 = bool(latest_close >= ma10[-1] * 0.99)
    support_valid = bool(support_5 and support_10)

    signal = "观望"
    if golden_cross and not dead_cross:
        signal = "🌟 5日线上穿20日线，关注"
    elif dead_cross and not golden_cross:
        signal = "⚠️ 5日线下穿20日线，减仓/观望"
    elif support_valid:
        signal = "✅ 5/10日线支撑有效"
    else:
        signal = "📌 5/10日线支撑失效，注意风险"

    return {
        "信号": signal,
        "金叉": golden_cross,
        "死叉": dead_cross,
        "支撑有效": support_valid,
        "当前MA5": round(float(ma5[-1]), 2),
        "当前MA10": round(float(ma10[-1]), 2),
        "当前MA20": round(float(ma20[-1]), 2),
    }


def weekly_macd_analysis(weekly_kline: list) -> dict:
    """
    周线MACD零上金叉/死叉系统
    返回：是否零上金叉、死叉、当前红柱第几根、建议
    """
    if not weekly_kline or len(weekly_kline) < 26:
        return {"状态": "数据不足", "零上金叉": False, "死叉": False, "红柱第几根": 0}

    tech = _import_technical()
    closes = np.array([d["收盘"] for d in weekly_kline], dtype=float)
    macd = tech.calc_macd(closes.tolist())
    dif = np.array(macd["DIF"])
    dea = np.array(macd["DEA"])
    bar = np.array(macd["MACD"])

    n = len(dif)
    # 近1年是否有零上金叉（DIF>0, DEA>0，DIF上穿DEA）
    zero_above_golden = False
    zero_above_dead = False
    golden_idx = -1
    dead_idx = -1

    for i in range(max(1, n - 52), n):
        if dif[i] > 0 and dea[i] > 0 and dif[i] > dea[i] and dif[i - 1] <= dea[i - 1]:
            zero_above_golden = True
            golden_idx = i
        if dif[i] < dea[i] and dif[i - 1] >= dea[i - 1]:
            zero_above_dead = True
            dead_idx = i

    # 计算当前红柱第几根（金叉后的连续红柱数量）
    red_bar_count = 0
    if zero_above_golden and golden_idx > 0:
        for i in range(golden_idx, n):
            if bar[i] > 0:
                red_bar_count += 1
            else:
                break

    # 买入/卖出建议
    if zero_above_dead and (dead_idx > golden_idx or not zero_above_golden):
        advice = "⚠️ 周线MACD死叉，开始减仓"
    elif zero_above_golden and red_bar_count == 2:
        advice = "🌟 周线MACD零上金叉后第2根红柱，胜率较高买点"
    elif zero_above_golden and red_bar_count > 0:
        advice = f"✅ 周线MACD零上金叉后第{red_bar_count}根红柱，持盈"
    elif zero_above_golden and red_bar_count == 0:
        advice = "📌 周线MACD零上金叉，关注"
    else:
        advice = "⏸️ 周线MACD未形成零上金叉，观望"

    return {
        "状态": advice,
        "零上金叉": zero_above_golden,
        "死叉": zero_above_dead,
        "金叉位置": golden_idx,
        "死叉位置": dead_idx,
        "红柱第几根": red_bar_count,
        "当前DIF": round(float(dif[-1]), 3) if not np.isnan(dif[-1]) else None,
        "当前DEA": round(float(dea[-1]), 3) if not np.isnan(dea[-1]) else None,
    }


# ── 进阶策略：真实需求/小市值/财报验证 ────────────────────────
def fundamental_validation_signal(quote: dict, kline_data: list) -> dict:
    """
    从图片中提取的第二条主线：
    - 小市值弹性（盘子小、主业专一、营收基数低）
    - 真实需求落地（需人工F10数据）
    - 财报验证（营收提速、毛利率抬升、订单增多等）
    """
    total_mv = quote.get("总市值", 0) or 0
    circulate_mv = quote.get("流通市值", 0) or 0
    # 如果流通市值缺失，用总市值估算
    effective_circ_mv = circulate_mv if circulate_mv > 0 else total_mv
    pe = quote.get("市盈率(动)", 0)

    total_mv_yi = total_mv
    circ_mv_yi = effective_circ_mv

    # 小市值评分：越小越弹性大，但太小(<30亿)流动性风险
    small_cap_score = 0
    if effective_circ_mv <= 0:
        small_cap_score = 50  # 数据缺失，给中性分
        cap_label = "市值数据缺失"
    elif 30 <= circ_mv_yi <= 100:
        small_cap_score = 100
        cap_label = "小盘高弹性（30~100亿）"
    elif 100 < circ_mv_yi <= 300:
        small_cap_score = 70
        cap_label = "中盘"
    elif 300 < circ_mv_yi <= 1000:
        small_cap_score = 40
        cap_label = "大盘，弹性有限"
    elif circ_mv_yi > 1000:
        small_cap_score = 20
        cap_label = "超大象，弹性很小"
    else:
        small_cap_score = 50
        cap_label = "小盘股（<30亿，注意流动性）"

    # 估值弹性（低PE + 小市值 = 估值修复空间大）
    valuation_flex_score = 0
    if pe > 0 and pe < 15 and circ_mv_yi < 300:
        valuation_flex_score = 100
    elif pe > 0 and pe < 25 and circ_mv_yi < 500:
        valuation_flex_score = 70
    elif pe > 0 and pe < 40:
        valuation_flex_score = 50
    else:
        valuation_flex_score = 30

    checks = {
        "小市值弹性": (
            f"流通市值 {circ_mv_yi:.1f}亿（总市值 {total_mv_yi:.1f}亿）→ {cap_label}"
        ),
        "真实需求落地": "📝 需人工/F10验证：下游订单、工厂排产、货品出货、现货涨价、财报提及新业务",
        "财报验证": "📝 需F10数据：营收增速、毛利率抬升、在手订单、交货周期、产能利用率、产品涨价、资本开支",
        "认知差机会": "📝 关注被市场贴错标签、业务实质与市值错配的公司",
    }

    return {
        "小市值评分": small_cap_score,
        "估值弹性评分": valuation_flex_score,
        "综合得分": round((small_cap_score + valuation_flex_score) / 2, 1),
        "检查项": checks,
    }


# ── 分阶段仓位建议 ────────────────────────────────────────────
def position_sizing_advice(selection_result: dict, ma_signal: dict, weekly_macd: dict) -> dict:
    """
    根据逻辑完善程度给出分阶段仓位建议：
    - 逻辑雏形 → 只观望
    - 需求初现 → 小仓位试错
    - 财报落地 → 稳步加仓
    - 逻辑证伪 → 直接止损
    """
    total_score = selection_result.get("选股总分", 0)
    grade = selection_result.get("选股评级", "")

    ma_support = ma_signal.get("支撑有效", False)
    weekly_bull = weekly_macd.get("零上金叉", False)
    weekly_dead = weekly_macd.get("死叉", False)
    red_bar_2 = weekly_macd.get("红柱第几根", 0) == 2

    # 综合判断
    if weekly_dead or total_score < 50:
        stage = "观望/止损"
        position = "0%"
        reason = "周线MACD死叉或选股总分低于50，不符合入场条件"
    elif total_score >= 80 and weekly_bull and ma_support:
        stage = "财报落地/稳步加仓"
        position = "50%~70%"
        reason = "四步框架优秀 + 周线零上金叉 + 日线支撑有效"
    elif total_score >= 65 and (weekly_bull or ma_support):
        stage = "需求初现/小仓位试错"
        position = "20%~30%"
        reason = "多数维度符合，趋势动能初步确认"
    elif red_bar_2 and total_score >= 60:
        stage = "高胜率买点/试错"
        position = "20%~30%"
        reason = "周线MACD零上金叉后第2根红柱，历史胜率较高"
    else:
        stage = "逻辑雏形/只观望"
        position = "0~10%"
        reason = "部分逻辑成立，但尚未到重仓时机，等待确认"

    return {
        "阶段": stage,
        "建议仓位": position,
        "理由": reason,
    }

def step1_quality_screen(quote: dict, kline_data: list, financial_data: dict = None) -> dict:
    """
    三大硬指标排雷：
    1. ROE ≥ 15%（连续5年理想，免费API仅提供当前PE/PB，用 ROE≈PB/PE 估算）
    2. 毛利率/净利率稳定或提升（需F10数据，此处标注待补充）
    3. 经营现金流覆盖利润（需F10数据，此处标注待补充）
    """
    pe = quote.get("市盈率(动)", 0)
    pb = quote.get("市净率", 0)

    # 通过 PB/PE 近似ROE（ROE = 净利润/净资产 = (P/E)/(P/B) = B/E = PB/PE）
    implied_roe = None
    if pe > 0:
        implied_roe = (pb / pe) * 100 if pb else (1 / pe) * 100

    roe_pass = False
    if implied_roe is not None and implied_roe >= 15:
        roe_pass = True

    # 价格趋势稳定性（替代毛利率稳定性的简易指标）
    n = len(kline_data)
    price_stable = False
    if n >= 60:
        closes = [d["收盘"] for d in kline_data]
        ret_60 = (closes[-1] - closes[-60]) / closes[-60] * 100
        # 60日跌幅<20%视为“相对稳定”的保守标准
        price_stable = ret_60 > -20

    score = 0
    checks = {}

    if roe_pass:
        score += 40
        checks["ROE排雷"] = f"✅ 隐含ROE约 {implied_roe:.1f}% ≥ 15%（注：由PE/PB推导，建议结合F10年报复核）"
    else:
        checks["ROE排雷"] = (f"⚠️ 隐含ROE约 {implied_roe:.1f}% 未达15%门槛，或需用F10数据精确判断" 
                           if implied_roe is not None else "⚠️ 无法获取ROE数据，需补充F10")

    # 毛利率/净利率（缺失标注）
    checks["毛利率/净利率趋势"] = (
        "📝 需要F10历史财务数据：建议观察最近3年毛利率/净利率是否稳定或提升，"
        "避免毛利率连续下滑的公司。"
    )

    # 现金流（缺失标注）
    checks["经营现金流"] = (
        "📝 需要F10现金流量表：经营现金流净额应持续为正，且覆盖净利润。"
        "警惕利润增长但现金流长期为负的公司。"
    )

    # 额外排雷：亏损股、ST股、PB异常
    red_flags = []
    if pe <= 0:
        red_flags.append("⚠️ 动态PE为负或亏损")
    if pb > 20:
        red_flags.append("⚠️ PB过高（>20）")
    if quote.get("涨跌幅", 0) > 20:
        red_flags.append("⚠️ 近期涨幅过大，注意追高风险")
    if not red_flags:
        red_flags.append("✅ 无明显异常信号")

    # 如果ROE通过且价格稳定，再加20分
    if roe_pass and price_stable:
        score += 30
    elif price_stable:
        score += 20
    elif roe_pass:
        score += 20

    return {
        "步骤": "一、硬指标排雷",
        "得分": min(100, score),
        "是否通过": roe_pass and price_stable,
        "隐含ROE(%)": round(implied_roe, 2) if implied_roe is not None else None,
        "价格稳定性": price_stable,
        "排雷检查": checks,
        "风险信号": red_flags,
        "建议": "通过" if (roe_pass and price_stable) else "需进一步用F10数据复核" if roe_pass else "暂不符合初筛条件，建议谨慎",
    }


# ── 第二步：PEG估值参考 ───────────────────────────────────────
def step2_peg_valuation(quote: dict, kline_data: list) -> dict:
    """
    PEG = PE / 盈利增速（%）
    免费API无法拿到盈利增速，用近60日/120日价格涨幅作为景气度代理。
    """
    pe = quote.get("市盈率(动)", 0)
    n = len(kline_data)

    # 用价格涨幅作为增速代理（保守处理：盈利增速通常比价格增速更稳定）
    growth_proxy = 0
    if n >= 120:
        closes = [d["收盘"] for d in kline_data]
        growth_120 = (closes[-1] - closes[-120]) / closes[-120] * 100
        growth_60 = (closes[-1] - closes[-60]) / closes[-60] * 100
        # 取较小值，避免高估增速
        growth_proxy = min(growth_120, growth_60)
    elif n >= 60:
        closes = [d["收盘"] for d in kline_data]
        growth_proxy = (closes[-1] - closes[-60]) / closes[-60] * 100
    else:
        growth_proxy = 0

    # 用年化增速估算：假设120日对应半年，乘以2；保守取60日年化
    annual_growth = growth_proxy * 2 if n >= 120 else growth_proxy * 4
    annual_growth = max(annual_growth, -50)  # 下限

    peg = None
    if pe > 0 and annual_growth > 0:
        peg = pe / annual_growth

    evaluation = "N/A"
    if peg is not None:
        if peg < 1:
            evaluation = "✅ PEG < 1，相对便宜"
        elif peg < 2:
            evaluation = "📌 PEG 1~2，合理区间"
        else:
            evaluation = "⚠️ PEG > 2，估值偏贵，需确认高增速能否持续"
    elif pe <= 0:
        evaluation = "⚠️ 亏损股，PEG无参考意义"
    else:
        evaluation = "📌 增速为负或接近0，PEG失效，需结合PB判断"

    score = 0
    if peg is not None:
        if peg < 1:
            score = 100
        elif peg < 1.5:
            score = 80
        elif peg < 2:
            score = 60
        elif peg < 3:
            score = 40
        else:
            score = 20
    elif pe > 0 and pe < 15:
        score = 70
    elif pe <= 0:
        score = 30

    return {
        "步骤": "二、PEG估值参考",
        "得分": score,
        "PE": pe,
        "代理增速(%)": round(annual_growth, 2),
        "PEG": round(peg, 2) if peg is not None else None,
        "估值评价": evaluation,
        "说明": "注：增速由近60/120日价格涨幅代理，精确PEG需用净利润增速",
    }


# ── 第三步：精挑细选（边际改善 + 筹码 + 相对强度） ──────────
def step3_pick_best(quote: dict, kline_data: list, sector_context: dict = None) -> dict:
    """
    精挑细选：
    - 业绩预期差/边际改善：用近期价格强度 + 量价背离信号
    - 股东人数/筹码：无法获取，标注提示
    - 相对强度：同板块比较
    """
    n = len(kline_data)
    if n < 20:
        return {"步骤": "三、精挑细选", "得分": 0, "建议": "数据不足"}

    closes = [d["收盘"] for d in kline_data]
    volumes = [d["成交量"] for d in kline_data]

    # 边际改善：短中期趋势是否转强
    ret_20 = (closes[-1] - closes[-20]) / closes[-20] * 100 if n >= 20 else 0
    ret_60 = (closes[-1] - closes[-60]) / closes[-60] * 100 if n >= 60 else 0
    ma20 = np.mean(closes[-20:]) if n >= 20 else closes[-1]
    ma60 = np.mean(closes[-60:]) if n >= 60 else closes[-1]
    price_above_ma20 = closes[-1] > ma20
    price_above_ma60 = closes[-1] > ma60
    ma20_turning_up = ma20 > np.mean(closes[-25:-5]) if n >= 25 else False

    # 量价是否配合改善
    avg_vol_20 = np.mean(volumes[-20:]) if n >= 20 else 0
    avg_vol_60 = np.mean(volumes[-60:]) if n >= 60 else 0
    volume_improving = avg_vol_20 > avg_vol_60 * 0.9  # 近20日均量未明显萎缩

    score = 0
    checks = {}

    if ret_20 > 0:
        score += 20
        checks["20日涨幅"] = f"✅ 20日 +{ret_20:.2f}%，短期偏强"
    else:
        checks["20日涨幅"] = f"⚠️ 20日 {ret_20:.2f}%，短期偏弱"

    if price_above_ma20 and price_above_ma60:
        score += 25
        checks["均线"] = "✅ 站上MA20和MA60"
    elif price_above_ma20:
        score += 10
        checks["均线"] = "📌 站上MA20但未上MA60"
    else:
        checks["均线"] = "⚠️ 未站上MA20"

    if ma20_turning_up:
        score += 15
        checks["MA20拐点"] = "✅ MA20拐头向上"
    else:
        checks["MA20拐点"] = "⚠️ MA20走平或向下"

    if volume_improving:
        score += 15
        checks["量能维持"] = "✅ 量能未明显萎缩"
    else:
        checks["量能维持"] = "⚠️ 量能有所萎缩"

    # 相对强度
    relative_strength = 0
    if sector_context and isinstance(sector_context, dict):
        relative_strength = sector_context.get("相对强度", 0)
        if relative_strength > 1:
            score += 25
            checks["相对强度"] = f"✅ 强于板块 {relative_strength:.2f}%"
        elif relative_strength < -1:
            checks["相对强度"] = f"⚠️ 弱于板块 {relative_strength:.2f}%"
        else:
            checks["相对强度"] = "📌 与板块同步"

    checks["筹码集中度"] = (
        "📝 股东人数/筹码集中度需F10股东户数数据，"
        "原则：低位筹码集中=有戏；高位散户涌入=再等等。"
    )
    checks["业绩预期差"] = (
        "📝 业绩预期差需研报/机构一致预期数据，"
        "原则：关注环比改善、超预期的个股。"
    )

    return {
        "步骤": "三、精挑细选",
        "得分": min(100, score),
        "20日涨幅": round(ret_20, 2),
        "60日涨幅": round(ret_60, 2),
        "站上MA20": price_above_ma20,
        "站上MA60": price_above_ma60,
        "MA20拐头": ma20_turning_up,
        "相对强度": round(relative_strength, 2),
        "检查项": checks,
    }


# ── 第四步：成交量验证资金态度 ─────────────────────────────────
def step4_volume_validation(kline_data: list) -> dict:
    """
    量价验证：
    - 上涨温和放量 + 回调缩量 = 量价健康
    - 放量滞涨 = 抛压重
    - 缩量硬拉新高 = 小心
    """
    n = len(kline_data)
    if n < 20:
        return {"步骤": "四、成交量验证", "得分": 0, "建议": "数据不足"}

    closes = np.array([d["收盘"] for d in kline_data], dtype=float)
    volumes = np.array([d["成交量"] for d in kline_data], dtype=float)
    highs = np.array([d["最高"] for d in kline_data], dtype=float)

    # 近20日数据
    c20 = closes[-20:]
    v20 = volumes[-20:]
    h20 = highs[-20:]

    # 上涨日与下跌日分开
    up_days = []
    down_days = []
    for i in range(1, len(c20)):
        if c20[i] > c20[i - 1]:
            up_days.append(v20[i])
        else:
            down_days.append(v20[i])

    avg_vol_up = np.mean(up_days) if up_days else 0
    avg_vol_down = np.mean(down_days) if down_days else 0
    avg_vol_all = np.mean(v20)

    # 创新高判断
    new_high = c20[-1] == np.max(c20)
    volume_vs_avg = v20[-1] / avg_vol_all if avg_vol_all > 0 else 0
    volume_vs_up_avg = v20[-1] / avg_vol_up if avg_vol_up > 0 else 0

    score = 50
    signals = []

    if avg_vol_up > avg_vol_down * 1.2:
        score += 25
        signals.append("✅ 上涨放量、回调缩量，量价健康")
    elif avg_vol_up > avg_vol_down:
        score += 10
        signals.append("📌 上涨略放量，量价正常")
    else:
        score -= 15
        signals.append("⚠️ 上涨缩量或下跌放量，量价背离")

    if new_high and volume_vs_avg < 0.8:
        score -= 25
        signals.append("⚠️ 缩量创新高，可能是假突破")
    elif new_high and volume_vs_avg > 1.5:
        score += 15
        signals.append("✅ 放量创新高，资金认可")

    # 放量滞涨检测
    recent_change = (c20[-1] - c20[-2]) / c20[-2] * 100 if len(c20) >= 2 else 0
    if volume_vs_avg > 1.8 and recent_change < 1:
        score -= 20
        signals.append("⚠️ 放量滞涨，抛压较重")

    score = max(0, min(100, score))

    return {
        "步骤": "四、成交量验证",
        "得分": score,
        "上涨日均量": round(avg_vol_up, 0),
        "下跌日均量": round(avg_vol_down, 0),
        "最新量比": round(volume_vs_avg, 2),
        "是否创新高": bool(new_high),
        "量价信号": signals,
    }


# ── 综合四步评分 ───────────────────────────────────────────────
def full_selection_analysis(quote: dict, kline_data: list, weekly_kline: list = None, sector_context: dict = None) -> dict:
    """执行完整四步选股分析 + 进阶信号，并汇总"""
    s1 = step1_quality_screen(quote, kline_data)
    s2 = step2_peg_valuation(quote, kline_data)
    s3 = step3_pick_best(quote, kline_data, sector_context)
    s4 = step4_volume_validation(kline_data)

    weights = [0.25, 0.25, 0.25, 0.25]
    total_score = (
        s1["得分"] * weights[0] +
        s2["得分"] * weights[1] +
        s3["得分"] * weights[2] +
        s4["得分"] * weights[3]
    )

    # 短板逻辑：任一维度低于40分，总评降级
    min_score = min(s1["得分"], s2["得分"], s3["得分"], s4["得分"])
    if min_score < 40:
        total_score = min(total_score, 60)

    # 进阶信号
    ma_signal = ma_cross_analysis(kline_data)
    weekly_macd = weekly_macd_analysis(weekly_kline) if weekly_kline else {"状态": "未提供周线数据"}
    fund_val = fundamental_validation_signal(quote, kline_data)
    position = position_sizing_advice({"选股总分": total_score, "选股评级": ""}, ma_signal, weekly_macd)

    # 根据进阶信号微调评级
    if weekly_macd.get("零上金叉") and ma_signal.get("金叉") and total_score >= 70:
        grade = "A+ 高胜率买点"
        advice = "🌟 四步框架优秀 + 日线金叉 + 周线MACD零上金叉，高胜率共振买点。"
    elif total_score >= 80:
        grade = "A 重点跟踪"
        advice = "🌟 四步框架整体优秀，建议加入重点观察池，等待合适买点入场。"
    elif total_score >= 65:
        grade = "B 符合条件"
        advice = "✅ 多数维度符合选股框架，可结合技术分析找买点。"
    elif total_score >= 50:
        grade = "C 一般"
        advice = "📌 部分维度存疑，建议观望或等待更多确认信号。"
    else:
        grade = "D 暂不考虑"
        advice = "⚠️ 不符合当前选股框架，建议放弃或等待基本面改善。"

    return {
        "选股总分": round(total_score, 1),
        "选股评级": grade,
        "综合建议": advice,
        "核心逻辑": "排雷 → 估值 → 精选 → 量价",
        "四步结果": [s1, s2, s3, s4],
        "进阶信号": {
            "日线MA系统": ma_signal,
            "周线MACD系统": weekly_macd,
            "小市值/财报验证": fund_val,
        },
        "仓位建议": position,
    }


# ── 批量筛选（输入候选股列表） ─────────────────────────────────
def batch_screen(candidates: list, kline_count: int = 120) -> list:
    """
    对候选股列表执行批量四步筛选，返回按综合得分排序的结果
    candidates: [{"code": ..., "name": ...}, ...]
    """
    results = []
    for c in candidates:
        # 这里需要外部传入 kline_data，避免本模块重复拉取
        pass
    return results
