#!/usr/bin/env python3
"""
A 股数据获取模块 — 基于腾讯/新浪公开 API
支持：实时行情、历史K线、财务摘要、股票列表、行业板块
数据源优先级：腾讯财经 > 东方财富
"""

import json
import re
import time
import sys
from typing import Optional
from urllib.request import Request, urlopen
from urllib.parse import quote

# ── 股票代码标准化 ────────────────────────────────────────────

def normalize_code(code: str) -> str:
    """将任意格式转为 sh/sz 前缀"""
    code = re.sub(r'[^0-9]', '', code).zfill(6)
    if code.startswith(('6', '9')):
        return f"sh{code}"
    elif code.startswith(('0', '3')):
        return f"sz{code}"
    elif code.startswith(('4', '8')):
        return f"bj{code}"
    return f"sh{code}"

# ── 底层 HTTP 请求 ────────────────────────────────────────────

def _http_get(url, encoding="utf-8", use_gbk=False, retries=3, referer=None):
    """通用 HTTP GET，返回文本"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    if referer:
        headers["Referer"] = referer
    for i in range(retries):
        try:
            req = Request(url, headers=headers)
            with urlopen(req, timeout=10) as resp:
                raw = resp.read()
                enc = "gbk" if use_gbk else encoding
                return raw.decode(enc, errors="replace")
        except Exception as e:
            if i == retries - 1:
                raise RuntimeError(f"HTTP请求失败: {url}, {e}")
            time.sleep(0.5)
    return ""

def _http_json(url, retries=3):
    """HTTP GET → JSON"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://quote.eastmoney.com/",
    }
    for i in range(retries):
        try:
            req = Request(url, headers=headers)
            with urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            if i == retries - 1:
                raise RuntimeError(f"JSON请求失败: {url}, {e}")
            time.sleep(0.5)
    return {}

# ── 实时行情 ──────────────────────────────────────────────────

def get_realtime_quote(code: str) -> dict:
    """获取个股实时行情（腾讯财经）"""
    ncode = normalize_code(code)
    url = f"https://qt.gtimg.cn/q={ncode}"
    text = _http_get(url, use_gbk=True)

    if not text or '=""' in text or "none_match" in text:
        raise ValueError(f"未找到股票: {code}")

    match = re.search(r'="(.+)"', text)
    if not match:
        raise ValueError(f"解析失败: {code}")
    parts = match.group(1).split("~")

    if len(parts) < 40:
        raise ValueError(f"数据不足: {len(parts)} 字段")

    return {
        "代码": parts[2],
        "名称": parts[1],
        "最新价": float(parts[3]) if parts[3] else 0,
        "昨收": float(parts[4]) if parts[4] else 0,
        "今开": float(parts[5]) if parts[5] else 0,
        "成交量(手)": int(float(parts[6])) if parts[6] else 0,
        "最高": float(parts[33]) if parts[33] else 0,
        "最低": float(parts[34]) if parts[34] else 0,
        "成交额(元)": float(parts[37]) if parts[37] else 0,
        "换手率": float(parts[38]) if parts[38] else 0,
        "涨跌额": float(parts[31]) if parts[31] else 0,
        "涨跌幅": float(parts[32]) if parts[32] else 0,
        "总市值": float(parts[45]) if len(parts) > 45 and parts[45] else 0,
        "流通市值": float(parts[44]) if len(parts) > 44 and parts[44] else 0,
        "市盈率(动)": float(parts[39]) if len(parts) > 39 and parts[39] else 0,
        "市净率": float(parts[46]) if len(parts) > 46 and parts[46] else 0,
    }

