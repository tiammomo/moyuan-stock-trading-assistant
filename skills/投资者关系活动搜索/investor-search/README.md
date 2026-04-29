# investor搜索技能

## 概述

investor搜索技能是一个专门用于搜索A股上市公司投资者关系相关内容的搜索引擎。通过调用同花顺问财的财经资讯搜索接口，帮助用户获取上市公司与投资机构、个人投资者等在各类活动中的交流纪要，及时掌握公司最新业务动态和重要事件披露。

**数据来源：同花顺问财**

## 功能特性

### 1. 全面的投资者关系活动覆盖
- 特定对象调研
- 分析师会议
- 媒体采访
- 业绩说明会
- 新闻发布会
- 路演活动
- 现场参观

### 2. 智能查询处理
- 自动拆解复杂查询
- 智能参数提取
- 多公司查询支持
- 日期范围自动处理

### 3. 多种输出格式
- Markdown报告
- 文本格式
- CSV文件
- JSON数据
- HTML报告

### 4. 批量处理能力
- 支持文件输入批量查询
- 批量结果输出
- 结果汇总统计

### 5. 完整的数据处理
- 公司名称自动识别
- 活动类型分类
- 参与机构提取
- 关键话题分析

## 安装要求

### 系统要求
- Python 3.7+
- 有效的同花顺问财API密钥

### 依赖安装
```bash
pip install -r scripts/requirements.txt
```

### 环境配置
```bash
export IWENCAI_API_KEY="your_api_key_here"
```

## 快速开始

### 1. 基本使用
```bash
# 基本搜索
investor-search "贵州茅台投资者关系活动"

# 带参数搜索
investor-search "人工智能公司调研" --company "科大讯飞" --date-start "2024-01-01"

# 输出到文件
investor-search "新能源行业路演" --output "results.csv" --format csv
```

### 2. Python API使用
```python
from investor_search import create_search

# 创建搜索实例
search = create_search()

# 执行搜索
results = search.search("贵州茅台投资者关系活动", limit=10)

# 生成报告
report = search.generate_report(results)
print(report)

# 保存结果
search.save_results(results, "results.csv", "csv")
```

## 命令行参数

### 必需参数
- `query`: 搜索查询语句

### 搜索参数
- `--company`: 指定公司名称
- `--activity-type`: 活动类型（调研/会议/采访/说明会/发布会/路演/参观）
- `--date-start`: 开始日期 (YYYY-MM-DD)
- `--date-end`: 结束日期 (YYYY-MM-DD)
- `--limit`: 限制返回结果数量 (默认: 20)

### 输出参数
- `--output`, `-o`: 输出文件路径
- `--format`: 输出格式 (csv/json/markdown/text，默认: markdown)
- `--verbose`, `-v`: 详细输出模式

### 文件处理参数
- `--input-file`, `-i`: 输入文件路径（批量查询）
- `--output-dir`: 输出目录路径

### 其他参数
- `--version`: 显示版本信息
- `--stats`: 显示搜索统计信息
- `--help`: 显示帮助信息

## 使用示例

### 示例1: 基本搜索
```bash
investor-search "贵州茅台投资者关系活动"
```

### 示例2: 带过滤搜索
```bash
investor-search "人工智能 调研" \
  --company "科大讯飞" \
  --activity-type "调研" \
  --date-start "2024-01-01" \
  --limit 10
```

### 示例3: 批量处理
```bash
# 创建查询文件
echo "贵州茅台投资者关系活动" > queries.txt
echo "五粮液业绩说明会" >> queries.txt
echo "宁德时代路演活动" >> queries.txt

# 执行批量搜索
investor-search --input-file queries.txt --output-dir results/
```

### 示例4: 多种输出格式
```bash
# CSV格式
investor-search "新能源行业" --output "results.csv" --format csv

# JSON格式
investor-search "科技公司" --output "results.json" --format json

# Markdown格式
investor-search "医药公司" --output "report.md" --format markdown
```

## 数据字段说明

