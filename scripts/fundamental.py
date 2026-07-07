#!/usr/bin/env python3
"""
基本盘分析模块
估值分析 / 盈利能力 / 成长性 / 财务健康 / 同行对比
"""

import numpy as np
from typing import Optional

# ── 估值分析 ──────────────────────────────────────────────────
def analyze_valuation(quote: dict, kline_data: list = None) -> dict:
    """
    估值水位分析
    - PE/PB 当前值与合理区间判断
    - 基于历史K线估算PE分位（需外部数据补充）
    """
    pe = quote.get("市盈率(动)", 0)
    pb = quote.get("市净率", 0)
    total_mv = quote.get("总市值", 0)
    price = quote.get("最新价", 0)

    analysis = {
        "市盈率(PE)": pe,
        "市净率(PB)": pb,
        "总市值(亿)": round(total_mv, 2) if total_mv else 0,
        "PE评价": _pe_evaluation(pe),
        "PB评价": _pb_evaluation(pb),
    }

    # 从K线估算简单估值区间
    if kline_data and len(kline_data) > 0:
        closes = [d["收盘"] for d in kline_data]
        if pe > 0 and len(closes) >= 60:
            # 估算历史PE范围（基于价格波动比例）
            high_60d = max(d["最高"] for d in kline_data[-60:])
            low_60d = min(d["最低"] for d in kline_data[-60:])
            price_ratio_high = high_60d / price if price > 0 else 1
            price_ratio_low = low_60d / price if price > 0 else 1
            analysis["60日高对应PE"] = round(pe * price_ratio_high, 2)
            analysis["60日低对应PE"] = round(pe * price_ratio_low, 2)

    return analysis

def _pe_evaluation(pe: float) -> str:
    if pe <= 0:
        return "亏损，PE无参考意义"
    if pe < 15:
        return "低估（PE < 15）"
    if pe < 25:
        return "合理偏低（15 ≤ PE < 25）"
    if pe < 40:
        return "合理（25 ≤ PE < 40）"
    if pe < 60:
        return "偏高（40 ≤ PE < 60）"
    return "高估（PE ≥ 60）"

def _pb_evaluation(pb: float) -> str:
    if pb <= 0:
        return "PB无参考意义"
    if pb < 1:
        return "破净（PB < 1）"
    if pb < 2:
        return "合理偏低（1 ≤ PB < 2）"
    if pb < 4:
        return "合理（2 ≤ PB < 4）"
    if pb < 8:
        return "偏高（4 ≤ PB < 8）"
    return "高估（PB ≥ 8）"

# ── 盈利能力分析 ──────────────────────────────────────────────
def analyze_profitability(quote: dict, financial: dict = None) -> dict:
    """
    盈利能力评估
    ROE、毛利率、净利率等（需财务数据支持）
    """
    result = {}

    # 从市盈率倒推ROE（PE 和 ROE 大致关系）
    pe = quote.get("市盈率(动)", 0)
    pb = quote.get("市净率", 0)

    if pe > 0:
        implied_roe = round(100 / pe, 2)  # 隐含收益率
        result["隐含收益率(%)"] = implied_roe
        if implied_roe > 8:
            result["隐含收益评价"] = "优秀（> 8%）"
        elif implied_roe > 5:
            result["隐含收益评价"] = "良好（5% - 8%）"
        elif implied_roe > 3:
            result["隐含收益评价"] = "一般（3% - 5%）"
        else:
            result["隐含收益评价"] = "偏低（< 3%）"

    if financial:
        result.update(financial)

    return result

# ── 成长性分析 ────────────────────────────────────────────────
def analyze_growth(quote: dict, kline_data: list = None) -> dict:
    """
    成长性评估（基于价格趋势 + 可获取的数据）
    """
    result = {}
    price = quote.get("最新价", 0)
    change_pct = quote.get("涨跌幅", 0)

    if kline_data and len(kline_data) >= 20:
        closes = [d["收盘"] for d in kline_data]
        n = len(closes)

        # 不同周期涨幅
        for period, label in [(5, "5日"), (10, "10日"), (20, "20日"), (60, "60日"), (120, "120日")]:
            if n > period and closes[-period - 1] > 0:
                ret = (closes[-1] - closes[-period - 1]) / closes[-period - 1] * 100
                result[f"{label}涨幅(%)"] = round(ret, 2)

        # 波动率
        if n >= 20:
            daily_returns = np.diff(closes[-21:]) / closes[-21:-1] * 100
            volatility = np.std(daily_returns) if len(daily_returns) > 0 else 0
            result["20日波动率(%)"] = round(volatility, 2)

    return result

