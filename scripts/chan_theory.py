#!/usr/bin/env python3
"""
缠论分析模块
实现：分型识别 → 笔构建 → 线段构建 → 中枢识别 → 买卖点分类 → 趋势分析
"""

import numpy as np
from typing import Optional

# ── 包含关系处理 ──────────────────────────────────────────────
def _process_containment(highs, lows, dates=None):
    """
    K线包含关系处理：
    上升趋势中取高高、高低；下降趋势中取低高、低低
    返回处理后的高低点索引映射
    """
    n = len(highs)
    keep = [True] * n

    for i in range(1, n):
        if not keep[i]:
            continue
        # 找前一个未被包含的K线
        prev = i - 1
        while prev >= 0 and not keep[prev]:
            prev -= 1
        if prev < 0:
            continue

        # 判断包含关系
        if highs[i] <= highs[prev] and lows[i] >= lows[prev]:
            # i 被 prev 包含
            if highs[i] > highs[i - 1]:  # 上升趋势（用原始K线判断）
                lows[prev] = max(lows[prev], lows[i])  # 取高高、高低
            else:  # 下降趋势
                highs[prev] = min(highs[prev], highs[i])  # 取低高、低低
            keep[i] = False
        elif highs[i] >= highs[prev] and lows[i] <= lows[prev]:
            # prev 被 i 包含
            if highs[prev] > highs[prev - 1] if prev > 0 else True:
                lows[i] = max(lows[prev], lows[i])
            else:
                highs[i] = min(highs[prev], highs[i])
            keep[prev] = False

    return keep

# ── 分型识别 ──────────────────────────────────────────────────
def find_fractals(data: list) -> dict:
    """
    识别顶分型和底分型
    顶分型：中间K线高点最高、低点最高（三K线组合）
    底分型：中间K线低点最低、高点最低
    返回 {"顶分型": [index, ...], "底分型": [index, ...]}
    """
    highs = np.array([d["最高"] for d in data], dtype=float)
    lows = np.array([d["最低"] for d in data], dtype=float)
    n = len(data)

    tops = []
    bottoms = []

    for i in range(1, n - 1):
        # 顶分型：中间最高点最高，且三根K线独立（无包含）
        if highs[i] > highs[i - 1] and highs[i] > highs[i + 1]:
            # 确认中间K线低点也是最高的（强化条件）
            if lows[i] >= lows[i - 1] or lows[i] >= lows[i + 1]:
                tops.append({
                    "索引": i,
                    "日期": data[i]["日期"],
                    "价格": highs[i],
                    "类型": "顶分型",
                })
        # 底分型：中间最低点最低
        elif lows[i] < lows[i - 1] and lows[i] < lows[i + 1]:
            if highs[i] <= highs[i - 1] or highs[i] <= highs[i + 1]:
                bottoms.append({
                    "索引": i,
                    "日期": data[i]["日期"],
                    "价格": lows[i],
                    "类型": "底分型",
                })

    return {"顶分型": tops, "底分型": bottoms}

# ── 笔构建 ────────────────────────────────────────────────────
def build_bi(data: list) -> list[dict]:
    """
    构建笔：相邻顶底分型之间的连线
    返回 [{start_idx, end_idx, start_date, end_date, start_price, end_price, direction}, ...]
    """
    fractals = find_fractals(data)
    tops = fractals["顶分型"]
    bottoms = fractals["底分型"]

    # 合并排序各分型点
    points = []
    for t in tops:
        points.append({**t, "dir": "top"})
    for b in bottoms:
        points.append({**b, "dir": "bottom"})
    points.sort(key=lambda x: x["索引"])

    if len(points) < 2:
        return []

    # 构建笔：确保顶底交替，且笔之间至少有1根K线间隔
    bi_list = []
    last = points[0]

    for i in range(1, len(points)):
        curr = points[i]
        # 跳过同向分型
        if curr["dir"] == last["dir"]:
            # 同向取更极端的
            if curr["dir"] == "top" and curr["价格"] > last["价格"]:
                last = curr
            elif curr["dir"] == "bottom" and curr["价格"] < last["价格"]:
                last = curr
            continue

        # 确保至少有1根K线间隔
        if curr["索引"] - last["索引"] >= 1:
            bi_list.append({
                "起点索引": last["索引"],
                "终点索引": curr["索引"],
                "起点日期": last["日期"],
                "终点日期": curr["日期"],
                "起点价格": last["价格"],
                "终点价格": curr["价格"],
                "方向": "向下笔" if last["dir"] == "top" else "向上笔",
            })
            last = curr

    return bi_list

# ── 线段构建 ──────────────────────────────────────────────────
def build_segments(data: list) -> list[dict]:
    """
    基于笔构建线段（简化版：至少3笔构成一线段）
    线段方向由第一笔方向决定
    """
    bi_list = build_bi(data)
    if len(bi_list) < 3:
        return []

    segments = []
    i = 0
    while i < len(bi_list) - 2:
        # 取连续3笔
        b1, b2, b3 = bi_list[i], bi_list[i + 1], bi_list[i + 2]

        # 有重叠区间才构成线段特征序列
        if b1["方向"] == b3["方向"]:
            segments.append({
                "起点索引": b1["起点索引"],
                "终点索引": b3["终点索引"],
                "起点日期": b1["起点日期"],
                "终点日期": b3["终点日期"],
                "起点价格": b1["起点价格"],
                "终点价格": b3["终点价格"],
                "方向": "向下段" if b1["方向"] == "向下笔" else "向上段",
                "包含笔数": 3,
            })
            i += 2
        else:
            i += 1

    return segments

