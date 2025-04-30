import requests
import re
from typing import Tuple, Optional
from .base_model import BaseModel
import aiohttp
import asyncio

class SiliconModel(BaseModel):
    """硅基流动大模型实现"""
    
    async def analyze_text(self, text: str) -> Tuple[str, Optional[list]]:
        """
        使用硅基流动分析文本
        
        Args:
            text (str): 要分析的文本
            
        Returns:
            tuple: (核心内容, 关键词列表)
        """
        try:
            # Split text into chunks of 2000 characters
            chunks = [text[i:i + 2000] for i in range(0, len(text), 2000)]
            all_responses = []
            
            async with aiohttp.ClientSession() as session:
                for chunk in chunks:
                    print("正在发送请求到硅流大模型API...")
                    
                    headers = {
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {self.api_key}"
                    }
                    
                    data = {
                        "model": "silicon-flow-v1",
                        "messages": [
                            {
                                "role": "user",
                                "content": f"请分析以下文本：\n{chunk}\n\n请提供以下内容：\n1. 核心内容：用一段不超过200字的完整段落总结文本的主要内容，不要使用列表或要点。\n2. 关键词：提供5个名词或名词短语，用逗号分隔，不要加引号。\n请严格按照这个格式输出，不要添加任何其他解释。"
                            }
                        ]
                    }
                    
                    try:
                        async with session.post(
                            "https://api.siliconflow.com/v1/chat/completions",
                            headers=headers,
                            json=data,
                            timeout=30
                        ) as response:
                            print(f"收到响应，状态码: {response.status}")
                            
                            if response.status != 200:
                                error_text = await response.text()
                                print(f"API请求失败。状态码: {response.status}")
                                print(f"错误信息: {error_text}")
                                print(f"请求头: {headers}")
                                print(f"请求数据: {data}")
                                raise Exception(f"API request failed with status {response.status}: {error_text}")
                            
                            response_json = await response.json()
                            print("成功获取API响应")
                            all_responses.append(response_json['choices'][0]['message']['content'])
                            
                            # Add delay to avoid rate limits
                            await asyncio.sleep(1)
                            
                    except aiohttp.ClientError as e:
                        print(f"API请求出错: {str(e)}")
                        print(f"请求头: {headers}")
                        print(f"请求数据: {data}")
                        raise
            
            # Combine all responses
            combined_response = " ".join(all_responses)
            
            # Extract core content and keywords using regex
            core_content_match = re.search(r"核心内容：(.*?)(?=关键词：|$)", combined_response, re.DOTALL)
            keywords_match = re.search(r"关键词：(.*?)$", combined_response, re.DOTALL)
            
            if not core_content_match or not keywords_match:
                print("无法从API响应中提取核心内容或关键词")
                print(f"API响应: {combined_response}")
                raise Exception("Failed to extract core content or keywords from API response")
            
            core_content = core_content_match.group(1).strip()
            keywords = [k.strip() for k in keywords_match.group(1).split(",")]
            
            return core_content, keywords
            
        except Exception as e:
            import traceback
            print(f"分析文本时出错: {str(e)}")
            print("错误追踪:")
            print(traceback.format_exc())
            raise 