def get_batch_quotes(codes: list) -> list[dict]:
    """批量获取行情"""
    ncodes = [normalize_code(c) for c in codes]
    url = f"https://qt.gtimg.cn/q={','.join(ncodes)}"
    text = _http_get(url, use_gbk=True)

    results = []
    for ncode in ncodes:
        escaped = ncode.replace("(", "\\(").replace(")", "\\)")
        m = re.search(rf'{escaped}="([^"]*)"', text)
        if m:
            parts = m.group(1).split("~")
            if len(parts) >= 40:
                results.append({
                    "代码": parts[2], "名称": parts[1],
                    "最新价": float(parts[3]) if parts[3] else 0,
                    "涨跌幅": float(parts[32]) if parts[32] else 0,
                    "总市值": float(parts[45]) if len(parts) > 45 and parts[45] else 0,
                    "市盈率(动)": float(parts[39]) if len(parts) > 39 and parts[39] else 0,
                })
    return results

# ── K 线数据 ──────────────────────────────────────────────────

def get_kline(code: str, period: str = "daily", count: int = 250) -> list:
    """获取历史K线（前复权）"""
    ncode = normalize_code(code)
    p_map = {"daily": "day", "weekly": "week", "monthly": "month"}
    p = p_map.get(period, "day")

    url = f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?_var=kline&param={ncode},{p},,,{count},qfq"
    text = _http_get(url, encoding="utf-8")

    if text.startswith("kline="):
        text = text[6:]

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []

    stock_data = data.get("data", {}).get(ncode, {})
    k_map = {"day": "qfqday", "week": "qfqweek", "month": "qfqmonth"}
    key = k_map.get(p, f"qfq{p}")
    klines = stock_data.get(key) if isinstance(stock_data.get(key), list) else []

    result = []
    for line in klines:
        if isinstance(line, list) and len(line) >= 6:
            # line[6] 可能是成交额（str/float）或分红信息（dict），需区分处理
            amount = 0
            if len(line) > 6 and line[6] is not None:
                if isinstance(line[6], (int, float)):
                    amount = float(line[6])
                elif isinstance(line[6], str) and line[6].strip():
                    amount = float(line[6])
                # 如果是 dict（分红信息），amount 保持 0
            result.append({
                "日期": str(line[0]),
                "开盘": float(line[1]),
                "收盘": float(line[2]),
                "最高": float(line[3]),
                "最低": float(line[4]),
                "成交量": int(float(line[5])),
                "成交额": amount,
                "涨跌幅": 0,
            })
    return result

# ── 股票搜索 ──────────────────────────────────────────────────

def search_stock(keyword: str) -> list:
    """搜索股票"""
    encoded = quote(keyword)
    url = f"https://smartbox.gtimg.cn/s3/?q={encoded}&t=all&c=10"
    text = _http_get(url, use_gbk=True)

    results = []
    for line in text.split("\n"):
        m = re.search(r'v_[^=]+="([^"]*)"', line)
        if not m:
            continue
        parts = m.group(1).split("~")
        for i, p in enumerate(parts):
            p_clean = p.strip()
            if re.match(r'^\d{6}$', p_clean) and i + 1 < len(parts):
                name = parts[i + 1].strip()
                results.append({
                    "代码": p_clean,
                    "名称": name,
                    "市场": "SH" if p_clean.startswith(("6", "9")) else "SZ",
                })
                break
    return results[:10]

# ── 行业板块 ──────────────────────────────────────────────────

