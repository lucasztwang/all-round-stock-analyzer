#!/usr/bin/env python3
"""
技术指标分析模块
计算: MA / MACD / RSI / KDJ / BOLL / 量价分析 / 支撑压力 / 综合信号
"""

import numpy as np
from typing import Optional

# ── 移动均线 ──────────────────────────────────────────────────
def calc_ma(closes: list, periods: list = None) -> dict:
    """
    计算多周期移动均线
    返回 {"MA5": [...], "MA10": [...], ...}
    """
    if periods is None:
        periods = [5, 10, 20, 60, 120, 250]
    closes = np.array(closes, dtype=float)
    result = {}
    for p in periods:
        if len(closes) >= p:
            ma = np.full(len(closes), np.nan)
            for i in range(p - 1, len(closes)):
                ma[i] = np.mean(closes[i - p + 1 : i + 1])
            result[f"MA{p}"] = ma.tolist()
        else:
            result[f"MA{p}"] = [np.nan] * len(closes)
    return result

# ── MACD ──────────────────────────────────────────────────────
def calc_macd(closes: list, fast: int = 12, slow: int = 26, signal: int = 9) -> dict:
    """
    计算 MACD
    返回 {"DIF": [], "DEA": [], "MACD": []} (柱状线)
    """
    closes = np.array(closes, dtype=float)
    n = len(closes)

    # EMA
    def ema(data, period):
        result = np.full(n, np.nan)
        if n < period:
            return result
        alpha = 2 / (period + 1)
        result[period - 1] = np.mean(data[:period])
        for i in range(period, n):
            result[i] = alpha * data[i] + (1 - alpha) * result[i - 1]
        return result

    ema_fast = ema(closes, fast)
    ema_slow = ema(closes, slow)
    dif = ema_fast - ema_slow
    dea = ema(dif, signal)
    macd_bar = 2 * (dif - dea)

    return {
        "DIF": dif.tolist(),
        "DEA": dea.tolist(),
        "MACD": macd_bar.tolist(),
    }

# ── RSI ───────────────────────────────────────────────────────
def calc_rsi(closes: list, period: int = 14) -> list:
    """Wilder's RSI"""
    closes = np.array(closes, dtype=float)
    n = len(closes)
    if n <= period:
        return [np.nan] * n

    deltas = np.diff(closes)
    gain = np.where(deltas > 0, deltas, 0)
    loss = np.where(deltas < 0, -deltas, 0)

    rsi = np.full(n, np.nan)
    avg_gain = np.mean(gain[:period])
    avg_loss = np.mean(loss[:period])

    if avg_loss == 0:
        rsi[period] = 100
    else:
        rs = avg_gain / avg_loss
        rsi[period] = 100 - (100 / (1 + rs))

    for i in range(period + 1, n):
        avg_gain = (avg_gain * (period - 1) + gain[i - 1]) / period
        avg_loss = (avg_loss * (period - 1) + loss[i - 1]) / period
        if avg_loss == 0:
            rsi[i] = 100
        else:
            rs = avg_gain / avg_loss
            rsi[i] = 100 - (100 / (1 + rs))

    return rsi.tolist()

# ── KDJ ───────────────────────────────────────────────────────
def calc_kdj(data: list, n: int = 9, m1: int = 3, m2: int = 3) -> dict:
    """
    计算 KDJ
    data: list of dict with "最高", "最低", "收盘"
    """
    highs = np.array([d["最高"] for d in data], dtype=float)
    lows = np.array([d["最低"] for d in data], dtype=float)
    closes = np.array([d["收盘"] for d in data], dtype=float)
    length = len(data)

    k = np.full(length, np.nan)
    d = np.full(length, np.nan)
    j = np.full(length, np.nan)

    # RSV
    rsv = np.full(length, np.nan)
    for i in range(n - 1, length):
        hn = np.max(highs[i - n + 1 : i + 1])
        ln = np.min(lows[i - n + 1 : i + 1])
        if hn != ln:
            rsv[i] = (closes[i] - ln) / (hn - ln) * 100
        else:
            rsv[i] = 50

    # K, D, J
    start = n + m1 - 2
    if start < length:
        k[start] = 50
        d[start] = 50
        j[start] = 50
        for i in range(start + 1, length):
            k[i] = (rsv[i] + (m1 - 1) * k[i - 1]) / m1
            d[i] = (k[i] + (m2 - 1) * d[i - 1]) / m2
            j[i] = 3 * k[i] - 2 * d[i]

    return {"K": k.tolist(), "D": d.tolist(), "J": j.tolist()}

