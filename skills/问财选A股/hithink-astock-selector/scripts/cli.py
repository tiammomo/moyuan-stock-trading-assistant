#!/usr/bin/env python3
"""
同花顺智能选股 - A股数据查询CLI
使用Python3标准库实现，无第三方依赖
注意：默认返回10条数据，可通过 --page 和 --limit 参数翻页获取更多数据
"""

import sys
import os
import json
import argparse
import urllib.request
import urllib.error


DEFAULT_API_URL = "https://openapi.iwencai.com/v1/query2data"
DEFAULT_PAGE = "1"
DEFAULT_LIMIT = "10"
DEFAULT_IS_CACHE = "1"
DEFAULT_EXPAND_INDEX = "true"


class AStockAPIError(Exception):
    """API错误异常类"""
    def __init__(self, message: str, status_code: int = None, response: str = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response = response


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="同花顺智能选股 - A股数据查询工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python3 scripts/cli.py --query "今日涨跌幅超过5%的A股有哪些？"
  python3 scripts/cli.py --query "科技股有哪些" --page "1" --limit "20"
  python3 scripts/cli.py --query "银行股" --api-key "your-key"

环境变量:
  IWENCAI_API_KEY   API密钥
  IWENCAI_API_URL   API地址（默认使用环境变量IWENCAI_API_URL的值）
        """
    )

    parser.add_argument(
        "--query", "-q",
        type=str,
        required=True,
        help="查询字符串（必填）"
    )

    parser.add_argument(
        "--page",
        type=str,
        default=DEFAULT_PAGE,
        help=f"分页参数（默认: {DEFAULT_PAGE}）"
    )

    parser.add_argument(
        "--limit",
        type=str,
        default=DEFAULT_LIMIT,
        help=f"每页条数（默认: {DEFAULT_LIMIT}）"
    )

    parser.add_argument(
        "--is-cache",
        type=str,
        default=DEFAULT_IS_CACHE,
        help=f"缓存参数（默认: {DEFAULT_IS_CACHE}）"
    )

    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="API密钥（默认从环境变量IWENCAI_API_KEY读取）"
    )

    return parser.parse_args()


def query_astock(query: str, page: str, limit: str,
                 is_cache: str, api_key: str) -> dict:
    """
    调用A股数据查询接口

    Args:
        query: 查询字符串
        page: 分页参数
        limit: 每页条数
        is_cache: 缓存参数
        api_key: API密钥

    Returns:
        包含datas、code_count、chunks_info等字段的字典

    Raises:
        AStockAPIError: API调用失败时抛出
    """
    # 获取API密钥
    if not api_key:
        api_key = os.environ.get("IWENCAI_API_KEY", "")
    if not api_key:
        raise AStockAPIError("API密钥未设置，请通过参数或环境变量IWENCAI_API_KEY指定")

    # 构造请求数据（使用传入的page和limit参数）
    payload = {
        "query": query,
        "page": page,
        "limit": limit,
        "is_cache": DEFAULT_IS_CACHE,
        "expand_index": DEFAULT_EXPAND_INDEX
    }

    # 构造请求头
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    # 使用默认API地址
    api_url = DEFAULT_API_URL

    # 创建请求对象
    request = urllib.request.Request(
        api_url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST"
    )

    try:
        # 发送请求
        with urllib.request.urlopen(request, timeout=30) as response:
            response_body = response.read().decode("utf-8")
            result = json.loads(response_body)

            # 检查响应是否包含错误
            if isinstance(result, dict):
                # 检查是否有错误信息 (status_code为0代表成功，不为0代表错误)
                if "status_code" in result and result["status_code"] != 0:
                    message = result.get("status_msg", "未知错误")
                    raise AStockAPIError(f"API返回错误: {message}")

                # 构造返回结果，包含 datas、code_count、chunks_info 等字段
                output = {
                    "datas": result.get("datas", []),
                    "code_count": result.get("code_count", 0),
                    "chunks_info": result.get("chunks_info", {}),
                    "page": page,
                    "limit": limit
                }
                return output
            return {"datas": [], "code_count": 0, "chunks_info": {}, "page": page, "limit": limit}

    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else ""
        raise AStockAPIError(
            f"HTTP错误 {e.code}: {e.reason}",
            status_code=e.code,
            response=error_body
        )
    except urllib.error.URLError as e:
        raise AStockAPIError(f"网络错误: {e.reason}")
    except json.JSONDecodeError as e:
        raise AStockAPIError(f"响应解析失败: {e}")


def main():
    """主函数"""
    args = parse_args()

    try:
        result = query_astock(
            query=args.query,
            page=args.page,
            limit=args.limit,
            is_cache=args.is_cache,
            api_key=args.api_key
        )

        datas = result.get("datas", [])
        code_count = result.get("code_count", 0)
        chunks_info = result.get("chunks_info", {})

        # 输出结果（JSON格式）
        output = {
            "success": True,
            "query": args.query,
            "code_count": code_count,
            "returned_count": len(datas),
            "page": args.page,
            "limit": args.limit,
            "has_more": code_count > len(datas),
            "chunks_info": chunks_info,
            "datas": datas
        }

        # 添加分页提示
        if code_count > len(datas):
            output["pagination_tip"] = f"共查到 {code_count} 只股票，当前返回第 {args.page} 页的 {len(datas)} 条。如需更多数据，请使用 --page 参数翻页。"

        print(json.dumps(output, ensure_ascii=False, indent=2))

    except AStockAPIError as e:
        error_output = {
            "success": False,
            "error": e.message
        }
        print(json.dumps(error_output, ensure_ascii=False, indent=2))
        sys.exit(1)
    except Exception as e:
        error_output = {
            "success": False,
            "error": f"发生错误: {str(e)}"
        }
        print(json.dumps(error_output, ensure_ascii=False, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()
