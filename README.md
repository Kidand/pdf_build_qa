# 增强型PDF问答生成器

这是一个增强型PDF文档问答对生成工具，可以从学术PDF文件中提取文本和公式，生成多层次的中文问答对，适用于构建特定领域的问答数据集。

## 主要功能

- **增强型PDF解析**：结合PyPDF2、pdfplumber和PyMuPDF，实现更准确的文本提取
- **LaTeX公式识别**：使用LatexOCR自动识别PDF中的数学公式，并将其转换为LaTeX格式
- **多层次问答生成**：支持生成基础(basic)、中级(intermediate)和高级(advanced)三种难度级别的问答对
- **模拟"学生-教授"对话**：针对不同级别使用不同提示词模板，模拟不同学习阶段的对话风格
- **多种格式导出**：将结果保存为Excel（多个工作表）和JSON格式，便于后续使用和分析
- **API调用重试机制**：实现智能重试，确保稳定性
- **详细统计报告**：自动生成数据集统计信息
- **处理失败文件记录**：详细记录处理失败的文件

## 如何使用

### 1. 环境配置

1. 克隆仓库并进入目录：

```bash
git clone https://github.com/yourusername/pdf-qa-generator.git
cd pdf-qa-generator
```

2. 安装依赖项：

```bash
pip install -r requirements.txt
```

3. 设置环境变量：

复制`.env.example`为`.env`，并填入您的API密钥：

```bash
cp .env.example .env
```

编辑`.env`文件，设置您的DeepSeek API密钥：

```
DEEPSEEK_API_KEY=your_api_key_here
DEEPSEEK_API_URL=https://api.deepseek.com/v1
MODEL_NAME=deepseek-chat
```

### 2. 准备PDF文件

将您的PDF文件放在`pdf_files`目录中（或您指定的其他目录）。

### 3. 运行程序

基本用法：

```bash
python main.py
```

这将使用默认参数处理`pdf_files`目录中的所有PDF文件，并将结果保存到`output`目录。

### 4. 命令行参数

您可以通过命令行参数自定义程序行为：

```bash
python main.py --pdf_dir=your_pdf_dir --num_qa=30 --qa_level=advanced
```

可用参数：

- `--pdf_dir`: PDF文件所在目录 (默认: pdf_files)
- `--output_dir`: 输出目录 (默认: output)
- `--num_qa`: 每个PDF生成的问答对数量 (默认: 10)
- `--max_workers`: 最大并行处理的文件数 (默认: 3)
- `--api_retries`: API调用失败时的最大重试次数 (默认: 3)
- `--retry_delay`: API重试间隔时间(秒) (默认: 2)
- `--qa_level`: 问答对级别 (可选: basic/intermediate/advanced/all，默认: all)
- `--use_latex_ocr`: 启用LaTeX公式OCR识别 (默认: 不启用)
- `--model`: 指定DeepSeek模型 (默认: 使用.env中的MODEL_NAME或deepseek-chat)

## 输出文件

程序会在输出目录生成以下文件：

1. `qa_pairs_[timestamp].xlsx`: 包含所有问答对的Excel文件，按难度级别和来源文件分不同工作表
2. `qa_pairs_[timestamp].json`: 包含所有问答对和元数据的JSON文件
3. `qa_stats_[timestamp].json`: 统计信息JSON文件
4. `failed_files.txt`: 处理失败的文件列表（如果有）

## 问答级别说明

系统支持生成三种不同难度级别的问答对：

1. **基础 (basic)**：
   - 关注基础概念、定义和简单原理
   - 适合初学者理解
   - 使用通俗易懂的语言，避免过多专业术语

2. **中级 (intermediate)**：
   - 关注概念间的联系、原理应用和中等复杂度的分析
   - 适合有一定基础的学习者
   - 包含一些专业术语和理论框架的讨论

3. **高级 (advanced)**：
   - 关注批判性分析、方法论和前沿问题
   - 适合研究人员和高级学者
   - 包含深入的专业讨论、方法论分析和研究局限性

## 依赖库

主要依赖库：

- openai: DeepSeek API调用
- PyPDF2: 基本PDF解析
- pdfplumber: 增强文本提取
- pymupdf: 结构化PDF解析
- pix2tex: LaTeX公式OCR识别
- pandas: 数据处理和Excel生成
- torch & transformers: 支持LatexOCR模型运行

## 注意事项

1. LatexOCR功能需要较大的系统资源，特别是GPU内存。如果您的系统资源有限，可以不启用此功能。
2. 首次运行时会下载LatexOCR模型，可能需要一些时间。
3. 如果处理大型PDF文件，建议增加API的max_tokens参数。
4. 该项目适合构建特定领域的问答数据集，生成的问答对可用于微调大型语言模型。

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