# ── 财务健康 ──────────────────────────────────────────────────
def analyze_financial_health(quote: dict) -> dict:
    """
    财务健康快速评估
    """
    pb = quote.get("市净率", 0)
    total_mv = quote.get("总市值", 0)
    circulate_mv = quote.get("流通市值", 0)
    turnover = quote.get("换手率", 0)

    result = {
        "流通市值(亿)": round(circulate_mv, 2) if circulate_mv else 0,
        "换手率(%)": round(turnover, 2) if turnover else 0,
    }

    # 流动性评估
    if turnover:
        if turnover < 1:
            result["流动性"] = "低换手（冷门）"
        elif turnover < 3:
            result["流动性"] = "正常换手"
        elif turnover < 8:
            result["流动性"] = "活跃"
        else:
            result["流动性"] = "过度活跃（注意风险）"

    # 破净风险评估
    if pb > 0 and pb < 1:
        result["破净提醒"] = "⚠️ 股价低于每股净资产，需关注资产质量"

    return result

# ── 同行对比 ──────────────────────────────────────────────────
def peer_comparison(quote: dict, sector_data: list = None) -> dict:
    """
    同行估值对比
    sector_data: 板块成分股列表 [{"代码":, "名称":, "市盈率":, "总市值":}, ...]
    """
    if not sector_data:
        return {"同行对比": "暂无板块数据"}

    pe_list = [s.get("市盈率", 0) for s in sector_data if s.get("市盈率", 0) > 0]
    pe = quote.get("市盈率(动)", 0)

    result = {
        "板块股票数": len(sector_data),
        "板块平均PE": round(np.mean(pe_list), 2) if pe_list else 0,
        "板块PE中位数": round(np.median(pe_list), 2) if pe_list else 0,
    }

    if pe > 0 and pe_list:
        rank = sum(1 for p in pe_list if p < pe) + 1
        total = len(pe_list)
        result["PE排名"] = f"{rank}/{total}"
        pct = (total - rank) / total * 100 if total > 0 else 0
        result["PE高于"] = f"{pct:.1f}% 的同行"
        if pct > 70:
            result["估值评价"] = "相对板块估值偏高"
        elif pct < 30:
            result["估值评价"] = "相对板块估值偏低"
        else:
            result["估值评价"] = "板块中位水平"

    return result

# ── 综合基本盘评分 ────────────────────────────────────────────
def fundamental_score(quote: dict, kline_data: list = None) -> dict:
    """基本盘综合评分（0-100）"""
    score = 50  # 基准分

    pe = quote.get("市盈率(动)", 0)
    pb = quote.get("市净率", 0)
    turnover = quote.get("换手率", 0)

    # PE 评分
    if 0 < pe < 15:
        score += 15
    elif 15 <= pe < 25:
        score += 10
    elif 25 <= pe < 40:
        score += 5
    elif pe >= 100:
        score -= 10
    elif pe <= 0:
        score -= 15

    # PB 评分
    if 0 < pb < 1.5:
        score += 10
    elif 1.5 <= pb < 4:
        score += 5
    elif pb >= 10:
        score -= 10

    # 流动性
    if turnover and 1 < turnover < 8:
        score += 5

    # 趋势加分
    if kline_data and len(kline_data) >= 60:
        close_now = kline_data[-1]["收盘"]
        close_60 = kline_data[-60]["收盘"]
        if close_60 > 0:
            ret_60 = (close_now - close_60) / close_60 * 100
            if ret_60 > 20:
                score += 10
            elif ret_60 > 0:
                score += 5
            elif ret_60 < -20:
                score -= 10
            elif ret_60 < 0:
                score -= 5

    score = max(0, min(100, score))

    grade = "A" if score >= 80 else "B" if score >= 60 else "C" if score >= 40 else "D"

    return {
        "基本盘评分": score,
        "评级": grade,
        "建议": {
            "A": "基本面优秀，适合长期持有",
            "B": "基本面良好，可关注配置",
            "C": "基本面一般，需精选时机",
            "D": "基本面较差，建议谨慎",
        }.get(grade, ""),
    }
