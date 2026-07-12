#!/usr/bin/env python3
"""
一夜持股法 — 尾盘选股模块
8条件筛选：时间/涨幅/量比/换手率/流通市值/成交量阶梯/盘中走势/尾盘确认

策略来源：尾盘2:30后确认强势标的，隔夜持仓，次日开盘30分钟内离场
核心纪律：红盘勿贪、绿盘别扛、无标空仓
"""

import numpy as np
from typing import List, Dict, Optional


# ── 工具函数 ──────────────────────────────────────────────────

def _norm_mv(mv_value: float) -> float:
    """流通市值统一转为亿（腾讯API直接返回亿单位，此处为兼容性保留）"""
    if mv_value > 1e8:
        return mv_value / 1e8  # 元 → 亿
    elif mv_value > 1e5:
        return mv_value / 1e4  # 万元 → 亿
    return mv_value  # 已是亿


def _compare_with_index(stock_change: float, index_change: float = 0) -> dict:
    """条件7：比较个股与大盘走势强弱"""
    diff = stock_change - index_change
    if diff > 2:
        return {"强于大盘": True, "强度差": round(diff, 2), "研判": "显著强于大盘"}
    elif diff > 0:
        return {"强于大盘": True, "强度差": round(diff, 2), "研判": "略强于大盘"}
    else:
        return {"强于大盘": False, "强度差": round(diff, 2), "研判": "弱于大盘"}


def _check_volume_ladder(kline_data: list = None, today_volume: int = 0) -> dict:
    """条件6：用日K线成交量形态近似判断阶梯放量
    
    逻辑：
    - 取最近5日成交量
    - 若逐日递增趋势 → 阶梯放量
    - 若震荡/递减 → 非阶梯
    - 无K线数据时标记需盘中确认
    """
    if not kline_data or len(kline_data) < 5:
        return {"阶梯放量": None, "研判": "📝 需盘中人工确认（无分钟K线数据）", "得分": 0.5}

    vols = np.array([d["成交量"] for d in kline_data[-5:]])
    if len(vols) < 5:
        return {"阶梯放量": None, "研判": "📝 数据不足", "得分": 0.5}

    # 计算逐日环比
    diffs = np.diff(vols)
    up_count = np.sum(diffs > 0)
    down_count = np.sum(diffs < 0)

    if up_count >= 3 and down_count <= 1:
        return {"阶梯放量": True, "研判": "✅ 近5日成交量阶梯式放大", "得分": 1.0}
    elif up_count >= 2 and down_count <= 2:
        return {"阶梯放量": True, "研判": "⚡ 成交量整体呈上升趋势", "得分": 0.5}
    else:
        return {"阶梯放量": False, "研判": "⚠️ 成交量未呈阶梯式放大", "得分": 0}


# ── 8条件逐项打分 ─────────────────────────────────────────────

