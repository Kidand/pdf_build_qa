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

## 详细使用步骤

### 1. 克隆仓库

首先将仓库克隆到本地:

```bash
git clone https://github.com/Kidand/pdf_build_qa.git
cd pdf_build_qa
```

### 2. 安装依赖

安装所需的Python依赖库:

```bash
pip install -r requirements.txt
```

### 3. 配置环境

复制示例环境配置文件并进行编辑:

```bash
cp .env.example .env
```

然后编辑`.env`文件，填入您的DeepSeek API密钥:

```
DEEPSEEK_API_KEY=your_api_key_here
DEEPSEEK_API_URL=https://api.deepseek.com/v1
MODEL_NAME=deepseek-chat
```

### 4. 准备PDF文件

将需要处理的PDF文件放入`pdf_files`目录中。如果该目录不存在，请创建它:

```bash
mkdir -p pdf_files
```

### 5. 运行程序

基本用法:

```bash
python main.py
```

高级用法 - 自定义参数:

```bash
python main.py --pdf_dir my_pdfs --output_dir results --num_qa 30 --max_workers 5
```

参数说明:

| 参数 | 说明 | 默认值 |
| ---- | ---- | ------ |
| --pdf_dir | PDF文件所在目录 | pdf_files |
| --output_dir | 输出目录 | output |
| --num_qa | 每个PDF生成的问答对数量 | 10 |
| --max_workers | 最大并行处理的文件数 | 3 |
| --api_retries | api尝试次数 | 3 |

### 6. 查看结果

程序处理完成后，结果会保存在`output`目录下的Excel文件中，文件名格式为`qa_pairs_YYYYMMDD_HHMMSS.xlsx`。

## 输出

程序生成的Excel文件包含以下列：
- question: 问题
- answer: 答案
- source: 来源PDF文件名

## 日志

程序运行日志会保存在`pdf_qa_generator.log`文件中，可用于排查问题。

## 项目结构

```
.
├── .env                  # 环境变量
├── .env.example          # 环境变量示例
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

## 故障排除

1. 如果遇到API密钥相关错误，请确保`.env`文件中的`DEEPSEEK_API_KEY`已正确设置。

2. 如果程序无法识别PDF文件，请确保文件扩展名为`.pdf`并且文件格式正确。

3. 如果生成的问答对较少，可以尝试增大`--num_qa`参数值。

4. 如果处理速度较慢，可以适当增加`--max_workers`参数值，但要注意不要超过CPU核心数太多。