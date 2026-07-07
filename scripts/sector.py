#!/usr/bin/env python3
"""
行业板块分析模块
板块热力图 / 排名 / 轮动 / 个股在板块中的位置
"""

import numpy as np
from typing import Optional


# ── 板块排名 ──────────────────────────────────────────────────
def sector_rank(sectors: list, metric: str = "涨跌幅") -> list[dict]:
    """
    按指定指标排序板块
    sectors: get_sector_list() 返回的板块列表
    metric: "涨跌幅" 或自定义字段
    """
    if not sectors:
        return []

    valid = [s for s in sectors if isinstance(s.get(metric), (int, float))]
    sorted_sectors = sorted(valid, key=lambda x: x[metric], reverse=True)

    return sorted_sectors

def sector_top(sectors: list, metric: str = "涨跌幅", top_n: int = 10) -> list[dict]:
    """涨幅前N板块"""
    return sector_rank(sectors, metric)[:top_n]

def sector_bottom(sectors: list, metric: str = "涨跌幅", bottom_n: int = 10) -> list[dict]:
    """跌幅前N板块"""
    ranked = sector_rank(sectors, metric)
    return ranked[-bottom_n:][::-1]

# ── 板块统计 ──────────────────────────────────────────────────
def sector_stats(sectors: list) -> dict:
    """
    板块整体统计
    """
    if not sectors:
        return {}

    changes = [s.get("涨跌幅", 0) for s in sectors if s.get("涨跌幅") is not None]
    up_count = sum(1 for c in changes if c > 0)
    down_count = sum(1 for c in changes if c < 0)
    flat_count = sum(1 for c in changes if c == 0)

    return {
        "板块总数": len(sectors),
        "上涨板块": up_count,
        "下跌板块": down_count,
        "平盘板块": flat_count,
        "上涨比例(%)": round(up_count / len(sectors) * 100, 1) if sectors else 0,
        "平均涨跌(%)": round(np.mean(changes), 2) if changes else 0,
        "最强板块": sectors[0]["名称"] if sectors else "",
        "最弱板块": sectors[-1]["名称"] if sectors else "",
    }

# ── 板块轮动分析 ──────────────────────────────────────────────
def sector_rotation(sectors: list, days: int = 5) -> dict:
    """
    板块轮动分析（基于当前快照）
    识别领涨/领跌板块、资金流向方向
    """
    if not sectors:
        return {"分析": "暂无板块数据"}

    top5 = sector_top(sectors, "涨跌幅", 5)
    bottom5 = sector_bottom(sectors, "涨跌幅", 5)

    # 风格判断
    changes = [s.get("涨跌幅", 0) for s in sectors if s.get("涨跌幅") is not None]
    if not changes:
        return {"分析": "无有效数据"}

    mean_change = np.mean(changes)
    std_change = np.std(changes)

    # 市场风格
    if std_change < 1.5:
        style = "板块分化小，市场风格均衡"
    elif std_change < 3:
        style = "板块适度分化"
    else:
        style = "板块分化明显，结构性行情"

    if mean_change > 1:
        style += "（普涨格局）"
    elif mean_change < -1:
        style += "（普跌格局）"

    return {
        "市场风格": style,
        "板块涨跌标准差": round(std_change, 2),
        "领涨板块": [{"名称": s["名称"], "涨跌幅": s.get("涨跌幅", 0)} for s in top5],
        "领跌板块": [{"名称": s["名称"], "涨跌幅": s.get("涨跌幅", 0)} for s in bottom5],
        "操作建议": _rotation_advice(mean_change, std_change, top5),
    }

def _rotation_advice(mean_change, std_change, top5):
    if mean_change > 1 and std_change < 2:
        return "市场普涨，可积极做多领涨板块龙头"
    elif mean_change > 0 and std_change > 3:
        return "结构性行情，关注领涨板块，回避领跌板块"
    elif mean_change < -1:
        return "市场偏弱，控制仓位，等待企稳信号"
    return "市场震荡，精选个股为主"

# ── 个股在板块中的位置 ────────────────────────────────────────
def stock_in_sector_context(quote: dict, sector_stocks: list) -> dict:
    """
    分析个股在其所属板块中的相对位置
    """
    if not sector_stocks or len(sector_stocks) < 3:
        return {"分析": "板块成分股数据不足"}

    stock_code = quote.get("代码", "")
    stock_change = quote.get("涨跌幅", 0)
    stock_pe = quote.get("市盈率(动)", 0)
    stock_mv = quote.get("总市值", 0)

    # 涨跌幅排名
    changes = [(s.get("涨跌幅", 0), s.get("代码", "")) for s in sector_stocks]
    changes.sort(key=lambda x: x[0], reverse=True)
    change_rank = next((i + 1 for i, (_, code) in enumerate(changes) if code == stock_code), len(sector_stocks))

    # 市值排名
    mvs = [(s.get("总市值", 0) or 0, s.get("代码", "")) for s in sector_stocks]
    mvs.sort(key=lambda x: x[0], reverse=True)
    mv_rank = next((i + 1 for i, (_, code) in enumerate(mvs) if code == stock_code), len(sector_stocks))

    # 板块内涨幅统计
    valid_changes = [s.get("涨跌幅", 0) for s in sector_stocks if s.get("涨跌幅") is not None]
    avg_change = np.mean(valid_changes) if valid_changes else 0

    relative_strength = stock_change - avg_change

    return {
        "板块名称": "所属行业板块",
        "板块成分股数": len(sector_stocks),
        "个股涨跌幅": round(stock_change, 2),
        "板块平均涨跌幅": round(avg_change, 2),
        "相对强度": round(relative_strength, 2),
        "涨幅排名": f"{change_rank}/{len(sector_stocks)}",
        "市值排名": f"{mv_rank}/{len(sector_stocks)}",
        "相对评价": (
            "强于板块 👍" if relative_strength > 1 else
            "弱于板块 👎" if relative_strength < -1 else
            "与板块同步"
        ),
    }

# ── 板块热度分析 ──────────────────────────────────────────────
def sector_heatmap_data(sectors: list, top_n: int = 30) -> dict:
    """
    生成板块热力图所需的数据
    """
    if not sectors:
        return {"板块": [], "涨跌幅": []}

    sorted_sectors = sorted(sectors, key=lambda x: abs(x.get("涨跌幅", 0)), reverse=True)
    top = sorted_sectors[:top_n]

    return {
        "板块": [s["名称"] for s in top],
        "涨跌幅": [s.get("涨跌幅", 0) for s in top],
        "代码": [s.get("代码", "") for s in top],
    }
