#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import pandas as pd
import logging
from datetime import datetime
import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ExcelWriter:
    """增强版Excel文件写入类，支持多层次问答对和元数据"""
    
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
        
        logger.info(f"增强版Excel写入器初始化，输出目录: {output_dir}")
    
    def save_qa_pairs(self, qa_pairs_list):
        """
        将多层次问答对保存到Excel文件
        
        Args:
            qa_pairs_list (list): 问答对列表，每个元素是一个四元组 (问答对列表, 源文件名, 原始内容, 元数据)
            
        Returns:
            str: 保存的Excel文件路径
        """
        try:
            # 准备数据
            data = []
            for qa_pairs, source, _, metadata in qa_pairs_list:
                doc_title = metadata.get('title', '') if metadata else ''
                
                for qa_pair in qa_pairs:
                    data.append({
                        'question': qa_pair.get('question', ''),
                        'answer': qa_pair.get('answer', ''),
                        'level': qa_pair.get('level', 'basic'),
                        'source': source,
                        'doc_title': doc_title
                    })
            
            # 创建DataFrame
            df = pd.DataFrame(data)
            
            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"qa_pairs_{timestamp}.xlsx"
            filepath = os.path.join(self.output_dir, filename)
            
            # 创建一个带有多个sheet的Excel工作簿
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                # 所有问答对
                df.to_excel(writer, sheet_name='全部问答对', index=False)
                
                # 按级别分组
                for level in ['basic', 'intermediate', 'advanced']:
                    level_df = df[df['level'] == level]
                    if not level_df.empty:
                        sheet_name = '基础问答' if level == 'basic' else '中级问答' if level == 'intermediate' else '高级问答'
                        level_df.to_excel(writer, sheet_name=sheet_name, index=False)
                
                # 按来源文件分组
                source_grouped = df.groupby('source')
                for source, group in source_grouped:
                    # 限制sheet名长度
                    sheet_name = source[:20] if len(source) > 20 else source
                    group.to_excel(writer, sheet_name=sheet_name, index=False)
            
            logger.info(f"成功将 {len(data)} 个问答对保存到文件: {filepath}")
            
            # 同时生成JSON格式输出
            json_filename = f"qa_pairs_{timestamp}.json"
            json_filepath = os.path.join(self.output_dir, json_filename)
            
            # 将数据转换为JSON友好格式
            json_data = []
            for qa_pairs, source, _, metadata in qa_pairs_list:
                doc_entry = {
                    "source": source,
                    "metadata": metadata or {},
                    "qa_pairs": qa_pairs
                }
                json_data.append(doc_entry)
            
            # 保存JSON文件
            with open(json_filepath, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"成功将数据保存为JSON格式: {json_filepath}")
            
            # 生成统计信息
            stats = {
                "total_documents": len(qa_pairs_list),
                "total_qa_pairs": len(data),
                "level_counts": {
                    "basic": len(df[df['level'] == 'basic']),
                    "intermediate": len(df[df['level'] == 'intermediate']),
                    "advanced": len(df[df['level'] == 'advanced'])
                },
                "source_counts": df.groupby('source').size().to_dict()
            }
            
            # 保存统计信息
            stats_filename = f"qa_stats_{timestamp}.json"
            stats_filepath = os.path.join(self.output_dir, stats_filename)
            with open(stats_filepath, 'w', encoding='utf-8') as f:
                json.dump(stats, f, ensure_ascii=False, indent=2)
            
            logger.info(f"成功保存统计信息: {stats_filepath}")
            
            return filepath
        
        except Exception as e:
            logger.error(f"保存问答对到Excel文件时出错: {str(e)}")
            return ""