def get_sector_list() -> list:
    """获取行业板块（预设+东方财富补充）"""
    default = [
        ("BK0477", "银行"), ("BK0473", "证券"), ("BK0474", "保险"),
        ("BK0485", "酿酒"), ("BK0478", "房地产"), ("BK0472", "汽车"),
        ("BK0480", "医药"), ("BK0487", "半导体"), ("BK0488", "元器件"),
        ("BK0481", "电力"), ("BK0479", "煤炭"), ("BK0482", "钢铁"),
        ("BK0483", "有色"), ("BK0484", "石油"), ("BK0486", "化工"),
        ("BK0475", "家电"), ("BK0476", "食品饮料"), ("BK0489", "通信设备"),
        ("BK0490", "互联网"), ("BK0491", "软件服务"), ("BK0653", "人工智能"),
        ("BK0655", "新能源"), ("BK0667", "锂电池"), ("BK0471", "军工"),
        ("BK0492", "环保"), ("BK0493", "建筑"), ("BK0494", "建材"),
        ("BK0495", "农林牧渔"), ("BK0496", "商业连锁"), ("BK0497", "传媒娱乐"),
    ]
    # 尝试从东方财富获取涨跌幅
    try:
        url = (
            "https://push2.eastmoney.com/api/qt/clist/get?"
            "fs=m:90+t:2&fields=f12,f14,f3&pn=1&pz=200"
            "&po=1&np=1&fltt=2&invt=2&fid=f3"
        )
        em_data = _http_json(url)
        sectors = em_data.get("data", {}).get("diff", [])
        if sectors:
            return [
                {"代码": s.get("f12", ""), "名称": s.get("f14", ""),
                 "涨跌幅": s.get("f3", 0) / 100 if s.get("f3") else 0}
                for s in sectors
            ]
    except Exception:
        pass
    return [{"代码": c, "名称": n, "涨跌幅": 0} for c, n in default]

def get_sector_stocks(sector_code: str) -> list:
    """板块成分股"""
    try:
        url = (
            f"https://push2.eastmoney.com/api/qt/clist/get?"
            f"fs=b:{sector_code}&fields=f12,f14,f2,f3,f20,f9"
            f"&pn=1&pz=500&po=1&np=1&fltt=2&invt=2&fid=f3"
        )
        em_data = _http_json(url)
        stocks = em_data.get("data", {}).get("diff", [])
        return [
            {"代码": s.get("f12", ""), "名称": s.get("f14", ""),
             "最新价": s.get("f2", 0) / 100 if s.get("f2") else 0,
             "涨跌幅": s.get("f3", 0) / 100 if s.get("f3") else 0,
             "总市值": s.get("f20", 0),
             "市盈率": s.get("f9", 0) / 100 if s.get("f9") else 0}
            for s in (stocks or [])
        ]
    except Exception:
        return []

# ── 股票列表 ──────────────────────────────────────────────────

def get_stock_list() -> list:
    """A股全列表"""
    try:
        url = (
            "https://push2.eastmoney.com/api/qt/clist/get?"
            "fs=m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23"
            "&fields=f12,f14&pn=1&pz=5000&po=1&np=1&fltt=2&invt=2&fid=f3"
        )
        em_data = _http_json(url)
        stocks = em_data.get("data", {}).get("diff", [])
        return [{"代码": s.get("f12", ""), "名称": s.get("f14", "")} for s in (stocks or [])]
    except Exception:
        return []

def get_financial_data(code: str) -> dict:
    """财务数据（从行情提取PE/PB/市值）"""
    q = get_realtime_quote(code)
    return {
        "市盈率(动)": q.get("市盈率(动)", 0),
        "市净率": q.get("市净率", 0),
        "总市值": q.get("总市值", 0),
        "流通市值": q.get("流通市值", 0),
        "换手率": q.get("换手率", 0),
    }

def get_full_data(code: str, kline_count: int = 250) -> dict:
    """一键获取个股完整数据"""
    quote = get_realtime_quote(code)
    return {
        "行情": quote,
        "日K线": get_kline(code, "daily", kline_count),
        "周K线": get_kline(code, "weekly", min(kline_count, 100)),
        "月K线": get_kline(code, "monthly", min(kline_count, 50)),
        "财务": get_financial_data(code),
    }

if __name__ == "__main__":
    try:
        q = get_realtime_quote("000001")
        print(f"行情: {q['名称']}({q['代码']}) {q['最新价']}")
        k = get_kline("000001", count=5)
        print(f"K线: {len(k)} 条")
    except Exception as e:
        print(f"错误: {e}")
