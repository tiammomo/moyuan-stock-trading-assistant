"""
investor搜索CLI接口
"""

import argparse
import sys
import os
from typing import List, Optional
import json

from investor_search import InvestorSearch, create_search
from config import config


def create_parser() -> argparse.ArgumentParser:
    """
    创建CLI参数解析器
    
    Returns:
        argparse.ArgumentParser实例
    """
    parser = argparse.ArgumentParser(
        description="investor搜索工具 - 搜索A股上市公司投资者关系相关内容",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  investor-search "贵州茅台投资者关系活动"
  investor-search "人工智能公司调研" --company "科大讯飞" --date-start "2024-01-01"
  investor-search "新能源行业路演" --output "results.csv" --format csv
  investor-search --input-file "queries.txt" --output-dir "results/"
  investor-search --version
        """
    )
    
    # 必需参数
    parser.add_argument(
        "query",
        nargs="?",
        help="搜索查询语句"
    )
    
    # 搜索参数
    search_group = parser.add_argument_group("搜索参数")
    
    search_group.add_argument(
        "--company",
        help="指定公司名称"
    )
    
    search_group.add_argument(
        "--activity-type",
        choices=["调研", "会议", "采访", "说明会", "发布会", "路演", "参观"],
        help="活动类型"
    )
    
    search_group.add_argument(
        "--date-start",
        help="开始日期 (YYYY-MM-DD)"
    )
    
    search_group.add_argument(
        "--date-end",
        help="结束日期 (YYYY-MM-DD)"
    )
    
    search_group.add_argument(
        "--limit",
        type=int,
        default=config.DEFAULT_LIMIT,
        help=f"限制返回结果数量 (默认: {config.DEFAULT_LIMIT})"
    )
    
    # 输出参数
    output_group = parser.add_argument_group("输出参数")
    
    output_group.add_argument(
        "--output",
        "-o",
        help="输出文件路径"
    )
    
    output_group.add_argument(
        "--format",
        choices=["csv", "json", "markdown", "text"],
        default=config.DEFAULT_OUTPUT_FORMAT,
        help=f"输出格式 (默认: {config.DEFAULT_OUTPUT_FORMAT})"
    )
    
    output_group.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="详细输出模式"
    )
    
    # 文件处理参数
    file_group = parser.add_argument_group("文件处理参数")
    
    file_group.add_argument(
        "--input-file",
        "-i",
        help="输入文件路径（批量查询）"
    )
    
    file_group.add_argument(
        "--output-dir",
        help="输出目录路径"
    )
    
    # 其他参数
    other_group = parser.add_argument_group("其他参数")
    
    other_group.add_argument(
        "--version",
        action="store_true",
        help="显示版本信息"
    )
    
    other_group.add_argument(
        "--stats",
        action="store_true",
        help="显示搜索统计信息"
    )
    
    return parser


def read_queries_from_file(filepath: str) -> List[str]:
    """
    从文件读取查询语句
    
    Args:
        filepath: 文件路径
        
    Returns:
        查询语句列表
    """
    queries = []
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    queries.append(line)
        
        print(f"从文件读取了 {len(queries)} 条查询语句")
        return queries
        
    except FileNotFoundError:
        print(f"错误: 文件不存在: {filepath}")
        return []
    except Exception as e:
        print(f"读取文件时出错: {e}")
        return []


def save_results_to_file(results, filepath: str, format: str):
    """
    保存结果到文件
    
    Args:
        results: 搜索结果
        filepath: 文件路径
        format: 文件格式
    """
    try:
        search = create_search()
        search.save_results(results, filepath, format)
    except Exception as e:
        print(f"保存文件时出错: {e}")


def print_results(results: List[dict], format: str = "markdown", verbose: bool = False):
    """
    打印结果
    
    Args:
        results: 搜索结果
        format: 输出格式
        verbose: 是否详细输出
    """
    if not results:
        print("未找到相关投资者关系活动信息。")
        return
    
    search = create_search()
    
    if format == "markdown":
        report = search.generate_report(results, "markdown")
        print(report)
    
    elif format == "text":
        report = search.generate_report(results, "text")
        print(report)
    
    elif format == "json":
        print(json.dumps(results, ensure_ascii=False, indent=2))
    
    elif format == "csv":
        # 简单表格输出
        print(f"共找到 {len(results)} 条记录:")
        print("-" * 100)
        print(f"{'序号':<4} {'公司':<10} {'活动类型':<8} {'日期':<12} {'标题':<50}")
        print("-" * 100)
        
        for i, item in enumerate(results, 1):
            title = item.get('title', '')[:45] + '...' if len(item.get('title', '')) > 45 else item.get('title', '')
            print(f"{i:<4} {item.get('company', ''):<10} {item.get('activity_type', ''):<8} "
                  f"{item.get('date', ''):<12} {title:<50}")
        
        print("-" * 100)
        print("数据来源: 同花顺问财")
    
    # 详细输出模式
    if verbose:
        print("\n详细统计信息:")
        stats = search.get_search_stats()
        print(f"- 总查询次数: {stats['total_queries']}")
        print(f"- API请求次数: {stats['api_request_count']}")
        
        if stats['query_history']:
            print(f"- 最近查询: {stats['query_history'][-1]['query']}")


def handle_batch_search(input_file: str, output_dir: Optional[str], **kwargs):
    """
    处理批量搜索
    
    Args:
        input_file: 输入文件路径
        output_dir: 输出目录路径
        **kwargs: 其他参数
    """
    # 读取查询语句
    queries = read_queries_from_file(input_file)
    if not queries:
        return
    
    # 创建搜索实例
    search = create_search()
    
    # 执行批量搜索
    print(f"开始批量搜索 {len(queries)} 条查询...")
    all_results = search.batch_search(queries, **kwargs)
    
    # 处理结果
    total_results = 0
    for query, results in all_results.items():
        total_results += len(results)
        
        # 生成报告
        report = search.generate_report(results, kwargs.get('format', 'markdown'))
        
        # 输出到文件或控制台
        if output_dir:
            # 创建输出目录
            os.makedirs(output_dir, exist_ok=True)
            
            # 生成安全的文件名
            safe_filename = query.replace(' ', '_').replace('/', '_')[:50]
            output_file = os.path.join(output_dir, f"{safe_filename}.{kwargs.get('format', 'md')}")
            
            # 保存报告
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report)
            
            print(f"查询 '{query}' 的结果已保存到: {output_file}")
        
        else:
            print(f"\n查询: {query}")
            print("-" * 50)
            print(report)
    
    print(f"\n批量搜索完成!")
    print(f"- 总查询数: {len(queries)}")
    print(f"- 总结果数: {total_results}")
    
    # 保存汇总数据
    if output_dir and kwargs.get('format') in ['csv', 'json']:
        # 合并所有结果
        all_results_list = []
        for results in all_results.values():
            all_results_list.extend(results)
        
        if all_results_list:
            summary_file = os.path.join(output_dir, f"summary.{kwargs.get('format')}")
            search.save_results(all_results_list, summary_file, kwargs.get('format'))
            print(f"- 汇总数据已保存到: {summary_file}")


def show_version():
    """显示版本信息"""
    version_info = {
        "技能名称": "investor搜索",
        "版本": "1.0.0",
        "描述": "搜索A股上市公司投资者关系相关内容",
        "数据来源": "同花顺问财",
        "接口地址": config.API_URL
    }
    
    print("investor搜索工具")
    print("=" * 50)
    for key, value in version_info.items():
        print(f"{key}: {value}")


def main():
    """主函数"""
    # 创建参数解析器
    parser = create_parser()
    args = parser.parse_args()
    
    # 显示版本信息
    if args.version:
        show_version()
        return
    
    # 检查配置
    if not config.validate_config():
        sys.exit(1)
    
    # 显示统计信息
    if args.stats:
        search = create_search()
        stats = search.get_search_stats()
        print("搜索统计信息:")
        print(json.dumps(stats, ensure_ascii=False, indent=2))
        return
    
    # 检查是否有查询输入
    if not args.query and not args.input_file:
        parser.print_help()
        print("\n错误: 必须提供查询语句或输入文件")
        sys.exit(1)
    
    # 构建搜索参数
    search_kwargs = {}
    if args.company:
        search_kwargs["company"] = args.company
    if args.activity_type:
        search_kwargs["activity_type"] = args.activity_type
    if args.date_start:
        search_kwargs["date_start"] = args.date_start
    if args.date_end:
        search_kwargs["date_end"] = args.date_end
    if args.limit:
        search_kwargs["limit"] = args.limit
    
    # 处理批量搜索
    if args.input_file:
        handle_batch_search(
            input_file=args.input_file,
            output_dir=args.output_dir,
            format=args.format,
            **search_kwargs
        )
        return
    
    # 单个查询搜索
    search = create_search()
    results = search.search(args.query, **search_kwargs)
    
    # 输出结果
    if args.output:
        # 保存到文件
        save_results_to_file(results, args.output, args.format)
        
        # 同时在控制台显示摘要
        if args.verbose:
            print(f"搜索结果已保存到: {args.output}")
            print(f"共找到 {len(results)} 条记录")
    else:
        # 输出到控制台
        print_results(results, args.format, args.verbose)


if __name__ == "__main__":
    main()