# ── 布林带 ────────────────────────────────────────────────────
def calc_bollinger(closes: list, period: int = 20, std_mult: float = 2.0) -> dict:
    """布林带（上轨/中轨/下轨）"""
    closes = np.array(closes, dtype=float)
    n = len(closes)
    mid = np.full(n, np.nan)
    upper = np.full(n, np.nan)
    lower = np.full(n, np.nan)
    width = np.full(n, np.nan)  # 带宽百分比

    for i in range(period - 1, n):
        window = closes[i - period + 1 : i + 1]
        mid[i] = np.mean(window)
        std = np.std(window, ddof=1)
        upper[i] = mid[i] + std_mult * std
        lower[i] = mid[i] - std_mult * std
        if mid[i] != 0:
            width[i] = (upper[i] - lower[i]) / mid[i] * 100

    return {
        "上轨": upper.tolist(),
        "中轨": mid.tolist(),
        "下轨": lower.tolist(),
        "带宽": width.tolist(),
    }

# ── 量价分析 ──────────────────────────────────────────────────
def calc_volume_analysis(data: list) -> dict:
    """
    量价关系分析
    data: list of dict with "收盘", "成交量"
    返回 量价配合度、放量/缩量标记
    """
    n = len(data)
    closes = np.array([d["收盘"] for d in data], dtype=float)
    volumes = np.array([d["成交量"] for d in data], dtype=float)

    price_change = np.full(n, np.nan)
    vol_change = np.full(n, np.nan)
    vol_ratio = np.full(n, np.nan)  # 量比 (vs 5日均量)
    signal = ["—"] * n  # 放量上涨 / 放量下跌 / 缩量上涨 / 缩量下跌

    for i in range(1, n):
        price_change[i] = (closes[i] - closes[i - 1]) / closes[i - 1] * 100

    for i in range(5, n):
        avg_vol = np.mean(volumes[i - 5 : i])
        if avg_vol > 0:
            vol_ratio[i] = volumes[i] / avg_vol
        if i > 0:
            vol_change[i] = (volumes[i] - volumes[i - 1]) / volumes[i - 1] * 100

        # 信号判断
        if price_change[i] > 0 and vol_ratio[i] > 1.5:
            signal[i] = "放量上涨 🔥"
        elif price_change[i] < 0 and vol_ratio[i] > 1.5:
            signal[i] = "放量下跌 ⚠️"
        elif price_change[i] > 0 and vol_ratio[i] < 0.8:
            signal[i] = "缩量上涨"
        elif price_change[i] < 0 and vol_ratio[i] < 0.8:
            signal[i] = "缩量下跌"
        elif vol_ratio[i] > 1.5:
            signal[i] = "异常放量"

    return {
        "涨跌幅": price_change.tolist(),
        "量比": vol_ratio.tolist(),
        "信号": signal,
    }

# ── 支撑/压力位 ──────────────────────────────────────────────
def calc_support_resistance(data: list) -> dict:
    """
    基于近期高低点和均线计算支撑/压力位
    """
    closes = np.array([d["收盘"] for d in data], dtype=float)
    highs = np.array([d["最高"] for d in data], dtype=float)
    lows = np.array([d["最低"] for d in data], dtype=float)
    n = len(closes)

    ma = calc_ma(closes.tolist(), [20, 60, 120])

    # 近期高点/低点
    recent = min(20, n)
    recent_high = np.max(highs[-recent:]) if n > 0 else closes[-1]
    recent_low = np.min(lows[-recent:]) if n > 0 else closes[-1]

    # 历史重要点位
    period = min(60, n)
    hist_high = np.max(highs[-period:]) if n > 0 else closes[-1]
    hist_low = np.min(lows[-period:]) if n > 0 else closes[-1]

    support_levels = []
    resistance_levels = []

    # 均线支撑/压力
    for key, period_val in [("MA20", 20), ("MA60", 60), ("MA120", 120)]:
        ma_vals = ma.get(key, [])
        last_ma = next((v for v in reversed(ma_vals) if not np.isnan(v)), None)
        if last_ma:
            if last_ma < closes[-1]:
                support_levels.append({"点位": round(last_ma, 2), "类型": key})
            else:
                resistance_levels.append({"点位": round(last_ma, 2), "类型": key})

    if recent_low < closes[-1]:
        support_levels.append({"点位": round(recent_low, 2), "类型": "20日低点"})
    if hist_low < closes[-1]:
        support_levels.append({"点位": round(hist_low, 2), "类型": "60日低点"})
    if recent_high > closes[-1]:
        resistance_levels.append({"点位": round(recent_high, 2), "类型": "20日高点"})
    if hist_high > closes[-1]:
        resistance_levels.append({"点位": round(hist_high, 2), "类型": "60日高点"})

    support_levels.sort(key=lambda x: x["点位"], reverse=True)
    resistance_levels.sort(key=lambda x: x["点位"])

    return {
        "支撑位": support_levels[:3],
        "压力位": resistance_levels[:3],
    }

