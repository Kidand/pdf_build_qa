/**
 * 增强型PDF问答生成器前端脚本
 * 处理用户交互、文件上传和任务状态监控
 */

$(document).ready(function() {
    console.log("Document ready, initializing app...");
    
    // 全局变量
    let uploadedFiles = []; // 修改为数组，存储多个文件
    let currentTask = null;
    let pollingInterval = null;
    let isProcessing = false; // 标记是否正在处理
    
    // DOM元素引用
    const dropZone = $('#dropZone');
    const fileInput = $('#fileInput');
    const selectedFilesList = $('#selectedFilesList');
    const fileList = $('#fileList');
    const fileCount = $('#fileCount');
    const clearFilesBtn = $('#clearFilesBtn');
    const startProcessingBtn = $('#startProcessingBtn');
    const processingCard = $('#processingCard');
    const progressBar = $('#progressBar');
    const processingMessage = $('#processingMessage');
    const resultCard = $('#resultCard');
    const resultSuccess = $('#resultSuccess');
    const resultError = $('#resultError');
    const errorMessage = $('#errorMessage');
    const newProcessingBtn = $('#newProcessingBtn');
    const downloadExcel = $('#downloadExcel');
    const downloadJson = $('#downloadJson');
    const downloadStats = $('#downloadStats');
    
    console.log("DOM elements initialized");
    
    // 检查DOM元素是否存在
    if (dropZone.length === 0) {
        console.error("Error: #dropZone element not found!");
    }
    if (fileInput.length === 0) {
        console.error("Error: #fileInput element not found!");
    }
    
    // 参数控件
    const numQASlider = $('#numQA');
    const numQAValue = $('#numQAValue');
    const qaLevelRadios = $('input[name="qaLevel"]');
    const useLatexOCRCheckbox = $('#useLatexOCR');
    const modelSelect = $('#model');
    const apiConfigSection = $('#apiConfigSection');
    const apiKeyInput = $('#apiKey');
    const apiUrlInput = $('#apiUrl');
    const maxWorkersInput = $('#maxWorkers');
    const apiRetriesInput = $('#apiRetries');
    const retryDelayInput = $('#retryDelay');
    
    // 显示数值的标签更新
    numQASlider.on('input', function() {
        numQAValue.text(this.value);
    });
    
    // 模型选择变更时，控制API配置显示
    modelSelect.on('change', function() {
        if (this.value === '') {
            // 默认模型，隐藏API配置
            apiConfigSection.addClass('d-none');
        } else {
            // 自定义模型，显示API配置
            apiConfigSection.removeClass('d-none');
        }
    });
    
    // 拖放区域事件处理
    console.log("Setting up drag & drop events");
    
    // 直接使用原生JavaScript绑定事件，以确保事件被正确捕获
    const dropZoneElement = document.getElementById('dropZone');
    const fileInputElement = document.getElementById('fileInput');
    
    if (dropZoneElement && fileInputElement) {
        // 拖拽相关事件
        dropZoneElement.addEventListener('dragover', function(e) {
            e.preventDefault();
            e.stopPropagation();
            this.classList.add('active');
            console.log("Drag over event triggered");
        });
        
        dropZoneElement.addEventListener('dragleave', function(e) {
            e.preventDefault();
            e.stopPropagation();
            this.classList.remove('active');
            console.log("Drag leave event triggered");
        });
        
        dropZoneElement.addEventListener('drop', function(e) {
            e.preventDefault();
            e.stopPropagation();
            this.classList.remove('active');
            console.log("Drop event triggered");
            
            if (e.dataTransfer.files.length) {
                handleFilesSelect(e.dataTransfer.files);
            }
        });
        
        // 点击上传事件
        dropZoneElement.addEventListener('click', function() {
            console.log("Drop zone clicked, triggering file input click");
            fileInputElement.click();
        });
        
        fileInputElement.addEventListener('change', function() {
            console.log("File input change event triggered");
            if (this.files.length) {
                handleFilesSelect(this.files);
            }
        });
        
        console.log("All drop zone events registered successfully");
    } else {
        console.error("Could not find drop zone or file input elements!");
        if (!dropZoneElement) {
            console.error("Drop zone element is missing");
        }
        if (!fileInputElement) {
            console.error("File input element is missing");
        }
    }
    
    // 保留jQuery事件绑定作为备份
    dropZone.on('dragover', function(e) {
        e.preventDefault();
        e.stopPropagation();
        $(this).addClass('active');
    });
    
    dropZone.on('dragleave', function(e) {
        e.preventDefault();
        e.stopPropagation();
        $(this).removeClass('active');
    });
    
    dropZone.on('drop', function(e) {
        e.preventDefault();
        e.stopPropagation();
        $(this).removeClass('active');
        
        if (e.originalEvent.dataTransfer.files.length) {
            handleFilesSelect(e.originalEvent.dataTransfer.files);
        }
    });
    
    dropZone.on('click', function() {
        console.log("Drop zone clicked (jQuery)");
        fileInput.click();
    });
    
    fileInput.on('change', function() {
        console.log("File input changed (jQuery)");
        if (this.files.length) {
            handleFilesSelect(this.files);
        }
    });
    
    // 多文件选择处理
    function handleFilesSelect(files) {
        if (!files || files.length === 0) return;
        
        console.log(`选择了 ${files.length} 个文件`);
        
        // 循环处理每个文件
        for (let i = 0; i < files.length; i++) {
            const file = files[i];
            
            // 验证文件类型
            if (file.type !== 'application/pdf' && !file.name.toLowerCase().endsWith('.pdf')) {
                showAlert(`错误：文件 "${file.name}" 不是PDF格式`);
                continue;
            }
            
            // 验证文件大小（最大50MB）
            if (file.size > 50 * 1024 * 1024) {
                showAlert(`错误：文件 "${file.name}" 大小超过50MB`);
                continue;
            }
            
            // 检查是否已存在同名文件
            const existingFileIndex = uploadedFiles.findIndex(f => f.name === file.name);
            if (existingFileIndex !== -1) {
                // 替换已存在的文件
                uploadedFiles[existingFileIndex] = file;
                // 更新UI中的文件项
                updateFileListItem(existingFileIndex, file);
            } else {
                // 添加新文件
                uploadedFiles.push(file);
                // 添加新的文件项到UI
                addFileListItem(uploadedFiles.length - 1, file);
            }
        }
        
        // 更新文件计数和控制按钮状态
        updateFileCount();
        
        // 清空文件输入，以便再次选择相同的文件
        fileInput.val('');
    }
    
    // 添加文件项到列表
    function addFileListItem(index, file) {
        const fileItem = $(`
            <li class="list-group-item file-list-item" data-index="${index}">
                <i class="bi bi-file-earmark-pdf file-icon"></i>
                <div class="file-details">
                    <div class="file-name">${file.name}</div>
                    <div class="file-size">${formatFileSize(file.size)}</div>
                </div>
                <button type="button" class="btn btn-sm btn-outline-danger file-remove">
                    <i class="bi bi-x"></i>
                </button>
            </li>
        `);
        
        // 绑定移除按钮事件
        fileItem.find('.file-remove').on('click', function() {
            removeFile(index);
        });
        
        fileList.append(fileItem);
    }
    
    // 更新现有文件项
    function updateFileListItem(index, file) {
        const fileItem = fileList.find(`li[data-index="${index}"]`);
        if (fileItem.length) {
            fileItem.find('.file-name').text(file.name);
            fileItem.find('.file-size').text(formatFileSize(file.size));
        }
    }
    
    // 移除单个文件
    function removeFile(index) {
        if (index < 0 || index >= uploadedFiles.length) return;
        
        // 从数组中移除
        uploadedFiles.splice(index, 1);
        
        // 重新渲染整个文件列表（避免index错位问题）
        renderFileList();
        
        // 更新文件计数和控制按钮状态
        updateFileCount();
    }
    
    // 渲染整个文件列表
    function renderFileList() {
        // 清空现有列表
        fileList.empty();
        
        // 重新添加所有文件
        uploadedFiles.forEach((file, index) => {
            addFileListItem(index, file);
        });
    }
    
    // 更新文件计数和按钮状态
    function updateFileCount() {
        const count = uploadedFiles.length;
        fileCount.text(count);
        
        if (count > 0) {
            selectedFilesList.removeClass('d-none');
            startProcessingBtn.prop('disabled', false);
        } else {
            selectedFilesList.addClass('d-none');
            startProcessingBtn.prop('disabled', true);
        }
    }
    
    // 清除所有文件按钮事件
    clearFilesBtn.on('click', function() {
        uploadedFiles = [];
        fileList.empty();
        updateFileCount();
    });
    
    // 开始处理按钮点击事件
    startProcessingBtn.on('click', function() {
        if (uploadedFiles.length === 0 || isProcessing) return;
        
        // 设置处理状态，禁用相关UI元素
        setProcessingState(true);
        
        // 显示处理进度UI
        processingCard.removeClass('d-none');
        resultCard.addClass('d-none');
        
        // 重置进度条
        updateProgress(0, '正在上传文件...');
        
        // 首先批量上传文件
        uploadFiles(uploadedFiles);
    });
    
    // 设置处理状态
    function setProcessingState(processing) {
        isProcessing = processing;
        
        // 处理中时禁用上传区域和开始按钮
        if (processing) {
            dropZone.addClass('processing-disabled');
            selectedFilesList.addClass('processing-disabled');
            startProcessingBtn.prop('disabled', true);
            
            // 禁用选项卡切换
            $('.sidebar-nav .nav-link').addClass('disabled');
        } else {
            dropZone.removeClass('processing-disabled');
            selectedFilesList.removeClass('processing-disabled');
            startProcessingBtn.prop('disabled', uploadedFiles.length === 0);
            
            // 启用选项卡切换
            $('.sidebar-nav .nav-link').removeClass('disabled');
        }
    }
    
    // 重新开始按钮点击事件
    newProcessingBtn.on('click', function() {
        resetProcessing();
        // 保留已上传的文件，只重置处理状态
        setProcessingState(false);
        
        // 切换回首页选项卡
        $('a[href="#home"]').tab('show');
    });
    
    // 批量上传文件到服务器
    function uploadFiles(files) {
        console.log(`开始上传 ${files.length} 个文件`);
        
        const formData = new FormData();
        
        // 添加所有文件到表单
        files.forEach((file, index) => {
            formData.append('files', file);
        });
        
        $.ajax({
            url: '/upload_batch',
            type: 'POST',
            data: formData,
            processData: false,
            contentType: false,
            success: function(response) {
                console.log("Batch upload response:", response);
                if (response.status === 'success') {
                    updateProgress(20, '文件上传成功，准备处理...');
                    startProcessing(response.batch_id);
                } else {
                    handleError('文件上传失败: ' + response.message);
                    setProcessingState(false);
                }
            },
            error: function(xhr, status, error) {
                console.error("Upload error:", error);
                let errorMsg = '文件上传失败';
                try {
                    const resp = JSON.parse(xhr.responseText);
                    errorMsg = resp.message || errorMsg;
                } catch (e) {}
                handleError(errorMsg);
                setProcessingState(false);
            }
        });
    }
    
    // 开始处理任务
    function startProcessing(batchId) {
        // 获取所有参数
        const params = {
            batch_id: batchId,
            num_qa: parseInt(numQASlider.val()),
            qa_level: $('input[name="qaLevel"]:checked').val(),
            use_latex_ocr: useLatexOCRCheckbox.is(':checked'),
            max_workers: parseInt(maxWorkersInput.val()),
            api_retries: parseInt(apiRetriesInput.val()),
            retry_delay: parseInt(retryDelayInput.val()),
            model: modelSelect.val()
        };
        
        // 如果选择了自定义模型，添加API配置
        if (modelSelect.val() !== '') {
            params.api_key = apiKeyInput.val();
            params.api_url = apiUrlInput.val();
        }
        
        $.ajax({
            url: '/process_batch',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(params),
            success: function(response) {
                if (response.status === 'success') {
                    currentTask = response.task_id;
                    updateProgress(30, '开始处理PDF文件...');
                    
                    // 开始轮询任务状态
                    startPolling(currentTask);
                } else {
                    handleError('处理请求失败: ' + response.message);
                    setProcessingState(false);
                }
            },
            error: function(xhr) {
                let errorMsg = '处理请求失败';
                try {
                    const resp = JSON.parse(xhr.responseText);
                    errorMsg = resp.message || errorMsg;
                } catch (e) {}
                handleError(errorMsg);
                setProcessingState(false);
            }
        });
    }
    
    // 开始轮询任务状态
    function startPolling(taskId) {
        // 清除可能存在的旧轮询
        if (pollingInterval) {
            clearInterval(pollingInterval);
        }
        
        // 设置轮询间隔（每秒）
        pollingInterval = setInterval(function() {
            checkTaskStatus(taskId);
        }, 1000);
    }
    
    // 检查任务状态
    function checkTaskStatus(taskId) {
        $.ajax({
            url: '/task/' + taskId,
            type: 'GET',
            success: function(response) {
                // 更新进度条和消息
                updateProgress(response.progress, response.message);
                
                // 如果任务完成，停止轮询
                if (response.status === 'completed') {
                    clearInterval(pollingInterval);
                    handleTaskCompletion(response);
                }
            },
            error: function() {
                clearInterval(pollingInterval);
                handleError('检查任务状态失败');
                setProcessingState(false);
            }
        });
    }
    
    // 处理任务完成
    function handleTaskCompletion(response) {
        const result = response.result;
        
        // 显示结果卡片
        resultCard.removeClass('d-none');
        
        if (result && result.success) {
            // 成功完成
            resultSuccess.removeClass('d-none');
            resultError.addClass('d-none');
            
            // 更新统计数据
            $('#processedFiles').text(result.stats.processed_files);
            $('#generatedQAPairs').text(result.stats.total_qa_pairs);
            $('#failedFiles').text(result.stats.failed_files_count);
            
            // 设置下载链接
            downloadExcel.attr('href', '/download/' + result.excel_file);
            downloadJson.attr('href', '/download/' + result.json_file);
            downloadStats.attr('href', '/download/' + result.stats_file);
        } else {
            // 处理失败
            resultSuccess.addClass('d-none');
            resultError.removeClass('d-none');
            
            if (result && result.error) {
                errorMessage.text(result.error);
            } else {
                errorMessage.text('处理过程中出现未知错误');
            }
        }
        
        // 恢复UI状态
        setProcessingState(false);
    }
    
    // 更新进度条和进度消息
    function updateProgress(percent, message) {
        progressBar.css('width', percent + '%');
        progressBar.attr('aria-valuenow', percent);
        processingMessage.text(message);
        
        // 如果进度为100%，修改进度条样式
        if (percent >= 100) {
            progressBar.removeClass('progress-bar-animated').removeClass('progress-bar-striped');
        } else {
            progressBar.addClass('progress-bar-animated').addClass('progress-bar-striped');
        }
    }
    
    // 处理错误
    function handleError(errorMsg) {
        console.error("Error:", errorMsg);
        // 停止所有轮询
        if (pollingInterval) {
            clearInterval(pollingInterval);
        }
        
        // 显示错误信息
        resultCard.removeClass('d-none');
        resultSuccess.addClass('d-none');
        resultError.removeClass('d-none');
        errorMessage.text(errorMsg);
        
        // 更新进度条为错误状态
        progressBar.css('width', '100%');
        progressBar.removeClass('progress-bar-animated').removeClass('progress-bar-striped');
        progressBar.addClass('bg-danger');
        processingMessage.text('处理出错');
    }
    
    // 显示警告提示
    function showAlert(message) {
        console.log("Showing alert:", message);
        // 检查是否已有警告框
        let alertBox = $('.alert-warning');
        if (alertBox.length === 0) {
            alertBox = $('<div class="alert alert-warning alert-dismissible fade show" role="alert">' +
                '<i class="bi bi-exclamation-triangle-fill me-2"></i>' +
                '<span class="alert-message"></span>' +
                '<button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>' +
                '</div>');
            $('.upload-section').prepend(alertBox);
        }
        
        // 设置消息并显示
        alertBox.find('.alert-message').text(message);
    }
    
    // 重置处理状态
    function resetProcessing() {
        // 停止轮询
        if (pollingInterval) {
            clearInterval(pollingInterval);
        }
        
        // 隐藏处理和结果UI
        processingCard.addClass('d-none');
        resultCard.addClass('d-none');
        
        // 重置进度条
        progressBar.css('width', '0%');
        progressBar.attr('aria-valuenow', 0);
        progressBar.removeClass('bg-danger');
        progressBar.addClass('progress-bar-animated').addClass('progress-bar-striped');
        processingMessage.text('正在处理PDF文件...');
        
        // 清除任务ID
        currentTask = null;
        
        // 恢复UI状态
        setProcessingState(false);
    }
    
    // 格式化文件大小显示
    function formatFileSize(bytes) {
        if (bytes < 1024) {
            return bytes + ' B';
        } else if (bytes < 1048576) {
            return (bytes / 1024).toFixed(2) + ' KB';
        } else {
            return (bytes / 1048576).toFixed(2) + ' MB';
        }
    }
    
    console.log("App initialization completed");
}); 