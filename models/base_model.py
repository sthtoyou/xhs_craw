from abc import ABC, abstractmethod
from typing import Tuple, Optional

class BaseModel(ABC):
    """大模型基类，定义所有大模型必须实现的接口"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
    
    @abstractmethod
    async def analyze_text(self, text: str) -> Tuple[Optional[str], Optional[list]]:
        """
        分析文本，提取核心内容和关键词
        
        Args:
            text (str): 要分析的文本
            
        Returns:
            tuple: (核心内容, 关键词列表)
        """
        pass
        
    @abstractmethod
    async def generate(self, prompt: str) -> str:
        """
        生成文本
        
        Args:
            prompt (str): 提示词
            
        Returns:
            str: 生成的文本
        """
        pass 