# ── 中枢识别 ──────────────────────────────────────────────────
def find_zhongshu(data: list) -> list[dict]:
    """
    识别中枢：三段重叠区间
    中枢区间 = [max(各段低点), min(各段高点)]
    """
    segments = build_segments(data)
    if len(segments) < 3:
        return []

    zhongshu_list = []
    i = 0
    while i < len(segments) - 2:
        s1, s2, s3 = segments[i], segments[i + 1], segments[i + 2]

        # 取三段的高低点
        highs = []
        lows = []
        for s in [s1, s2, s3]:
            # 用起点/终点中更低/更高的
            highs.append(max(s["起点价格"], s["终点价格"]))
            lows.append(min(s["起点价格"], s["终点价格"]))

        zg = min(highs)  # 中枢上沿
        zd = max(lows)  # 中枢下沿

        if zg > zd:  # 有重叠
            zhongshu_list.append({
                "起点日期": s1["起点日期"],
                "终点日期": s3["终点日期"],
                "中枢上沿(ZG)": round(zg, 2),
                "中枢下沿(ZD)": round(zd, 2),
                "中枢区间": f"{round(zd, 2)} - {round(zg, 2)}",
                "中枢中轴": round((zg + zd) / 2, 2),
            })
            i += 3
        else:
            i += 1

    return zhongshu_list

# ── 买卖点分类 ────────────────────────────────────────────────
def classify_buy_points(data: list) -> dict:
    """
    三类买卖点识别（简化版）
    - 一买：下跌趋势背驰后第一个底分型
    - 一卖：上涨趋势背驰后第一个顶分型
    - 二买：回调不破一买低点
    - 二卖：反弹不破一卖高点
    - 三买：回调不破中枢上沿
    - 三卖：反弹不破中枢下沿
    """
    closes = np.array([d["收盘"] for d in data], dtype=float)
    n = len(closes)

    fractals = find_fractals(data)
    zhongshu_list = find_zhongshu(data)

    buy_points = []
    sell_points = []

    # 简易背驰判断（此处做简化处理，实际应结合MACD面积比较）

    # 一买/一卖
    bottoms = fractals["底分型"]
    tops = fractals["顶分型"]

    # 最近的中枢
    last_zs = zhongshu_list[-1] if zhongshu_list else None

    # 三买/三卖判断
    if last_zs and n > 5:
        zg = last_zs["中枢上沿(ZG)"]
        zd = last_zs["中枢下沿(ZD)"]
        recent_low = min(d["最低"] for d in data[-10:])
        recent_high = max(d["最高"] for d in data[-10:])

        if recent_low > zg:
            buy_points.append({
                "类型": "三买",
                "日期": data[-1]["日期"],
                "价格": round(data[-1]["收盘"], 2),
                "说明": f"回调不破中枢上沿({zg})，构成第三类买点",
            })
        if recent_high < zd:
            sell_points.append({
                "类型": "三卖",
                "日期": data[-1]["日期"],
                "价格": round(data[-1]["收盘"], 2),
                "说明": f"反弹不破中枢下沿({zd})，构成第三类卖点",
            })

    # 一买：最近底分型 + MACD面积缩小
    if bottoms:
        last_bottom = bottoms[-1]
        buy_points.append({
            "类型": "一买（潜力）",
            "日期": last_bottom["日期"],
            "价格": last_bottom["价格"],
            "说明": f"底分型确认于{last_bottom['日期']}，若MACD背驰则第一类买点成立",
        })

    if tops:
        last_top = tops[-1]
        sell_points.append({
            "类型": "一卖（潜力）",
            "日期": last_top["日期"],
            "价格": last_top["价格"],
            "说明": f"顶分型确认于{last_top['日期']}，若MACD背驰则第一类卖点成立",
        })

    return {"缠论买点": buy_points, "缠论卖点": sell_points}

# ── 趋势分析 ──────────────────────────────────────────────────
def analyze_chan_trend(data: list) -> dict:
    """
    缠论综合趋势分析
    """
    bi_list = build_bi(data)
    zhongshu_list = find_zhongshu(data)
    buy_sell_points = classify_buy_points(data)

    # 趋势判断：基于最近的中枢和方向
    trend = "盘整"
    if bi_list:
        last_bi = bi_list[-1]
        if last_bi["方向"] == "向上笔":
            if zhongshu_list:
                last_zs = zhongshu_list[-1]
                if last_bi["终点价格"] > last_zs["中枢上沿(ZG)"]:
                    trend = "向上离开中枢（上涨趋势）"
                else:
                    trend = "中枢内向上运行"
            else:
                trend = "无中枢，向上笔运行中"
        else:
            if zhongshu_list:
                last_zs = zhongshu_list[-1]
                if last_bi["终点价格"] < last_zs["中枢下沿(ZD)"]:
                    trend = "向下离开中枢（下跌趋势）"
                else:
                    trend = "中枢内向下运行"
            else:
                trend = "无中枢，向下笔运行中"

    return {
        "缠论趋势": trend,
        "笔数量": len(bi_list),
        "中枢数量": len(zhongshu_list),
        "最近中枢": zhongshu_list[-1] if zhongshu_list else None,
        "买点": buy_sell_points.get("缠论买点", []),
        "卖点": buy_sell_points.get("缠论卖点", []),
    }
