# 板块数据查询接口文档

## 接口概述

查询市场板块相关金融数据，支持自然语言问句输入，返回相关金融数据结果。

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
| query | STRING | 是 | 用户问句，例如："今日涨幅最大的板块有哪些？" |
| source | STRING | 否 | 来源，默认值：test |
| page | STRING | 否 | 分页参数，默认值：1 |
| limit | STRING | 否 | 分页参数，默认值：10 |
| is_cache | STRING | 否 | 缓存参数，默认值：1 |

### 请求示例

```json
{
  "query": "今日涨幅最大的板块有哪些？",
  "source": "test",
  "page": "1",
  "limit": "10",
  "is_cache": "1"
}
```

## 响应参数

| 参数名 | 类型 | 说明 |
|--------|------|------|
| datas | ARRAY | 金融数据列表，接口返回的金融数据数组，默认返回10条 |
| code_count | INT | 符合查询条件的总板块数量（注意：可能大于当前返回的datas条数） |
| chunks_info | OBJECT | 用户问句查询返回的字句信息，包含查询条件的解析结果 |
| status_code | INT | 状态码，0代表成功，不为0代表错误 |
| status_msg | STRING | 错误信息，当status_code不为0时返回 |

### 响应示例

**成功响应：**
```json
{
  "datas": [
    {
      "板块名称": "半导体",
      "涨跌幅": 3.25,
      "主力资金净流入": "50亿"
    },
    {
      "板块名称": "人工智能",
      "涨跌幅": 2.85,
      "主力资金净流入": "35亿"
    },
    {
      "板块名称": "新能源汽车",
      "涨跌幅": 2.12,
      "主力资金净流入": "28亿"
    }
  ],
  "code_count": 50,
  "chunks_info": {
    "query": "涨幅前五的板块",
    "parsed_conditions": ["涨跌幅排名前五"]
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

**分页说明：**
- `datas` 默认只返回10条数据，但符合条件的板块总数 `code_count` 可能远大于此
- 当 `code_count > len(datas)` 时，表示还有更多数据，需要通过 `page` 参数翻页获取
- 例如：code_count=50，limit=10，则需要翻5页才能获取全部数据

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
    "query": "今日涨幅最大的板块有哪些？",
    "source": "test",
    "page": "1",
    "limit": "10",
    "is_cache": "1"
}

data = json.dumps(payload).encode("utf-8")
request = urllib.request.Request(url, data=data, headers=headers, method="POST")
response = urllib.request.urlopen(request, timeout=30)
result = json.loads(response.read().decode("utf-8"))
print(result.get("datas", []))
```

## 使用说明（Agent 参考）

- 当用户询问 **板块筛选、板块行情、行业估值、资金流向、板块涨跌** 等相关问题时，调用本接口。
- 将用户的自然语言问题直接作为 `query` 参数传入。
- 返回的 `datas` 字段为对象数组，每个对象包含板块名称(`板块名称`)、涨跌幅(`涨跌幅`)、主力资金净流入(`主力资金净流入`)等字段，可直接拼接后回复用户。
- `source` `page` `limit` `is_cache` 均为可选参数，使用默认值即可。
- 环境变量 `IWENCAI_API_KEY` 为鉴权密钥，需提前配置。
