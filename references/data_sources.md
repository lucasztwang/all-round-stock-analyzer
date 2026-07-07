# A 股数据源参考

## 东方财富公开 API

本 Skill 使用的全部数据来自东方财富（East Money）的公开行情接口，无需 API Key，免费使用。

### 实时行情

```
GET https://push2.eastmoney.com/api/qt/stock/get
参数:
  secid   - 市场.代码 (如 1.600519 表示上证贵州茅台)
  fields  - 返回字段列表
```

常用字段：
| 字段 | 含义 | 单位 |
|------|------|------|
| f43  | 最新价 | 分(÷100) |
| f44  | 最高价 | 分 |
| f45  | 最低价 | 分 |
| f46  | 开盘价 | 分 |
| f47  | 成交量 | 手 |
| f48  | 成交额 | 元 |
| f50  | 量比 | % |
| f57  | 股票代码 | — |
| f58  | 股票名称 | — |
| f60  | 昨收价 | 分 |
| f116 | 总市值 | 元 |
| f117 | 流通市值 | 元 |
| f162 | 市盈率(动) | % |
| f167 | 市净率 | % |
| f168 | 换手率 | % |
| f169 | 涨跌额 | 分 |
| f170 | 涨跌幅 | % |

### 历史 K 线

```
GET https://push2his.eastmoney.com/api/qt/stock/kline/get
参数:
  secid    - 市场.代码
  klt      - K线周期: 101(日) 102(周) 103(月)
  fqt      - 复权: 0(不复权) 1(前复权) 2(后复权)
  lmt      - 获取条数 (max ~2000)
  fields1  - 固定 f1,f2,f3,f4,f5,f6
  fields2  - f51(日期),f52(开盘),f53(收盘),f54(最高),f55(最低),f56(成交量),f57(成交额),f58(涨跌幅)
```

返回 K 线为 CSV 行格式：`日期,开盘,收盘,最高,最低,成交量,成交额,涨跌幅`

### 股票列表

```
GET https://push2.eastmoney.com/api/qt/clist/get
参数:
  fs   - 筛选条件: m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23 (全部A股)
  pn   - 页码
  pz   - 每页数量
  fields - f12(代码),f14(名称),f2(最新价),f3(涨跌幅),...
```

### 行业板块

```
GET https://push2.eastmoney.com/api/qt/clist/get
参数:
  fs   - m:90+t:2 (行业板块) / m:90+t:3 (概念板块)
```

### 板块成分股

```
GET https://push2.eastmoney.com/api/qt/clist/get
参数:
  fs   - b:{板块代码} (如 b:BK0477)
```

### 股票搜索

```
GET https://searchadapter.eastmoney.com/api/suggest/get
参数:
  input  - 搜索关键词 (名称/代码)
  type   - 14
  token  - D43BF722C8E33BDC906FB84D85E326E8
```

## 市场编码规则

| 代码开头 | 市场 | secid 格式 |
|---------|------|-----------|
| 60xxxx  | 上海主板 | 1.60xxxx |
| 00xxxx  | 深圳主板 | 0.00xxxx |
| 30xxxx  | 创业板 | 0.30xxxx |
| 688xxx  | 科创板 | 1.688xxx |
| 8xxxxx  | 北交所 | 0.8xxxxx |

## 注意事项

1. **频率限制**：短时间内高频请求可能导致 IP 被临时限制，建议每次请求间隔 ≥ 0.5s
2. **盘前/盘后**：非交易时段行情数据可能不更新
3. **财务数据**：东方财富 F10 页面结构可能变化，如解析失败会降级到实时行情中的 PE/PB
4. **K 线复权**：默认使用前复权（fqt=1），确保技术指标计算准确
