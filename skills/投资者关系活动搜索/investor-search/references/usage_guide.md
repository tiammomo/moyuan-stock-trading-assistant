# investor搜索技能使用指南

## 目录

1. [快速入门](#快速入门)
2. [环境配置](#环境配置)
3. [基本使用](#基本使用)
4. [高级功能](#高级功能)
5. [输出格式](#输出格式)
6. [批量处理](#批量处理)
7. [最佳实践](#最佳实践)
8. [故障排除](#故障排除)
9. [常见问题](#常见问题)

## 快速入门

### 1. 安装技能
```bash
# 进入技能目录
cd .trae/skills/investor-search/scripts

# 安装依赖
pip install -r requirements.txt

# 安装技能
python setup.py install
```

### 2. 设置环境变量
```bash
# 设置API密钥
export IWENCAI_API_KEY="your_api_key_here"

# 验证设置
echo $IWENCAI_API_KEY
```

### 3. 第一个搜索
```bash
# 搜索贵州茅台投资者关系活动
investor-search "贵州茅台投资者关系活动"
```

## 环境配置

### 必需配置

#### 1. API密钥获取
1. 访问同花顺问财平台
2. 申请API访问权限
3. 获取API密钥

#### 2. 环境变量设置

##### Linux/macOS
```bash
# 临时设置（当前终端有效）
export IWENCAI_API_KEY="your_api_key_here"

# 永久设置（添加到 ~/.bashrc 或 ~/.zshrc）
echo 'export IWENCAI_API_KEY="your_api_key_here"' >> ~/.bashrc
source ~/.bashrc
```

##### Windows
```cmd
# 命令行设置
set IWENCAI_API_KEY=your_api_key_here

# PowerShell设置
$env:IWENCAI_API_KEY="your_api_key_here"
```

### 可选配置

#### 1. 代理设置
如果需要通过代理访问：
```bash
export HTTP_PROXY="http://proxy.example.com:8080"
export HTTPS_PROXY="http://proxy.example.com:8080"
```

#### 2. 超时设置
默认超时为30秒，如需调整：
```python
# 在代码中自定义
search = InvestorSearch()
search.api_client.timeout = 60  # 60秒超时
```

## 基本使用

### 1. 简单搜索
```bash
# 基本格式
investor-search "查询语句"

# 示例
investor-search "贵州茅台投资者关系活动"
investor-search "人工智能公司调研"
investor-search "新能源行业路演"
```

### 2. 带参数搜索
```bash
# 指定公司
investor-search "调研" --company "科大讯飞"

# 指定活动类型
investor-search "投资者关系" --activity-type "会议"

# 指定日期范围
investor-search "活动" --date-start "2024-01-01" --date-end "2024-06-30"

# 限制结果数量
investor-search "路演" --limit 10
```

### 3. 组合参数
```bash
# 多参数组合
investor-search "人工智能" \
  --company "科大讯飞" \
  --activity-type "调研" \
  --date-start "2024-01-01" \
  --limit 5
```

## 高级功能

### 1. 查询分析
技能会自动分析复杂查询：

#### 多公司查询
```bash
# 自动拆分为两个查询
investor-search "最近贵州茅台和五粮液的投资者关系活动"
```

#### 日期范围识别
```bash
# 自动识别日期范围
investor-search "今年人工智能公司调研"
investor-search "最近三个月路演活动"
```

### 2. 智能过滤

#### 公司名称自动提取
```bash
# 即使不指定--company，也会自动提取
investor-search "贵州茅台调研活动记录"
```

#### 活动类型识别
```bash
# 自动识别活动类型
investor-search "分析师会议纪要"
investor-search "业绩说明会信息"
```

### 3. 数据增强

#### 参与机构提取
自动从摘要中提取参与的投资机构。

#### 关键话题识别
识别活动中讨论的核心话题。

## 输出格式

### 1. 控制台输出

#### Markdown格式（默认）
```bash
investor-search "贵州茅台投资者关系活动" --format markdown
```

#### 文本格式
```bash
investor-search "贵州茅台投资者关系活动" --format text
```

#### CSV表格格式
```bash
investor-search "贵州茅台投资者关系活动" --format csv
```

#### JSON格式
```bash
investor-search "贵州茅台投资者关系活动" --format json
```

### 2. 文件输出

#### 保存为CSV
```bash
investor-search "新能源行业" --output "results.csv" --format csv
```

#### 保存为JSON
```bash
investor-search "科技公司" --output "results.json" --format json
```

#### 保存为Markdown报告
```bash
investor-search "医药公司" --output "report.md" --format markdown
```

### 3. 输出内容

#### 基本信息
- 公司名称
- 活动类型
- 活动日期
- 活动标题

#### 详细内容
- 活动摘要（截断至500字符）
- 参与机构列表
- 关键话题列表

#### 来源信息
- 原文链接
- 数据来源声明（同花顺问财）

## 批量处理

### 1. 文件输入
```bash
# 创建查询文件
cat > queries.txt << EOF
贵州茅台投资者关系活动
五粮液业绩说明会
宁德时代路演活动
人工智能公司调研
新能源行业投资者沟通
EOF

# 批量搜索
investor-search --input-file queries.txt
```

### 2. 批量输出
```bash
# 批量搜索并保存到目录
investor-search --input-file queries.txt --output-dir results/

# 指定输出格式
investor-search --input-file queries.txt --output-dir results/ --format csv
```

### 3. 结果汇总
```bash
# 生成汇总报告
investor-search --input-file queries.txt --output-dir results/ --format markdown
```

## 最佳实践

### 1. 查询优化

#### 使用具体关键词
```bash
# 不推荐：太宽泛
investor-search "公司活动"

# 推荐：具体明确
investor-search "贵州茅台特定对象调研"
investor-search "宁德时代新能源业务路演"
```

#### 合理组合关键词
```bash
# 公司 + 活动类型
investor-search "科大讯飞 人工智能 调研"

# 行业 + 活动类型
investor-search "医药行业 业绩说明会"

# 时间段 + 活动类型
investor-search "2024年 第一季度 投资者关系活动"
```

### 2. 参数使用

#### 日期范围过滤
```bash
# 搜索特定时间段
investor-search "路演" --date-start "2024-01-01" --date-end "2024-03-31"

# 搜索最近一段时间
investor-search "调研" --date-start $(date -d "30 days ago" +%Y-%m-%d)
```

#### 结果数量控制
```bash
# 获取最新10条记录
investor-search "投资者关系" --limit 10

# 获取全部记录（谨慎使用）
investor-search "活动" --limit 100
```

### 3. 性能优化

#### 缓存重复查询
```python
from functools import lru_cache

@lru_cache(maxsize=100)
def cached_search(query, **kwargs):
    return search.search(query, **kwargs)
```

#### 批量请求优化
```python
# 使用线程池并发请求
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=5) as executor:
    futures = [executor.submit(search.search, query) for query in queries]
    results = [f.result() for f in futures]
```

### 4. 数据质量

#### 验证数据完整性
```python
def validate_result(result):
    required_fields = ['company', 'activity_type', 'date', 'title']
    for field in required_fields:
        if not result.get(field):
            return False
    return True
```

#### 检查数据时效性
```python
from datetime import datetime

def is_recent_result(result, days=30):
    result_date = datetime.strptime(result['date'], '%Y-%m-%d')
    delta = datetime.now() - result_date
    return delta.days <= days
```

## 故障排除

### 1. 常见错误

#### API密钥错误
```
错误: 请设置环境变量 IWENCAI_API_KEY
示例: export IWENCAI_API_KEY="your_api_key_here"
```

**解决方案：**
1. 检查环境变量是否正确设置
2. 重新设置环境变量
3. 重启终端

#### 网络连接错误
```
错误: 请求失败: 无法连接到服务器
```

**解决方案：**
1. 检查网络连接
2. 验证代理设置
3. 检查防火墙设置

#### 请求频率限制
```
错误: 请求频率超限，请稍后重试
```

**解决方案：**
1. 降低请求频率
2. 添加请求延迟
3. 使用缓存减少重复请求

### 2. 调试方法

#### 启用详细输出
```bash
investor-search "测试查询" --verbose
```

#### 检查环境变量
```bash
# 检查API密钥
echo $IWENCAI_API_KEY

# 检查Python路径
which python
python --version
```

#### 测试API连接
```python
import requests

response = requests.get("https://openapi.iwencai.com", timeout=10)
print(f"API连接状态: {response.status_code}")
```

### 3. 性能问题

#### 响应缓慢
**可能原因：**
1. 网络延迟
2. API服务器负载
3. 查询复杂度高

**解决方案：**
1. 增加超时时间
2. 简化查询语句
3. 使用缓存

#### 内存占用高
**可能原因：**
1. 结果数据量大
2. 批量处理未分页

**解决方案：**
1. 限制结果数量
2. 使用流式处理
3. 分批次处理

## 常见问题

### Q1: 如何获取API密钥？
A: 需要向同花顺问财平台申请API访问权限。具体流程：
1. 访问问财平台官网
2. 注册开发者账号
3. 申请API密钥
4. 等待审核通过

### Q2: 支持哪些活动类型？
A: 支持7种主要活动类型：
1. 调研（特定对象调研）
2. 会议（分析师会议）
3. 采访（媒体采访）
4. 说明会（业绩说明会）
5. 发布会（新闻发布会）
6. 路演（路演活动）
7. 参观（现场参观）

### Q3: 数据更新频率如何？
A: 数据更新取决于问财平台：
- 实时或近实时更新
- 建议重要数据手动验证
- 历史数据可能有限制

### Q4: 是否有请求限制？
A: 是的，API有请求频率限制：
- 具体限制请参考问财文档
- 建议控制并发请求
- 使用缓存优化

### Q5: 如何批量导出数据？
A: 使用文件输入和输出目录：
```bash
investor-search --input-file queries.txt --output-dir results/ --format csv
```

### Q6: 数据准确性如何保证？
A: 采取多种措施：
1. 关键词匹配算法
2. 数据验证规则
3. 定期质量检查
4. 用户反馈机制

### Q7: 是否支持自定义字段？
A: 目前支持标准字段，如需自定义：
1. 修改data_processor.py
2. 添加新的处理逻辑
3. 更新数据字段文档

### Q8: 如何处理特殊字符？
A: 系统自动处理：
1. 统一UTF-8编码
2. 特殊字符转义
3. 格式标准化

## 技术支持

### 1. 获取帮助
- 查看本文档
- 运行 `investor-search --help`
- 参考代码注释

### 2. 报告问题
如遇问题，请提供：
1. 错误信息
2. 查询语句
3. 环境信息
4. 复现步骤

### 3. 建议反馈
欢迎提出改进建议：
1. 功能需求
2. 性能优化
3. 用户体验

---

**重要提示**: 使用本技能时，请遵守相关法律法规，并注明数据来源于同花顺问财。