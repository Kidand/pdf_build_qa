#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import pandas as pd
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ExcelWriter:
    """Excel文件写入类"""
    
    def __init__(self, output_dir="output"):
        """
        初始化Excel写入器
        
        Args:
            output_dir (str): 输出目录路径
        """
        self.output_dir = output_dir
        
        # 确保输出目录存在
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            logger.info(f"创建输出目录: {output_dir}")
        
        logger.info(f"Excel写入器初始化，输出目录: {output_dir}")
    
    def save_qa_pairs(self, qa_pairs_list):
        """
        将问答对保存到Excel文件
        
        Args:
            qa_pairs_list (list): 问答对列表，每个元素是一个三元组 (问答对列表, 源文件名, 原始内容)
            
        Returns:
            str: 保存的Excel文件路径
        """
        try:
            # 准备数据
            data = []
            for qa_pairs, source, _ in qa_pairs_list:
                for qa_pair in qa_pairs:
                    data.append({
                        'question': qa_pair.get('question', ''),
                        'answer': qa_pair.get('answer', ''),
                        'source': source
                    })
            
            # 创建DataFrame
            df = pd.DataFrame(data)
            
            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"qa_pairs_{timestamp}.xlsx"
            filepath = os.path.join(self.output_dir, filename)
            
            # 保存Excel文件
            df.to_excel(filepath, index=False)
            logger.info(f"成功将 {len(data)} 个问答对保存到文件: {filepath}")
            
            return filepath
        
        except Exception as e:
            logger.error(f"保存问答对到Excel文件时出错: {str(e)}")
            return ""