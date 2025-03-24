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
import json
import shutil
from flask import Flask, render_template, request, jsonify, send_from_directory, session
from werkzeug.utils import secure_filename
from src.pdf_processor import PDFProcessor
from src.deepseek_client import DeepSeekClient
from src.qa_generator import QAGenerator
from src.excel_writer import ExcelWriter
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed

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
TASKS_FILE = 'tasks_status.json'

# 加载已有任务状态(如果存在)
def load_tasks():
    global tasks
    try:
        if os.path.exists(TASKS_FILE):
            with open(TASKS_FILE, 'r', encoding='utf-8') as f:
                tasks = json.load(f)
                logger.info(f"已加载 {len(tasks)} 个任务状态")
    except Exception as e:
        logger.error(f"加载任务状态失败: {str(e)}")
        tasks = {}

# 保存任务状态
def save_tasks():
    try:
        with open(TASKS_FILE, 'w', encoding='utf-8') as f:
            json.dump(tasks, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"保存任务状态失败: {str(e)}")

# 在应用启动时加载任务状态
load_tasks()

@app.route('/')
def index():
    """渲染主页"""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """处理单个文件上传请求"""
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "没有选择文件"}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({"status": "error", "message": "没有选择文件"}), 400
    
    if not file.filename.lower().endswith('.pdf'):
        return jsonify({"status": "error", "message": "只支持PDF文件"}), 400
    
    # 生成一个唯一的文件名以避免冲突，但保留原始文件名
    original_filename = file.filename
    # 移除文件名中的不安全字符，但保留中文字符
    base_name = os.path.splitext(original_filename)[0]
    # 过滤掉不安全的字符，但保留中文和基本拉丁字符
    safe_base_name = "".join(c for c in base_name if c.isalnum() or c in ".-_ " or ('\u4e00' <= c <= '\u9fff'))
    if not safe_base_name:
        safe_base_name = "pdf_file"  # 如果过滤后为空，使用默认名称
    
    # 添加时间戳确保唯一性
    filename = f"{int(time.time())}_{safe_base_name}.pdf"
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

@app.route('/upload_batch', methods=['POST'])
def upload_batch():
    """处理批量文件上传请求"""
    if 'files' not in request.files:
        return jsonify({"status": "error", "message": "没有选择文件"}), 400
    
    files = request.files.getlist('files')
    
    if not files or files[0].filename == '':
        return jsonify({"status": "error", "message": "没有选择文件"}), 400
    
    # 创建批次目录
    batch_id = str(uuid.uuid4())
    batch_dir = os.path.join(app.config['UPLOAD_FOLDER'], batch_id)
    os.makedirs(batch_dir, exist_ok=True)
    
    # 记录文件信息
    file_info = []
    success_count = 0
    
    for file in files:
        # 检查文件名是否以.pdf结尾（不区分大小写）
        original_filename = file.filename
        if not original_filename.lower().endswith('.pdf'):
            logger.warning(f"跳过非PDF文件: {original_filename}")
            continue
        
        # 保留原始文件名，但移除不安全字符，保留中文字符
        # 使用一种更安全的方式处理文件名
        base_name = os.path.splitext(original_filename)[0]
        # 过滤掉不安全的字符，但保留中文和基本拉丁字符
        safe_base_name = "".join(c for c in base_name if c.isalnum() or c in ".-_ " or ('\u4e00' <= c <= '\u9fff'))
        if not safe_base_name:
            safe_base_name = f"pdf_file_{int(time.time())}"  # 如果过滤后为空，使用默认名称
        
        safe_filename = f"{safe_base_name}.pdf"
        
        filepath = os.path.join(batch_dir, safe_filename)
        
        try:
            # 如果存在同名文件，添加时间戳
            if os.path.exists(filepath):
                timestamp = int(time.time())
                safe_filename = f"{safe_base_name}_{timestamp}.pdf"
                filepath = os.path.join(batch_dir, safe_filename)
            
            file.save(filepath)
            file_info.append({
                "original_name": original_filename,
                "saved_name": safe_filename,
                "size": os.path.getsize(filepath)
            })
            success_count += 1
            logger.info(f"批量上传 - 文件保存成功: {filepath}")
        except Exception as e:
            logger.error(f"批量上传 - 文件保存失败: {original_filename}, 错误: {str(e)}")
    
    if success_count == 0:
        # 如果没有成功上传任何文件，删除批次目录
        try:
            shutil.rmtree(batch_dir)
        except Exception:
            pass
        return jsonify({"status": "error", "message": "没有上传任何有效的PDF文件"}), 400
    
    logger.info(f"批量上传完成 - 批次ID: {batch_id}, 成功文件数: {success_count}")
    return jsonify({
        "status": "success",
        "message": f"成功上传 {success_count} 个文件",
        "batch_id": batch_id,
        "file_count": success_count,
        "files": file_info
    })

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

