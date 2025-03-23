# 增强型PDF问答生成器 - Web界面

这是增强型PDF问答生成器的Web界面版本，提供了直观的用户交互方式，让您更方便地从PDF文件中生成问答对。

## 功能特点

- **美观直观的界面**：提供现代化的Web界面，支持拖拽上传PDF文件
- **实时进度显示**：处理过程中实时显示进度和状态
- **参数可视化配置**：通过图形界面轻松设置所有参数
- **结果统计展示**：直观展示处理结果和统计数据
- **一键下载结果**：方便地下载生成的Excel、JSON和统计文件

## 如何使用

### 1. 安装

1. 克隆仓库并进入目录：

```bash
git clone https://github.com/Kidand/pdf_build_qa.git
cd pdf_build_qa
```

2. 创建conda环境并安装依赖项：

```bash
conda create -n pdf_qa_env python=3.10
conda activate pdf_qa_env
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

### 2. 运行Web应用

启动Web服务器：

```bash
python app.py
```

然后在浏览器中访问：http://localhost:5000

### 3. 使用界面

1. **上传PDF文件**：
   - 在首页拖放PDF文件到上传区域，或点击上传区域选择文件
   - 文件大小限制为50MB
   - 只支持PDF格式

2. **配置参数**：
   - 问答对数量：使用滑块设置生成的问答对数量（5-30）
   - 问答对级别：选择基础、中级、高级或全部
   - LaTeX公式OCR：是否启用LaTeX公式识别（需要更多计算资源）
   - 使用模型：选择使用的DeepSeek模型
   - 高级设置：可设置并行处理数、API重试次数和重试间隔

3. **处理文件**：
   - 点击"开始处理"按钮
   - 在进度页面查看实时处理状态

4. **查看结果**：
   - 处理完成后查看统计数据
   - 下载Excel、JSON和统计文件
   - 如有错误，可查看错误信息

5. **重新开始**：
   - 点击"开始新的处理"按钮重新上传文件

## 常见问题

1. **为什么文件上传失败？**
   - 确保文件格式为PDF
   - 确保文件大小不超过50MB
   - 检查服务器日志获取详细错误信息

2. **为什么处理过程很慢？**
   - 启用LaTeX OCR会显著增加处理时间
   - 大型PDF文件处理需要更多时间
   - API调用可能受限于网络状况

3. **如何处理更多文件？**
   - 目前界面版本一次只支持处理一个文件
   - 如需批处理多个文件，请使用命令行版本

## 系统要求

- 支持现代Web浏览器（Chrome、Firefox、Edge等）
- 至少4GB内存（使用LaTeX OCR时建议8GB以上）
- 使用LaTeX OCR时建议有GPU支持

## 注意事项

- 本应用在本地运行，所有文件都保存在本地
- 确保API密钥安全性，不要泄露给他人
- 定期清理临时文件目录，避免占用过多磁盘空间 