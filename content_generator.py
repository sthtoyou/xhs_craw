import pandas as pd
import asyncio
from typing import List, Dict
import os
import argparse
from models import get_model

class ContentGenerator:
    def __init__(self, model_type: str, model_api_key: str):
        self.model = get_model(model_type, model_api_key)
        
    async def generate_xiaohongshu_content(self, keywords: str, original_content: str) -> str:
        """
        生成小红书风格的文案
        
        Args:
            keywords (str): 关键词
            original_content (str): 原始内容
            
        Returns:
            str: 生成的小红书风格文案
        """
        prompt = f"""# 角色：
你是小红书爆款写作专家

## 任务：
根据以下关键词和原始内容，帮我写一篇小红书文案，使用亲切专业的语气，希望看完这文章的人有深深的共鸣，并产生主动联系博主的想法。

关键词：{keywords}
原始内容：{original_content}

## 技能要求：
1.自我思考: 请你列出10个反对理由后再给出文案
2.换位思考: 如果你是老板, 你会怎么批评这个文案
3.反复推敲: 在给出答案前将回答复盘至少10轮,直至你自己满意为至
4.文案分镜: 将生成的正文分拆为多个分镜文案, 每个分镜能清晰的表达一个观点
5.配图建议: 针对每个分镜文案, 给出配图建议(包括但不限于 风格\内容\网感元素等几个方面)

## 工作流程：
1.首先产出5个标题（含适当的emoji表情）
2.其次产出1个正文（每一个段落含有适当的emoji表情，文末有合适的tag标签）
3.对上述1-2步,运用自我思考\换位思考\反复推敲技能进行复盘, 直至得出你满意的标题和正文
4.运用文案分镜和配图建议技能, 生成分镜文案和配图建议

## 输出格式：
请按照以下格式输出：

【标题】
1. 标题1
2. 标题2
3. 标题3
4. 标题4
5. 标题5

【正文】
[正文内容，每个段落包含emoji表情]

【分镜文案】
1. 分镜1：[文案内容]
   配图建议：[配图建议]

2. 分镜2：[文案内容]
   配图建议：[配图建议]

3. 分镜3：[文案内容]
   配图建议：[配图建议]

【标签】
#标签1 #标签2 #标签3

## 限制：
- 字数控制在500字以内
- 使用小红书特有的表达方式，如"姐妹们"、"绝绝子"、"yyds"等
- 加入emoji表情符号增加趣味性
- 使用短句和分段，增加可读性
- 加入个人感受和体验分享
- 使用感叹号和问号增加互动感
- 适当使用网络流行语
- 保持真诚和亲切的语气"""

        try:
            return await self.model.generate(prompt)
        except Exception as e:
            print(f"生成内容时出错: {str(e)}")
            return ""

    async def process_excel(self, input_file: str, output_file: str = None, limit: int = None):
        """
        处理Excel文件，为每行数据生成小红书风格文案
        
        Args:
            input_file (str): 输入Excel文件路径
            output_file (str): 输出Excel文件路径，如果为None则自动生成
            limit (int): 限制处理的数据条数，如果为None则处理所有数据
        """
        try:
            # 读取Excel文件
            df = pd.read_excel(input_file)
            
            # 确保有必要的列
            required_columns = ['关键词', '原始文本']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                print(f"Excel文件中缺少以下列: {', '.join(missing_columns)}")
                print(f"当前列名: {', '.join(df.columns.tolist())}")
                return
            
            # 如果指定了限制，只处理前limit条数据
            if limit is not None:
                df = df.head(limit)
            
            # 生成新内容
            titles = []
            contents = []
            storyboards = []
            
            for _, row in df.iterrows():
                keywords = row['关键词']
                original_content = row['原始文本']
                generated_content = await self.generate_xiaohongshu_content(keywords, original_content)
                
                # 解析生成的内容
                title_section = ""
                content_section = ""
                storyboard_section = ""
                
                current_section = ""
                for line in generated_content.split('\n'):
                    if line.startswith('【标题】'):
                        current_section = 'title'
                    elif line.startswith('【正文】'):
                        current_section = 'content'
                    elif line.startswith('【分镜文案】'):
                        current_section = 'storyboard'
                    elif line.startswith('【标签】'):
                        break
                    else:
                        if current_section == 'title':
                            title_section += line + '\n'
                        elif current_section == 'content':
                            content_section += line + '\n'
                        elif current_section == 'storyboard':
                            storyboard_section += line + '\n'
                
                titles.append(title_section.strip())
                contents.append(content_section.strip())
                storyboards.append(storyboard_section.strip())
                
                print(f"已处理一条内容，关键词: {keywords}")
            
            # 添加新列
            df['小红书标题'] = titles
            df['小红书正文'] = contents
            df['小红书分镜文案'] = storyboards
            
            # 生成输出文件名
            if output_file is None:
                base_name = os.path.splitext(input_file)[0]
                output_file = f"{base_name}_小红书风格.xlsx"
            
            # 保存结果
            df.to_excel(output_file, index=False)
            print(f"处理完成，结果已保存到: {output_file}")
            
        except Exception as e:
            print(f"处理Excel文件时出错: {str(e)}")

async def main_async():
    parser = argparse.ArgumentParser(description='生成小红书风格文案')
    parser.add_argument('--input', required=True, help='输入Excel文件路径')
    parser.add_argument('--output', help='输出Excel文件路径（可选）')
    parser.add_argument('--model_type', required=True, help='模型类型')
    parser.add_argument('--model_api_key', required=True, help='模型API密钥')
    parser.add_argument('--limit', type=int, help='限制处理的数据条数（可选）')
    
    args = parser.parse_args()
    
    generator = ContentGenerator(args.model_type, args.model_api_key)
    await generator.process_excel(args.input, args.output, args.limit)

def main():
    asyncio.run(main_async())

if __name__ == '__main__':
    main() 