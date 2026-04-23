"""
investor搜索API客户端
基于问财财经资讯搜索接口实现
"""

import json
import time
from typing import List, Dict, Any, Optional
import requests

from config import config


class InvestorSearchAPIClient:
    """investor搜索API客户端"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        初始化API客户端
        
        Args:
            api_key: API密钥，如果为None则从环境变量获取
        """
        self.base_url = config.BASE_URL
        self.api_path = config.API_PATH
        self.api_url = config.API_URL
        
        if api_key:
            self.api_key = api_key
        else:
            self.api_key = config.get_api_key()
        
        if not self.api_key:
            raise ValueError(f"API密钥未设置，请设置环境变量 {config.ENV_API_KEY}")
        
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        # 请求统计
        self.request_count = 0
        self.last_request_time = 0
    
    def search(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        执行investor搜索
        
        Args:
            query: 搜索查询语句
            params: 额外参数，如limit、date_start、date_end等
            
        Returns:
            搜索结果列表
        """
        # 构建请求参数
        payload = self._build_payload(query, params)
        
        # 控制请求频率
        self._rate_limit()
        
        try:
            # 发送请求
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json=payload,
                timeout=30
            )
            
            # 更新统计
            self.request_count += 1
            self.last_request_time = time.time()
            
            # 处理响应
            if response.status_code == 200:
                data = response.json()
                return self._process_response(data)
            else:
                self._handle_error(response)
                return []
                
        except requests.exceptions.RequestException as e:
            print(f"API请求异常: {e}")
            return []
        except json.JSONDecodeError as e:
            print(f"JSON解析异常: {e}")
            return []
    
    def batch_search(self, queries: List[str], params: Optional[Dict[str, Any]] = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        批量搜索
        
        Args:
            queries: 搜索查询语句列表
            params: 额外参数
            
        Returns:
            按查询语句分组的搜索结果字典
        """
        results = {}
        
        for query in queries:
            print(f"正在搜索: {query}")
            results[query] = self.search(query, params)
            time.sleep(0.5)  # 批量请求间添加延迟
        
        return results
    
    def _build_payload(self, query: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """构建请求参数"""
        payload = config.get_base_payload()
        payload["query"] = query
        
        # 添加额外参数
        if params:
            # 处理日期范围
            date_query_parts = []
            if params.get("date_start"):
                date_query_parts.append(f"发布时间>={params['date_start']}")
            if params.get("date_end"):
                date_query_parts.append(f"发布时间<={params['date_end']}")
            
            if date_query_parts:
                payload["query"] = f"{query} {' '.join(date_query_parts)}"
            
            # 处理公司过滤
            if params.get("company"):
                payload["query"] = f"{payload['query']} {params['company']}"
        
        return payload
    
    def _process_response(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """处理API响应"""
        results = data.get("data", [])
        
        # 添加数据来源标记
        for result in results:
            result["source"] = "同花顺问财"
        
        return results
    
    def _handle_error(self, response: requests.Response):
        """处理错误响应"""
        status_code = response.status_code
        
        if status_code == 400:
            print("错误: 请求参数错误")
        elif status_code == 401:
            print("错误: API密钥无效或过期")
            print(f"请检查环境变量 {config.ENV_API_KEY} 是否正确设置")
        elif status_code == 403:
            print("错误: 权限不足")
        elif status_code == 429:
            print("错误: 请求频率超限，请稍后重试")
        elif status_code == 500:
            print("错误: 服务器内部错误")
        else:
            print(f"错误: HTTP {status_code}")
        
        try:
            error_data = response.json()
            print(f"错误详情: {error_data}")
        except:
            print(f"响应内容: {response.text[:200]}")
    
    def _rate_limit(self):
        """请求频率控制"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        # 如果距离上次请求不足1秒，等待
        if time_since_last < 1.0:
            time.sleep(1.0 - time_since_last)
    
    def get_request_stats(self) -> Dict[str, Any]:
        """获取请求统计信息"""
        return {
            "request_count": self.request_count,
            "last_request_time": self.last_request_time
        }


def create_api_client() -> InvestorSearchAPIClient:
    """创建API客户端实例"""
    return InvestorSearchAPIClient()