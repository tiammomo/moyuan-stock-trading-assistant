#!/usr/bin/env python3
"""
investor搜索技能基本测试
"""

import unittest
import os
import sys
from unittest.mock import Mock, patch

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from investor_search import InvestorSearch
from api_client import InvestorSearchAPIClient
from data_processor import InvestorDataProcessor
from config import config


class TestConfig(unittest.TestCase):
    """配置测试"""
    
    def test_config_constants(self):
        """测试配置常量"""
        self.assertEqual(config.BASE_URL, "https://openapi.iwencai.com")
        self.assertEqual(config.API_PATH, "/v1/comprehensive/search")
        self.assertEqual(config.CHANNELS, ["investor"])
        self.assertEqual(config.APP_ID, "AIME_SKILL")
        self.assertEqual(config.DEFAULT_LIMIT, 20)
        self.assertEqual(config.DEFAULT_OUTPUT_FORMAT, "markdown")
        self.assertEqual(config.ENV_API_KEY, "IWENCAI_API_KEY")
    
    @patch.dict(os.environ, {"IWENCAI_API_KEY": "test_key_12345"})
    def test_get_api_key(self):
        """测试获取API密钥"""
        api_key = config.get_api_key()
        self.assertEqual(api_key, "test_key_12345")
    
    @patch.dict(os.environ, {}, clear=True)
    def test_get_api_key_missing(self):
        """测试API密钥缺失"""
        api_key = config.get_api_key()
        self.assertIsNone(api_key)
    
    @patch.dict(os.environ, {"IWENCAI_API_KEY": "test_key"})
    def test_validate_config(self):
        """测试配置验证"""
        self.assertTrue(config.validate_config())
    
    @patch.dict(os.environ, {}, clear=True)
    def test_validate_config_missing(self):
        """测试配置验证缺失"""
        self.assertFalse(config.validate_config())


class TestDataProcessor(unittest.TestCase):
    """数据处理测试"""
    
    def setUp(self):
        self.processor = InvestorDataProcessor()
    
    def test_parse_date(self):
        """测试日期解析"""
        # 测试完整日期时间
        date_str = "2024-01-15 14:30:00"
        result = self.processor._parse_date(date_str)
        self.assertEqual(result, "2024-01-15")
        
        # 测试简单日期
        date_str = "2024-01-15"
        result = self.processor._parse_date(date_str)
        self.assertEqual(result, "2024-01-15")
        
        # 测试其他格式
        date_str = "2024/01/15"
        result = self.processor._parse_date(date_str)
        self.assertEqual(result, "2024-01-15")
        
        # 测试空字符串
        date_str = ""
        result = self.processor._parse_date(date_str)
        self.assertEqual(result, "")
    
    def test_extract_company(self):
        """测试提取公司名称"""
        # 测试包含公司名的标题
        title = "贵州茅台2024年投资者关系活动记录"
        summary = "贵州茅台公司近期举行了投资者关系活动..."
        result = self.processor._extract_company(title, summary)
        self.assertEqual(result, "茅台")
        
        # 测试包含公司名的摘要
        title = "投资者关系活动"
        summary = "五粮液公司举办了业绩说明会..."
        result = self.processor._extract_company(title, summary)
        self.assertEqual(result, "五粮液")
        
        # 测试未知公司
        title = "某公司活动"
        summary = "某公司举办了活动..."
        result = self.processor._extract_company(title, summary)
        self.assertEqual(result, "未知公司")
    
    def test_identify_activity_type(self):
        """测试识别活动类型"""
        # 测试调研活动
        title = "贵州茅台调研活动记录"
        summary = "公司组织了调研活动..."
        result = self.processor._identify_activity_type(title, summary)
        self.assertEqual(result, "调研")
        
        # 测试会议活动
        title = "分析师会议纪要"
        summary = "公司召开了分析师会议..."
        result = self.processor._identify_activity_type(title, summary)
        self.assertEqual(result, "会议")
        
        # 测试其他活动
        title = "公司活动"
        summary = "公司举办了活动..."
        result = self.processor._identify_activity_type(title, summary)
        self.assertEqual(result, "其他")
    
    def test_process_single_result(self):
        """测试处理单个结果"""
        raw_result = {
            "title": "贵州茅台调研活动记录",
            "summary": "贵州茅台公司于2024年1月15日组织了调研活动，多家投资机构参与...",
            "url": "https://example.com/article/123",
            "publish_date": "2024-01-15 14:30:00",
            "source": "同花顺问财"
        }
        
        result = self.processor._process_single_result(raw_result)
        
        self.assertIsNotNone(result)
        self.assertEqual(result["company"], "茅台")
        self.assertEqual(result["activity_type"], "调研")
        self.assertEqual(result["date"], "2024-01-15")
        self.assertEqual(result["title"], raw_result["title"])
        self.assertTrue(result["summary"].startswith("贵州茅台公司于2024年1月15日组织了调研活动"))
        self.assertEqual(result["source"], "同花顺问财")
        self.assertEqual(result["url"], raw_result["url"])
    
    def test_generate_markdown_report(self):
        """测试生成Markdown报告"""
        processed_data = [
            {
                "company": "茅台",
                "activity_type": "调研",
                "date": "2024-01-15",
                "title": "贵州茅台调研活动记录",
                "summary": "调研活动摘要...",
                "participants": ["机构A", "机构B"],
                "topics": ["业绩增长", "市场前景"],
                "source": "同花顺问财",
                "url": "https://example.com/article/123"
            }
        ]
        
        report = self.processor._generate_markdown_report(processed_data)
        
        self.assertIsInstance(report, str)
        self.assertIn("investor搜索结果", report)
        self.assertIn("数据来源：同花顺问财", report)
        self.assertIn("茅台", report)
        self.assertIn("调研", report)