@app.route('/process_batch', methods=['POST'])
def process_batch():
    """处理批量PDF生成问答对"""
    data = request.json
    batch_id = data.get('batch_id')
    
    if not batch_id:
        return jsonify({"status": "error", "message": "未指定批次ID"}), 400
    
    # 验证批次目录是否存在
    batch_dir = os.path.join(app.config['UPLOAD_FOLDER'], batch_id)
    if not os.path.exists(batch_dir) or not os.path.isdir(batch_dir):
        return jsonify({"status": "error", "message": "批次不存在或已过期"}), 404
    
    # 检查目录中是否有PDF文件
    pdf_files = [f for f in os.listdir(batch_dir) if f.lower().endswith('.pdf')]
    if not pdf_files:
        return jsonify({"status": "error", "message": "批次中没有PDF文件"}), 400
    
    # 准备参数
    params = {
        'num_qa': int(data.get('num_qa', 10)),
        'qa_level': data.get('qa_level', 'all'),
        'use_latex_ocr': data.get('use_latex_ocr', False),
        'max_workers': int(data.get('max_workers', 3)),
        'api_retries': int(data.get('api_retries', 3)),
        'retry_delay': int(data.get('retry_delay', 2)),
        'model': data.get('model', None),
        'batch_id': batch_id,
        'batch_dir': batch_dir
    }
    
    # 处理自定义API配置
    if data.get('model'):
        if 'api_key' in data and data['api_key']:
            params['api_key'] = data['api_key']
        
        if 'api_url' in data and data['api_url']:
            params['api_url'] = data['api_url']
    
    # 创建任务ID
    task_id = str(uuid.uuid4())
    tasks[task_id] = {
        "status": "processing",
        "progress": 0,
        "message": f"初始化批处理 ({len(pdf_files)} 个文件)...",
        "result": None
    }
    
    # 启动后台处理线程
    thread = threading.Thread(
        target=process_pdf_batch_task,
        args=(task_id, params)
    )
    thread.daemon = True
    thread.start()
    
    return jsonify({
        "status": "success", 
        "message": "批处理已开始", 
        "task_id": task_id,
        "file_count": len(pdf_files)
    })

