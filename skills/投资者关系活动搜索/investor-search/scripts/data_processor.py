"""
investor搜索数据处理模块
"""

import csv
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
import os


class InvestorDataProcessor:
    """investor搜索数据处理"""
    
    def __init__(self):
        self.activity_types = {
            "调研": ["调研", "走访", "考察", "参观"],
            "会议": ["会议", "交流会", "座谈会", "研讨会"],
            "采访": ["采访", "访谈", "专访", "对话"],
            "说明会": ["说明会", "业绩说明会", "发布会", "通报会"],
            "路演": ["路演", "推介会", "投资者日"],
            "其他": ["活动", "沟通", "交流"]
        }
    
    def process_search_results(self, raw_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        处理API返回的原始数据
        
        Args:
            raw_results: API返回的原始数据
            
        Returns:
            处理后的数据
        """
        processed_results = []
        
        for result in raw_results:
            processed = self._process_single_result(result)
            if processed:
                processed_results.append(processed)
        
        # 按日期排序（最新的在前）
        processed_results.sort(
            key=lambda x: x.get("date", ""),
            reverse=True
        )
        
        return processed_results
    
    def _process_single_result(self, result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """处理单个结果"""
        try:
            # 提取基本信息
            title = result.get("title", "")
            summary = result.get("summary", "")
            url = result.get("url", "")
            publish_date = result.get("publish_date", "")
            source = result.get("source", "同花顺问财")
            
            # 解析日期
            date_str = self._parse_date(publish_date)
            
            # 识别公司名称
            company = self._extract_company(title, summary)
            
            # 识别活动类型
            activity_type = self._identify_activity_type(title, summary)
            
            # 提取参与机构
            participants = self._extract_participants(summary)
            
            # 提取关键话题
            topics = self._extract_topics(summary)
            
            return {
                "company": company,
                "activity_type": activity_type,
                "date": date_str,
                "title": title,
                "summary": summary[:500] + "..." if len(summary) > 500 else summary,
                "participants": participants,
                "topics": topics,
                "source": source,
                "url": url,
                "raw_date": publish_date
            }
            
        except Exception as e:
            print(f"处理结果时出错: {e}")
            return None
    
    def _parse_date(self, date_str: str) -> str:
        """解析日期字符串"""
        if not date_str:
            return ""
        
        try:
            # 尝试解析各种格式的日期
            formats = [
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d",
                "%Y/%m/%d %H:%M:%S",
                "%Y/%m/%d"
            ]
            
            for fmt in formats:
                try:
                    dt = datetime.strptime(date_str, fmt)
                    return dt.strftime("%Y-%m-%d")
                except ValueError:
                    continue
            
            return date_str[:10] if len(date_str) >= 10 else date_str
            
        except Exception:
            return date_str[:10] if len(date_str) >= 10 else date_str
    
    def _extract_company(self, title: str, summary: str) -> str:
        """从标题和摘要中提取公司名称"""
        text = title + " " + summary
        
        # 常见的A股上市公司名称关键词
        company_keywords = [
            # 白酒
            "茅台", "五粮液", "泸州老窖", "洋河", "山西汾酒",
            # 银行
            "工商银行", "建设银行", "农业银行", "中国银行", "招商银行",
            # 保险
            "中国平安", "中国人寿", "中国太保", "新华保险",
            # 证券
            "中信证券", "海通证券", "国泰君安", "华泰证券",
            # 科技
            "腾讯", "阿里巴巴", "百度", "京东", "美团", "字节跳动",
            "华为", "小米", "中兴", "科大讯飞", "海康威视",
            # 新能源
            "宁德时代", "比亚迪", "隆基绿能", "通威股份",
            # 医药
            "恒瑞医药", "药明康德", "迈瑞医疗", "长春高新",
            # 其他
            "贵州茅台", "贵州", "茅台"
        ]
        
        for keyword in company_keywords:
            if keyword in text:
                return keyword
        
        return "未知公司"
    
    def _identify_activity_type(self, title: str, summary: str) -> str:
        """识别活动类型"""
        text = title + " " + summary
        
        for activity_type, keywords in self.activity_types.items():
            for keyword in keywords:
                if keyword in text:
                    return activity_type
        
        return "其他"
    
    def _extract_participants(self, summary: str) -> List[str]:
        """提取参与机构"""
        participants = []
        
        # 常见的投资机构关键词
        institution_keywords = [
            "基金", "证券", "保险", "银行", "资管", "信托",
            "投资", "资本", "私募", "公募", "券商", "研究所",
            "分析师", "研究员", "机构", "投资者"
        ]
        
        # 简单的关键词匹配
        words = summary.split()
        for word in words:
            for keyword in institution_keywords:
                if keyword in word and len(word) <= 20:
                    participants.append(word)
                    break
        
        return list(set(participants))[:5]  # 去重并限制数量
    
    def _extract_topics(self, summary: str) -> List[str]:
        """提取关键话题"""
        topics = []
        
        # 常见的投资者关系话题
        topic_keywords = [
            "业绩", "增长", "利润", "收入", "营收",
            "市场", "竞争", "战略", "规划", "发展",
            "产品", "技术", "研发", "创新", "升级",
            "行业", "政策", "监管", "环境", "趋势",
            "风险", "挑战", "机遇", "展望", "预期"
        ]
        
        sentences = summary.split("。")
        for sentence in sentences:
            for keyword in topic_keywords:
                if keyword in sentence and len(sentence) <= 100:
                    topics.append(sentence.strip())
                    break
        
        return list(set(topics))[:3]  # 去重并限制数量
    
    def generate_report(self, processed_data: List[Dict[str, Any]], format: str = "markdown") -> str:
        """
        生成报告
        
        Args:
            processed_data: 处理后的数据
            format: 报告格式，支持 "markdown", "text", "html"
            
        Returns:
            报告内容
        """
        if format == "markdown":
            return self._generate_markdown_report(processed_data)
        elif format == "text":
            return self._generate_text_report(processed_data)
        elif format == "html":
            return self._generate_html_report(processed_data)
        else:
            return self._generate_markdown_report(processed_data)
    
    def _generate_markdown_report(self, data: List[Dict[str, Any]]) -> str:
        """生成Markdown格式报告"""
        if not data:
            return "未找到相关投资者关系活动信息。"
        
        report = "# investor搜索结果\n\n"
        report += f"**数据来源：同花顺问财**\n\n"
        report += f"共找到 {len(data)} 条相关记录：\n\n"
        
        for i, item in enumerate(data, 1):
            report += f"## {i}. {item['company']} - {item['activity_type']}\n\n"
            report += f"**活动日期**：{item['date']}\n\n"
            report += f"**活动标题**：{item['title']}\n\n"
            report += f"**活动摘要**：{item['summary']}\n\n"
            
            if item['participants']:
                report += f"**参与机构**：{', '.join(item['participants'])}\n\n"
            
            if item['topics']:
                report += f"**关键话题**：\n"
                for topic in item['topics']:
                    report += f"- {topic}\n"
                report += "\n"
            
            if item['url']:
                report += f"**原文链接**：[点击查看]({item['url']})\n\n"
            
            report += "---\n\n"
        
        report += "**注：以上数据来源于同花顺问财**\n"
        return report
    
    def _generate_text_report(self, data: List[Dict[str, Any]]) -> str:
        """生成文本格式报告"""
        if not data:
            return "未找到相关投资者关系活动信息。"
        
        report = "investor搜索结果\n"
        report += "=" * 50 + "\n"
        report += f"数据来源：同花顺问财\n"
        report += f"共找到 {len(data)} 条相关记录：\n\n"
        
        for i, item in enumerate(data, 1):
            report += f"{i}. {item['company']} - {item['activity_type']}\n"
            report += f"   活动日期：{item['date']}\n"
            report += f"   活动标题：{item['title']}\n"
            report += f"   活动摘要：{item['summary']}\n"
            
            if item['participants']:
                report += f"   参与机构：{', '.join(item['participants'])}\n"
            
            if item['topics']:
                report += f"   关键话题：{', '.join(item['topics'])}\n"
            
            if item['url']:
                report += f"   原文链接：{item['url']}\n"
            
            report += "\n"
        
        report += "注：以上数据来源于同花顺问财\n"
        return report
    
    def _generate_html_report(self, data: List[Dict[str, Any]]) -> str:
        """生成HTML格式报告"""
        if not data:
            return "<p>未找到相关投资者关系活动信息。</p>"
        
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>investor搜索结果</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                h1 { color: #333; }
                h2 { color: #666; margin-top: 30px; }
                .item { border: 1px solid #ddd; padding: 15px; margin: 10px 0; border-radius: 5px; }
                .company { font-weight: bold; color: #0066cc; }
                .date { color: #666; font-size: 0.9em; }
                .summary { margin: 10px 0; line-height: 1.5; }
                .source { font-size: 0.9em; color: #999; margin-top: 20px; }
                a { color: #0066cc; text-decoration: none; }
                a:hover { text-decoration: underline; }
            </style>
        </head>
        <body>
            <h1>investor搜索结果</h1>
            <p><strong>数据来源：同花顺问财</strong></p>
            <p>共找到 {} 条相关记录：</p>
        """.format(len(data))
        
        for i, item in enumerate(data, 1):
            html += f"""
            <div class="item">
                <h2>{i}. <span class="company">{item['company']}</span> - {item['activity_type']}</h2>
                <div class="date">活动日期：{item['date']}</div>
                <div><strong>活动标题：</strong>{item['title']}</div>
                <div class="summary"><strong>活动摘要：</strong>{item['summary']}</div>
            """
            
            if item['participants']:
                html += f"<div><strong>参与机构：</strong>{', '.join(item['participants'])}</div>"
            
            if item['topics']:
                html += f"<div><strong>关键话题：</strong>{', '.join(item['topics'])}</div>"
            
            if item['url']:
                html += f'<div><strong>原文链接：</strong><a href="{item["url"]}" target="_blank">{item["url"]}</a></div>'
            
            html += "</div>"
        
        html += """
            <div class="source">
                <p>注：以上数据来源于同花顺问财</p>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def save_to_csv(self, data: List[Dict[str, Any]], filepath: str):
        """
        保存为CSV文件
        
        Args:
            data: 要保存的数据
            filepath: 文件路径
        """
        if not data:
            print("没有数据可保存")
            return
        
        # 确保目录存在
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # 定义CSV字段
        fieldnames = [
            "company", "activity_type", "date", "title", 
            "summary", "participants", "topics", "source", "url"
        ]
        
        try:
            with open(filepath, 'w', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for item in data:
                    # 将列表字段转换为字符串
                    row = item.copy()
                    row['participants'] = ';'.join(row.get('participants', []))
                    row['topics'] = ';'.join(row.get('topics', []))
                    writer.writerow(row)
            
            print(f"数据已保存到: {filepath}")
            
        except Exception as e:
            print(f"保存CSV文件时出错: {e}")
    
    def save_to_json(self, data: List[Dict[str, Any]], filepath: str):
        """
        保存为JSON文件
        
        Args:
            data: 要保存的数据
            filepath: 文件路径
        """
        if not data:
            print("没有数据可保存")
            return
        
        # 确保目录存在
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as jsonfile:
                json.dump(data, jsonfile, ensure_ascii=False, indent=2)
            
            print(f"数据已保存到: {filepath}")
            
        except Exception as e:
            print(f"保存JSON文件时出错: {e}")


def create_data_processor() -> InvestorDataProcessor:
    """创建数据处理实例"""
    return InvestorDataProcessor()