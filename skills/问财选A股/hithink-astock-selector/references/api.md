# A股数据查询接口文档

## 接口概述

查询A股相关金融数据，支持自然语言问句输入，返回相关金融数据结果。

## 基本信息

| 字段 | 值 |
|------|-----|
| 接口地址 | `IWENCAI_API_URL` |
| 请求方式 | POST |
| 认证方式 | API Key |

## 认证

请求头中需携带 API Key：

```
Authorization: Bearer {IWENCAI_API_KEY}
```

## 请求参数

### Headers

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| Authorization | STRING | 是 | Bearer {IWENCAI_API_KEY} |
| Content-Type | STRING | 是 | application/json |

### Body

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| query | STRING | 是 | 用户问句，例如："茅台今日股价是多少？" |
| page | STRING | 否 | 分页参数，默认值：1 |
| limit | STRING | 否 | 分页参数，默认值：10 |
| is_cache | STRING | 否 | 缓存参数，默认值：1 |

### 请求示例

```json
{
  "query": "茅台今日股价是多少？",
  "page": "1",
  "limit": "10",
  "is_cache": "1"
}
```

## 响应参数

| 参数名 | 类型 | 说明 |
|--------|------|------|
| datas | ARRAY | 金融数据列表，接口返回的金融数据数组，默认返回10条 |
| code_count | INT | 符合查询条件的总股票数量（注意：可能大于当前返回的datas条数） |
| chunks_info | OBJECT | 用户问句查询返回的字句信息，包含查询条件的解析结果 |
| status_code | INT | 状态码，0代表成功，不为0代表错误 |
| status_msg | STRING | 错误信息，当status_code不为0时返回 |

**分页说明：**
- `datas` 默认只返回10条数据，但符合条件的股票总数 `code_count` 可能远大于此
- 当 `code_count > len(datas)` 时，表示还有更多数据，需要通过 `page` 参数翻页获取
- 例如：code_count=150，limit=10，则需要翻15页才能获取全部数据

### 响应示例

**成功响应：**
```json
{
  "datas": [
    {
      "股票代码": "002840.SZ",
      "股票简称": "华统股份",
      "涨跌幅[20260323]": 6.986027999999999
    },
    {
      "股票代码": "688295.SH",
      "股票简称": "中复神鹰",
      "涨跌幅[20260323]": 2.800445
    },
    {
      "股票代码": "300118.SZ",
      "股票简称": "东方日升",
      "涨跌幅[20260323]": 3.9630840000000003
    }
  ],
  "code_count": 150,
  "chunks_info": {
    "query": "今日涨跌幅大于5",
    "parsed_conditions": ["涨跌幅>5%"]
  },
  "status_code": 0,
  "status_msg": ""
}
```

**错误响应：**
```json
{
  "status_code": 1001,
  "status_msg": "查询参数错误",
  "datas": [],
  "code_count": 0,
  "chunks_info": {}
}
```

## 调用示例

```python
import os
import urllib.request
import json

url = "IWENCAI_API_URL"
headers = {
    "Authorization": f"Bearer {os.environ['IWENCAI_API_KEY']}",
    "Content-Type": "application/json"
}
payload = {
    "query": "茅台今日股价是多少？",
    "page": "1",
    "limit": "10",
    "is_cache": "1"
}

data = json.dumps(payload).encode("utf-8")
request = urllib.request.Request(url, data=data, headers=headers, method="POST")
response = urllib.request.urlopen(request, timeout=30)
result = json.loads(response.read().decode("utf-8"))

# 解析返回数据
datas = result.get("datas", [])              # 当前页股票列表
code_count = result.get("code_count", 0)     # 符合条件的总股票数
chunks_info = result.get("chunks_info", {})  # 查询字句解析信息

# 分页提示：如果 code_count > len(datas)，说明还有更多数据
if code_count > len(datas):
    print(f"共查到 {code_count} 只股票，当前返回 {len(datas)} 条，可通过 page 参数翻页获取更多")

# 解析表格数据：遍历 datas 数组，提取各字段
for item in datas:
    stock_code = item.get("股票代码")       # 股票代码，如 "002840.SZ"
    stock_name = item.get("股票简称")       # 股票简称，如 "华统股份"
    # 其他字段根据查询类型而定，如涨跌幅、成交量、市盈率等
    print(f"{stock_code} {stock_name}")
```

## 使用说明（Agent 参考）

- 当用户询问 **A股股票行情、财务数据、市场资讯** 等相关问题时，调用本接口。
- 将用户的自然语言问题直接作为 `query` 参数传入。
- 返回的 `datas` 字段为对象数组（默认10条），每个对象包含股票代码(`股票代码`)、股票简称(`股票简称`)、涨跌幅(`涨跌幅[YYYYMMDD]`)等字段。
- **`code_count` 字段非常重要**：表示符合条件的总股票数，可能远大于 `datas` 的长度，需要通过 `page` 参数翻页获取全部数据。
- **`chunks_info` 字段**：包含用户问句的解析信息，可用于理解查询条件。
- `page`、`limit`、`is_cache` 均为可选参数，默认返回10条数据，可通过调整 `limit` 和 `page` 翻页。
- 环境变量 `IWENCAI_API_KEY` 为鉴权密钥，需提前配置。
- **数据解析**：返回的 `datas` 是表格数据，需要遍历解析每个对象的字段（如 `股票代码`、`股票简称`、`涨跌幅[日期]` 等），根据不同查询类型字段会有所不同。