def _score_single_stock(
    stock: dict,
    index_data: dict = None,
    kline_data: list = None,
    is_tail_session: bool = False,
) -> dict:
    """对单只股票执行8条件逐项打分
    
    Parameters
    ----------
    stock : dict
        需包含: {"代码","名称","最新价","涨跌幅","换手率","量比",
                 "最高","最低","今开","流通市值"}
    index_data : dict, optional
        大盘数据 {"涨跌幅", "名称"}
    kline_data : list, optional
        日K线数据，用于条件6成交量阶梯判断
    is_tail_session : bool
        是否在尾盘操作时段（14:30-15:00）
    
    Returns
    -------
    dict {"总分", "各条件": [...], "评级", "建议"}
    """
    conditions = []
    total = 0.0
    mv_yi = _norm_mv(stock.get("流通市值", 0))

    # ── 条件1：尾盘时间 ──
    time_ok = is_tail_session
    conditions.append({
        "序号": 1, "条件": "尾盘时间(14:30后)",
        "阈值": "14:30-15:00",
        "实际值": "尾盘时段 ✅" if time_ok else "非尾盘时段 ⚠️",
        "状态": "✅" if time_ok else "⚠️",
        "得分": 1.0 if time_ok else 0,
        "备注": "" if time_ok else "预筛模式"
    })
    total += 1.0 if time_ok else 0

    # ── 条件2：涨幅3%-5% ──
    change = stock.get("涨跌幅", 0)
    if 3.0 <= change <= 5.0:
        c2_score = 1.0
        c2_status = "✅"
        c2_note = ""
    elif 2.5 <= change < 3.0:
        c2_score = 0.5
        c2_status = "⚡"
        c2_note = "涨幅略低"
    elif 5.0 < change <= 6.0:
        c2_score = 0.5
        c2_status = "⚡"
        c2_note = "涨幅略高"
    else:
        c2_score = 0
        c2_status = "❌"
        c2_note = "不在3%-5%范围"
    conditions.append({
        "序号": 2, "条件": "涨幅3%-5%",
        "阈值": "3.0%-5.0%",
        "实际值": f"{change:+.2f}%",
        "状态": c2_status,
        "得分": c2_score,
        "备注": c2_note
    })
    total += c2_score

    # ── 条件3：量比>1 ──
    vol_ratio = stock.get("量比", 0)
    if vol_ratio > 1.5:
        c3_score = 1.0
        c3_status = "✅"
        c3_note = "显著放量"
    elif vol_ratio > 1.0:
        c3_score = 1.0
        c3_status = "✅"
        c3_note = "放量"
    elif vol_ratio >= 0.8:
        c3_score = 0.5
        c3_status = "⚡"
        c3_note = "量比略低"
    else:
        c3_score = 0
        c3_status = "❌"
        c3_note = "缩量"
    conditions.append({
        "序号": 3, "条件": "量比>1",
        "阈值": ">1.0",
        "实际值": f"{vol_ratio:.2f}",
        "状态": c3_status,
        "得分": c3_score,
        "备注": c3_note
    })
    total += c3_score

    # ── 条件4：换手率5%-10% ──
    turnover = stock.get("换手率", 0)
    if 5.0 <= turnover <= 10.0:
        c4_score = 1.0
        c4_status = "✅"
        c4_note = "活跃适中"
    elif 3.0 <= turnover < 5.0:
        c4_score = 0.5
        c4_status = "⚡"
        c4_note = "换手略低"
    elif 10.0 < turnover <= 15.0:
        c4_score = 0.5
        c4_status = "⚡"
        c4_note = "换手偏高"
    else:
        c4_score = 0
        c4_status = "❌"
        c4_note = "异常换手"
    conditions.append({
        "序号": 4, "条件": "换手率5%-10%",
        "阈值": "5%-10%",
        "实际值": f"{turnover:.1f}%",
        "状态": c4_status,
        "得分": c4_score,
        "备注": c4_note
    })
    total += c4_score

    # ── 条件5：流通市值30-150亿 ──
    if 30 <= mv_yi <= 150:
        c5_score = 1.0
        c5_status = "✅"
        c5_note = "小盘弹性好"
    elif 20 <= mv_yi < 30:
        c5_score = 0.5
        c5_status = "⚡"
        c5_note = "市值偏小"
    elif 150 < mv_yi <= 200:
        c5_score = 0.5
        c5_status = "⚡"
        c5_note = "市值偏大"
    else:
        c5_score = 0
        c5_status = "❌"
        c5_note = "不在此范围"
    conditions.append({
        "序号": 5, "条件": "流通市值30-150亿",
        "阈值": "30亿-150亿",
        "实际值": f"{mv_yi:.1f}亿",
        "状态": c5_status,
        "得分": c5_score,
        "备注": c5_note
    })
    total += c5_score

    # ── 条件6：成交量阶梯放大 ──
    vol_ladder = _check_volume_ladder(kline_data, stock.get("成交量(手)", 0))
    conditions.append({
        "序号": 6, "条件": "成交量阶梯放大",
        "阈值": "逐级放大",
        "实际值": vol_ladder["研判"],
        "状态": "✅" if vol_ladder["得分"] >= 1 else ("⚠️" if vol_ladder["得分"] > 0 else "❌"),
        "得分": vol_ladder["得分"],
        "备注": ""
    })
    total += vol_ladder["得分"]

    # ── 条件7：盘中强于大盘 ──
    idx_change = index_data.get("涨跌幅", 0) if index_data else 0
    cmp = _compare_with_index(change, idx_change)
    c7_status = "✅" if cmp["强于大盘"] else "❌"
    c7_note = cmp["研判"]
    if cmp["强于大盘"] and cmp["强度差"] > 2:
        c7_score = 1.0
    elif cmp["强于大盘"]:
        c7_score = 1.0
    else:
        c7_score = 0
    conditions.append({
        "序号": 7, "条件": "盘中强于大盘",
        "阈值": f"跑赢大盘(大盘{idx_change:+.2f}%)",
        "实际值": f"{cmp['强度差']:+.2f}%",
        "状态": c7_status,
        "得分": c7_score,
        "备注": c7_note
    })
    total += c7_score

    # ── 条件8：尾盘创新高回踩 ──
    high = stock.get("最高", 0)
    price = stock.get("最新价", 0)
    open_p = stock.get("今开", 0)
    if high > 0 and price > 0:
        near_high = price >= (high * 0.98)
        above_open = price >= open_p
        if near_high and above_open:
            c8_score = 1.0
            c8_status = "✅"
            c8_note = "近新高+高于开盘（近似判断）"
        elif near_high:
            c8_score = 0.5
            c8_status = "⚡"
            c8_note = "近新高但需确认"
        else:
            c8_score = 0
            c8_status = "⚠️"
            c8_note = "距高点较远"
    else:
        c8_score = 0.5
        c8_status = "⚠️"
        c8_note = "数据不足，需盘中确认"
    conditions.append({
        "序号": 8, "条件": "尾盘高位回踩(近高未破)",
        "阈值": f"≈最高价{high:.2f}",
        "实际值": f"现价{price:.2f} (距高{(1-price/high)*100:.1f}%)" if high > 0 else "N/A",
        "状态": c8_status,
        "得分": c8_score,
        "备注": c8_note
    })
    total += c8_score

    # ── 评级 ──
    if total >= 7:
        grade = "A"
        suggestion = "🌟 高度符合一夜持股法，尾盘确认后可介入"
    elif total >= 5:
        grade = "B"
        suggestion = "✅ 基本符合条件，可轻仓试探"
    elif total >= 3:
        grade = "C"
        suggestion = "⚡ 部分符合，观望为主"
    else:
        grade = "D"
        suggestion = "❌ 不符合一夜持股法，放弃"

    return {
        "代码": stock.get("代码", ""),
        "名称": stock.get("名称", ""),
        "涨跌幅": stock.get("涨跌幅", 0),
        "量比": stock.get("量比", 0),
        "换手率": stock.get("换手率", 0),
        "流通市值": _norm_mv(stock.get("流通市值", 0)),
        "最新价": stock.get("最新价", 0),
        "总分": round(total, 1),
        "满分": 8,
        "评级": grade,
        "建议": suggestion,
        "各条件": conditions,
    }


