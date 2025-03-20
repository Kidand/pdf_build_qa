#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import logging
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from .pdf_processor import PDFProcessor
from .deepseek_client import DeepSeekClient

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class QAGenerator:
    """问答生成器类"""
    
    # 定义问答等级
    LEVEL_BASIC = "basic"      # 基础级别，适合初学者
    LEVEL_INTERMEDIATE = "intermediate"  # 中级水平，适合有一定基础的学习者
    LEVEL_ADVANCED = "advanced"     # 高级水平，适合深入研究的学者
    
    def __init__(self, pdf_dir="pdf_files", num_qa_pairs=20, max_workers=3, 
                 api_max_retries=3, api_retry_delay=2, qa_level=None, 
                 use_latex_ocr=True):
        """
        初始化问答生成器
        
        Args:
            pdf_dir (str): PDF文件目录
            num_qa_pairs (int): 每个PDF生成的问答对数量
            max_workers (int): 最大并行处理的文件数
            api_max_retries (int): API调用最大重试次数
            api_retry_delay (int): API调用重试间隔(秒)
            qa_level (str): 问答对级别 (basic/intermediate/advanced)
            use_latex_ocr (bool): 是否使用LaTeX OCR
        """
        self.pdf_processor = PDFProcessor(pdf_dir, use_latex_ocr)
        self.deepseek_client = DeepSeekClient(max_retries=api_max_retries, retry_delay=api_retry_delay)
        self.num_qa_pairs = num_qa_pairs
        self.max_workers = max_workers
        self.failed_files = []  # 用于记录处理失败的文件
        
        # 设置问答等级，默认生成所有级别
        self.qa_level = qa_level
        
        logger.info(f"问答生成器初始化，目录: {pdf_dir}，每个PDF生成 {num_qa_pairs} 个问答对，级别: {qa_level or '全部'}")
    
    def _get_prompt_template(self, level, num_pairs, metadata=None):
        """
        获取指定级别的提示模板
        
        Args:
            level (str): 问答级别
            num_pairs (int): 需要生成的问答对数量
            metadata (dict): PDF元数据，包含标题、作者等
            
        Returns:
            str: 提示模板
        """
        # 提取文档标题，如果有的话
        title = ""
        if metadata and metadata.get("title"):
            title = metadata.get("title")
        
        # 基础级别：简单的问答，适合初学者
        if level == self.LEVEL_BASIC:
            return f"""你是一位资深的教育工作者，需要为初学者生成{num_pairs}个基础级别的中文问答对，涵盖以下学术内容的基本概念和简单应用。
            
【文档标题】：{title}

【要求】：
1. 问题应该关注基础概念、定义和简单原理，适合初学者理解
2. 回答应该简明扼要，使用通俗易懂的语言，避免过多专业术语
3. 问答难度相当于本科一年级或入门水平
4. 确保问题和回答清晰明了，不要过于复杂
5. 每个问题都必须提及论文的标题或主题

【内容】：
{{content[:50000]}}

请仅返回JSON格式，每个问答对包含'question'和'answer'字段：
[
  {{"question": "问题1", "answer": "答案1", "level": "basic"}},
  {{"question": "问题2", "answer": "答案2", "level": "basic"}}
]"""
        
        # 中级级别：更深入的问答，需要一定的专业基础
        elif level == self.LEVEL_INTERMEDIATE:
            return f"""你是一位资深的大学教授，需要为有一定基础的学生生成{num_pairs}个中级难度的中文问答对，帮助他们深入理解以下学术内容。
            
【文档标题】：{title}

【要求】：
1. 问题应关注概念间的联系、原理应用和中等复杂度的分析
2. 回答应该全面且包含一定深度，但仍然保持清晰易懂
3. 可以包含一些专业术语和理论框架的讨论
4. 问答难度相当于高年级本科或硕士初级水平
5. 引导学生思考"为什么"和"如何"的问题
6. 每个问题都必须提及论文的标题或主题

【内容】：
{{content[:50000]}}

请仅返回JSON格式，每个问答对包含'question'和'answer'字段：
[
  {{"question": "问题1", "answer": "答案1", "level": "intermediate"}},
  {{"question": "问题2", "answer": "答案2", "level": "intermediate"}}
]"""
        
        # 高级级别：深度分析和批判性思考的问答
        elif level == self.LEVEL_ADVANCED:
            return f"""你是一位资深的研究员和博士导师，需要为高级学者生成{num_pairs}个高级学术水平的中文问答对，基于以下学术内容进行深度探讨和批判性分析。
            
【文档标题】：{title}

【要求】：
1. 问题应该触及理论深处，包含方法论分析、跨领域整合和研究局限性
2. 鼓励批判性思考、创新视角和对现有研究的质疑
3. 回答应该体现专家水平的深度与广度，包括多种观点和争议
4. 可以讨论研究前沿和未解决的问题
5. 问答难度相当于博士或资深研究者水平
6. 应包含对相关理论体系和方法论的深入理解
7. 每个问题都必须提及论文的标题或主题

【内容】：
{{content[:50000]}}

请仅返回JSON格式，每个问答对包含'question'和'answer'字段：
[
  {{"question": "问题1", "answer": "答案1", "level": "advanced"}},
  {{"question": "问题2", "answer": "答案2", "level": "advanced"}}
]"""
        
        # 默认模板（同时包含不同级别的问答）
        else:
            return f"""你是一位科研与教育并重的学术专家，需要基于以下学术内容，生成三种不同难度级别的中文问答对，总共{num_pairs}个问答对（尽量平均分配到各级别）。

【文档标题】：{title}

【要求】：
1. 为每个问题标记难度级别：基础(basic)、中级(intermediate)或高级(advanced)
2. 基础级问题：关注基本概念和定义，适合初学者
3. 中级问题：关注原理应用和概念关联，适合有一定基础的学习者
4. 高级问题：关注批判性分析、方法论和前沿问题，适合研究人员
5. 确保问答深度与标记的难度级别相符
6. 每个问题都必须提及论文的标题或主题

【内容】：
{{content[:50000]}}

请仅返回JSON格式，每个问答对包含'question'、'answer'和'level'字段：
[
  {{"question": "基础问题...", "answer": "基础回答...", "level": "basic"}},
  {{"question": "中级问题...", "answer": "中级回答...", "level": "intermediate"}},
  {{"question": "高级问题...", "answer": "高级回答...", "level": "advanced"}}
]"""
    
    def _prepare_qa_prompt(self, content, level, num_pairs, metadata=None):
        """准备问答生成的提示词

        Args:
            content (str): PDF内容
            level (str): 问答级别
            num_pairs (int): 问答对数量
            metadata (dict): PDF元数据

        Returns:
            str: 完整提示词
        """
        template = self._get_prompt_template(level, num_pairs, metadata)
        # 将content插入到模板中
        prompt = template.replace("{content}", content)
        return prompt
    
    def process_pdf(self, pdf_path):
        """
        处理单个PDF文件
        
        Args:
            pdf_path (str): PDF文件路径
            
        Returns:
            tuple: (问答对列表, 源文件名, 原始内容, 元数据, 是否成功)
        """
        filename = os.path.basename(pdf_path)
        try:
            # 从PDF提取文本
            content, filename, metadata = self.pdf_processor.extract_text_from_pdf(pdf_path)
            
            if not content:
                logger.warning(f"PDF文件 {filename} 没有提取到内容")
                return [], filename, "", {}, False
            
            # 根据配置选择问答级别
            if self.qa_level:
                levels = [self.qa_level]
            else:
                levels = [None]  # 使用默认模板生成混合级别的问答对
            
            all_qa_pairs = []
            
            # 生成指定级别的问答对
            for level in levels:
                prompt = self._prepare_qa_prompt(content, level, self.num_qa_pairs, metadata)
                
                # 生成问答对
                qa_pairs = self.deepseek_client.generate_qa_pairs(prompt, self.num_qa_pairs)
                
                if not qa_pairs:
                    logger.warning(f"文件 {filename} 生成 {level or '混合'} 级别问答对失败")
                    continue
                    
                # 确保每个问答对都有level字段
                for qa in qa_pairs:
                    if 'level' not in qa:
                        # 如果特定单一级别，添加该级别
                        if level:
                            qa['level'] = level
                        else:
                            # 默认设为基础级别
                            qa['level'] = self.LEVEL_BASIC
                
                all_qa_pairs.extend(qa_pairs)
                logger.info(f"文件 {filename} 成功生成 {len(qa_pairs)} 个 {level or '混合'} 级别问答对")
            
            if not all_qa_pairs:
                logger.warning(f"文件 {filename} 生成所有级别问答对均失败")
                return [], filename, content, metadata, False
                
            return all_qa_pairs, filename, content, metadata, True
            
        except Exception as e:
            logger.error(f"处理PDF文件 {pdf_path} 时出错: {str(e)}")
            return [], filename, "", {}, False
    
    def generate_qa_from_pdfs(self):
        """
        从所有PDF文件生成问答对
        
        Returns:
            tuple: (问答对列表, 失败文件列表)
                  问答对列表: 每个元素是一个四元组 (问答对列表, 源文件名, 原始内容, 元数据)
                  失败文件列表: 处理失败的文件名列表
        """
        pdf_files = self.pdf_processor.get_pdf_files()
        
        if not pdf_files:
            logger.warning("没有找到PDF文件")
            return [], []
        
        results = []
        self.failed_files = []  # 重置失败文件列表
        
        # 使用线程池并行处理PDF文件
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任务
            future_to_pdf = {executor.submit(self.process_pdf, pdf): pdf for pdf in pdf_files}
            
            # 收集结果
            for future in as_completed(future_to_pdf):
                pdf = future_to_pdf[future]
                pdf_name = os.path.basename(pdf)
                try:
                    qa_pairs, filename, content, metadata, success = future.result()
                    if success:
                        results.append((qa_pairs, filename, content, metadata))
                    else:
                        self.failed_files.append(filename)
                except Exception as e:
                    logger.error(f"获取文件 {pdf} 的处理结果时出错: {str(e)}")
                    self.failed_files.append(pdf_name)
        
        logger.info(f"共处理了 {len(pdf_files)} 个PDF文件，成功: {len(results)}，失败: {len(self.failed_files)}")
        
        # 打印处理失败的文件列表
        if self.failed_files:
            logger.warning("以下文件处理失败:")
            for failed_file in self.failed_files:
                logger.warning(f"  - {failed_file}")
        
        return results, self.failed_files
    
    def get_failed_files(self):
        """获取处理失败的文件列表"""
        return self.failed_files