#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
增强型PDF问答生成器Web应用
提供Web界面用于上传PDF文件、配置参数并生成问答对
"""

import os
import time
import logging
import threading
import uuid
from flask import Flask, render_template, request, jsonify, send_from_directory, session
from werkzeug.utils import secure_filename
from src.pdf_processor import PDFProcessor
from src.deepseek_client import DeepSeekClient
from src.qa_generator import QAGenerator
from src.excel_writer import ExcelWriter
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("pdf_qa_generator_gui.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 初始化Flask应用
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))
app.config['UPLOAD_FOLDER'] = 'pdf_files'
app.config['OUTPUT_FOLDER'] = 'output'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 限制上传文件大小为50MB

# 确保上传和输出目录存在
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

# 存储任务状态
tasks = {}

@app.route('/')
def index():
    """渲染主页"""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """处理文件上传请求"""
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "没有选择文件"}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({"status": "error", "message": "没有选择文件"}), 400
    
    if not file.filename.lower().endswith('.pdf'):
        return jsonify({"status": "error", "message": "只支持PDF文件"}), 400
    
    # 生成一个唯一的文件名以避免冲突
    original_filename = secure_filename(file.filename)
    filename = f"{int(time.time())}_{original_filename}"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    try:
        file.save(filepath)
        logger.info(f"文件上传成功: {filepath}")
        return jsonify({
            "status": "success", 
            "message": "文件上传成功", 
            "filename": filename,
            "original_filename": original_filename
        })
    except Exception as e:
        logger.error(f"文件上传失败: {str(e)}")
        return jsonify({"status": "error", "message": f"文件上传失败: {str(e)}"}), 500

@app.route('/process', methods=['POST'])
def process_file():
    """处理PDF生成问答对"""
    data = request.json
    filename = data.get('filename')
    params = {
        'num_qa': int(data.get('num_qa', 10)),
        'qa_level': data.get('qa_level', 'all'),
        'use_latex_ocr': data.get('use_latex_ocr', False),
        'max_workers': int(data.get('max_workers', 3)),
        'api_retries': int(data.get('api_retries', 3)),
        'retry_delay': int(data.get('retry_delay', 2)),
        'model': data.get('model', None)
    }
    
    # 处理自定义API配置
    api_key = data.get('api_key')
    api_url = data.get('api_url')
    
    if params['model'] and api_key:
        os.environ["DEEPSEEK_API_KEY"] = api_key
        params['api_key'] = api_key
    
    if params['model'] and api_url:
        os.environ["DEEPSEEK_API_URL"] = api_url
        params['api_url'] = api_url
    
    if not filename:
        return jsonify({"status": "error", "message": "未指定文件"}), 400
    
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(filepath):
        return jsonify({"status": "error", "message": "文件不存在"}), 404
    
    # 创建任务ID
    task_id = str(uuid.uuid4())
    tasks[task_id] = {
        "status": "processing",
        "progress": 0,
        "message": "初始化中...",
        "result": None
    }
    
    # 启动后台处理线程
    thread = threading.Thread(
        target=process_pdf_task,
        args=(task_id, filepath, params)
    )
    thread.daemon = True
    thread.start()
    
    return jsonify({
        "status": "success", 
        "message": "处理已开始", 
        "task_id": task_id
    })

@app.route('/task/<task_id>', methods=['GET'])
def get_task_status(task_id):
    """获取任务处理状态"""
    if task_id not in tasks:
        return jsonify({"status": "error", "message": "任务不存在"}), 404
    
    return jsonify(tasks[task_id])

@app.route('/download/<path:filename>', methods=['GET'])
def download_file(filename):
    """下载生成的文件"""
    return send_from_directory(
        app.config['OUTPUT_FOLDER'], 
        filename, 
        as_attachment=True
    )

def process_pdf_task(task_id, filepath, params):
    """后台处理PDF任务"""
    try:
        tasks[task_id]["message"] = "正在处理PDF文件..."
        tasks[task_id]["progress"] = 10
        
        # 如果指定了模型，设置环境变量
        if params['model']:
            os.environ["MODEL_NAME"] = params['model']
            
            # 如果提供了API配置，也设置相应的环境变量
            if 'api_key' in params and params['api_key']:
                os.environ["DEEPSEEK_API_KEY"] = params['api_key']
            
            if 'api_url' in params and params['api_url']:
                os.environ["DEEPSEEK_API_URL"] = params['api_url']
        
        # 处理qa_level参数
        qa_level = None if params['qa_level'] == 'all' else params['qa_level']
        
        # 创建临时目录存放单个PDF
        temp_dir = os.path.join(app.config['UPLOAD_FOLDER'], task_id)
        os.makedirs(temp_dir, exist_ok=True)
        
        # 复制文件到临时目录
        import shutil
        temp_filepath = os.path.join(temp_dir, os.path.basename(filepath))
        shutil.copy2(filepath, temp_filepath)
        
        tasks[task_id]["progress"] = 20
        tasks[task_id]["message"] = "正在初始化问答生成器..."
        
        # 初始化问答生成器
        qa_generator = QAGenerator(
            pdf_dir=temp_dir, 
            num_qa_pairs=params['num_qa'],
            max_workers=params['max_workers'],
            api_max_retries=params['api_retries'],
            api_retry_delay=params['retry_delay'],
            qa_level=qa_level,
            use_latex_ocr=params['use_latex_ocr']
        )
        
        tasks[task_id]["progress"] = 30
        tasks[task_id]["message"] = "正在从PDF生成问答对..."
        
        # 从PDF生成问答对
        qa_results, failed_files = qa_generator.generate_qa_from_pdfs()
        
        tasks[task_id]["progress"] = 80
        tasks[task_id]["message"] = "正在保存结果..."
        
        if not qa_results:
            tasks[task_id]["status"] = "completed"
            tasks[task_id]["progress"] = 100
            tasks[task_id]["message"] = "没有生成任何问答对"
            tasks[task_id]["result"] = {
                "success": False,
                "error": "没有生成任何问答对",
                "failed_files": failed_files
            }
            return
        
        # 初始化Excel写入器
        excel_writer = ExcelWriter(output_dir=app.config['OUTPUT_FOLDER'])
        
        # 保存问答对到Excel
        excel_file = excel_writer.save_qa_pairs(qa_results)
        
        if not excel_file:
            tasks[task_id]["status"] = "completed"
            tasks[task_id]["progress"] = 100
            tasks[task_id]["message"] = "保存结果到Excel文件失败"
            tasks[task_id]["result"] = {
                "success": False,
                "error": "保存结果到Excel文件失败"
            }
            return
        
        # 处理完成，设置任务状态
        tasks[task_id]["status"] = "completed"
        tasks[task_id]["progress"] = 100
        tasks[task_id]["message"] = "处理完成"
        
        # 统计信息
        total_qa_pairs = sum(len(qa_pairs) for qa_pairs, _, _, _ in qa_results)
        
        # 设置结果
        tasks[task_id]["result"] = {
            "success": True,
            "excel_file": os.path.basename(excel_file),
            "json_file": os.path.basename(excel_file).replace('.xlsx', '.json'),
            "stats_file": os.path.basename(excel_file).replace('qa_pairs_', 'qa_stats_'),
            "failed_files": failed_files,
            "stats": {
                "total_qa_pairs": total_qa_pairs,
                "processed_files": len(qa_results),
                "failed_files_count": len(failed_files)
            }
        }
        
        # 清理临时目录
        shutil.rmtree(temp_dir, ignore_errors=True)
        
    except Exception as e:
        logger.error(f"处理PDF任务时出错: {str(e)}", exc_info=True)
        tasks[task_id]["status"] = "completed"
        tasks[task_id]["progress"] = 100
        tasks[task_id]["message"] = f"处理出错: {str(e)}"
        tasks[task_id]["result"] = {
            "success": False,
            "error": str(e)
        }

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=8080) 