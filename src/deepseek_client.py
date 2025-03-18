import os
import logging
from openai import OpenAI
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()

class DeepSeekClient:
    """DeepSeek API客户端类（使用OpenAI SDK）"""
    
    def __init__(self):
        """初始化DeepSeek API客户端"""
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        self.api_base = os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com/v1")
        
        if not self.api_key:
            logger.error("未设置DEEPSEEK_API_KEY环境变量")
            raise ValueError("请设置DEEPSEEK_API_KEY环境变量")
        
        # 初始化OpenAI客户端，指向DeepSeek API
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.api_base
        )
        
        logger.info("DeepSeek API客户端初始化完成")
    
    def generate_qa_pairs(self, content, num_pairs=20):
        """使用OpenAI SDK生成问答对"""
        try:
            # 构建提示词
            prompt = f"""根据以下内容，生成{num_pairs}个中文问答对，生成的问答对要尽可能覆盖内容，深刻理解内容。返回成JSON格式的数组，每个问答对包含'question'和'answer'字段。
            
内容:
{content[:10000]}

请仅返回JSON数组，不要包含任何其他文本或解释。格式示例:
[
  {{"question": "问题1", "answer": "答案1"}},
  {{"question": "问题2", "answer": "答案2"}}
]"""

            logger.info("开始调用DeepSeek API生成问答对")
            
            # 使用OpenAI SDK调用API
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=4000
            )
            
            # 获取响应文本
            response_text = response.choices[0].message.content
            
            # 尝试解析JSON
            import json
            import re
            
            try:
                # 尝试直接解析JSON
                qa_pairs = json.loads(response_text)
            except json.JSONDecodeError:
                # 如果直接解析失败，尝试从文本中提取JSON部分
                json_match = re.search(r'\[\s*{.*}\s*\]', response_text, re.DOTALL)
                if json_match:
                    try:
                        qa_pairs = json.loads(json_match.group(0))
                    except json.JSONDecodeError:
                        logger.error("无法解析API返回的JSON格式")
                        return []
                else:
                    logger.error("无法从API响应中提取JSON")
                    return []
            
            logger.info(f"成功生成 {len(qa_pairs)} 个问答对")
            return qa_pairs
            
        except Exception as e:
            logger.error(f"调用DeepSeek API生成问答对时出错: {str(e)}")
            return []