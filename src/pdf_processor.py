#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import logging
import re
import io
import numpy as np
from PIL import Image
import PyPDF2
import pdfplumber
import fitz  # PyMuPDF
from pix2tex.cli import LatexOCR

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PDFProcessor:
    """增强型PDF处理类，支持文本、结构和公式提取"""
    
    def __init__(self, pdf_dir, use_latex_ocr=True):
        """
        初始化PDF处理器
        
        Args:
            pdf_dir (str): PDF文件所在的目录路径
            use_latex_ocr (bool): 是否使用LatexOCR处理公式
        """
        self.pdf_dir = pdf_dir
        self.use_latex_ocr = use_latex_ocr
        self.latex_ocr = None
        
        # 如果启用了LaTeX OCR，就初始化模型
        if self.use_latex_ocr:
            try:
                logger.info("正在加载LatexOCR模型...")
                self.latex_ocr = LatexOCR()
                logger.info("LatexOCR模型加载完成")
            except Exception as e:
                logger.error(f"加载LatexOCR模型失败: {str(e)}")
                self.use_latex_ocr = False
        
        logger.info(f"增强型PDF处理器初始化，目录: {pdf_dir}, 公式OCR: {self.use_latex_ocr}")
    
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
    
    def _detect_and_extract_formulas(self, doc, page_num):
        """
        检测并提取页面中的公式
        
        Args:
            doc: PyMuPDF文档对象
            page_num: 页码
            
        Returns:
            list: 公式列表，每个元素是(bbox, latex)元组
        """
        if not self.use_latex_ocr or self.latex_ocr is None:
            return []
            
        formulas = []
        page = doc[page_num]
        
        # 使用PyMuPDF检测可能是公式的区域
        # 这里使用启发式方法：寻找被空白环绕且没有明确文本结构的区域
        blocks = page.get_text("dict")["blocks"]
        
        for block in blocks:
            if "lines" not in block:
                continue
                
            # 检查是否可能是公式区域
            if len(block["lines"]) <= 3:  # 通常公式不会有很多行
                # 获取区域坐标
                bbox = block["bbox"]
                x0, y0, x1, y1 = bbox
                
                # 为了更好地识别，稍微扩大区域
                margin = 5
                x0 = max(0, x0 - margin)
                y0 = max(0, y0 - margin)
                x1 = min(page.rect.width, x1 + margin)
                y1 = min(page.rect.height, y1 + margin)
                
                # 渲染区域为图像
                pix = page.get_pixmap(clip=(x0, y0, x1, y1), matrix=fitz.Matrix(2, 2))
                img_bytes = pix.tobytes("png")
                img = Image.open(io.BytesIO(img_bytes))
                
                # 使用LatexOCR识别公式
                try:
                    latex = self.latex_ocr(img)
                    if latex and len(latex) > 5:  # 确保有意义的输出
                        formulas.append((bbox, latex))
                        logger.debug(f"识别到公式: {latex}")
                except Exception as e:
                    logger.debug(f"公式识别失败: {str(e)}")
                    continue
        
        return formulas
    
    def _process_with_pdfplumber(self, pdf_path):
        """
        使用pdfplumber提取文本
        
        Args:
            pdf_path: PDF文件路径
            
        Returns:
            str: 提取的文本
        """
        text = ""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text(x_tolerance=1, y_tolerance=3)
                    if page_text:
                        text += page_text + "\n"
            return text
        except Exception as e:
            logger.error(f"使用pdfplumber提取文本失败: {str(e)}")
            return ""
    
    def _process_with_pymupdf(self, pdf_path):
        """
        使用PyMuPDF提取结构化内容
        
        Args:
            pdf_path: PDF文件路径
            
        Returns:
            tuple: (结构化文本, 公式列表)
        """
        structured_text = ""
        all_formulas = []
        
        try:
            # 打开PDF文档
            doc = fitz.open(pdf_path)
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                # 提取普通文本
                page_text = page.get_text("text")
                
                # 检测并提取公式
                formulas = self._detect_and_extract_formulas(doc, page_num)
                all_formulas.extend([(page_num, *formula) for formula in formulas])
                
                # 添加页面文本
                structured_text += page_text + "\n"
            
            return structured_text, all_formulas
        except Exception as e:
            logger.error(f"使用PyMuPDF提取结构化内容失败: {str(e)}")
            return "", []
    
    def _integrate_content(self, basic_text, structured_text, formulas):
        """
        整合不同来源的内容，确保文本连贯，公式位于正确位置
        
        Args:
            basic_text: 基本文本
            structured_text: 结构化文本
            formulas: 公式列表
            
        Returns:
            str: 整合后的最终文本
        """
        # 如果没有检测到公式，直接返回更好的文本版本
        if not formulas:
            return structured_text if structured_text else basic_text
        
        # 将公式按照页码和位置排序
        formulas.sort(key=lambda x: (x[0], x[1][1]))  # 按页码和y坐标排序
        
        # 将公式插入到文本中适当位置
        lines = structured_text.split('\n')
        result = []
        formula_idx = 0
        
        # 假设每个公式应该插入在最近的文本段落后面
        current_page = 0
        
        for i, line in enumerate(lines):
            # 检查是否需要插入公式
            result.append(line)
            
            if formula_idx < len(formulas):
                formula_page, formula_bbox, formula_latex = formulas[formula_idx]
                
                if i < len(lines) - 1:
                    next_line = lines[i + 1]
                    if not next_line.strip():  # 如果下一行是空行，可能是段落结束
                        if formula_page == current_page:
                            # 在段落结束处插入公式
                            result.append(f"[FORMULA: {formula_latex}]")
                            formula_idx += 1
            
            # 估计当前页码
            if not line.strip() and i > 0 and i < len(lines) - 1:
                # 检测可能的页面变化
                if lines[i - 1].strip() and lines[i + 1].strip():
                    current_page += 1
        
        # 将剩余的公式添加到文档末尾
        while formula_idx < len(formulas):
            _, _, formula_latex = formulas[formula_idx]
            result.append(f"[FORMULA: {formula_latex}]")
            formula_idx += 1
        
        return '\n'.join(result)
    
    def extract_text_from_pdf(self, pdf_path):
        """
        从PDF文件中提取增强的文本内容
        
        Args:
            pdf_path (str): PDF文件路径
            
        Returns:
            tuple: (增强文本内容, 文件名, 元数据)
        """
        try:
            pdf_filename = os.path.basename(pdf_path)
            logger.info(f"开始增强处理PDF文件: {pdf_filename}")
            
            # 使用PyPDF2提取基本文本
            basic_text = ""
            metadata = {}
            
            try:
                reader = PyPDF2.PdfReader(pdf_path)
                # 提取元数据
                if reader.metadata:
                    metadata = {
                        "title": reader.metadata.get('/Title', ''),
                        "author": reader.metadata.get('/Author', ''),
                        "subject": reader.metadata.get('/Subject', ''),
                        "creator": reader.metadata.get('/Creator', ''),
                        "producer": reader.metadata.get('/Producer', '')
                    }
                
                # 提取文本
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        basic_text += page_text + "\n"
            except Exception as e:
                logger.error(f"使用PyPDF2提取文本失败: {str(e)}")
            
            # 使用pdfplumber提取更精确的文本
            plumber_text = self._process_with_pdfplumber(pdf_path)
            
            # 使用PyMuPDF提取结构化文本和公式
            structured_text, formulas = self._process_with_pymupdf(pdf_path)
            
            # 整合内容
            final_text = self._integrate_content(basic_text, structured_text, formulas)
            
            # 后处理：清理文本中的特殊字符和多余空白
            final_text = re.sub(r'\s+', ' ', final_text)  # 替换多个空白为单个空格
            final_text = re.sub(r'(\n\s*){3,}', '\n\n', final_text)  # 最多保留两个连续换行
            
            content_length = len(final_text)
            formula_count = len(formulas)
            logger.info(f"成功从 {pdf_filename} 提取文本，共 {content_length} 个字符，检测到 {formula_count} 个公式")
            
            return final_text, pdf_filename, metadata
        except Exception as e:
            logger.error(f"从PDF文件 {pdf_path} 提取文本时出错: {str(e)}")
            return "", os.path.basename(pdf_path), {}