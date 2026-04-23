"""
investor搜索核心模块
"""

import os
import sys
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta

from api_client import InvestorSearchAPIClient, create_api_client
from data_processor import InvestorDataProcessor, create_data_processor
from config import config


class InvestorSearch:
    """investor搜索主类"""
    
    def __init__(self, api_client: Optional[InvestorSearchAPIClient] = None, 
                 data_processor: Optional[InvestorDataProcessor] = None):
        """
        初始化搜索类
        
        Args:
            api_client: API客户端实例
            data_processor: 数据处理实例
        """
        self.api_client = api_client or create_api_client()
        self.data_processor = data_processor or create_data_processor()
        
        # 查询历史记录
        self.query_history = []
    
    def search(self, query: str, **kwargs) -> List[Dict[str, Any]]:
        """
        执行investor搜索
        
        Args:
            query: 搜索查询语句
            **kwargs: 额外参数
                - company: 公司名称
                - activity_type: 活动类型
                - date_start: 开始日期
                - date_end: 结束日期
                - limit: 结果数量限制
                
        Returns:
            搜索结果列表
        """
        # 记录查询历史
        self.query_history.append({
            "query": query,
            "params": kwargs,
            "timestamp": datetime.now().isoformat()
        })
        
        # 构建查询参数
        search_params = self._build_search_params(query, kwargs)
        
        # 执行搜索
        raw_results = self.api_client.search(
            query=search_params["query"],
            params=search_params["params"]
        )
        
        # 处理结果
        if raw_results:
            processed_results = self.data_processor.process_search_results(raw_results)
            
            # 应用结果限制
            limit = kwargs.get("limit", config.DEFAULT_LIMIT)
            if limit and len(processed_results) > limit:
                processed_results = processed_results[:limit]
            
            return processed_results
        else:
            return []
    
    def batch_search(self, queries: List[str], **kwargs) -> Dict[str, List[Dict[str, Any]]]:
        """
        批量搜索
        
        Args:
            queries: 查询语句列表
            **kwargs: 额外参数
            
        Returns:
            按查询分组的搜索结果
        """
        all_results = {}
        
        for query in queries:
            results = self.search(query, **kwargs)
            all_results[query] = results
        
        return all_results
    
    def search_with_filters(self, query: str, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        使用过滤器搜索
        
        Args:
            query: 搜索查询语句
            filters: 过滤器字典
                - companies: 公司列表
                - activity_types: 活动类型列表
                - date_range: 日期范围
                - min_participants: 最小参与机构数
                
        Returns:
            搜索结果列表
        """
        # 如果有多个公司，拆分为多个查询
        companies = filters.get("companies", [])
        if companies and len(companies) > 1:
            all_results = []
            for company in companies:
                company_query = f"{query} {company}"
                results = self.search(company_query, **filters)
                all_results.extend(results)
            
            # 去重和排序
            unique_results = self._deduplicate_results(all_results)
            return unique_results
        else:
            # 单个公司查询
            if companies:
                query = f"{query} {companies[0]}"
            
            return self.search(query, **filters)
    
    def _build_search_params(self, query: str, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """构建搜索参数"""
        params = {}
        
        # 处理公司过滤
        if "company" in kwargs and kwargs["company"]:
            query = f"{query} {kwargs['company']}"
        
        # 处理活动类型过滤
        if "activity_type" in kwargs and kwargs["activity_type"]:
            activity_type = kwargs["activity_type"]
            activity_keywords = {
                "调研": "调研",
                "会议": "会议",
                "采访": "采访",
                "说明会": "说明会",
                "发布会": "发布会",
                "路演": "路演",
                "参观": "参观"
            }
            
            if activity_type in activity_keywords:
                query = f"{query} {activity_keywords[activity_type]}"
        
        # 处理日期范围
        if "date_start" in kwargs and kwargs["date_start"]:
            params["date_start"] = kwargs["date_start"]
        
        if "date_end" in kwargs and kwargs["date_end"]:
            params["date_end"] = kwargs["date_end"]
        
        # 如果没有日期范围，默认搜索最近一年
        if "date_start" not in params and "date_end" not in params:
            one_year_ago = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
            params["date_start"] = one_year_ago
        
        return {
            "query": query,
            "params": params
        }
    
    def _deduplicate_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """去重结果"""
        seen_titles = set()
        unique_results = []
        
        for result in results:
            title = result.get("title", "")
            if title and title not in seen_titles:
                seen_titles.add(title)
                unique_results.append(result)
        
        return unique_results
    
    def generate_report(self, results: List[Dict[str, Any]], format: str = "markdown") -> str:
        """
        生成报告
        
        Args:
            results: 搜索结果
            format: 报告格式
        """
        return self.data_processor.generate_report(results, format)
    
    def save_results(self, results: List[Dict[str, Any]], filepath: str, format: str = "csv"):
        """
        保存结果到文件
        
        Args:
            results: 要保存的结果
            filepath: 文件路径
            format: 文件格式，支持 "csv", "json"
        """
        if format == "csv":
            self.data_processor.save_to_csv(results, filepath)
        elif format == "json":
            self.data_processor.save_to_json(results, filepath)
        else:
            print(f"不支持的格式: {format}")
    
    def get_search_stats(self) -> Dict[str, Any]:
        """获取搜索统计信息"""
        api_stats = self.api_client.get_request_stats()
        
        return {
            "total_queries": len(self.query_history),
            "api_request_count": api_stats.get("request_count", 0),
            "last_request_time": api_stats.get("last_request_time", 0),
            "query_history": self.query_history[-10:]  # 最近10条查询
        }
    
    def analyze_query(self, user_query: str) -> Tuple[List[str], Dict[str, Any]]:
        """
        分析用户查询，决定是否拆解
        
        Args:
            user_query: 用户原始查询
            
        Returns:
            (queries, params): 查询列表和参数
        """
        queries = []
        params = {}
        
        # 检查是否包含多个公司
        common_companies = [
            "茅台", "五粮液", "泸州老窖", "洋河", "山西汾酒",
            "工商银行", "建设银行", "农业银行", "中国银行", "招商银行",
            "中国平安", "中国人寿", "中国太保", "新华保险",
            "宁德时代", "比亚迪", "隆基绿能", "通威股份",
            "恒瑞医药", "药明康德", "迈瑞医疗", "长春高新"
        ]
        
        found_companies = []
        for company in common_companies:
            if company in user_query:
                found_companies.append(company)
        
        # 如果找到多个公司，拆分为多个查询
        if len(found_companies) > 1:
            for company in found_companies:
                # 从原查询中移除公司名，避免重复
                clean_query = user_query
                for comp in found_companies:
                    clean_query = clean_query.replace(comp, "")
                clean_query = clean_query.strip()
                
                if clean_query:
                    queries.append(f"{clean_query} {company}")
                else:
                    queries.append(f"投资者关系活动 {company}")
            
            # 提取其他参数
            params = self._extract_params_from_query(user_query)
            
        else:
            # 单个查询
            queries = [user_query]
            params = self._extract_params_from_query(user_query)
        
        return queries, params
    
    def _extract_params_from_query(self, query: str) -> Dict[str, Any]:
        """从查询中提取参数"""
        params = {}
        
        # 检查活动类型关键词
        activity_keywords = {
            "调研": "调研",
            "会议": "会议",
            "采访": "采访",
            "说明会": "说明会",
            "发布会": "发布会",
            "路演": "路演",
            "参观": "参观"
        }
        
        for keyword, activity_type in activity_keywords.items():
            if keyword in query:
                params["activity_type"] = activity_type
                break
        
        # 检查日期关键词
        date_patterns = [
            ("最近一周", 7),
            ("最近一月", 30),
            ("最近三月", 90),
            ("最近半年", 180),
            ("最近一年", 365),
            ("今年", "current_year"),
            ("去年", "last_year")
        ]
        
        for pattern, days in date_patterns:
            if pattern in query:
                if days == "current_year":
                    params["date_start"] = datetime.now().replace(month=1, day=1).strftime("%Y-%m-%d")
                elif days == "last_year":
                    last_year = datetime.now().year - 1
                    params["date_start"] = f"{last_year}-01-01"
                    params["date_end"] = f"{last_year}-12-31"
                else:
                    date_start = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
                    params["date_start"] = date_start
                break
        
        return params


def create_search() -> InvestorSearch:
    """创建搜索实例"""
    return InvestorSearch()


def main():
    """命令行入口函数"""
    # 检查配置
    if not config.validate_config():
        sys.exit(1)
    
    # 创建搜索实例
    search = create_search()
    
    # 示例搜索
    print("investor搜索示例")
    print("=" * 50)
    
    # 示例1: 基本搜索
    print("\n1. 搜索贵州茅台投资者关系活动:")
    results = search.search("贵州茅台投资者关系活动", limit=3)
    
    if results:
        report = search.generate_report(results)
        print(report)
    else:
        print("未找到相关结果")
    
    # 示例2: 带过滤搜索
    print("\n2. 搜索人工智能公司调研记录:")
    results = search.search("人工智能 调研", activity_type="调研", limit=3)
    
    if results:
        report = search.generate_report(results)
        print(report)
    else:
        print("未找到相关结果")
    
    # 获取统计信息
    stats = search.get_search_stats()
    print(f"\n搜索统计:")
    print(f"- 总查询次数: {stats['total_queries']}")
    print(f"- API请求次数: {stats['api_request_count']}")


if __name__ == "__main__":
    main()