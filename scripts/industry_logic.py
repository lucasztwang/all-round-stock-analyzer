#!/usr/bin/env python3
"""
产业逻辑分析模块
生成 F10 财报/公告/研报的获取URL，解析关键数据，输出产业逻辑分析
"""

import re
import json
from typing import Optional
from urllib.request import Request, urlopen
from urllib.parse import quote

# ── URL 生成 ──────────────────────────────────────────────────

def f10_urls(code: str) -> dict:
    """生成东方财富 F10 关键页面 URL"""
    ncode = re.sub(r'[^0-9]', '', code).zfill(6)
    market = "SH" if ncode.startswith(("6", "9")) else "SZ"
    em_code = f"{market}{ncode}"

    return {
        "公司概况": f"https://emweb.securities.eastmoney.com/pc_hsf10/pages/index.html?code={em_code}&type=web",
        "财务摘要": f"https://emweb.securities.eastmoney.com/PC_HSF10/FinanceSummary/Index?type=web&code={em_code}",
        "主营构成": f"https://emweb.securities.eastmoney.com/PC_HSF10/BusinessAnalysis/Index?type=web&code={em_code}",
        "十大股东": f"https://emweb.securities.eastmoney.com/PC_HSF10/ShareholderResearch/Index?type=web&code={em_code}",
        "最新公告": f"https://emweb.securities.eastmoney.com/PC_HSF10/Announcement/Index?type=web&code={em_code}",
        "研报": f"https://emweb.securities.eastmoney.com/PC_HSF10/StockResearch/Index?type=web&code={em_code}",
        "核心题材": f"https://emweb.securities.eastmoney.com/PC_HSF10/CoreConception/Index?type=web&code={em_code}",
        "财务分析": f"https://emweb.securities.eastmoney.com/PC_HSF10/FinanceAnalysis/Index?type=web&code={em_code}",
    }


def search_urls(code: str, name: str) -> dict:
    """生成搜索用的 URL（供 WebSearch 工具使用）"""
    return {
        "最新公告": f"{name} {code} 最新公告 site:data.eastmoney.com 2026",
        "深度研报": f"{name} {code} 研报 深度报告 site:eastmoney.com 2026",
        "产业链分析": f"{name} 产业链 上下游 业务分析 2026",
        "行业景气度": f"{name} 行业景气度 订单 产能 2026",
        "财报解读": f"{name} {code} 财报 营收 净利润 毛利率 2026",
    }


# ── 数据解析 ──────────────────────────────────────────────────

def parse_financial_summary(html_text: str) -> dict:
    """从东方财富F10财务摘要页面提取关键财务指标"""
    result = {}

    # 提取 JSON 数据块
    patterns = {
        "营业总收入": r'"TOTALOPERATEREVE"\s*:\s*([\d.]+)',
        "净利润": r'"PARENTNETPROFIT"\s*:\s*([\d.]+)',
        "ROE_加权": r'"WEIGHTAVG_ROE"\s*:\s*([\d.]+)',
        "每股收益": r'"BASICEPS"\s*:\s*([\d.]+)',
        "营收增速": r'"TOTALOPERATEREVETZ"\s*:\s*([\-\d.]+)',
        "净利增速": r'"PARENTNETPROFITTZ"\s*:\s*([\-\d.]+)',
        "毛利率": r'"XSMLL"\s*:\s*([\d.]+)',
        "净利率": r'"XSJLL"\s*:\s*([\d.]+)',
    }

    for key, pattern in patterns.items():
        match = re.search(pattern, html_text)
        if match:
            val = float(match.group(1))
            if key == "营收增速" or key == "净利增速":
                result[key] = round(val, 2)
            else:
                result[key] = val

    return result


def parse_business_composition(html_text: str) -> list:
    """从主营构成页面提取业务板块"""
    # 提取表格数据
    businesses = []
    rows = re.findall(r'<tr[^>]*>.*?</tr>', html_text, re.DOTALL)
    for row in rows:
        tds = re.findall(r'<td[^>]*>(.*?)</td>', row)
        if tds and len(tds) >= 3:
            name = re.sub(r'<[^>]+>', '', tds[0]).strip()
            revenue = re.sub(r'<[^>]+>', '', tds[1]).strip()
            if name and revenue and name not in ['主营业务', '项目', '—', '合计']:
                try:
                    businesses.append({"业务": name, "营收占比": revenue})
                except:
                    pass
    return businesses[:5]


def parse_core_concept(html_text: str) -> list:
    """从核心题材页面提取概念标签"""
    concepts = re.findall(r'"board_name"\s*:\s*"([^"]+)"', html_text)
    return concepts[:6]


# ── 产业逻辑分析 ──────────────────────────────────────────────

