import os
import logging
import time
from openai import OpenAI
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()

class DeepSeekClient:
    """DeepSeek API客户端类（使用OpenAI SDK）"""
    
    def __init__(self, max_retries=3, retry_delay=2):
        """
        初始化DeepSeek API客户端
        
        Args:
            max_retries (int): 最大重试次数
            retry_delay (int): 重试间隔时间(秒)
        """
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        self.api_base = os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com/v1")
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        if not self.api_key:
            logger.error("未设置DEEPSEEK_API_KEY环境变量")
            raise ValueError("请设置DEEPSEEK_API_KEY环境变量")
        
        # 初始化OpenAI客户端，指向DeepSeek API
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.api_base
        )
        
        logger.info("DeepSeek API客户端初始化完成")
    
    def generate_qa_pairs(self, prompt, num_pairs=10):
        """
        使用OpenAI SDK生成问答对，带有重试机制
        
        Args:
            prompt (str): 完整的提示词
            num_pairs (int): 期望生成的问答对数量
            
        Returns:
            list: 问答对列表
        """
        # 实现重试机制
        attempts = 0
        while attempts < self.max_retries:
            attempts += 1
            try:
                if attempts == 1:
                    logger.info("开始调用DeepSeek API生成问答对")
                else:
                    logger.info(f"重试调用DeepSeek API (第 {attempts-1}/{self.max_retries-1} 次重试)")
                
                # 使用OpenAI SDK调用API
                response = self.client.chat.completions.create(
                    model = os.getenv("MODEL_NAME", "deepseek-chat"),
                    messages=[
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=8000  # 增加token数量以支持更复杂的回答
                )
                
                # 获取响应文本
                response_text = response.choices[0].message.content
                
                # 尝试解析JSON
                import json
                import re
                
                try:
                    # 尝试直接解析JSON
                    qa_pairs = json.loads(response_text)
                    logger.info(f"成功生成 {len(qa_pairs)} 个问答对")
                    
                    # 验证问答对格式
                    self._validate_qa_pairs(qa_pairs)
                    
                    return qa_pairs
                except json.JSONDecodeError:
                    # 如果直接解析失败，尝试从文本中提取JSON部分
                    json_match = re.search(r'\[\s*{.*}\s*\]', response_text, re.DOTALL)
                    if json_match:
                        try:
                            qa_pairs = json.loads(json_match.group(0))
                            logger.info(f"成功从部分响应中提取并生成 {len(qa_pairs)} 个问答对")
                            
                            # 验证问答对格式
                            self._validate_qa_pairs(qa_pairs)
                            
                            return qa_pairs
                        except json.JSONDecodeError:
                            logger.error("无法解析API返回的JSON格式")
                            # 继续重试
                    else:
                        logger.error("无法从API响应中提取JSON")
                        logger.debug(f"API响应内容: {response_text[:200]}...")
                        # 继续重试
                
            except Exception as e:
                logger.error(f"调用DeepSeek API生成问答对时出错: {str(e)}")
                # 如果已经达到最大重试次数，则退出循环
                if attempts >= self.max_retries:
                    break
                
                # 否则等待后继续重试
                wait_time = self.retry_delay * (attempts-1)  # 指数退避策略
                logger.info(f"将在 {wait_time} 秒后进行重试")
                time.sleep(wait_time)
        
        # 如果所有重试都失败了
        logger.error(f"经过 {self.max_retries} 次尝试后，仍然无法成功调用DeepSeek API")
        return []
    
    def _validate_qa_pairs(self, qa_pairs):
        """
        验证问答对格式并进行必要的修复
        
        Args:
            qa_pairs (list): 问答对列表
            
        Returns:
            list: 验证后的问答对列表
        """
        valid_pairs = []
        
        for qa in qa_pairs:
            # 检查基本字段
            if not isinstance(qa, dict):
                continue
                
            if 'question' not in qa or 'answer' not in qa:
                continue
                
            # 如果没有level字段，添加默认level
            if 'level' not in qa:
                qa['level'] = 'basic'
            
            valid_pairs.append(qa)
        
        return valid_pairs