# ── 批量综合筛选 ──────────────────────────────────────────────

def tail_market_screen(
    candidates: list,
    index_data: dict = None,
    is_tail_session: bool = False,
) -> dict:
    """对尾盘候选股执行8条件综合筛选打分
    
    Parameters
    ----------
    candidates : list[dict]
        粗筛后的候选股列表，需包含: 代码,名称,最新价,涨跌幅,换手率,量比,最高,最低,今开,流通市值
    index_data : dict, optional
        大盘指数数据 {"涨跌幅": xx, "名称": "上证指数", "最新价": xx}
    is_tail_session : bool
        是否在尾盘时段
    
    Returns
    -------
    dict {"入选标的": [...], "筛选统计": {...}, "操作建议": "...", "纪律提醒": "..."}
    """
    if not candidates:
        return {
            "入选标的": [],
            "筛选统计": {"候选数": 0, "入选数": 0, "各条件通过率": {}},
            "操作建议": "无符合条件的标的，建议空仓等待",
            "纪律提醒": "无达标标的不强做，空仓也是一种操作",
        }

    # 对每只股票打分
    scored = []
    for stock in candidates:
        # 从fetch_data获取K线数据用于条件6
        kline_data = None
        try:
            from fetch_data import get_kline
            kline_data = get_kline(stock.get("代码", ""), "daily", 10)
        except Exception:
            pass

        result = _score_single_stock(stock, index_data, kline_data, is_tail_session)
        scored.append(result)

    # 按总分降序排序
    scored.sort(key=lambda x: x["总分"], reverse=True)

    # 统计各条件通过率
    cond_names = [c["条件"] for c in scored[0]["各条件"]] if scored else []
    cond_pass = {cn: 0 for cn in cond_names}
    for r in scored:
        for c in r["各条件"]:
            if c["得分"] >= 1:
                cond_pass[c["条件"]] = cond_pass.get(c["条件"], 0) + 1

    n = len(scored)
    cond_stats = {}
    for cn, cp in cond_pass.items():
        cond_stats[cn] = f"{cp}/{n} ({cp*100//n if n else 0}%)"

    # 取前3名
    top3 = scored[:3]

    # 生成操作建议
    if top3 and top3[0]["总分"] >= 7:
        advice = f"🌟 最佳标的 {top3[0]['名称']}({top3[0]['代码']}) 得分 {top3[0]['总分']}/8，高度符合一夜持股法，尾盘确认后可介入。"
    elif top3 and top3[0]["总分"] >= 5:
        advice = f"✅ 最优标的 {top3[0]['名称']}({top3[0]['代码']}) 得分 {top3[0]['总分']}/8，基本符合，可轻仓试探。"
    elif top3 and top3[0]["总分"] >= 3:
        advice = f"⚠️ 最优标的得分仅 {top3[0]['总分']}/8，建议观望为主，不强行操作。"
    else:
        advice = "❌ 无高评分标的，建议今日空仓。记住：宁可不做，不可做错。"

    discipline = (
        "🔴 持仓时间：次日开盘30分钟内必须离场 | "
        "🔴 止损线：-3%无条件止损 | "
        "🔴 仓位上限：单票≤5%，总仓≤20% | "
        "🔴 空仓纪律：无达标标的不强做 | "
        "🟡 绿盘规则：次日若低开/绿盘，开盘即走"
    )

    return {
        "入选标的": top3,
        "全部结果": scored,
        "筛选统计": {
            "候选数": len(candidates),
            "入选数": len(top3),
            "各条件通过率": cond_stats,
            "平均分": round(np.mean([s["总分"] for s in scored]), 1) if scored else 0,
            "最高分": round(scored[0]["总分"], 1) if scored else 0,
        },
        "操作建议": advice,
        "纪律提醒": discipline,
    }


