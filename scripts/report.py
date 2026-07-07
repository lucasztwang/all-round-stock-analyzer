#!/usr/bin/env python3
"""
报告生成模块 — 汇总所有分析结果，生成结构化 Markdown 报告
"""

import os
from datetime import datetime

OUTPUT_DIR = "/workspace"

# ── 报告模板 ──────────────────────────────────────────────────
REPORT_TEMPLATE = """# 📊 {stock_name}（{stock_code}）综合分析报告

> 生成时间：{report_time}
> 最新价：**{price}** 元 | 涨跌幅：**{change_pct}%**

---

## 一、行情概览

| 指标 | 数值 | 指标 | 数值 |
|------|------|------|------|
| 最新价 | {price} 元 | 今开 | {open_price} 元 |
| 最高 | {high} 元 | 最低 | {low} 元 |
| 涨跌额 | {change_amount} 元 | 换手率 | {turnover}% |
| 成交量 | {volume} 手 | 成交额 | {amount} 亿 |
| 总市值 | {total_mv} 亿 | 流通市值 | {circulate_mv} 亿 |
| 市盈率(动) | {pe} | 市净率 | {pb} |

---

## 二、技术分析

### 趋势判断
{trade_signal}

### {trend_analysis}

### 支撑 / 压力位
{support_resistance}

### 买卖信号
{buy_sell_signals}

### K 线图
![K线图]({kline_path})

### MACD 指标
![MACD]({macd_path})

### RSI + KDJ
![RSI KDJ]({rsi_kdj_path})

---

## 三、缠论分析

{chan_analysis}

### 缠论标注图
![缠论]({chan_path})

---

## 四、量价分析

{volume_analysis}

---

## 五、基本盘分析

### 估值分析
{valuation}

### 同行对比
{peer_comparison}

---

## 六、行业板块分析

{sector_analysis}

---

## 七、产业逻辑分析

**产业逻辑评分**：{industry_score}

### 公司画像

{industry_chain}

### 动态跟踪与研究方向

{industry_track}

---

## 八、买卖点研判

**综合信号**：{buy_sell_signal}

{buy_sell_advice}

{buy_sell_details}

---

## 九、选股框架（老刘四步选股法）

**核心逻辑**：排雷 → 估值 → 精选 → 量价

**综合评分**：{selection_score} / {selection_grade}

{selection_advice}

### 四步详情

{selection_details}

![选股雷达]({selection_chart_path})

---

## 十、止盈止损策略

**投资者类型**：{investor_type}

**推荐方法**：{recommended_method}

**综合建议**：{stop_profit_overall}

{stop_profit_methods}

### 心理提示

{psychology_reminders}

---

## 十一、仓位管理（三层仓位法则）

**当前阶段**：{position_stage}

**建议总仓位**：{position_total}

**操作建议**：{position_overall}

**核心理念**：{position_risk}

### 三层仓位分配

{position_layers}

### 升级条件

{position_upgrade}

---

## 十二、综合评分

| 维度 | 评分/结论 |
|------|----------|
| 技术面 | {tech_conclusion} |
| 缠论 | {chan_conclusion} |
| 基本盘 | {fundamental_conclusion} |
| 板块 | {sector_conclusion} |

### 综合评价

{overall_recommendation}

---

*免责声明：本报告由AI自动生成，仅供参考，不构成任何投资建议。投资有风险，入市需谨慎。*
"""


