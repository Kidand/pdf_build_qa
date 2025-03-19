#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from .pdf_processor import PDFProcessor
from .deepseek_client import DeepSeekClient

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class QAGenerator:
    """问答生成器类"""
    
    def __init__(self, pdf_dir="pdf_files", num_qa_pairs=20, max_workers=3, api_max_retries=3, api_retry_delay=2):
        """
        初始化问答生成器
        
        Args:
            pdf_dir (str): PDF文件目录
            num_qa_pairs (int): 每个PDF生成的问答对数量
            max_workers (int): 最大并行处理的文件数
            api_max_retries (int): API调用最大重试次数
            api_retry_delay (int): API调用重试间隔(秒)
        """
        self.pdf_processor = PDFProcessor(pdf_dir)
        self.deepseek_client = DeepSeekClient(max_retries=api_max_retries, retry_delay=api_retry_delay)
        self.num_qa_pairs = num_qa_pairs
        self.max_workers = max_workers
        self.failed_files = []  # 用于记录处理失败的文件
        logger.info(f"问答生成器初始化，目录: {pdf_dir}，每个PDF生成 {num_qa_pairs} 个问答对，API最大重试次数: {api_max_retries}")
    
    def process_pdf(self, pdf_path):
        """
        处理单个PDF文件
        
        Args:
            pdf_path (str): PDF文件路径
            
        Returns:
            tuple: (问答对列表, 源文件名, 原始内容, 是否成功)
        """
        filename = os.path.basename(pdf_path)
        try:
            # 从PDF提取文本
            content, filename = self.pdf_processor.extract_text_from_pdf(pdf_path)
            
            if not content:
                logger.warning(f"PDF文件 {filename} 没有提取到内容")
                return [], filename, "", False
            
            # 生成问答对
            qa_pairs = self.deepseek_client.generate_qa_pairs(content, self.num_qa_pairs)
            
            if not qa_pairs:
                logger.warning(f"文件 {filename} 生成问答对失败")
                return [], filename, content, False
                
            logger.info(f"文件 {filename} 成功生成 {len(qa_pairs)} 个问答对")
            return qa_pairs, filename, content, True
            
        except Exception as e:
            logger.error(f"处理PDF文件 {pdf_path} 时出错: {str(e)}")
            return [], filename, "", False
    
    def generate_qa_from_pdfs(self):
        """
        从所有PDF文件生成问答对
        
        Returns:
            tuple: (问答对列表, 失败文件列表)
                  问答对列表: 每个元素是一个三元组 (问答对列表, 源文件名, 原始内容)
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
                    qa_pairs, filename, content, success = future.result()
                    if success:
                        results.append((qa_pairs, filename, content))
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