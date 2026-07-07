#!/usr/bin/env python3
"""
买卖点集中研判模块
聚合多指标共振、顶底背离、多周期信号、量价突破，给出统一买入/卖出评分
"""

import numpy as np


class BuySellPointAnalyzer:
    """买卖点综合研判器"""

    def __init__(self, kline: list, weekly_kline: list = None):
        self.kline = kline
        self.weekly = weekly_kline
        self.n = len(kline)
        self.closes = np.array([d["收盘"] for d in kline], float)
        self.highs = np.array([d["最高"] for d in kline], float)
        self.lows = np.array([d["最低"] for d in kline], float)
        self.volumes = np.array([d["成交量"] for d in kline], float)

    # ── MACD ──────────────────────────────────────────────────
    def _calc_macd(self, data, fast=12, slow=26, signal=9):
        nlen = len(data)
        def ema(arr, p):
            r = np.full(nlen, np.nan)
            if nlen >= p:
                r[p - 1] = np.mean(arr[:p])
                alpha = 2 / (p + 1)
                for i in range(p, nlen):
                    r[i] = alpha * arr[i] + (1 - alpha) * r[i - 1]
            return r
        ef = ema(data, fast)
        es = ema(data, slow)
        dif = ef - es
        dea = ema(dif, signal)
        bar = 2 * (dif - dea)
        return dif, dea, bar

    # ── 1. 多指标共振分析 ─────────────────────────────────────
    def multi_indicator_resonance(self) -> dict:
        """多指标共振：当多个指标同时给出同向信号时，力量最强"""
        n = self.n
        if n < 60:
            return {"信号": "数据不足", "得分": 50, "方向": "中性"}

        closes = self.closes
        buy_score = 0
        sell_score = 0
        signals = []

        # MACD 金叉/死叉
        dif, dea, bar = self._calc_macd(closes)
        if dif[-1] > dea[-1] and dif[-2] <= dea[-2]:
            buy_score += 25
            signals.append("✅ MACD金叉")
        elif dif[-1] < dea[-1] and dif[-2] >= dea[-2]:
            sell_score += 25
            signals.append("⚠️ MACD死叉")
        elif dif[-1] > dea[-1]:
            buy_score += 10
            signals.append("📌 DIF在DEA上方")
        else:
            sell_score += 10
            signals.append("📌 DIF在DEA下方")

        # MACD 零轴位置
        if dif[-1] > 0:
            buy_score += 10
            signals.append("✅ MACD零轴上方")
        else:
            sell_score += 5
            signals.append("⚠️ MACD零轴下方")

        # RSI
        rsi = self._calc_rsi(closes)
        if rsi > 70:
            sell_score += 15
            signals.append(f"⚠️ RSI={rsi:.1f}超买")
        elif rsi < 30:
            buy_score += 15
            signals.append(f"✅ RSI={rsi:.1f}超卖")
        elif rsi > 50:
            buy_score += 5
            signals.append(f"📌 RSI={rsi:.1f}偏强")
        else:
            sell_score += 5
            signals.append(f"📌 RSI={rsi:.1f}偏弱")

        # KDJ
        kdj = self._calc_kdj()
        last_k = self._last_valid(kdj.get("K", []))
        last_d = self._last_valid(kdj.get("D", []))
        last_j = self._last_valid(kdj.get("J", []))
        if last_k and last_d and last_j:
            if last_j < 0:
                buy_score += 15
                signals.append(f"✅ J值={last_j:.1f}超卖钝化")
            elif last_j > 100:
                sell_score += 15
                signals.append(f"⚠️ J值={last_j:.1f}超买钝化")
            elif last_k > last_d:
                buy_score += 8
                signals.append("📌 K在D上方")
            else:
                sell_score += 8
                signals.append("📌 K在D下方")

        # 均线排列
        ma5 = np.mean(closes[-5:])
        ma10 = np.mean(closes[-10:])
        ma20 = np.mean(closes[-20:])
        ma60 = np.mean(closes[-60:])
        if ma5 > ma10 > ma20 > ma60:
            buy_score += 20
            signals.append("✅ 多头排列")
        elif ma5 < ma10 < ma20 < ma60:
            sell_score += 20
            signals.append("⚠️ 空头排列")

        # 布林带位置
        mid = ma20
        std = np.std(closes[-20:], ddof=1)
        upper = mid + 2 * std
        lower = mid - 2 * std
        if closes[-1] < lower:
            buy_score += 10
            signals.append("✅ 跌破布林下轨")
        elif closes[-1] > upper:
            sell_score += 10
            signals.append("⚠️ 突破布林上轨")

        # 综合判断
        total = buy_score - sell_score
        if total >= 30:
            direction = "强力买入"
            overall = "🔥 多指标共振偏多"
        elif total >= 10:
            direction = "偏多"
            overall = "📌 多数指标偏多"
        elif total >= -15:
            direction = "中性"
            overall = "⏸️ 信号不明确"
        elif total >= -30:
            direction = "偏空"
            overall = "⚠️ 多数指标偏空"
        else:
            direction = "强力卖出"
            overall = "🚨 多指标共振偏空"

        return {
            "信号": overall,
            "方向": direction,
            "买入得分": buy_score,
            "卖出得分": sell_score,
            "净得分": total,
            "细分信号": signals,
        }

    # ── 2. 顶底背离检测 ─────────────────────────────────────
    def divergence_analysis(self) -> dict:
        """检测 MACD 顶/底背离"""
        n = self.n
        if n < 40:
            return {"背离": "数据不足"}

        closes = self.closes
        dif, dea, bar = self._calc_macd(closes)

        # 最近40日窗口
        lookback = min(40, n)
        c_recent = closes[-lookback:]
        dif_recent = dif[-lookback:]
        bar_recent = bar[-lookback:]

        # 顶背离：价格新高，DIF 未新高（或量能柱缩小）
        top_divergence = False
        price_high_idx = np.argmax(c_recent)
        dif_at_price_high = dif_recent[price_high_idx]
        dif_prev_30 = dif_recent[:30] if len(dif_recent) >= 30 else dif_recent
        if np.max(dif_prev_30) > dif_at_price_high and c_recent[-1] > np.percentile(c_recent, 80):
            top_divergence = True

        # 底背离：价格新低，DIF 未新低
        bottom_divergence = False
        price_low_idx = np.argmin(c_recent)
        dif_at_price_low = dif_recent[price_low_idx]
        dif_prev_30 = dif_recent[:30] if len(dif_recent) >= 30 else dif_recent
        if np.min(dif_prev_30) < dif_at_price_low and c_recent[-1] < np.percentile(c_recent, 20):
            bottom_divergence = True

        if top_divergence:
            return {"背离": "⚠️ 顶背离", "信号": "卖出", "说明": "价格高位但MACD动能衰减，见顶风险"}
        elif bottom_divergence:
            return {"背离": "✅ 底背离", "信号": "买入", "说明": "价格低位但MACD动能转强，见底信号"}
        else:
            return {"背离": "无明显背离", "信号": "中性"}

    # ── 3. 量价突破确认 ─────────────────────────────────────
    def volume_price_breakout(self) -> dict:
        """量价配合的突破确认"""
        n = self.n
        if n < 20:
            return {"状态": "数据不足"}

        closes = self.closes
        volumes = self.volumes
        highs = self.highs

        avg_vol_20 = np.mean(volumes[-20:])
        latest_vol = volumes[-1]
        latest_close = closes[-1]
        prev_close = closes[-2]

        # 创新高判断
        high_20 = np.max(highs[-20:])
        new_high = latest_close >= high_20 * 0.98

        # 放量判断
        vol_surge = latest_vol > avg_vol_20 * 1.5
        vol_ok = latest_vol > avg_vol_20 * 1.2

        # 价格涨幅
        pct_change = (latest_close - prev_close) / prev_close * 100

        signals = []
        score = 50

        if new_high and vol_surge and pct_change > 3:
            signals.append("✅ 放量突破新高，资金认可")
            score = 90
        elif new_high and vol_ok:
            signals.append("📌 温和放量创新高")
            score = 75
        elif new_high and not vol_ok:
            signals.append("⚠️ 缩量创新高，可能假突破")
            score = 40
        elif pct_change > 3 and vol_surge:
            signals.append("📌 放量大涨但未创新高")
            score = 65
        elif pct_change < -3 and vol_surge:
            signals.append("⚠️ 放量大跌，抛压重")
            score = 25
        elif pct_change > 0 and not vol_ok:
            signals.append("⚠️ 缩量上涨，动能不足")
            score = 45
        elif pct_change < 0 and not vol_ok:
            score = 40

        return {
            "状态": signals[0] if signals else "量价正常",
            "得分": score,
            "创新高": bool(new_high),
            "放量": bool(vol_surge),
            "当日涨跌幅": round(pct_change, 2),
            "量能比": round(latest_vol / avg_vol_20, 2),
        }

    # ── 4. 多周期信号对比 ────────────────────────────────────
    def multi_timeframe_signal(self) -> dict:
        """日线+周线多周期共振分析"""
        day_trend = self._evaluate_trend(self.kline)
        week_trend = {}
        if self.weekly and len(self.weekly) >= 20:
            week_trend = self._evaluate_trend(self.weekly)

        resonance = "无"
        day_dir = day_trend.get("方向", "中性")
        week_dir = week_trend.get("方向", "中性") if week_trend else "N/A"

        if day_dir == "上涨" and week_dir == "上涨":
            resonance = "✅ 日周共振看多，上涨确定性高"
        elif day_dir == "上涨" and week_dir == "下跌":
            resonance = "📌 日线反弹但周线偏空，可能只是短线反弹"
        elif day_dir == "下跌" and week_dir == "上涨":
            resonance = "📌 日线回调但周线偏多，可能是回调买入机会"
        elif day_dir == "下跌" and week_dir == "下跌":
            resonance = "⚠️ 日周共振看空，下跌风险大"

        return {
            "日线趋势": day_dir,
            "周线趋势": week_dir,
            "共振信号": resonance,
            "建议": (
                "日周共振 → 高确定性" if "共振" in resonance and ("看多" in resonance or "看空" in resonance)
                else "方向不一致 → 建议观望或轻仓"
            ),
        }

    # ── 5. 综合买卖点评分 ─────────────────────────────────────
    def comprehensive_analysis(self) -> dict:
        """汇总所有分析，输出最终买卖点判断"""
        resonance = self.multi_indicator_resonance()
        divergence = self.divergence_analysis()
        breakout = self.volume_price_breakout()
        timeframe = self.multi_timeframe_signal()

        # 加权综合
        score = 0
        score += resonance["净得分"] * 0.4
        if divergence["背离"].startswith("✅"):
            score += 25
        elif divergence["背离"].startswith("⚠️"):
            score -= 25
        score += (breakout["得分"] - 50) * 0.3

        # 最终信号
        if "共振看多" in timeframe["共振信号"]:
            score += 10
        elif "共振看空" in timeframe["共振信号"]:
            score -= 10

        if score >= 25:
            signal = "🟢 强烈买入"
            advice = "多指标共振偏多+底背离+量价配合，可考虑积极建仓"
        elif score >= 10:
            signal = "🟢 买入"
            advice = "多数指标偏多，可考虑逢低买入"
        elif score >= -10:
            signal = "⏸️ 观望"
            advice = "信号不明确，建议观察等待"
        elif score >= -25:
            signal = "🔴 卖出"
            advice = "多数指标偏空，建议减仓或卖出"
        else:
            signal = "🚨 强烈卖出"
            advice = "多指标共振偏空+顶背离，建议果断离场"

        return {
            "综合信号": signal,
            "综合建议": advice,
            "买卖点评分": round(score, 1),
            "共振分析": resonance,
            "背离检测": divergence,
            "量价突破": breakout,
            "多周期": timeframe,
        }

    # ── 辅助方法 ──────────────────────────────────────────────
    def _calc_rsi(self, data, period=14):
        nlen = len(data)
        deltas = np.diff(data)
        gain = np.where(deltas > 0, deltas, 0)
        loss = np.where(deltas < 0, -deltas, 0)
        avg_gain = np.mean(gain[:period])
        avg_loss = np.mean(loss[:period])
        if avg_loss == 0:
            return 100
        return 100 - 100 / (1 + avg_gain / avg_loss)

    def _calc_kdj(self, n=9):
        highs, lows, closes = self.highs, self.lows, self.closes
        length = self.n
        rsv = np.full(length, np.nan)
        for i in range(n - 1, length):
            hn = np.max(highs[i - n + 1:i + 1])
            ln = np.min(lows[i - n + 1:i + 1])
            rsv[i] = (closes[i] - ln) / (hn - ln) * 100 if hn != ln else 50

        k = np.full(length, np.nan)
        d = np.full(length, np.nan)
        j = np.full(length, np.nan)
        start = n + 2
        if start < length:
            k[start] = d[start] = j[start] = 50
            for i in range(start + 1, length):
                k[i] = (rsv[i] + 2 * k[i - 1]) / 3
                d[i] = (k[i] + 2 * d[i - 1]) / 3
                j[i] = 3 * k[i] - 2 * d[i]
        return {"K": k, "D": d, "J": j}

    def _evaluate_trend(self, data):
        if len(data) < 20:
            return {"方向": "中性"}
        c = np.array([d["收盘"] for d in data], float)
        ma5 = np.mean(c[-5:])
        ma10 = np.mean(c[-10:])
        ma20 = np.mean(c[-20:])
        ma60 = np.mean(c[-60:]) if len(c) >= 60 else ma20
        if ma5 > ma10 > ma20 > ma60:
            return {"方向": "上涨", "强度": "强"}
        elif ma5 > ma20:
            return {"方向": "上涨", "强度": "中"}
        elif ma5 < ma10 < ma20:
            return {"方向": "下跌", "强度": "中"}
        elif ma5 < ma20:
            return {"方向": "下跌", "强度": "弱"}
        return {"方向": "震荡", "强度": "中"}

    def _last_valid(self, arr):
        for v in reversed(arr):
            if v is not None and not (isinstance(v, float) and np.isnan(v)):
                return v
        return None


# ── 快捷函数 ───────────────────────────────────────────────────
def quick_buy_sell_analysis(kline: list, weekly_kline: list = None) -> dict:
    """快速获取买卖点研判结果"""
    a = BuySellPointAnalyzer(kline, weekly_kline)
    return a.comprehensive_analysis()


def batch_buy_sell_compare(stocks_kline: dict) -> dict:
    """
    多只股票买卖点对比
    stocks_kline: {"000001": kline_data, "600519": kline_data, ...}
    """
    results = {}
    for code, kline in stocks_kline.items():
        a = BuySellPointAnalyzer(kline)
        results[code] = a.comprehensive_analysis()
    return results


if __name__ == "__main__":
    print("BuySellPointAnalyzer ready")
