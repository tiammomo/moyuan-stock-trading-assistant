# 问财财经资讯搜索接口文档

## 接口概述

本接口用于搜索问财平台的财经资讯文章，主要面向投资者渠道，特别适用于投资者关系活动内容的搜索。

## 基础信息

- **Base URL**: `https://openapi.iwencai.com`
- **接口路径**: `/v1/comprehensive/search`
- **请求方式**: POST
- **Content-Type**: `application/json`
- **认证方式**: API Key (通过 `IWENCAI_API_KEY` 环境变量传递)

## 认证要求

### 环境变量配置
在使用接口前，需要设置环境变量：
```bash
export IWENCAI_API_KEY="your_api_key_here"
```

### 请求头认证
API Key需要通过Bearer Token方式在请求头中传递：
```http
Authorization: Bearer {IWENCAI_API_KEY}
```

## 请求参数

### 固定参数 (必填)

| 参数名 | 类型 | 说明 | 值 |
|--------|------|------|----|
| channels | LIST | 搜索渠道类型 | `["investor"]` |
| app_id | STRING | 应用ID | `AIME_SKILL` |

### 可变参数 (必填)

| 参数名 | 类型 | 说明 | 示例 |
|--------|------|------|------|
| query | STRING | 用户搜索问句 | `"人工智能投资机会"` |

### 投资者关系活动搜索专用参数

#### 公司名称过滤
在query参数中添加公司名称关键词：
```json
{
  "query": "贵州茅台 投资者关系活动"
}
```

#### 活动类型过滤
在query参数中添加活动类型关键词：
```json
{
  "query": "调研 记录"
}
```

#### 日期范围过滤
在query参数中添加日期范围：
```json
{
  "query": "投资者关系活动 发布时间>=2024-01-01 发布时间<=2024-12-31"
}
```

### 完整请求示例

#### 示例1: 基本搜索
```json
{
  "channels": ["investor"],
  "app_id": "AIME_SKILL",
  "query": "贵州茅台投资者关系活动"
}
```

#### 示例2: 带过滤搜索
```json
{
  "channels": ["investor"],
  "app_id": "AIME_SKILL",
  "query": "人工智能 调研 科大讯飞 发布时间>=2024-01-01"
}
```

#### 示例3: 日期范围搜索
```json
{
  "channels": ["investor"],
  "app_id": "AIME_SKILL",
  "query": "新能源行业路演 发布时间>=2024-01-01 发布时间<=2024-06-30"
}
```

## 响应格式

### 成功响应

```json
{
  "data": [
    {
      "title": "贵州茅台2024年第一季度投资者关系活动记录",
      "summary": "贵州茅台公司于2024年1月15日组织了投资者关系活动，多家投资机构参与交流...",
      "url": "https://www.iwencai.com/article/123456",
      "publish_date": "2024-01-15 14:30:00"
    },
    {
      "title": "贵州茅台业绩说明会纪要",
      "summary": "公司召开了2023年度业绩说明会，管理层就公司经营情况与投资者进行交流...",
      "url": "https://www.iwencai.com/article/123457",
      "publish_date": "2024-03-20 10:00:00"
    }
  ]
}
```

### 空结果响应
```json
{
  "data": []
}
```

### 错误响应
```json
{
  "error": {
    "code": 401,
    "message": "Unauthorized"
  }
}
```

### 响应字段说明

| 字段名 | 类型 | 说明 |
|--------|------|------|
| data | LIST | 返回的文章信息列表 |
| data[].title | STRING | 文章标题 |
| data[].summary | STRING | 文章摘要 |
| data[].url | STRING | 文章网址 |
| data[].publish_date | STRING | 文章发布时间，格式为 `YYYY-MM-DD HH:MM:SS` |

## 投资者关系活动数据特征

### 1. 标题特征
- 通常包含公司名称
- 包含活动类型关键词（调研、会议、采访、说明会等）
- 可能包含日期信息

### 2. 摘要特征
- 描述活动基本情况
- 包含参与机构信息
- 涉及讨论话题
- 可能有管理层观点

### 3. 常见关键词
- 投资者关系活动
- 特定对象调研
- 分析师会议
- 媒体采访
- 业绩说明会
- 新闻发布会
- 路演活动
- 现场参观

## 使用示例

### Python 示例

```python
import os
import requests
import json

# 从环境变量获取API Key
api_key = os.getenv("IWENCAI_API_KEY")

# 请求头
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {api_key}"
}

# 请求参数 - 投资者关系活动搜索
payload = {
    "channels": ["investor"],
    "app_id": "AIME_SKILL",
    "query": "贵州茅台投资者关系活动 发布时间>=2024-01-01"
}

# 发送请求
response = requests.post(
    "https://openapi.iwencai.com/v1/comprehensive/search",
    headers=headers,
    json=payload,
    timeout=30
)

# 处理响应
if response.status_code == 200:
    data = response.json()
    articles = data.get("data", [])
    
    print(f"找到 {len(articles)} 条投资者关系活动记录:")
    for article in articles:
        print(f"标题: {article['title']}")
        print(f"发布时间: {article['publish_date']}")
        print(f"摘要: {article['summary'][:100]}...")
        print(f"链接: {article['url']}")
        print("-" * 50)
else:
    print(f"请求失败: {response.status_code}")
    print(response.text)
```

### cURL 示例

```bash
# 基本搜索
curl -X POST "https://openapi.iwencai.com/v1/comprehensive/search" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $IWENCAI_API_KEY" \
  -d '{
    "channels": ["investor"],
    "app_id": "AIME_SKILL",
    "query": "贵州茅台投资者关系活动"
  }'

# 带日期过滤的搜索
curl -X POST "https://openapi.iwencai.com/v1/comprehensive/search" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $IWENCAI_API_KEY" \
  -d '{
    "channels": ["investor"],
    "app_id": "AIME_SKILL",
    "query": "人工智能公司调研 发布时间>=2024-01-01"
  }'
```

## 最佳实践

### 1. 查询优化
- 使用具体的关键词组合
- 合理使用日期范围过滤
- 结合公司名称和活动类型

### 2. 错误处理
- 检查API密钥有效性
- 处理网络超时
- 解析错误响应

### 3. 性能考虑
- 控制请求频率
- 缓存重复查询结果
- 批量处理多个查询

### 4. 数据质量
- 验证返回数据的完整性
- 检查数据时效性
- 评估数据相关性

## 错误码说明

| 错误码 | 说明 | 处理建议 |
|--------|------|----------|
| 400 | 请求参数错误 | 检查请求参数格式和内容 |
| 401 | 认证失败 | 检查API密钥是否正确设置 |
| 403 | 权限不足 | 确认API密钥有足够的权限 |
| 429 | 请求频率限制 | 降低请求频率，稍后重试 |
| 500 | 服务器内部错误 | 联系服务提供商 |

## 限制说明

### 1. 请求限制
- 频率限制：具体限制请参考问财平台文档
- 并发限制：建议控制并发请求数量

### 2. 数据限制
- 返回结果数量可能受限制
- 历史数据访问可能有限制

### 3. 使用限制
- 仅限合法合规使用
- 遵守数据使用协议
- 注明数据来源

## 更新日志

### v1.0.0 (2024-01-01)
- 初始接口文档
- 投资者关系活动搜索专用说明
- 完整的使用示例

## 支持与反馈

如有问题或建议，请联系：
- 问财平台技术支持
- 开发者文档
- 社区论坛

---

**重要声明**: 本接口数据来源于同花顺问财平台，使用时请遵守相关法律法规和数据使用协议。