# ── 趋势判断 ──────────────────────────────────────────────────
def analyze_trend(data: list) -> dict:
    """基于均线排列判断趋势"""
    closes = np.array([d["收盘"] for d in data], dtype=float)
    ma = calc_ma(closes.tolist(), [5, 10, 20, 60])

    trend = "震荡"
    score = 0

    last_ma5 = _last_valid(ma.get("MA5", []))
    last_ma10 = _last_valid(ma.get("MA10", []))
    last_ma20 = _last_valid(ma.get("MA20", []))
    last_ma60 = _last_valid(ma.get("MA60", []))

    if last_ma5 and last_ma10 and last_ma20 and last_ma60:
        if last_ma5 > last_ma10 > last_ma20 > last_ma60:
            trend = "多头排列（强势上涨）"
            score = 90
        elif last_ma5 < last_ma10 < last_ma20 < last_ma60:
            trend = "空头排列（弱势下跌）"
            score = 10
        elif last_ma5 > last_ma60 and last_ma10 > last_ma60:
            trend = "中长期偏多"
            score = 70
        elif last_ma5 < last_ma60 and last_ma10 < last_ma60:
            trend = "中长期偏空"
            score = 30
        elif last_ma5 > last_ma20:
            trend = "短期偏多"
            score = 60
        else:
            trend = "短期偏空"
            score = 40

    return {"趋势": trend, "趋势评分": score}

# ── 综合信号 ──────────────────────────────────────────────────
def generate_signals(data: list) -> dict:
    """
    综合技术信号汇总
    返回买入/卖出信号列表
    """
    closes = np.array([d["收盘"] for d in data], dtype=float)
    n = len(closes)
    signals = {"买入信号": [], "卖出信号": [], "综合建议": "观望"}

    if n < 60:
        return signals

    # MACD 金叉/死叉
    macd_data = calc_macd(closes.tolist())
    dif = macd_data["DIF"]
    dea = macd_data["DEA"]

    for i in range(max(2, n - 5), n):
        if dif[i] > dea[i] and dif[i - 1] <= dea[i - 1]:
            signals["买入信号"].append(f"{data[i]['日期']} MACD金叉")
        if dif[i] < dea[i] and dif[i - 1] >= dea[i - 1]:
            signals["卖出信号"].append(f"{data[i]['日期']} MACD死叉")

    # RSI 超买超卖
    rsi = calc_rsi(closes.tolist())
    last_rsi = rsi[-1] if not np.isnan(rsi[-1]) else 50
    if last_rsi < 30:
        signals["买入信号"].append(f"RSI={last_rsi:.1f} 超卖区域")
    elif last_rsi > 70:
        signals["卖出信号"].append(f"RSI={last_rsi:.1f} 超买区域")

    # KDJ
    kdj = calc_kdj(data)
    last_k = _last_valid(kdj["K"])
    last_d = _last_valid(kdj["D"])
    last_j = _last_valid(kdj["J"])
    if last_k and last_d and last_j:
        if last_j < 0:
            signals["买入信号"].append(f"J值={last_j:.1f} 超卖钝化")
        if last_j > 100:
            signals["卖出信号"].append(f"J值={last_j:.1f} 超买钝化")
        if last_k > last_d and _prev_valid(kdj["K"], -2) and _prev_valid(kdj["D"], -2):
            pk = _prev_valid(kdj["K"], -2)
            pd = _prev_valid(kdj["D"], -2)
            if pk <= pd:
                signals["买入信号"].append("KDJ金叉")

    # 布林带
    boll = calc_bollinger(closes.tolist())
    last_close = closes[-1]
    last_lower = _last_valid(boll["下轨"])
    last_upper = _last_valid(boll["上轨"])
    if last_lower and last_close < last_lower:
        signals["买入信号"].append("价格跌破布林下轨 超跌")
    if last_upper and last_close > last_upper:
        signals["卖出信号"].append("价格突破布林上轨 超涨")

    # 量价信号
    vol = calc_volume_analysis(data)
    last_sig = vol["信号"][-1] if vol["信号"] else ""
    if "放量上涨" in str(last_sig):
        signals["买入信号"].append("放量上涨 量价配合良好")
    if "放量下跌" in str(last_sig):
        signals["卖出信号"].append("放量下跌 注意风险")

    # 综合建议
    buy_count = len(signals["买入信号"])
    sell_count = len(signals["卖出信号"])
    if buy_count >= 3 and sell_count == 0:
        signals["综合建议"] = "偏多"
    elif sell_count >= 3 and buy_count == 0:
        signals["综合建议"] = "偏空"
    elif buy_count > sell_count:
        signals["综合建议"] = "谨慎偏多"
    elif sell_count > buy_count:
        signals["综合建议"] = "谨慎偏空"
    else:
        signals["综合建议"] = "观望"

    return signals

# ── 辅助函数 ──────────────────────────────────────────────────
def _last_valid(arr) -> Optional[float]:
    for v in reversed(arr):
        if v is not None and not (isinstance(v, float) and np.isnan(v)):
            return v
    return None

def _prev_valid(arr, offset: int) -> Optional[float]:
    valid_indices = [i for i, v in enumerate(arr) if v is not None and not np.isnan(v)]
    if len(valid_indices) >= abs(offset):
        return arr[valid_indices[offset]]
    return None