def generate_report(
    code: str,
    quote: dict,
    technical_data: dict,
    chan_data: dict,
    fundamental_data: dict,
    sector_data: dict,
    chart_paths: dict,
    selection_data: dict = None,
    stop_profit_data: dict = None,
    position_data: dict = None,
    buy_sell_data: dict = None,
    industry_data: dict = None,
    investor_type: str = "综合",
    cost_price: float = None,
) -> str:
    """
    生成股票分析报告（深度报告）
    返回报告文件路径
    """

    # ── 行情摘要 ──────────────────────────────────────────────
    stock_name = quote.get("名称", code)
    price = quote.get("最新价", 0)
    change_pct = quote.get("涨跌幅", 0)
    change_amount = quote.get("涨跌额", 0)
    high = quote.get("最高", 0)
    low = quote.get("最低", 0)
    open_price = quote.get("今开", 0)
    turnover = round(quote.get("换手率", 0), 2)
    volume = quote.get("成交量(手)", 0)
    amount = round(quote.get("成交额(元)", 0) / 10000, 2)  # 腾讯成交额字段为万元
    total_mv = round(quote.get("总市值", 0), 2) if quote.get("总市值") else 0
    circulate_mv = round(quote.get("流通市值", 0), 2) if quote.get("流通市值") else 0
    pe = quote.get("市盈率(动)", 0)
    pb = quote.get("市净率", 0)

    # ── 技术分析汇总 ──────────────────────────────────────────
    signals = technical_data.get("综合信号", {})
    trend = technical_data.get("趋势判断", {})
    sr = technical_data.get("支撑压力", {})

    trade_signal = f"**{signals.get('综合建议', '观望')}**"

    trend_text = ""
    if trend:
        trend_text = f"**趋势**: {trend.get('趋势', '震荡')} | **评分**: {trend.get('趋势评分', 50)}/100"

    sr_text = ""
    if sr:
        supports = sr.get("支撑位", [])
        resistances = sr.get("压力位", [])
        sr_parts = []
        if supports:
            sr_parts.append("**支撑**: " + " | ".join(
                f"{s.get('点位', 0)} ({s.get('类型', '')})" for s in supports[:3]))
        if resistances:
            sr_parts.append("**压力**: " + " | ".join(
                f"{r.get('点位', 0)} ({r.get('类型', '')})" for r in resistances[:3]))
        sr_text = "\n".join(sr_parts)

    buy_signals = signals.get("买入信号", [])
    sell_signals = signals.get("卖出信号", [])
    bs_text = ""
    if buy_signals:
        bs_text += "**🟢 买入信号**:\n" + "\n".join(f"- {s}" for s in buy_signals[:5]) + "\n"
    if sell_signals:
        bs_text += "**🔴 卖出信号**:\n" + "\n".join(f"- {s}" for s in sell_signals[:5])
    if not bs_text:
        bs_text = "暂无明确买卖信号"

    # ── 缠论分析 ──────────────────────────────────────────────
    chan_trend = chan_data.get("缠论趋势", "盘整")
    chan_bi_count = chan_data.get("笔数量", 0)
    chan_zs_count = chan_data.get("中枢数量", 0)
    chan_buy = chan_data.get("买点", [])
    chan_sell = chan_data.get("卖点", [])
    last_zs = chan_data.get("最近中枢")

    chan_text = f"**趋势**: {chan_trend}\n\n"
    chan_text += f"- 已识别 **{chan_bi_count}** 笔、**{chan_zs_count}** 个中枢\n"

    if last_zs:
        chan_text += f"- 最近中枢: {last_zs.get('中枢区间', 'N/A')}（中轴: {last_zs.get('中枢中轴', 'N/A')}）\n"

    if chan_buy:
        chan_text += "\n**买点**:\n"
        for bp in chan_buy[:3]:
            chan_text += f"- [{bp.get('类型', '')}] {bp.get('日期', '')} @ {bp.get('价格', '')} | {bp.get('说明', '')}\n"

    if chan_sell:
        chan_text += "\n**卖点**:\n"
        for sp in chan_sell[:3]:
            chan_text += f"- [{sp.get('类型', '')}] {sp.get('日期', '')} @ {sp.get('价格', '')} | {sp.get('说明', '')}\n"

    # ── 量价分析 ──────────────────────────────────────────────
    vol_data = technical_data.get("量价分析", {})
    vol_signals = vol_data.get("信号", [])
    vol_text = "最近信号:\n"
    for sig in vol_signals[-5:]:
        if sig and sig != "—":
            vol_text += f"- {sig}\n"

    # ── 估值分析 ──────────────────────────────────────────────
    val_data = fundamental_data.get("估值", {})
    val_pe_eval = val_data.get("PE评价", "N/A")
    val_pb_eval = val_data.get("PB评价", "N/A")
    valuation_text = f"- PE: {pe} → **{val_pe_eval}**\n- PB: {pb} → **{val_pb_eval}**\n"

    pe_high = val_data.get("60日高对应PE", 0)
    pe_low = val_data.get("60日低对应PE", 0)
    if pe_high and pe_low:
        valuation_text += f"- 60日估值区间: PE {pe_low} ~ {pe_high}\n"

    # ── 同行对比 ──────────────────────────────────────────────
    peer_data = fundamental_data.get("同行对比", {})
    if isinstance(peer_data, dict) and "板块平均PE" in peer_data:
        peer_text = (f"- 板块平均PE: {peer_data.get('板块平均PE', 'N/A')}  |  中位数: {peer_data.get('板块PE中位数', 'N/A')}\n"
                     f"- PE排名: {peer_data.get('PE排名', 'N/A')}  |  {peer_data.get('PE高于', 'N/A')}\n"
                     f"- 评价: {peer_data.get('估值评价', 'N/A')}")
    else:
        peer_text = str(peer_data.get("同行对比", "暂无数据"))

    # ── 板块分析 ──────────────────────────────────────────────
    stock_sector = sector_data.get("个股在板块", {})
    sector_text = ""
    if isinstance(stock_sector, dict) and "相对强度" in stock_sector:
        sector_text = (
            f"- 涨幅排名: {stock_sector.get('涨幅排名', 'N/A')} | "
            f"市值排名: {stock_sector.get('市值排名', 'N/A')}\n"
            f"- 相对强度: {stock_sector.get('相对强度', 0):+.2f}% → {stock_sector.get('相对评价', 'N/A')}"
        )

    rotation = sector_data.get("板块轮动", {})
    if rotation and isinstance(rotation, dict):
        sector_text += f"\n\n**市场风格**: {rotation.get('市场风格', 'N/A')}"
        top_leads = rotation.get("领涨板块", [])
        if top_leads:
            sector_text += "\n\n领涨板块: " + ", ".join(s["名称"] for s in top_leads[:5])

    # ── 综合结论 ──────────────────────────────────────────────
    fund_score = fundamental_data.get("基本盘", {})
    score = fund_score.get("基本盘评分", 50)
    grade = fund_score.get("评级", "C")

    tech_conclusion = f"{signals.get('综合建议', '观望')} ({trend.get('趋势', '震荡')})"
    chan_conclusion = chan_trend
    fund_conclusion = f"{score}分 / {grade}级"
    sector_conclusion = stock_sector.get("相对评价", "N/A") if isinstance(stock_sector, dict) else "N/A"

    # 综合建议
    if score >= 70 and signals.get("综合建议") in ("偏多", "谨慎偏多"):
        overall = "✅ 基本面与技术面共振偏多，可考虑逢低布局，注意止损。"
    elif score < 40 and signals.get("综合建议") in ("偏空", "谨慎偏空"):
        overall = "⚠️ 基本面与技术面均偏弱，建议观望或减仓，等待右侧信号。"
    elif score >= 60:
        overall = "📌 基本面尚可但技术面不确定，可轻仓试探，严格止损。"
    elif signals.get("综合建议") == "偏多":
        overall = "📌 技术面偏多但基本面一般，短线为主，快进快出。"
    else:
        overall = "⏸️ 信号不明确，建议观望等待更清晰的入场时机。"

    # ── 选股框架 ─────────────────────────────────────────────
    selection_score = "N/A"
    selection_grade = "N/A"
    selection_advice = "未启用选股框架分析"
    selection_details = ""
    selection_chart_path = ""

    if selection_data:
        selection_score = selection_data.get("选股总分", 0)
        selection_grade = selection_data.get("选股评级", "N/A")
        selection_advice = selection_data.get("综合建议", "")
        steps = selection_data.get("四步结果", [])
        details_parts = []
        for s in steps:
            details_parts.append(f"**{s.get('步骤', '')}**  得分：{s.get('得分', 0)}/100")
            if "是否通过" in s:
                details_parts.append(f"- 初筛通过：{'是' if s['是否通过'] else '否'}")
            if "隐含ROE(%)" in s and s["隐含ROE(%)"] is not None:
                details_parts.append(f"- 隐含ROE：{s['隐含ROE(%)']:.2f}%")
            if "PEG" in s and s["PEG"] is not None:
                details_parts.append(f"- PEG：{s['PEG']:.2f}")
            if "20日涨幅" in s:
                details_parts.append(f"- 20日涨幅：{s['20日涨幅']:.2f}%")
            if "相对强度" in s:
                details_parts.append(f"- 相对板块强度：{s['相对强度']:.2f}%")
            if "量价信号" in s:
                details_parts.append(f"- 量价信号：{'; '.join(s['量价信号'])}")
            # 检查项
            checks = s.get("排雷检查") or s.get("检查项")
            if checks and isinstance(checks, dict):
                for k, v in checks.items():
                    details_parts.append(f"- {k}：{v}")
            details_parts.append("")

        # 进阶信号
        adv = selection_data.get("进阶信号", {})
        if adv:
            details_parts.append("### 进阶信号（趋势动能 + 小市值/财报验证）")
            ma = adv.get("日线MA系统", {})
            weekly = adv.get("周线MACD系统", {})
            fv = adv.get("小市值/财报验证", {})
            details_parts.append(f"- **日线MA系统**：{ma.get('信号', 'N/A')} | 5/10日线支撑：{'有效' if ma.get('支撑有效') else '无效'} | MA5:{ma.get('当前MA5')} MA10:{ma.get('当前MA10')} MA20:{ma.get('当前MA20')}")
            details_parts.append(f"- **周线MACD系统**：{weekly.get('状态', 'N/A')} | 零上金叉：{weekly.get('零上金叉')} | 死叉：{weekly.get('死叉')} | 红柱第{weekly.get('红柱第几根')}根")
            details_parts.append(f"- **小市值/财报验证**：综合得分 {fv.get('综合得分', 'N/A')} | 小市值评分 {fv.get('小市值评分', 'N/A')} | 估值弹性评分 {fv.get('估值弹性评分', 'N/A')}")
            if "检查项" in fv and isinstance(fv["检查项"], dict):
                for k, v in fv["检查项"].items():
                    details_parts.append(f"  - {k}：{v}")
            details_parts.append("")

        # 仓位建议
        position = selection_data.get("仓位建议", {})
        if position:
            details_parts.append(f"### 分阶段仓位建议")
            details_parts.append(f"- **阶段**：{position.get('阶段', 'N/A')}")
            details_parts.append(f"- **建议仓位**：{position.get('建议仓位', 'N/A')}")
            details_parts.append(f"- **理由**：{position.get('理由', 'N/A')}")
            details_parts.append("")

        selection_details = "\n".join(details_parts)
        selection_chart_path = chart_paths.get("selection", "")

    # ── 止盈止损策略 ──────────────────────────────────────────
    stop_profit_overall = "未启用止盈止损分析"
    stop_profit_methods = ""
    psychology_reminders_text = ""
    recommended_method = "N/A"

    if stop_profit_data:
        stop_profit_overall = stop_profit_data.get("综合建议", "")
        recommend = stop_profit_data.get("推荐方法", {})
        recommended_method = f"{recommend.get('推荐方法', 'N/A')}（{recommend.get('理由', '')}）"

        methods = stop_profit_data.get("五种方法", [])
        method_parts = []
        for m in methods:
            method_parts.append(f"#### {m.get('方法', '')}")
            method_parts.append(f"- 当前状态：{m.get('建议', '')}")
            if "目标清单" in m:
                targets = " | ".join(
                    f"{t['涨幅目标']}→{t['目标价']}({'已触发' if t['是否触发'] else '未触发'})"
                    for t in m["目标清单"]
                )
                method_parts.append(f"- 目标：{targets}")
            if "移动止盈位" in m:
                method_parts.append(f"- 止盈位：{m['移动止盈位']}，当前价：{m['当前价']}")
            if "买入PE" in m:
                method_parts.append(f"- 买入PE：{m['买入PE']}，当前PE：{m['当前PE']}，扩张：{m.get('PE扩张幅度')}%")
            if "触发信号" in m:
                sigs = m["触发信号"]
                method_parts.append(f"- 触发信号：{'、'.join(sigs) if sigs else '无'}")
            if "分批计划" in m:
                batches = " | ".join(
                    f"{b['涨幅']}卖{b['卖出比例']}({'已触发' if b['是否触发'] else '未触发'})"
                    for b in m["分批计划"]
                )
                method_parts.append(f"- 分批：{batches}")
            method_parts.append(f"- 适合：{m.get('适合人群', '')}")
            method_parts.append("")
        stop_profit_methods = "\n".join(method_parts)

        # 心理提示
        psych = stop_profit_data.get("心理提示", {})
        if psych:
            psychology_reminders_text = (
                f"**{psych.get('核心原则', '')}**\n\n"
                f"- {psych.get('损失厌恶', '')}\n"
            )
            for item in psych.get("常见误区", []):
                psychology_reminders_text += (
                    f"- ❌ **{item['误区']}**：{item['真相']} → ✅ {item['正确做法']}\n"
                )
            psychology_reminders_text += f"\n>{psych.get('心法', '')}"

    # ── 仓位管理（三层仓位法则） ──────────────────────────────
    position_stage = "未启用"
    position_total = "N/A"
    position_layers = ""
    position_upgrade = ""
    position_risk = ""
    position_overall = "未启用仓位管理分析"
    if position_data:
        position_stage = position_data.get("当前阶段", "N/A")
        position_total = position_data.get("建议总仓位", "N/A")
        position_overall = position_data.get("操作建议", "")
        position_risk = position_data.get("核心理念", "")
        layers_text = []
        for layer, info in position_data.get("仓位分配", {}).items():
            layers_text.append(f"- **{layer}**：{info['比例']} | {info.get('建议', '')} | 条件：{info.get('条件', '')}")
        position_layers = "\n".join(layers_text)
        upgrade = position_data.get("升级条件", {})
        if upgrade:
            parts = []
            for k, v in upgrade.items():
                parts.append(f"- {k}：{v}")
            position_upgrade = "\n".join(parts)

    # ── 买卖点研判 ─────────────────────────────────────────────
    buy_sell_signal = "未启用"
    buy_sell_advice = ""
    buy_sell_details = ""
    if buy_sell_data:
        buy_sell_signal = buy_sell_data.get("综合信号", "N/A")
        buy_sell_advice = buy_sell_data.get("综合建议", "")
        resonance = buy_sell_data.get("共振分析", {})
        divergence = buy_sell_data.get("背离检测", {})
        breakout = buy_sell_data.get("量价突破", {})
        timeframe = buy_sell_data.get("多周期", {})
        parts = [
            f"**多指标共振**：{resonance.get('信号', 'N/A')}（买入{resonance.get('买入得分',0)} 卖出{resonance.get('卖出得分',0)}）",
            f"**背离检测**：{divergence.get('背离', 'N/A')} | {divergence.get('说明', '')}",
            f"**量价突破**：{breakout.get('状态', 'N/A')}（{'放量' if breakout.get('放量') else '未放量'}，{'创新高' if breakout.get('创新高') else '未创新高'}）",
            f"**多周期共振**：{timeframe.get('共振信号', 'N/A')}（日线{timeframe.get('日线趋势', 'N/A')} / 周线{timeframe.get('周线趋势', 'N/A')}）",
        ]
        buy_sell_details = "\n".join(parts)

    # ── 产业逻辑 ─────────────────────────────────────────────
    industry_score = "N/A"
    industry_review = "未启用产业逻辑分析"
    industry_chain = ""
    industry_track = ""
    if industry_data:
        industry_score = industry_data.get("产业逻辑评分", "N/A")
        industry_review = industry_data.get("综合产业评估", "")
        chain_text = []
        for k in ["公司规模", "盈利评价", "成长评价"]:
            if k in industry_data:
                chain_text.append(f"- **{k}**：{industry_data[k]}")
        if "核心概念" in industry_data and industry_data["核心概念"]:
            chain_text.append(f"- **概念标签**：{'、'.join(industry_data['核心概念'])}")
        if "主营构成" in industry_data and industry_data["主营构成"]:
            biz_list = [f"{b.get('业务','')}({b.get('营收占比','')})" for b in industry_data["主营构成"][:3]]
            chain_text.append(f"- **主营构成**：{' / '.join(biz_list)}")
        industry_chain = "\n".join(chain_text)
        track = industry_data.get("动态跟踪", "")
        research = industry_data.get("研究建议", [])
        if research:
            track += "\n\n**研究建议**：\n" + "\n".join(research)
        industry_track = track

    # ── 仓位管理（三层仓位法则） ──────────────────────────────
    position_stage = "N/A"
    position_total = "N/A"
    position_layers = ""
    position_upgrade = ""
    position_risk = ""

    if position_data:
        position_overall = position_data.get("操作建议", "")
        position_stage = position_data.get("当前阶段", "")
        position_total = position_data.get("建议总仓位", "")
        position_risk = position_data.get("核心理念", "")

        layers = position_data.get("仓位分配", {})
        layer_parts = []
        for layer_name, layer_info in layers.items():
            layer_parts.append(f"**{layer_name}**：{layer_info.get('比例', '0%')}")
            layer_parts.append(f"- 入场条件：{layer_info.get('条件', '')}")
            layer_parts.append(f"- 建议：{layer_info.get('建议', '')}")
            layer_parts.append("")
        position_layers = "\n".join(layer_parts)

        upgrade = position_data.get("升级条件", {})
        if upgrade:
            position_upgrade = "\n".join([f"- {k}：{v}" for k, v in upgrade.items()])

    # ── 填充模板 ──────────────────────────────────────────────
    report = REPORT_TEMPLATE.format(
        stock_name=stock_name,
        stock_code=code,
        report_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        price=price,
        change_pct=f"{change_pct:+.2f}",
        open_price=open_price,
        high=high,
        low=low,
        change_amount=f"{change_amount:+.2f}",
        turnover=turnover,
        volume=f"{volume:,}" if volume else "N/A",
        amount=amount,
        total_mv=total_mv,
        circulate_mv=circulate_mv,
        pe=f"{pe:.2f}" if pe else "N/A",
        pb=f"{pb:.2f}" if pb else "N/A",
        trade_signal=trade_signal,
        trend_analysis=trend_text,
        support_resistance=sr_text,
        buy_sell_signals=bs_text,
        kline_path=chart_paths.get("kline", ""),
        macd_path=chart_paths.get("macd", ""),
        rsi_kdj_path=chart_paths.get("rsi_kdj", ""),
        chan_analysis=chan_text,
        chan_path=chart_paths.get("chan", ""),
        volume_analysis=vol_text,
        valuation=valuation_text,
        peer_comparison=peer_text,
        sector_analysis=sector_text,
        tech_conclusion=tech_conclusion,
        chan_conclusion=chan_conclusion,
        fundamental_conclusion=fund_conclusion,
        sector_conclusion=sector_conclusion,
        selection_score=selection_score,
        selection_grade=selection_grade,
        selection_advice=selection_advice,
        selection_details=selection_details,
        selection_chart_path=selection_chart_path,
        investor_type=investor_type,
        recommended_method=recommended_method,
        stop_profit_overall=stop_profit_overall,
        stop_profit_methods=stop_profit_methods,
        psychology_reminders=psychology_reminders_text,
        position_stage=position_stage,
        position_total=position_total,
        position_layers=position_layers,
        position_upgrade=position_upgrade,
        position_risk=position_risk,
        position_overall=position_overall,
        buy_sell_signal=buy_sell_signal,
        buy_sell_advice=buy_sell_advice,
        buy_sell_details=buy_sell_details,
        industry_score=industry_score,
        industry_review=industry_review,
        industry_chain=industry_chain,
        industry_track=industry_track,
        overall_recommendation=overall,
    )

    # ── 保存 ──────────────────────────────────────────────────
    filename = f"{code}_{stock_name}_分析报告_{datetime.now().strftime('%Y%m%d_%H%M')}.md"
    filepath = os.path.join(OUTPUT_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(report)

    return filepath
