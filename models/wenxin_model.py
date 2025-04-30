import aiohttp
import asyncio
import re
import time
from typing import Tuple, Optional
from .base_model import BaseModel

class WenxinModel(BaseModel):
    """文心一言大模型实现"""
    
    def __init__(self, api_key: str):
        super().__init__(api_key)
        
    async def analyze_text(self, text: str) -> Tuple[Optional[str], Optional[list]]:
        """
        使用文心一言分析文本
        
        Args:
            text (str): 要分析的文本
            
        Returns:
            tuple: (核心内容, 关键词列表)
        """
        try:
            # 将文本分成较小的块进行分析
            max_chunk_size = 2000
            chunks = [text[i:i+max_chunk_size] for i in range(0, len(text), max_chunk_size)]
            
            summary = []
            keywords = []
            
            async with aiohttp.ClientSession() as session:
                for chunk in chunks:
                    # 构建文心一言API请求
                    url = "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/completions"
                    headers = {
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {self.api_key}"
                    }
                    data = {
                        "messages": [
                            {
                                "role": "user",
                                "content": f"""请分析以下文本，提取核心内容并列出关键词：
                                
{chunk}

请严格按照以下格式输出，不要添加任何其他内容：

核心内容：
[用一段话概括文本的核心内容，不超过200字]

关键词：
[关键词1, 关键词2, 关键词3, 关键词4, 关键词5]

注意：
1. 核心内容必须是一段完整的文字，不要使用列表或分点
2. 关键词必须是5个，用逗号分隔，不要使用引号
3. 关键词应该是名词或名词短语，不要使用动词或形容词
4. 不要添加任何其他说明或解释"""
                            }
                        ]
                    }
                    
                    async with session.post(url, headers=headers, json=data) as response:
                        if response.status == 200:
                            result = await response.json()
                            content = result.get('result', '')
                            
                            # 提取核心内容和关键词
                            summary_match = re.search(r'核心内容：\n(.*?)\n\n关键词：', content, re.DOTALL)
                            keywords_match = re.search(r'关键词：\n(.*?)$', content, re.DOTALL)
                            
                            if summary_match:
                                summary.append(summary_match.group(1).strip())
                            if keywords_match:
                                keywords.extend([k.strip() for k in keywords_match.group(1).strip('[]').split(',')])
                        
                    # 添加延迟避免API限制
                    await asyncio.sleep(1)
            
            return '\n'.join(summary), list(set(keywords))
            
        except Exception as e:
            print(f"使用文心一言分析文本时出错: {str(e)}")
            return None, None
            
    async def generate(self, prompt: str) -> str:
        """
        使用文心一言生成文本
        
        Args:
            prompt (str): 提示词
            
        Returns:
            str: 生成的文本
        """
        try:
            async with aiohttp.ClientSession() as session:
                url = "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/completions"
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                }
                data = {
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                }
                
                async with session.post(url, headers=headers, json=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result.get('result', '')
                    else:
                        print(f"API调用失败: {response.status}")
                        return ""
                
        except Exception as e:
            print(f"使用文心一言生成文本时出错: {str(e)}")
            return "" 