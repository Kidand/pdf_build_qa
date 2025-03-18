#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PDF问答生成器主程序

使用DeepSeek API从PDF文件生成问答对，并保存到Excel文件
"""

import os
import argparse
import logging
from src.pdf_processor import PDFProcessor
from src.deepseek_client import DeepSeekClient
from src.qa_generator import QAGenerator
from src.excel_writer import ExcelWriter
from dotenv import load_dotenv

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("pdf_qa_generator.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='从PDF文件生成问答对并保存到Excel文件')
    
    parser.add_argument('--pdf_dir', type=str, default='pdf_files',
                        help='PDF文件所在目录 (默认: pdf_files)')
    
    parser.add_argument('--output_dir', type=str, default='output',
                        help='输出目录 (默认: output)')
    
    parser.add_argument('--num_qa', type=int, default=20,
                        help='每个PDF生成的问答对数量 (默认: 20)')
    
    parser.add_argument('--max_workers', type=int, default=3,
                        help='最大并行处理的文件数 (默认: 3)')
    
    return parser.parse_args()

def main():
    """主程序入口"""
    # 加载环境变量
    load_dotenv()
    
    # 解析命令行参数
    args = parse_arguments()
    
    try:
        logger.info("开始执行PDF问答生成器")
        
        # 检查PDF目录是否存在
        if not os.path.exists(args.pdf_dir):
            logger.error(f"PDF目录不存在: {args.pdf_dir}")
            print(f"错误: PDF目录不存在: {args.pdf_dir}")
            return
        
        # 初始化问答生成器
        qa_generator = QAGenerator(
            pdf_dir=args.pdf_dir, 
            num_qa_pairs=args.num_qa,
            max_workers=args.max_workers
        )
        
        # 初始化Excel写入器
        excel_writer = ExcelWriter(output_dir=args.output_dir)
        
        # 从PDF生成问答对
        qa_results = qa_generator.generate_qa_from_pdfs()
        
        if not qa_results:
            logger.warning("没有生成任何问答对")
            print("警告: 没有生成任何问答对")
            return
        
        # 保存问答对到Excel
        excel_file = excel_writer.save_qa_pairs(qa_results)
        
        if excel_file:
            logger.info(f"处理完成，结果保存到: {excel_file}")
            print(f"处理完成，结果保存到: {excel_file}")
        else:
            logger.error("保存结果到Excel文件失败")
            print("错误: 保存结果到Excel文件失败")
    
    except Exception as e:
        logger.error(f"执行过程中发生错误: {str(e)}", exc_info=True)
        print(f"执行过程中发生错误: {str(e)}")

if __name__ == "__main__":
    main()