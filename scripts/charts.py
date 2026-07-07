#!/usr/bin/env python3
"""
图表生成模块 — matplotlib 可视化
K线图 / MACD / RSI+KDJ / 缠论标注 / 估值水位 / 板块热力图
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import FancyBboxPatch
import matplotlib.font_manager as fm
import numpy as np
from datetime import datetime
import os

# ── 中文支持 ──────────────────────────────────────────────────
# 查找可用的 CJK 字体
_cjk_fonts = [f.name for f in fm.fontManager.ttflist if "CJK" in f.name]
_CJK_FONT = _cjk_fonts[0] if _cjk_fonts else "DejaVu Sans"

# ── 导入辅助 ──────────────────────────────────────────────────
def _import_technical():
    """兼容相对/绝对导入"""
    try:
        from . import technical
    except ImportError:
        import technical
    return technical

# ── 全局样式 ──────────────────────────────────────────────────
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": [_CJK_FONT, "DejaVu Sans"],
    "axes.unicode_minus": False,
    "figure.dpi": 150,
    "savefig.dpi": 150,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.1,
    "figure.facecolor": "#1a1a2e",
    "axes.facecolor": "#16213e",
    "axes.edgecolor": "#333",
    "axes.labelcolor": "#ccc",
    "text.color": "#ccc",
    "xtick.color": "#888",
    "ytick.color": "#888",
    "grid.color": "#2a2a4a",
    "grid.alpha": 0.5,
})

OUTPUT_DIR = "/workspace"
COLORS = {
    "up": "#00ff88",
    "down": "#ff4466",
    "ma5": "#ffcc00",
    "ma10": "#ff8800",
    "ma20": "#ff4466",
    "ma60": "#00ccff",
    "volume": "#4488ff",
    "macd": "#ffcc00",
    "dif": "#00ccff",
    "dea": "#ff8800",
    "rsi": "#cc66ff",
    "k": "#ffcc00",
    "d": "#ff8800",
    "j": "#cc66ff",
}

# ── K 线图 ────────────────────────────────────────────────────
def plot_kline(data: list, title: str = "", filename: str = "kline.png") -> str:
    """绘制K线图 + 均线 + 成交量"""
    n = len(data)
    if n == 0:
        return ""

    dates = [datetime.strptime(d["日期"], "%Y-%m-%d") for d in data]
    opens = np.array([d["开盘"] for d in data], dtype=float)
    highs = np.array([d["最高"] for d in data], dtype=float)
    lows = np.array([d["最低"] for d in data], dtype=float)
    closes = np.array([d["收盘"] for d in data], dtype=float)
    volumes = np.array([d["成交量"] for d in data], dtype=float)

    fig = plt.figure(figsize=(14, 8))
    gs = fig.add_gridspec(2, 1, height_ratios=[3, 1], hspace=0.05)

    ax1 = fig.add_subplot(gs[0])
    ax1.grid(True, alpha=0.3)

    width = 0.6
    for i in range(n):
        color = COLORS["up"] if closes[i] >= opens[i] else COLORS["down"]
        ax1.plot([dates[i], dates[i]], [lows[i], highs[i]], color=color, linewidth=0.8, alpha=0.8)
        body_bottom = min(opens[i], closes[i])
        body_height = abs(closes[i] - opens[i])
        if body_height > 0:
            ax1.bar(dates[i], body_height, width=width, bottom=body_bottom,
                    color=color, edgecolor=color, linewidth=0.5, alpha=0.9)

    ma_periods = [5, 10, 20, 60]
    ma_colors = [COLORS["ma5"], COLORS["ma10"], COLORS["ma20"], COLORS["ma60"]]
    for p, c in zip(ma_periods, ma_colors):
        if n >= p:
            ma = np.full(n, np.nan)
            for j in range(p - 1, n):
                ma[j] = np.mean(closes[j - p + 1 : j + 1])
            ax1.plot(dates, ma, color=c, linewidth=1, alpha=0.8, label=f"MA{p}")

    ax1.legend(loc="upper left", fontsize=7, framealpha=0.3)
    ax1.set_ylabel("Price", fontsize=9)
    if title:
        ax1.set_title(title, fontsize=12, fontweight="bold", color="#fff")
    ax1.tick_params(labelsize=7)

    ax2 = fig.add_subplot(gs[1], sharex=ax1)
    ax2.grid(True, alpha=0.3)
    colors_vol = [COLORS["up"] if closes[i] >= opens[i] else COLORS["down"] for i in range(n)]
    ax2.bar(dates, volumes, width=width, color=colors_vol, alpha=0.7, edgecolor="none")
    ax2.set_ylabel("Volume", fontsize=9)
    ax2.tick_params(labelsize=7)
    ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x/1e6:.0f}M" if x >= 1e6 else f"{x/1e4:.0f}W"))

    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))
    ax1.xaxis.set_major_locator(mdates.AutoDateLocator())
    fig.autofmt_xdate()

    path = os.path.join(OUTPUT_DIR, filename)
    fig.savefig(path, facecolor=fig.get_facecolor())
    plt.close(fig)
    return path

# ── MACD 图 ──────────────────────────────────────────────────
def plot_macd(data: list, filename: str = "macd.png") -> str:
    """绘制MACD指标图"""
    n = len(data)
    if n < 26:
        return ""

    tech = _import_technical()
    dates = [datetime.strptime(d["日期"], "%Y-%m-%d") for d in data]
    closes = np.array([d["收盘"] for d in data], dtype=float)
    macd_data = tech.calc_macd(closes.tolist())
    dif = np.array(macd_data["DIF"])
    dea = np.array(macd_data["DEA"])
    bar = np.array(macd_data["MACD"])

    fig, ax = plt.subplots(figsize=(14, 3))
    ax.grid(True, alpha=0.3)

    colors_bar = [COLORS["up"] if v >= 0 else COLORS["down"] for v in bar]
    ax.bar(dates, bar, width=0.8, color=colors_bar, alpha=0.7, edgecolor="none")
    ax.plot(dates, dif, color=COLORS["dif"], linewidth=1, label="DIF")
    ax.plot(dates, dea, color=COLORS["dea"], linewidth=1, label="DEA")
    ax.axhline(y=0, color="#555", linewidth=0.5, linestyle="--")

    ax.legend(loc="upper left", fontsize=7, framealpha=0.3)
    ax.set_title("MACD (12,26,9)", fontsize=10, color="#fff")
    ax.tick_params(labelsize=7)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))

    path = os.path.join(OUTPUT_DIR, filename)
    fig.savefig(path, facecolor=fig.get_facecolor())
    plt.close(fig)
    return path

# ── RSI + KDJ 组合图 ─────────────────────────────────────────
def plot_rsi_kdj(data: list, filename: str = "rsi_kdj.png") -> str:
    """RSI + KDJ 双指标图"""
    n = len(data)
    if n < 14:
        return ""

    tech = _import_technical()
    dates = [datetime.strptime(d["日期"], "%Y-%m-%d") for d in data]
    closes = np.array([d["收盘"] for d in data], dtype=float)

    rsi = tech.calc_rsi(closes.tolist())
    kdj = tech.calc_kdj(data)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 5), sharex=True)
    fig.subplots_adjust(hspace=0.08)

    ax1.grid(True, alpha=0.3)
    ax1.plot(dates, rsi, color=COLORS["rsi"], linewidth=1.2, label="RSI(14)")
    ax1.axhline(y=70, color="#ff4466", linewidth=0.5, linestyle="--", alpha=0.6)
    ax1.axhline(y=30, color="#00ff88", linewidth=0.5, linestyle="--", alpha=0.6)
    ax1.axhline(y=50, color="#555", linewidth=0.5, linestyle=":", alpha=0.4)
    ax1.fill_between(dates, 70, 100, alpha=0.05, color="#ff4466")
    ax1.fill_between(dates, 0, 30, alpha=0.05, color="#00ff88")
    ax1.set_ylim(0, 100)
    ax1.legend(loc="upper left", fontsize=7, framealpha=0.3)
    ax1.set_title("RSI(14)", fontsize=10, color="#fff")
    ax1.tick_params(labelsize=7)

    ax2.grid(True, alpha=0.3)
    ax2.plot(dates, kdj["K"], color=COLORS["k"], linewidth=1, label="K")
    ax2.plot(dates, kdj["D"], color=COLORS["d"], linewidth=1, label="D")
    ax2.plot(dates, kdj["J"], color=COLORS["j"], linewidth=0.8, alpha=0.7, label="J")
    ax2.axhline(y=80, color="#ff4466", linewidth=0.5, linestyle="--", alpha=0.6)
    ax2.axhline(y=20, color="#00ff88", linewidth=0.5, linestyle="--", alpha=0.6)
    ax2.set_ylim(-20, 120)
    ax2.legend(loc="upper left", fontsize=7, framealpha=0.3)
    ax2.set_title("KDJ(9,3,3)", fontsize=10, color="#fff")
    ax2.tick_params(labelsize=7)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))

    path = os.path.join(OUTPUT_DIR, filename)
    fig.savefig(path, facecolor=fig.get_facecolor())
    plt.close(fig)
    return path

# ── 缠论标注图 ────────────────────────────────────────────────
def plot_chan_theory(data: list, chan_result: dict, filename: str = "chan_theory.png") -> str:
    """缠论可视化"""
    n = len(data)
    if n < 20:
        return ""

    dates = [datetime.strptime(d["日期"], "%Y-%m-%d") for d in data]
    highs = np.array([d["最高"] for d in data], dtype=float)
    lows = np.array([d["最低"] for d in data], dtype=float)
    closes = np.array([d["收盘"] for d in data], dtype=float)

    fig, ax = plt.subplots(figsize=(14, 6))
    ax.grid(True, alpha=0.3)
    ax.plot(dates, closes, color="#aaa", linewidth=0.8, alpha=0.6)

    if "顶分型" in chan_result:
        for t in chan_result["顶分型"]:
            idx = t["索引"]
            if idx < n:
                ax.scatter(dates[idx], highs[idx], color="#ff4466", s=40, marker="v", zorder=5)
    if "底分型" in chan_result:
        for b in chan_result["底分型"]:
            idx = b["索引"]
            if idx < n:
                ax.scatter(dates[idx], lows[idx], color="#00ff88", s=40, marker="^", zorder=5)

    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], marker="v", color="w", markerfacecolor="#ff4466", markersize=8, label="Top"),
        Line2D([0], [0], marker="^", color="w", markerfacecolor="#00ff88", markersize=8, label="Bottom"),
    ]
    ax.legend(handles=legend_elements, loc="upper left", fontsize=7, framealpha=0.3)
    ax.set_title("Chan Theory", fontsize=12, fontweight="bold", color="#fff")
    ax.set_ylabel("Price", fontsize=9)
    ax.tick_params(labelsize=7)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))

    path = os.path.join(OUTPUT_DIR, filename)
    fig.savefig(path, facecolor=fig.get_facecolor())
    plt.close(fig)
    return path

# ── 估值水位图 ────────────────────────────────────────────────
def plot_valuation(quote: dict, fundamental: dict, filename: str = "valuation.png") -> str:
    """估值仪表盘"""
    pe = quote.get("市盈率(动)", 0)
    score_data = fundamental.get("基本盘", {})

    fig, axes = plt.subplots(1, 2, figsize=(10, 4))

    # PE 标尺
    ax1 = axes[0]
    ax1.set_xlim(0, 100)
    ax1.set_ylim(0, 1)
    ax1.axis("off")

    zones = [
        (0, 15, "#00ff88"), (15, 25, "#88ff44"), (25, 40, "#ffcc00"),
        (40, 60, "#ff8800"), (60, 100, "#ff4466"),
    ]
    labels = ["Low", "Fair-Low", "Fair", "High", "Overvalued"]
    for (x1, x2, color), label in zip(zones, labels):
        ax1.fill_between([x1, x2], 0.3, 0.7, color=color, alpha=0.5)
        ax1.text((x1 + x2) / 2, 0.5, label, ha="center", va="center", fontsize=8, color="#fff")

    if pe > 0 and pe < 100:
        ax1.arrow(pe, 1.0, 0, -0.25, head_width=1.5, head_length=0.08, fc="#fff", ec="#fff", lw=1.5)
        ax1.text(pe, 1.08, f"PE={pe:.1f}", ha="center", fontsize=10, fontweight="bold", color="#fff")
    ax1.set_title("PE Level", fontsize=10, color="#fff")

    # 评分仪表盘
    ax2 = axes[1]
    ax2.axis("off")
    score = score_data.get("基本盘评分", 50) if score_data else 50
    grade = score_data.get("评级", "C") if score_data else "C"

    for (t1, t2, color) in [
        (0, np.pi * 0.25, "#ff4466"),
        (np.pi * 0.25, np.pi * 0.5, "#ff8800"),
        (np.pi * 0.5, np.pi * 0.75, "#ffcc00"),
        (np.pi * 0.75, np.pi, "#00ff88"),
    ]:
        t = np.linspace(t1, t2, 30)
        ax2.fill_between(t, 0.6, 0.9, color=color, alpha=0.6)

    angle = np.pi - (score / 100) * np.pi
    ax2.arrow(angle, 0, 0, 0.5, head_width=0.08, head_length=0.1, fc="#fff", ec="#fff", lw=1.5)
    ax2.text(np.pi / 2, -0.15, f"{score}/{grade}", ha="center", fontsize=14, fontweight="bold", color="#fff")
    ax2.set_xlim(-1.2, 1.2)
    ax2.set_ylim(-0.3, 1.5)
    ax2.set_title("Fundamental Score", fontsize=10, color="#fff")

    path = os.path.join(OUTPUT_DIR, filename)
    fig.savefig(path, facecolor=fig.get_facecolor())
    plt.close(fig)
    return path

# ── 板块热力图 ────────────────────────────────────────────────
def plot_sector_heatmap(heatmap_data: dict, filename: str = "sector_heatmap.png") -> str:
    """板块涨跌横向图"""
    sectors = heatmap_data.get("板块", [])
    changes = heatmap_data.get("涨跌幅", [])
    if not sectors:
        return ""

    pairs = sorted(zip(sectors, changes), key=lambda x: x[1])
    sectors_sorted = [p[0] for p in pairs]
    changes_sorted = [p[1] for p in pairs]

    fig, ax = plt.subplots(figsize=(10, max(6, len(sectors_sorted) * 0.3)))
    colors = ["#00ff88" if c > 2 else "#66cc88" if c > 0 else "#ff8866" if c > -2 else "#ff4466" for c in changes_sorted]

    bars = ax.barh(range(len(sectors_sorted)), changes_sorted, color=colors, alpha=0.8, height=0.7)
    ax.set_yticks(range(len(sectors_sorted)))
    ax.set_yticklabels(sectors_sorted, fontsize=8)
    ax.axvline(x=0, color="#fff", linewidth=0.5, linestyle="--")
    ax.grid(True, alpha=0.2, axis="x")

    for bar, val in zip(bars, changes_sorted):
        ax.text(val + (0.3 if val >= 0 else -0.3), bar.get_y() + bar.get_height() / 2,
                f"{val:+.2f}%", va="center", ha="left" if val >= 0 else "right", fontsize=7, color="#fff")

    ax.set_title("Sector Performance", fontsize=12, fontweight="bold", color="#fff")
    ax.set_xlabel("Change (%)", fontsize=9)
    ax.tick_params(labelsize=7)

    path = os.path.join(OUTPUT_DIR, filename)
    fig.savefig(path, facecolor=fig.get_facecolor())
    plt.close(fig)
    return path


# ── 选股框架雷达图 ────────────────────────────────────────────
def plot_selection_radar(selection_data: dict, filename: str = "selection_radar.png") -> str:
    """四步选股法雷达图/条形图"""
    steps = selection_data.get("四步结果", [])
    if len(steps) < 4:
        return ""

    labels = [s["步骤"].replace("一、", "").replace("二、", "").replace("三、", "").replace("四、", "").replace("硬指标排雷", "排雷").replace("PEG估值参考", "估值").replace("精挑细选", "精选").replace("成交量验证资金态度", "量价") for s in steps]
    scores = [s.get("得分", 0) for s in steps]

    fig, ax = plt.subplots(figsize=(10, 4))
    colors = ["#00ff88" if s >= 70 else "#ffcc00" if s >= 50 else "#ff4466" for s in scores]
    bars = ax.barh(labels, scores, color=colors, alpha=0.8, height=0.5)

    for bar, s in zip(bars, scores):
        ax.text(s + 1, bar.get_y() + bar.get_height() / 2, f"{s:.0f}",
                va="center", ha="left", fontsize=10, fontweight="bold", color="#fff")

    ax.set_xlim(0, 105)
    ax.axvline(x=70, color="#00ff88", linewidth=0.8, linestyle="--", alpha=0.5)
    ax.axvline(x=50, color="#ffcc00", linewidth=0.8, linestyle="--", alpha=0.5)
    ax.set_xlabel("Score", fontsize=9)
    ax.set_title(f"Stock Selection Framework | Total: {selection_data.get('选股总分', 0):.1f} | {selection_data.get('选股评级', '')}",
                 fontsize=11, fontweight="bold", color="#fff")
    ax.tick_params(labelsize=9)
    ax.grid(True, alpha=0.2, axis="x")

    path = os.path.join(OUTPUT_DIR, filename)
    fig.savefig(path, facecolor=fig.get_facecolor())
    plt.close(fig)
    return path


if __name__ == "__main__":
    print(f"Charts module ready (font: {_CJK_FONT})")
