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
    
    parser.add_argument('--num_qa', type=int, default=10,
                        help='每个PDF生成的问答对数量 (默认: 10)')
    
    parser.add_argument('--max_workers', type=int, default=3,
                        help='最大并行处理的文件数 (默认: 3)')
    
    parser.add_argument('--api_retries', type=int, default=3,
                        help='API尝试调用次数 (默认: 3)')
    
    parser.add_argument('--retry_delay', type=int, default=2,
                        help='API重试间隔时间(秒) (默认: 2)')
    
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
            max_workers=args.max_workers,
            api_max_retries=args.api_retries,
            api_retry_delay=args.retry_delay
        )
        
        # 初始化Excel写入器
        excel_writer = ExcelWriter(output_dir=args.output_dir)
        
        # 从PDF生成问答对
        qa_results, failed_files = qa_generator.generate_qa_from_pdfs()
        
        if not qa_results:
            logger.warning("没有生成任何问答对")
            print("警告: 没有生成任何问答对")
            
            if failed_files:
                print(f"\n处理失败的文件 ({len(failed_files)}):")
                for file in failed_files:
                    print(f"  - {file}")
            return
        
        # 保存问答对到Excel
        excel_file = excel_writer.save_qa_pairs(qa_results)
        
        if excel_file:
            logger.info(f"处理完成，结果保存到: {excel_file}")
            print(f"处理完成，结果保存到: {excel_file}")
            
            # 保存失败文件列表到单独的文本文件
            if failed_files:
                failed_files_log = os.path.join(args.output_dir, "failed_files.txt")
                with open(failed_files_log, "w", encoding="utf-8") as f:
                    f.write(f"处理失败的文件列表 ({len(failed_files)}):\n")
                    for file in failed_files:
                        f.write(f"{file}\n")
                
                print(f"\n处理失败的文件 ({len(failed_files)}):")
                for file in failed_files:
                    print(f"  - {file}")
                print(f"失败文件列表已保存到: {failed_files_log}")
        else:
            logger.error("保存结果到Excel文件失败")
            print("错误: 保存结果到Excel文件失败")
    
    except Exception as e:
        logger.error(f"执行过程中发生错误: {str(e)}", exc_info=True)
        print(f"执行过程中发生错误: {str(e)}")

if __name__ == "__main__":
    main()