def analyze_industry_logic(quote: dict, kline_data: list,
                           financial_html: str = "",
                           announcement_text: str = "",
                           research_text: str = "") -> dict:
    """
    综合产业逻辑分析
    - 财务数据（从F10页面提取）
    - 业务构成与核心竞争力
    - 产业链定位
    - 公告/研报摘要
    """
    name = quote.get("名称", "")
    pe = quote.get("市盈率(动)", 0)
    pb = quote.get("市净率", 0)
    total_mv = quote.get("总市值", 0) or 0
    change_pct = quote.get("涨跌幅", 0)

    # 从K线算涨幅
    n = len(kline_data)
    ret_60 = 0
    if n >= 60:
        closes = [d["收盘"] for d in kline_data]
        ret_60 = (closes[-1] - closes[-60]) / closes[-60] * 100

    # 财务数据解析
    fin = parse_financial_summary(financial_html) if financial_html else {}
    biz = parse_business_composition(financial_html) if financial_html else []
    concepts = parse_core_concept(financial_html) if financial_html else []

    # 规模判断（腾讯API市值字段已为亿元单位）
    mv_yi = total_mv if total_mv else 0
    if mv_yi < 50:
        scale = "小盘（<50亿）"
        scale_note = "小盘股弹性大但波动也大，一笔订单可改写全年业绩"
    elif mv_yi < 200:
        scale = "中盘（50-200亿）"
        scale_note = "中盘股兼顾弹性与稳定性"
    elif mv_yi < 500:
        scale = "中大盘（200-500亿）"
        scale_note = "中大盘股有一定流动性溢价"
    else:
        scale = "大盘（>500亿）"
        scale_note = "大盘股市值锚定效应强，需催化力度大才能拉动"

    # 盈利评估
    roe = fin.get("ROE_加权", 0)
    gross_margin = fin.get("毛利率", 0)
    net_margin = fin.get("净利率", 0)

    profitability = ""
    if roe >= 20:
        profitability = f"✅ ROE {roe}% — 优秀，盈利能力突出"
    elif roe >= 10:
        profitability = f"📌 ROE {roe}% — 良好"
    elif roe > 0:
        profitability = f"⚠️ ROE {roe}% — 一般"
    else:
        profitability = "⚠️ ROE 不足 — 需关注盈利模式可持续性"

    # 成长评估
    rev_growth = fin.get("营收增速", 0)
    profit_growth = fin.get("净利增速", 0)

    growth_eval = ""
    if rev_growth > 20:
        growth_eval = f"✅ 营收增速 {rev_growth}% — 高成长"
    elif rev_growth > 10:
        growth_eval = f"📌 营收增速 {rev_growth}% — 稳健增长"
    elif rev_growth > 0:
        growth_eval = f"📌 营收增速 {rev_growth}% — 缓慢增长"
    elif rev_growth < 0:
        growth_eval = f"⚠️ 营收增速 {rev_growth}% — 负增长，警惕"
    else:
        growth_eval = "📝 营收增速数据缺失"

    # 产业链定位（基于概念标签）
    chain_note = ""
    if concepts:
        chain_note = f"**概念标签**: {'、'.join(concepts)}\n\n"
    chain_note += "**分析建议**: 请基于概念标签判断公司所处的产业链位置（上游/中游/下游），分析其议价能力、竞争壁垒、客户集中度。"

    # 公告/研报摘要
    news_section = ""
    if announcement_text:
        news_section += f"\n**最新动态**: {announcement_text[:300]}..."
    if research_text:
        news_section += f"\n\n**研报观点**: {research_text[:300]}..."

    # 综合产业逻辑评分
    logic_score = 50
    if roe >= 15:
        logic_score += 15
    if rev_growth > 20:
        logic_score += 10
    if gross_margin > 0 and gross_margin > 30:
        logic_score += 10
    if concepts and len(concepts) >= 3:
        logic_score += 5  # 概念丰富度
    if ret_60 > 20:
        logic_score += 10

    logic_score = min(100, logic_score)

    return {
        "产业逻辑评分": logic_score,
        "公司规模": scale,
        "规模分析": scale_note,
        "盈利评价": profitability,
        "成长评价": growth_eval,
        "产业链定位": chain_note,
        "核心概念": concepts,
        "主营构成": biz,
        "财务指标": fin,
        "动态跟踪": news_section if news_section else "📝 未获取到最新公告/研报（建议手动搜索）",
        "研究建议": [
            "1. 查看近3年营收和净利润趋势是否稳定/增长",
            "2. 关注毛利率是否稳定或提升（毛利率下滑=竞争加剧）",
            "3. 检查在手订单/合同负债是否增长（预收款增加=需求旺盛）",
            "4. 关注公司是否加大资本开支/建厂（扩张信号）",
            "5. 对比同行业公司的估值和增速，判断相对性价比",
        ],
    }


# ── 财报模板 ──────────────────────────────────────────────────
def generate_financial_template(name: str, code: str) -> str:
    """生成财报分析模板，引导 agent 使用 WebFetch 获取数据"""
    urls = f10_urls(code)
    search = search_urls(code, name)

    return f"""
## 财报数据获取指引

### 1. 直接访问 F10 页面
- 财务摘要：{urls['财务摘要']}
- 主营构成：{urls['主营构成']}
- 核心题材：{urls['核心题材']}

### 2. 搜索最新公告/研报
- {search['最新公告']}
- {search['深度研报']}

### 3. 关键验证项
- 近3年营收趋势：稳定增长/波动/下滑？
- 毛利率/净利率：稳定/提升/下降？
- 经营现金流：为正/为负？趋势？
- 合同负债/在手订单：增长/持平/减少？
- 产能利用率/资本开支：扩张/维持/收缩？
"""


if __name__ == "__main__":
    print("Industry logic module ready")
    print(f10_urls("003031"))