@app.route('/task/<task_id>', methods=['GET'])
def get_task_status(task_id):
    """获取任务处理状态"""
    if task_id not in tasks:
        # 尝试重新加载任务状态
        load_tasks()
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
        save_tasks()  # 保存任务状态更新
        
        # 记录处理文件信息
        logger.info(f"开始处理PDF文件: {filepath}")
        logger.info(f"处理参数: qa_level={params['qa_level']}, num_qa={params['num_qa']}, use_latex_ocr={params['use_latex_ocr']}")
        
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
        
        tasks[task_id]["progress"] = 30
        tasks[task_id]["message"] = "正在初始化问答生成器..."
        save_tasks()  # 保存任务状态更新
        
        # 初始化问答生成器
        qa_generator = QAGenerator(
            pdf_dir=temp_dir, 
            num_qa_pairs=params['num_qa'],
            max_workers=1,  # 只处理一个文件不需要并行
            api_max_retries=params['api_retries'],
            api_retry_delay=params['retry_delay'],
            qa_level=qa_level,
            use_latex_ocr=params['use_latex_ocr']
        )
        
        # 添加Monkey Patch来记录提示词构建过程
        original_prepare_prompt = qa_generator._prepare_qa_prompt
        def patched_prepare_prompt(content, level, num_pairs, metadata=None):
            # 记录原始内容信息
            logger.info(f"PDF内容长度: {len(content)} 字符")
            if content:
                logger.info(f"PDF内容前100字符: {content[:100]}...")
                logger.info(f"PDF内容后100字符: {content[-100:]}...")
            else:
                logger.warning("PDF内容为空!")
            
            # 获取模板
            template = qa_generator._get_prompt_template(level, num_pairs, metadata)
            # 记录模板信息
            logger.info(f"使用模板级别: {level or '混合'}, 模板长度: {len(template)} 字符")
            logger.info(f"模板中的占位符: {'{{content[:50000]}}' in template}")
            
            # 调用原始方法
            prompt = original_prepare_prompt(content, level, num_pairs, metadata)
            
            # 记录最终提示词
            logger.info(f"最终提示词长度: {len(prompt)} 字符")
            if 'content' in prompt:
                content_pos = prompt.find('内容')
                if content_pos > 0:
                    logger.info(f"提示词中'内容'附近文本: ...{prompt[content_pos-20:content_pos+100]}...")
                else:
                    logger.info(f"提示词前100字符: {prompt[:100]}...")
            
            return prompt
        
        # 替换方法以添加日志
        qa_generator._prepare_qa_prompt = patched_prepare_prompt
        
        # 同样记录DeepSeekClient的调用
        original_generate_qa = qa_generator.deepseek_client.generate_qa_pairs
        def patched_generate_qa(prompt, num_pairs):
            logger.info(f"调用DeepSeek API, 提示词长度: {len(prompt)}, 请求生成 {num_pairs} 个问答对")
            return original_generate_qa(prompt, num_pairs)
        
        qa_generator.deepseek_client.generate_qa_pairs = patched_generate_qa
        
        tasks[task_id]["progress"] = 50
        tasks[task_id]["message"] = "正在生成问答对..."
        save_tasks()  # 保存任务状态更新
        
        # 使用QAGenerator的process_pdf方法处理单个PDF文件
        logger.info(f"调用process_pdf处理文件: {temp_filepath}")
        qa_pairs, pdf_filename, content, metadata, success = qa_generator.process_pdf(temp_filepath)
        
        # 记录处理结果
        if success:
            logger.info(f"文件处理成功: {pdf_filename}, 生成 {len(qa_pairs)} 个问答对")
            if qa_pairs:
                logger.info(f"第一个问题: {qa_pairs[0].get('question', '')[:100]}")
        else:
            logger.error(f"文件处理失败: {pdf_filename}")
        
        if not success or not qa_pairs:
            tasks[task_id]["status"] = "completed"
            tasks[task_id]["progress"] = 100
            tasks[task_id]["message"] = "没有生成任何问答对"
            tasks[task_id]["result"] = {
                "success": False,
                "error": "没有生成任何问答对"
            }
            # 清理临时目录
            shutil.rmtree(temp_dir, ignore_errors=True)
            save_tasks()  # 保存最终任务状态
            return
        
        # 收集结果（不保存原文）
        qa_results = [(qa_pairs, pdf_filename, "", metadata)]
        
        tasks[task_id]["progress"] = 80
        tasks[task_id]["message"] = "正在保存结果..."
        save_tasks()  # 保存任务状态更新
        
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
            # 清理临时目录
            shutil.rmtree(temp_dir, ignore_errors=True)
            save_tasks()  # 保存最终任务状态
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
            "stats": {
                "total_qa_pairs": total_qa_pairs,
                "processed_files": len(qa_results),
                "failed_files_count": 0
            },
            "pdf_filepath": temp_filepath  # 添加PDF文件路径信息
        }
        
        # 不再删除PDF文件
        # shutil.rmtree(temp_dir, ignore_errors=True)
        logger.info(f"任务完成，保留PDF文件: {temp_filepath}")
        save_tasks()  # 保存最终任务状态
        
    except Exception as e:
        logger.error(f"处理PDF任务时出错: {str(e)}", exc_info=True)
        tasks[task_id]["status"] = "completed"
        tasks[task_id]["progress"] = 100
        tasks[task_id]["message"] = f"处理出错: {str(e)}"
        tasks[task_id]["result"] = {
            "success": False,
            "error": str(e)
        }
        save_tasks()  # 保存错误状态
        # 失败时也不删除PDF文件
        # try:
        #     shutil.rmtree(temp_dir, ignore_errors=True)
        # except:
        #     pass
        logger.error(f"处理出错，但保留PDF文件: {temp_filepath if 'temp_filepath' in locals() else '未知'}")

