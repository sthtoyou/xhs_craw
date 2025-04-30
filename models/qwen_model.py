import dashscope
import re
import time
from typing import Tuple, Optional
from .base_model import BaseModel

class QwenModel(BaseModel):
    """通义千问大模型实现"""
    
    def __init__(self, api_key: str):
        super().__init__(api_key)
        dashscope.api_key = api_key
    
    async def analyze_text(self, text: str) -> Tuple[Optional[str], Optional[list]]:
        """
        使用通义千问分析文本
        
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
            
            for chunk in chunks:
                # 使用通义千问API分析文本
                response = dashscope.Generation.call(
                    model='qwen-max',
                    prompt=f"""请分析以下文本，提取核心内容并列出关键词：
                    
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
                )
                
                if response.status_code == 200:
                    result = response.output.text
                    
                    # 提取核心内容和关键词
                    summary_match = re.search(r'核心内容：\n(.*?)\n\n关键词：', result, re.DOTALL)
                    keywords_match = re.search(r'关键词：\n(.*?)$', result, re.DOTALL)
                    
                    if summary_match:
                        summary.append(summary_match.group(1).strip())
                    if keywords_match:
                        keywords.extend([k.strip() for k in keywords_match.group(1).strip('[]').split(',')])
                
                # 添加延迟避免API限制
                time.sleep(1)
            
            return '\n'.join(summary), list(set(keywords))
            
        except Exception as e:
            print(f"使用通义千问分析文本时出错: {str(e)}")
            return None, None
            
    async def generate(self, prompt: str) -> str:
        """
        使用通义千问生成文本
        
        Args:
            prompt (str): 提示词
            
        Returns:
            str: 生成的文本
        """
        try:
            response = dashscope.Generation.call(
                model='qwen-max',
                prompt=prompt
            )
            
            if response.status_code == 200:
                return response.output.text
            else:
                print(f"API调用失败: {response.code} - {response.message}")
                return ""
                
        except Exception as e:
            print(f"使用通义千问生成文本时出错: {str(e)}")
            return "" 