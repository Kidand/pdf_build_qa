# PDF问答生成器

这个项目可以从PDF文件中提取内容，使用DeepSeek API生成问答对，并将结果保存到Excel文件中。

## 功能特点

- 遍历指定目录下的所有PDF文件
- 从PDF中提取文本内容
- 使用DeepSeek API为每个文档生成多个问答对
- 将生成的问答对保存到Excel文件，包含问题、答案和来源信息
- 支持多线程并行处理多个PDF文件

## 环境要求

- Python 3.10 +
- 依赖库：见requirements.txt

## 安装

1. 安装依赖：

```bash
pip install -r requirements.txt
```

2. 配置环境变量：

在`.env`中添加DeepSeek API密钥：

```
DEEPSEEK_API_KEY=your_api_key_here
DEEPSEEK_API_URL=https://api.deepseek.com/v1/chat/completions
```

## 使用方法

1. 将PDF文件放入`pdf_files`目录

2. 运行程序：

```bash
python main.py
```

3. 可选参数：

```
--pdf_dir     PDF文件所在目录 (默认: pdf_files)
--output_dir  输出目录 (默认: output)
--num_qa      每个PDF生成的问答对数量 (默认: 20)
--max_workers 最大并行处理的文件数 (默认: 3)
```

例如：

```bash
python main.py --pdf_dir my_pdfs --output_dir results --num_qa 30 --max_workers 5
```

## 输出

程序会在output目录下生成一个Excel文件，包含以下列：
- question: 问题
- answer: 答案
- source: 来源PDF文件名

## 日志

程序运行日志会保存在`pdf_qa_generator.log`文件中。

## 项目结构

```
.
├── .env                  # 环境变量
├── README.md             # 项目说明文档
├── main.py               # 主程序入口
├── requirements.txt      # 依赖库列表
├── pdf_files/            # PDF文件目录
├── output/               # 输出目录
└── src/                  # 源代码目录
    ├── __init__.py
    ├── pdf_processor.py  # PDF处理模块
    ├── deepseek_client.py # DeepSeek API客户端
    ├── qa_generator.py   # 问答生成模块
    └── excel_writer.py   # Excel写入模块
```