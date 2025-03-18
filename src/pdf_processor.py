#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from PyPDF2 import PdfReader
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PDFProcessor:
    """处理PDF文件的类"""
    
    def __init__(self, pdf_dir):
        """
        初始化PDF处理器
        
        Args:
            pdf_dir (str): PDF文件所在的目录路径
        """
        self.pdf_dir = pdf_dir
        logger.info(f"PDF处理器初始化，目录: {pdf_dir}")
        
    def get_pdf_files(self):
        """
        获取目录中所有的PDF文件
        
        Returns:
            list: PDF文件路径列表
        """
        pdf_files = []
        try:
            for file in os.listdir(self.pdf_dir):
                if file.lower().endswith('.pdf'):
                    pdf_files.append(os.path.join(self.pdf_dir, file))
            logger.info(f"找到 {len(pdf_files)} 个PDF文件")
            return pdf_files
        except Exception as e:
            logger.error(f"获取PDF文件列表时出错: {str(e)}")
            return []
    
    def extract_text_from_pdf(self, pdf_path):
        """
        从PDF文件中提取文本内容
        
        Args:
            pdf_path (str): PDF文件路径
            
        Returns:
            tuple: (文本内容, 文件名)
        """
        try:
            pdf_filename = os.path.basename(pdf_path)
            logger.info(f"开始处理PDF文件: {pdf_filename}")
            
            reader = PdfReader(pdf_path)
            text = ""
            
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            
            logger.info(f"成功从 {pdf_filename} 提取文本，共 {len(text)} 个字符")
            return text, pdf_filename
        except Exception as e:
            logger.error(f"从PDF文件 {pdf_path} 提取文本时出错: {str(e)}")
            return "", os.path.basename(pdf_path)