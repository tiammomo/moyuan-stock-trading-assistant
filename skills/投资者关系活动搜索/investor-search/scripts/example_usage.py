#!/usr/bin/env python3
"""
investor搜索使用示例
"""

import os
import sys

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from investor_search import create_search
from config import config


def example_basic_search():
    """基本搜索示例"""
    print("=" * 60)
    print("示例1: 基本搜索")
    print("=" * 60)
    
    # 创建搜索实例
    search = create_search()
    
    # 执行搜索
    results = search.search("贵州茅台投资者关系活动", limit=3)
    
    # 生成报告
    if results:
        report = search.generate_report(results)
        print(report)
    else:
        print("未找到相关结果")
    
    print()


def example_search_with_filters():
    """带过滤器的搜索示例"""
    print("=" * 60)
    print("示例2: 带过滤器的搜索")
    print("=" * 60)
    
    search = create_search()
    
    # 带公司过滤的搜索
    results = search.search(
        "人工智能 调研",
        company="科大讯飞",
        activity_type="调研",
        date_start="2024-01-01",
        limit=3
    )
    
    if results:
        report = search.generate_report(results, format="text")
        print(report)
    else:
        print("未找到相关结果")
    
    print()


def example_batch_search():
    """批量搜索示例"""
    print("=" * 60)
    print("示例3: 批量搜索")
    print("=" * 60)
    
    search = create_search()
    
    # 批量查询
    queries = [
        "贵州茅台投资者关系活动",
        "五粮液业绩说明会",
        "宁德时代路演活动"
    ]
    
    print(f"执行批量搜索 ({len(queries)} 条查询):")
    for query in queries:
        print(f"  - {query}")
    
    print()
    
    # 执行批量搜索
    all_results = search.batch_search(queries, limit=2)
    
    # 输出结果
    total_results = 0
    for query, results in all_results.items():
        total_results += len(results)
        print(f"查询: {query}")
        print(f"找到 {len(results)} 条记录")
        
        if results:
            for i, result in enumerate(results, 1):
                print(f"  {i}. {result.get('company', '')} - {result.get('activity_type', '')} - {result.get('date', '')}")
                print(f"     标题: {result.get('title', '')[:60]}...")
        print()
    
    print(f"批量搜索完成，共找到 {total_results} 条记录")
    print()


def example_save_to_file():
    """保存到文件示例"""
    print("=" * 60)
    print("示例4: 保存到文件")
    print("=" * 60)
    
    search = create_search()
    
    # 执行搜索
    results = search.search("新能源行业路演", limit=5)
    
    if results:
        # 保存为CSV
        csv_file = "新能源路演活动.csv"
        search.save_results(results, csv_file, "csv")
        print(f"数据已保存到CSV文件: {csv_file}")
        
        # 保存为JSON
        json_file = "新能源路演活动.json"
        search.save_results(results, json_file, "json")
        print(f"数据已保存到JSON文件: {json_file}")
        
        # 生成Markdown报告
        md_file = "新能源路演活动.md"
        report = search.generate_report(results, "markdown")
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"报告已保存到Markdown文件: {md_file}")
    else:
        print("未找到相关结果")
    
    print()


def example_query_analysis():
    """查询分析示例"""
    print("=" * 60)
    print("示例5: 查询分析")
    print("=" * 60)
    
    search = create_search()
    
    # 测试查询分析
    test_queries = [
        "最近贵州茅台和五粮液的投资者关系活动",
        "人工智能公司最近一年的调研记录",
        "新能源行业业绩说明会",
        "科技公司路演活动"
    ]
    
    for query in test_queries:
        print(f"原始查询: {query}")
        queries, params = search.analyze_query(query)
        
        print(f"  分析结果:")
        print(f"    拆解为 {len(queries)} 个查询:")
        for q in queries:
            print(f"      - {q}")
        
        if params:
            print(f"    提取的参数: {params}")
        
        print()


def example_cli_usage():
    """CLI使用示例"""
    print("=" * 60)
    print("示例6: CLI命令示例")
    print("=" * 60)
    
    print("以下是在命令行中使用的示例命令:\n")
    
    print("1. 基本搜索:")
    print("   investor-search \"贵州茅台投资者关系活动\"\n")
    
    print("2. 带参数搜索:")
    print("   investor-search \"人工智能公司调研\" --company \"科大讯飞\" --date-start \"2024-01-01\"\n")
    
    print("3. 输出到文件:")
    print("   investor-search \"新能源行业路演\" --output \"results.csv\" --format csv\n")
    
    print("4. 批量处理:")
    print("   investor-search --input-file \"queries.txt\" --output-dir \"results/\"\n")
    
    print("5. 显示帮助:")
    print("   investor-search --help\n")
    
    print("6. 显示版本:")
    print("   investor-search --version\n")
    
    print("7. 显示统计:")
    print("   investor-search --stats\n")


def check_environment():
    """检查环境配置"""
    print("=" * 60)
    print("环境检查")
    print("=" * 60)
    
    # 检查API密钥
    api_key = config.get_api_key()
    if api_key:
        print(f"✓ API密钥已设置 (环境变量: {config.ENV_API_KEY})")
        print(f"  密钥前几位: {api_key[:10]}...")
    else:
        print(f"✗ API密钥未设置")
        print(f"  请设置环境变量: export {config.ENV_API_KEY}=\"your_api_key_here\"")
    
    # 检查Python版本
    python_version = sys.version_info
    print(f"✓ Python版本: {python_version.major}.{python_version.minor}.{python_version.micro}")
    
    # 检查必要模块
    required_modules = ['requests', 'pandas', 'tabulate']
    missing_modules = []
    
    for module in required_modules:
        try:
            __import__(module)
            print(f"✓ 模块 {module} 已安装")
        except ImportError:
            print(f"✗ 模块 {module} 未安装")
            missing_modules.append(module)
    
    if missing_modules:
        print(f"\n请安装缺失的模块:")
        print(f"  pip install {' '.join(missing_modules)}")
    
    print()


def main():
    """主函数"""
    print("investor搜索技能 - 使用示例")
    print("=" * 60)
    print("数据来源: 同花顺问财")
    print()
    
    # 检查环境
    check_environment()
    
    # 运行示例
    example_basic_search()
    example_search_with_filters()
    example_batch_search()
    example_save_to_file()
    example_query_analysis()
    example_cli_usage()
    
    print("=" * 60)
    print("示例运行完成!")
    print("=" * 60)


if __name__ == "__main__":
    main()