# ── 输出格式化 ────────────────────────────────────────────────

def format_tail_market_output(
    screen_result: dict,
    market_status: dict = None,
    index_data: dict = None,
    coarse_count: int = 0,
) -> str:
    """格式化尾盘选股结果为Markdown
    
    Parameters
    ----------
    screen_result : dict
        tail_market_screen() 的返回结果
    market_status : dict
        get_market_status() 的结果
    index_data : dict
        大盘指数行情
    coarse_count : int
        粗筛前原始股票数
    
    Returns
    -------
    str Markdown格式字符串
    """
    lines = []
    ms = market_status or {}

    # ── 头部 ──
    lines.append("=" * 64)
    if ms.get("is_tail_session"):
        lines.append(f"  一夜持股法 — 尾盘选股结果（🟢 尾盘操作模式）")
        lines.append(f"  当前时间：{ms.get('current_time', '')} | 距收盘还有约{ms.get('next_tail_time', '')}分钟")
    else:
        lines.append(f"  一夜持股法 — 尾盘选股结果（⚠️ 预筛模式 — 非交易时段）")
        lines.append(f"  当前时间：{ms.get('current_time', '')} | 下一个尾盘操作窗口：{ms.get('next_tail_time', '')}")
    lines.append("=" * 64)
    lines.append("")

    # ── 市场总览 ──
    lines.append("## 市场总览")
    if index_data:
        idx_name = index_data.get("名称", "上证指数")
        idx_price = index_data.get("最新价", 0)
        idx_change = index_data.get("涨跌幅", 0)
        lines.append(f"- {idx_name}：{idx_price:.2f} ({idx_change:+.2f}%)")
    stats = screen_result.get("筛选统计", {})
    lines.append(f"- 全市场粗筛范围：涨幅3%-5% + 流通市值30-150亿")
    lines.append(f"- 粗筛结果：{stats.get('候选数', 0)}只 → 精细筛选后：**{stats.get('入选数', 0)}只入选**")
    lines.append(f"- 平均得分：{stats.get('平均分', 0)}/8 | 最高得分：{stats.get('最高分', 0)}/8")
    lines.append("")

    # ── 条件通过率 ──
    cond_pass = stats.get("各条件通过率", {})
    if cond_pass:
        lines.append("### 各条件通过率")
        lines.append("| 条件 | 通过率 |")
        lines.append("|------|--------|")
        for cn, cp in cond_pass.items():
            lines.append(f"| {cn} | {cp} |")
        lines.append("")

    # ── 入围标的表格 ──
    top = screen_result.get("入选标的", [])
    if top:
        lines.append("---")
        lines.append("")
        lines.append("## 入围标的（按总分排序）")
        lines.append("")
        lines.append("| # | 代码 | 名称 | 涨幅 | 量比 | 换手率 | 流通市值(亿) | 总分 | 评级 |")
        lines.append("|---|------|------|------|------|--------|-------------|------|------|")
        for i, stock in enumerate(top, 1):
            lines.append(
                f"| {i} | {stock.get('代码', '')} | {stock.get('名称', '')} | "
                f"{stock.get('涨跌幅', 0):+.2f}% | {stock.get('量比', 0):.2f} | "
                f"{stock.get('换手率', 0):.1f}% | {stock.get('流通市值', 0):.0f} | "
                f"{stock.get('总分', 0)} | {stock.get('评级', '')} |"
            )
        lines.append("")

        # ── 每只标的详细打分 ──
        for i, stock in enumerate(top, 1):
            lines.append("---")
            lines.append("")
            lines.append(f"## 第{i}名：{stock.get('名称', '')}（{stock.get('代码', '')}）详细打分")
            lines.append("")
            lines.append("| # | 条件 | 阈值 | 实际值 | 状态 | 得分 |")
            lines.append("|---|------|------|--------|------|------|")
            for c in stock.get("各条件", []):
                lines.append(
                    f"| {c['序号']} | {c['条件']} | {c['阈值']} | {c['实际值']} | {c['状态']} | {c['得分']}/1 |"
                )
            lines.append("")
            lines.append(f"> **总分**: {stock['总分']}/8 | **评级**: {stock['评级']} | **建议**: {stock.get('建议', '')}")
            lines.append("")
    else:
        lines.append("---")
        lines.append("")
        lines.append("## ⚠️ 无符合条件标的")
        lines.append("")
        lines.append("当前全市场无满足一夜持股法8条件的标的。")
        lines.append("")
        lines.append("> 空仓也是一种操作。今日建议观望，等待下一个尾盘窗口。")
        lines.append("")

    # ── 强制操作纪律 ──
    lines.append("---")
    lines.append("")
    lines.append("## ⚠️ 强制操作纪律（不合规必亏）")
    lines.append("")
    lines.append("| 纪律 | 要求 | 违反后果 |")
    lines.append("|------|------|----------|")
    lines.append("| 🔴 持仓时间 | **次日开盘30分钟内必须离场** | 隔夜变短线，短线变套牢 |")
    lines.append("| 🔴 止损线 | **-3%无条件止损** | 等待反弹变深套 |")
    lines.append("| 🔴 仓位上限 | 单票≤5%，总仓≤20% | 重仓单票风险极大 |")
    lines.append("| 🔴 空仓纪律 | **无达标标的不强做** | 强行操作往往亏损 |")
    lines.append("| 🟡 绿盘规则 | 次日若低开/绿盘，开盘即走 | 期待翻红大概率落空 |")
    lines.append("")

    # ── 明日操作计划 ──
    lines.append("---")
    lines.append("")
    lines.append("## 次日操作计划（若决定介入）")
    lines.append("")
    lines.append("1. **开盘前**：确认标的开盘情况，检查是否有重大公告")
    lines.append("2. **09:30-09:35**：若红盘且成交量正常 → 持仓至09:55左右择机离场")
    lines.append("3. **09:30-09:35**：若绿盘或低开 → 立即离场，止损")
    lines.append("4. **10:00**：无论盈亏，清仓完毕")
    lines.append("")

    # ── 免责声明 ──
    lines.append("---")
    lines.append("")
    lines.append("*免责声明：以上为AI模型基于公开数据的量化筛选结果，不构成投资建议。一夜持股为高风险短线策略，请勿重仓。股市有风险，投资需谨慎。*")

    return "\n".join(lines)