### 输出字段
- `company`: 公司名称
- `activity_type`: 活动类型
- `date`: 活动日期 (YYYY-MM-DD)
- `title`: 活动标题
- `summary`: 活动摘要
- `participants`: 参与机构列表
- `topics`: 关键话题列表
- `source`: 数据来源 (同花顺问财)
- `url`: 原文链接

### 数据来源声明
在所有输出中都会明确标注"数据来源于同花顺问财"，确保数据来源的透明性。

## 高级功能

### 1. 查询分析
技能会自动分析用户查询，决定是否拆分为多个子查询：
- 多公司查询自动拆解
- 日期范围自动提取
- 活动类型识别

### 2. 批量处理
支持从文件读取多个查询，批量执行并保存结果：
```bash
investor-search --input-file queries.txt --output-dir results/ --format csv
```

### 3. 结果后处理
- 自动去重
- 按日期排序
- 关键信息提取
- 质量评估

## 错误处理

### 常见错误
1. **API密钥错误**: 检查环境变量 `IWENCAI_API_KEY` 是否正确设置
2. **网络错误**: 检查网络连接和API服务状态
3. **参数错误**: 检查命令行参数格式
4. **文件错误**: 检查文件路径和权限

### 错误信息示例
```bash
# API密钥未设置
错误: 请设置环境变量 IWENCAI_API_KEY
示例: export IWENCAI_API_KEY="your_api_key_here"

# 文件不存在
错误: 文件不存在: queries.txt

# 请求频率限制
错误: 请求频率超限，请稍后重试
```

## 性能优化

### 请求控制
- 自动请求频率控制
- 请求缓存支持
- 批量请求优化

### 内存管理
- 流式处理大文件
- 内存使用监控
- 结果分页处理

## 测试

### 运行测试
```bash
cd scripts
python test_basic.py
```

### 测试覆盖
- 配置管理测试
- 数据处理测试
- API客户端测试
- 集成测试

## 开发指南

### 项目结构
```
investor-search/
├── SKILL.md          # 技能说明和元数据
├── scripts/          # 可执行代码
│   ├── __main__.py          # CLI入口点
│   ├── investor_search.py   # 核心搜索逻辑
│   ├── api_client.py        # API客户端
│   ├── data_processor.py    # 数据处理
│   ├── cli.py              # CLI参数解析
│   ├── config.py           # 配置管理
│   ├── requirements.txt    # 依赖列表
│   ├── setup.py           # 安装配置
│   ├── example_usage.py    # 使用示例
│   ├── test_basic.py       # 测试文件
│   └── test_queries.txt    # 测试查询
├── references/       # 文档和参考资料
└── assets/           # 模板和资源文件
```

### 代码规范
- 遵循PEP 8代码规范
- 使用类型提示
- 完整的文档字符串
- 单元测试覆盖

### 扩展开发
1. 添加新的活动类型识别
2. 优化公司名称提取算法
3. 增加更多的输出格式
4. 集成其他数据源

## 常见问题

### Q1: 如何获取API密钥？
A: 需要向同花顺问财平台申请API密钥，具体申请流程请联系问财平台。

### Q2: 支持哪些活动类型？
A: 支持特定对象调研、分析师会议、媒体采访、业绩说明会、新闻发布会、路演活动、现场参观等。

### Q3: 数据更新频率如何？
A: 数据更新频率取决于同花顺问财平台的更新策略，通常为实时或近实时更新。

### Q4: 是否有请求限制？
A: 是的，API有请求频率限制，具体限制请参考问财平台的API文档。

### Q5: 如何批量导出数据？
A: 使用 `--input-file` 和 `--output-dir` 参数进行批量处理，支持CSV、JSON等格式。

## 版本历史

### v1.0.0 (2024-01-01)
- 初始版本发布
- 基本搜索功能
- 多种输出格式支持
- 批量处理功能
- 完整测试覆盖

## 许可证

本项目基于MIT许可证开源。

## 支持

如有问题或建议，请通过以下方式联系：
- 提交GitHub Issue
- 查看项目文档
- 联系开发者

---

**重要提醒**: 在使用本技能时，请确保遵守相关法律法规和数据使用协议。所有数据来源于同花顺问财，使用时请注明数据来源。