def process_pdf_batch_task(task_id, params):
    """后台处理批量PDF任务"""
    try:
        batch_dir = params['batch_dir']
        pdf_files = [f for f in os.listdir(batch_dir) if f.lower().endswith('.pdf')]
        total_files = len(pdf_files)
        
        # 记录批处理信息
        logger.info(f"开始批量处理 {total_files} 个PDF文件, 目录: {batch_dir}")
        logger.info(f"PDF文件列表: {', '.join(pdf_files)}")
        logger.info(f"处理参数: qa_level={params['qa_level']}, num_qa={params['num_qa']}, use_latex_ocr={params['use_latex_ocr']}, max_workers={params['max_workers']}")
        
        tasks[task_id]["message"] = f"正在准备批量处理 {total_files} 个PDF文件..."
        tasks[task_id]["progress"] = 10
        save_tasks()  # 保存任务状态更新
        
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
        
        tasks[task_id]["progress"] = 30
        tasks[task_id]["message"] = "正在初始化问答生成器..."
        save_tasks()  # 保存任务状态更新
        
        # 初始化问答生成器
        qa_generator = QAGenerator(
            pdf_dir=batch_dir, 
            num_qa_pairs=params['num_qa'],
            max_workers=params['max_workers'],
            api_max_retries=params['api_retries'],
            api_retry_delay=params['retry_delay'],
            qa_level=qa_level,
            use_latex_ocr=params['use_latex_ocr']
        )
        
        # 添加Monkey Patch来记录PDF处理过程
        original_process_pdf = qa_generator.process_pdf
        def patched_process_pdf(pdf_path):
            logger.info(f"开始处理单个PDF文件: {pdf_path}")
            result = original_process_pdf(pdf_path)
            qa_pairs, filename, content, metadata, success = result
            
            if content:
                logger.info(f"PDF '{filename}' 内容长度: {len(content)} 字符")
                logger.info(f"PDF '{filename}' 内容前100字符: {content[:100]}...")
            else:
                logger.warning(f"PDF '{filename}' 内容为空!")
                
            if success:
                logger.info(f"文件处理成功: {filename}, 生成 {len(qa_pairs)} 个问答对")
                if qa_pairs:
                    logger.info(f"第一个问题: {qa_pairs[0].get('question', '')[:100]}")
            else:
                logger.error(f"文件处理失败: {filename}")
                
            return result
        
        # 替换方法以添加日志
        qa_generator.process_pdf = patched_process_pdf
        
        tasks[task_id]["progress"] = 40
        tasks[task_id]["message"] = f"正在处理 {total_files} 个PDF文件..."
        save_tasks()  # 保存任务状态更新
        
        # 使用QAGenerator的generate_qa_from_pdfs方法处理PDF文件
        logger.info(f"调用generate_qa_from_pdfs开始批量处理PDF文件")
        qa_results, failed_files = qa_generator.generate_qa_from_pdfs()
        
        # 记录处理结果
        logger.info(f"批量处理完成: 成功处理 {len(qa_results)} 个文件, 失败 {len(failed_files)} 个文件")
        if failed_files:
            logger.warning(f"处理失败的文件: {', '.join(failed_files)}")
        
        # 修改qa_results中的原文内容为空字符串，以减小内存占用
        qa_results_no_content = []
        for qa_pairs, source, _, metadata in qa_results:
            qa_results_no_content.append((qa_pairs, source, "", metadata))
        
        tasks[task_id]["progress"] = 80
        tasks[task_id]["message"] = "正在保存结果..."
        save_tasks()  # 保存任务状态更新
        
        if not qa_results_no_content:
            tasks[task_id]["status"] = "completed"
            tasks[task_id]["progress"] = 100
            tasks[task_id]["message"] = "没有生成任何问答对"
            tasks[task_id]["result"] = {
                "success": False,
                "error": "没有生成任何问答对",
                "failed_files": failed_files
            }
            
            # 清理批次目录
            shutil.rmtree(batch_dir, ignore_errors=True)
            save_tasks()  # 保存最终任务状态
            return
        
        # 收集所有PDF文件路径
        pdf_file_paths = []
        for pdf_file in pdf_files:
            pdf_file_paths.append(os.path.join(batch_dir, pdf_file))
        
        # 初始化Excel写入器
        excel_writer = ExcelWriter(output_dir=app.config['OUTPUT_FOLDER'])
        
        # 保存问答对到Excel
        excel_file = excel_writer.save_qa_pairs(qa_results_no_content)
        
        if not excel_file:
            tasks[task_id]["status"] = "completed"
            tasks[task_id]["progress"] = 100
            tasks[task_id]["message"] = "保存结果到Excel文件失败"
            tasks[task_id]["result"] = {
                "success": False,
                "error": "保存结果到Excel文件失败"
            }
            
            # 清理批次目录
            shutil.rmtree(batch_dir, ignore_errors=True)
            save_tasks()  # 保存最终任务状态
            return
        
        # 处理完成，设置任务状态
        tasks[task_id]["status"] = "completed"
        tasks[task_id]["progress"] = 100
        tasks[task_id]["message"] = "批处理完成"
        save_tasks()  # 保存任务状态更新
        
        # 统计信息
        total_qa_pairs = sum(len(qa_pairs) for qa_pairs, _, _, _ in qa_results_no_content)
        
        # 设置结果
        tasks[task_id]["result"] = {
            "success": True,
            "excel_file": os.path.basename(excel_file),
            "json_file": os.path.basename(excel_file).replace('.xlsx', '.json'),
            "stats_file": os.path.basename(excel_file).replace('qa_pairs_', 'qa_stats_').replace('.xlsx', '.json'),
            "failed_files": failed_files,
            "stats": {
                "total_qa_pairs": total_qa_pairs,
                "processed_files": len(qa_results_no_content),
                "failed_files_count": len(failed_files),
                "total_files": total_files
            },
            "pdf_directory": batch_dir,  # 添加批次目录信息
            "pdf_files": pdf_file_paths  # 添加所有PDF文件路径
        }
        
        # 保存详细统计信息到JSON文件
        stats_file = os.path.join(
            app.config['OUTPUT_FOLDER'], 
            os.path.basename(excel_file).replace('qa_pairs_', 'qa_stats_').replace('.xlsx', '.json')
        )
        
        # 构建详细统计信息
        detailed_stats = {
            "batch_id": params['batch_id'],
            "timestamp": time.strftime("%Y%m%d_%H%M%S"),
            "total_files": total_files,
            "processed_files": len(qa_results_no_content),
            "failed_files_count": len(failed_files),
            "total_qa_pairs": total_qa_pairs,
            "configuration": {
                "num_qa": params['num_qa'],
                "qa_level": params['qa_level'],
                "use_latex_ocr": params['use_latex_ocr'],
                "max_workers": params['max_workers']
            },
            "file_details": [],
            "failed_files": failed_files,
            "pdf_directory": batch_dir  # 添加PDF目录信息到统计
        }
        
        # 添加每个文件的详细信息
        for i, (qa_pairs, filename, _, _) in enumerate(qa_results_no_content):
            detailed_stats["file_details"].append({
                "filename": filename,
                "qa_count": len(qa_pairs),
                "pdf_path": os.path.join(batch_dir, filename)  # 添加PDF路径
            })
        
        # 保存统计信息到文件
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(detailed_stats, f, ensure_ascii=False, indent=2)
        
        # 不再删除批次目录，保留所有PDF文件
        # shutil.rmtree(batch_dir, ignore_errors=True)
        logger.info(f"批处理任务完成，保留PDF文件目录: {batch_dir}")
        save_tasks()  # 保存最终任务状态
        
    except Exception as e:
        logger.error(f"处理批量PDF任务时出错: {str(e)}", exc_info=True)
        tasks[task_id]["status"] = "completed"
        tasks[task_id]["progress"] = 100
        tasks[task_id]["message"] = f"处理出错: {str(e)}"
        tasks[task_id]["result"] = {
            "success": False,
            "error": str(e)
        }
        save_tasks()  # 保存错误状态
        
        # 失败时也不删除批次目录
        # try:
        #     if 'batch_dir' in params and os.path.exists(params['batch_dir']):
        #         shutil.rmtree(params['batch_dir'], ignore_errors=True)
        # except Exception:
        #     pass
        logger.error(f"批处理出错，但保留PDF文件目录: {params['batch_dir'] if 'batch_dir' in params else '未知'}")

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=8080) 