# ── 便捷入口：一键尾盘选股 ────────────────────────────────────

def run_tail_market_selection(verbose: bool = True) -> str:
    """一键执行尾盘选股全流程（供Skill直接调用）
    
    从 fetch_data 获取全市场快照、大盘指数、市场状态，
    执行粗筛+精细筛选，返回格式化的Markdown结果。
    """
    from fetch_data import get_market_snapshot, get_index_quote, get_market_status

    # 0. 时间检查
    ms = get_market_status()
    is_tail = ms.get("is_tail_session", False)

    # 1. 获取大盘指数
    try:
        idx_data = get_index_quote("sh000001")
    except Exception:
        idx_data = {"名称": "上证指数", "最新价": 0, "涨跌幅": 0}

    # 2. 全市场快照
    if verbose:
        print("📡 正在获取全市场行情快照...")
    snap = get_market_snapshot(verbose=verbose)
    total_stocks = len(snap)

    # 3. 粗筛：涨幅3-5% + 流通市值30-150亿
    coarse = [
        s for s in snap
        if 3.0 <= s.get("涨跌幅", 0) <= 5.0
        and 30 <= _norm_mv(s.get("流通市值", 0)) <= 150
    ]
    if verbose:
        print(f"🔍 粗筛结果：{len(coarse)}只（涨幅3-5% + 流通市值30-150亿），来自{total_stocks}只全市场")

    # 4. 精细筛选
    if verbose:
        print("📊 正在执行8条件精细筛选...")
    result = tail_market_screen(coarse, idx_data, is_tail)

    # 5. 格式化输出
    output = format_tail_market_output(result, ms, idx_data, total_stocks)
    return output


# ── 测试入口 ──────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    sys.path.insert(0, ".")
    
    output = run_tail_market_selection(verbose=True)
    print(output)