class TestAPIClient(unittest.TestCase):
    """API客户端测试"""
    
    @patch('requests.post')
    def test_search_success(self, mock_post):
        """测试搜索成功"""
        # 模拟API响应
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {
                    "title": "测试文章",
                    "summary": "测试摘要",
                    "url": "https://example.com",
                    "publish_date": "2024-01-15 14:30:00"
                }
            ]
        }
        mock_post.return_value = mock_response
        
        # 创建客户端
        client = InvestorSearchAPIClient(api_key="test_key")
        
        # 执行搜索
        results = client.search("测试查询")
        
        # 验证结果
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "测试文章")
        self.assertEqual(results[0]["source"], "同花顺问财")
        
        # 验证请求参数
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        self.assertEqual(call_args[0][0], "https://openapi.iwencai.com/v1/comprehensive/search")
        
        # 验证请求头
        headers = call_args[1]['headers']
        self.assertEqual(headers['Authorization'], 'Bearer test_key')
        
        # 验证请求体
        json_data = call_args[1]['json']
        self.assertEqual(json_data['channels'], ['investor'])
        self.assertEqual(json_data['app_id'], 'AIME_SKILL')
        self.assertEqual(json_data['query'], '测试查询')
    
    @patch('requests.post')
    def test_search_error(self, mock_post):
        """测试搜索错误"""
        # 模拟API错误响应
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_post.return_value = mock_response
        
        # 创建客户端
        client = InvestorSearchAPIClient(api_key="test_key")
        
        # 执行搜索
        results = client.search("测试查询")
        
        # 验证结果为空
        self.assertEqual(len(results), 0)


class TestInvestorSearch(unittest.TestCase):
    """主搜索类测试"""
    
    def setUp(self):
        # 创建模拟对象
        self.mock_api_client = Mock(spec=InvestorSearchAPIClient)
        self.mock_data_processor = Mock(spec=InvestorDataProcessor)
        
        # 创建搜索实例
        self.search = InvestorSearch(
            api_client=self.mock_api_client,
            data_processor=self.mock_data_processor
        )
    
    def test_search_basic(self):
        """测试基本搜索"""
        # 模拟API响应
        mock_raw_results = [
            {"title": "测试文章1", "summary": "摘要1"},
            {"title": "测试文章2", "summary": "摘要2"}
        ]
        
        # 模拟数据处理结果
        mock_processed_results = [
            {"company": "测试公司", "title": "测试文章1"},
            {"company": "测试公司", "title": "测试文章2"}
        ]
        
        # 设置模拟行为
        self.mock_api_client.search.return_value = mock_raw_results
        self.mock_data_processor.process_search_results.return_value = mock_processed_results
        
        # 执行搜索
        results = self.search.search("测试查询", limit=2)
        
        # 验证结果
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["company"], "测试公司")
        
        # 验证API调用
        self.mock_api_client.search.assert_called_once()
        
        # 验证数据处理调用
        self.mock_data_processor.process_search_results.assert_called_once_with(mock_raw_results)
    
    def test_analyze_query_single(self):
        """测试分析单个查询"""
        query = "贵州茅台投资者关系活动"
        
        queries, params = self.search.analyze_query(query)
        
        self.assertEqual(len(queries), 1)
        self.assertEqual(queries[0], query)
        self.assertEqual(params, {})
    
    def test_analyze_query_multiple_companies(self):
        """测试分析包含多个公司的查询"""
        query = "最近贵州茅台和五粮液的投资者关系活动"
        
        queries, params = self.search.analyze_query(query)
        
        # 应该拆分为两个查询
        self.assertGreaterEqual(len(queries), 2)
        
        # 每个查询应该包含公司名
        for q in queries:
            self.assertTrue("茅台" in q or "五粮液" in q)


class TestIntegration(unittest.TestCase):
    """集成测试"""
    
    @patch.dict(os.environ, {"IWENCAI_API_KEY": "test_key"})
    def test_create_search(self):
        """测试创建搜索实例"""
        from investor_search import create_search
        
        search = create_search()
        
        self.assertIsInstance(search, InvestorSearch)
        self.assertIsInstance(search.api_client, InvestorSearchAPIClient)
        self.assertIsInstance(search.data_processor, InvestorDataProcessor)


def run_tests():
    """运行所有测试"""
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试类
    suite.addTests(loader.loadTestsFromTestCase(TestConfig))
    suite.addTests(loader.loadTestsFromTestCase(TestDataProcessor))
    suite.addTests(loader.loadTestsFromTestCase(TestAPIClient))
    suite.addTests(loader.loadTestsFromTestCase(TestInvestorSearch))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    print("运行investor搜索技能测试...")
    print("=" * 60)
    
    success = run_tests()
    
    print("=" * 60)
    if success:
        print("所有测试通过!")
    else:
        print("部分测试失败!")
    
    sys.exit(0 if success else 1)