"""
investor搜索技能配置模块
"""

import os
from typing import Optional


class Config:
    """配置管理类"""
    
    # API配置
    BASE_URL = "https://openapi.iwencai.com"
    API_PATH = "/v1/comprehensive/search"
    API_URL = BASE_URL + API_PATH
    
    # 固定请求参数
    CHANNELS = ["investor"]
    APP_ID = "AIME_SKILL"
    
    # 默认搜索参数
    DEFAULT_LIMIT = 20
    DEFAULT_OUTPUT_FORMAT = "markdown"
    
    # 环境变量名称
    ENV_API_KEY = "IWENCAI_API_KEY"
    
    @classmethod
    def get_api_key(cls) -> Optional[str]:
        """获取API密钥"""
        return os.getenv(cls.ENV_API_KEY)
    
    @classmethod
    def validate_config(cls) -> bool:
        """验证配置是否完整"""
        api_key = cls.get_api_key()
        if not api_key:
            print(f"错误: 请设置环境变量 {cls.ENV_API_KEY}")
            print(f"示例: export {cls.ENV_API_KEY}=\"your_api_key_here\"")
            return False
        return True
    
    @classmethod
    def get_headers(cls) -> dict:
        """获取请求头"""
        api_key = cls.get_api_key()
        if not api_key:
            raise ValueError(f"API密钥未设置，请设置环境变量 {cls.ENV_API_KEY}")
        
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
    
    @classmethod
    def get_base_payload(cls) -> dict:
        """获取基础请求参数"""
        return {
            "channels": cls.CHANNELS,
            "app_id": cls.APP_ID
        }


# 导出配置实例
config = Config()