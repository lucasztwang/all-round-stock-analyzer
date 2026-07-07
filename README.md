# A-Stock Analyzer

> 中国 A 股综合分析 CodeBuddy Skill — 技术面、基本面、缠论、止盈止损、三层仓位管理，一站式搞定。

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Lines](https://img.shields.io/badge/代码-5276行-green.svg)](.)

---

## 功能概览

本 Skill 提供两条分析路径，覆盖从选股到持仓管理的完整投资决策链：

| 路径 | 场景 | 核心能力 |
|------|------|----------|
| **路径 A：选股** | "帮我找几只值得关注的票" | 四步选股框架（排雷→估值→精选→量价）+ 仓位建议 + 买卖点初判 |
| **路径 B：股票分析** | "分析一下 XX 股票" | 持仓询问→产业逻辑→财报/公告/研报→技术买卖点→调仓建议 |

### 技术分析能力

- **多指标综合**：MA(5/10/20/60/120/250)、MACD(金叉死叉+背离)、RSI(超买超卖)、KDJ、BOLL(轨道位置)
- **缠论分析**：分型识别 → 笔构建 → 线段合并 → 中枢定位 → 买卖点分类（一买/二买/三买/一卖/二卖/三卖）
- **买卖点研判**：多指标共振 + 背离检测 + 多周期验证 + 量价突破确认
- **趋势评分**：0-100 分综合评分，含趋势强度、量能配合、指标共振三维度

### 仓位与风控

- **三层仓位法则**：观察仓(2-5%) → 确认仓(30-50%) → 进攻仓(30-50%)
- **五大止盈方法**：固定比例、移动止盈、技术止盈、分批止盈、基本面止盈
- **做 T 策略**：高开先卖后买 / 低开先买后卖 / 分批做 T，附带止盈止损约束

### 板块分析

- 支持行业板块/概念板块内部多只标的横向对比
- 板块资金流向 + 龙头识别 + 轮动研判

---

## 安装

```bash
# 将整个仓库放到 CodeBuddy 的 skills 目录
cp -r a-stock-analyzer ~/.codebuddy/skills/
```

安装后在对话中直接使用关键词即可触发，无需额外配置。Skill 会根据你的意图自动选择选股路径或股票分析路径。

---

## 使用示例

### 选股

```
> 帮我从新能源汽车板块选几只值得关注的票
```

Skill 会：
1. 获取板块成分股列表
2. 逐只拉取行情数据
3. 四步选股框架打分排序
4. 给出三层仓位初始分配
5. 多只买卖点横向对比

### 股票分析

```
> 深度分析双环传动，我持有 700 股，成本 42.32
```

Skill 会：
1. 拉取实时行情 + 日/周/月 K 线
2. 计算 MACD/RSI/KDJ/BOLL 等指标
3. 缠论中枢分析与买卖点分类
4. 多周期信号共振研判
5. 基于你的持仓给出止盈/止损/做 T 建议

### 板块分析

```
> 分析功率半导体板块，只看主板
```

---

## 项目结构

```
a-stock-analyzer/
├── SKILL.md                    # Skill 入口：意图决策树 + 路径定义
├── scripts/
│   ├── fetch_data.py           # 数据获取（腾讯/东方财富 API）
│   ├── fundamental.py          # 基本面分析（PE/PB/ROE/财报）
│   ├── technical.py            # 技术指标计算（MA/MACD/RSI/KDJ/BOLL）
│   ├── chan_theory.py          # 缠论分析（分型/笔/线段/中枢/买卖点）
│   ├── buy_sell_point.py       # 买卖点多维度研判
│   ├── stock_selection.py      # 四步选股框架
│   ├── stop_profit.py          # 止盈止损策略
│   ├── position_management.py  # 三层仓位管理
│   ├── sector.py               # 板块分析与轮动
│   ├── industry_logic.py       # 产业逻辑分析
│   ├── charts.py               # 可视化（趋势图/雷达图）
│   └── report.py               # 报告生成
├── references/
│   ├── data_sources.md         # 数据源 API 文档
│   ├── indicators_guide.md     # 技术指标使用指南
│   ├── stock_selection_framework.md  # 选股框架详解
│   ├── stop_profit_guide.md    # 止盈方法详解
│   └── position_management_guide.md  # 仓位管理详解
└── assets/
    └── report_template.md      # 报告模板
```

---

## 数据源

所有数据来自公开接口，**免费使用，无需 API Key**：

- **实时行情**：腾讯财经 `qt.gtimg.cn`
- **历史 K 线**：腾讯财经 K 线接口 + 东方财富
- **财务数据**：东方财富 F10 页面解析

⚠️ 财务数据通过 HTML 页面解析获取，结构可能随网站改版而变化。如解析失败会自动降级到实时行情中的 PE/PB 数据。

---

## 依赖

```bash
pip install requests matplotlib numpy
```

与 CodeBuddy 沙箱环境兼容，所有依赖均为预装或可通过 pip 安装的标准库。

---

## 免责声明

本工具仅为技术分析辅助，**不构成任何投资建议**。A 股市场风险较高，所有投资决策请自行判断，盈亏自负。

---

## License

MIT License — 详见 [LICENSE](LICENSE) 文件。
