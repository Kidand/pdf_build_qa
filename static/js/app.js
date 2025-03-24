/**
 * 增强型PDF问答生成器前端脚本
 * 处理用户交互、文件上传和任务状态监控
 */

$(document).ready(function() {
    console.log("Document ready, initializing app...");
    
    // 全局变量
    let uploadedFile = null;
    let currentTask = null;
    let pollingInterval = null;
    
    // DOM元素引用
    const dropZone = $('#dropZone');
    const fileInput = $('#fileInput');
    const selectedFileInfo = $('#selectedFileInfo');
    const selectedFileName = $('#selectedFileName');
    const selectedFileSize = $('#selectedFileSize');
    const removeFileBtn = $('#removeFileBtn');
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
                handleFileSelect(e.dataTransfer.files[0]);
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
                handleFileSelect(this.files[0]);
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
            handleFileSelect(e.originalEvent.dataTransfer.files[0]);
        }
    });
    
    dropZone.on('click', function() {
        console.log("Drop zone clicked (jQuery)");
        fileInput.click();
    });
    
    fileInput.on('change', function() {
        console.log("File input changed (jQuery)");
        if (this.files.length) {
            handleFileSelect(this.files[0]);
        }
    });
    
    // 文件选择处理
    function handleFileSelect(file) {
        console.log("File selected:", file.name);
        if (!file) return;
        
        // 验证文件类型
        if (file.type !== 'application/pdf' && !file.name.toLowerCase().endsWith('.pdf')) {
            showAlert('错误：请选择PDF文件');
            return;
        }
        
        // 验证文件大小（最大50MB）
        if (file.size > 50 * 1024 * 1024) {
            showAlert('错误：文件大小不能超过50MB');
            return;
        }
        
        uploadedFile = file;
        
        // 更新UI显示选中的文件
        selectedFileName.text(file.name);
        selectedFileSize.text('文件大小: ' + formatFileSize(file.size));
        selectedFileInfo.removeClass('d-none');
        startProcessingBtn.prop('disabled', false);
        
        // 自动切换到参数设置选项卡
        $('a[href="#settings"]').tab('show');
    }
    
    // 移除文件按钮点击事件
    removeFileBtn.on('click', function() {
        resetFileSelection();
    });
    
    // 开始处理按钮点击事件
    startProcessingBtn.on('click', function() {
        if (!uploadedFile) return;
        
        // 显示处理进度UI
        processingCard.removeClass('d-none');
        resultCard.addClass('d-none');
        
        // 重置进度条
        updateProgress(0, '正在上传文件...');
        
        // 首先上传文件
        uploadFile(uploadedFile);
    });
    
    // 重新开始按钮点击事件
    newProcessingBtn.on('click', function() {
        resetProcessing();
        resetFileSelection();
        
        // 切换回首页选项卡
        $('a[href="#home"]').tab('show');
    });
    
    // 上传文件到服务器
    function uploadFile(file) {
        console.log("Uploading file:", file.name);
        const formData = new FormData();
        formData.append('file', file);
        
        $.ajax({
            url: '/upload',
            type: 'POST',
            data: formData,
            processData: false,
            contentType: false,
            success: function(response) {
                console.log("Upload response:", response);
                if (response.status === 'success') {
                    updateProgress(20, '文件上传成功，准备处理...');
                    startProcessing(response.filename);
                } else {
                    handleError('文件上传失败: ' + response.message);
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
            }
        });
    }
    
    // 开始处理任务
    function startProcessing(filename) {
        // 获取所有参数
        const params = {
            filename: filename,
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
            url: '/process',
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
                }
            },
            error: function(xhr) {
                let errorMsg = '处理请求失败';
                try {
                    const resp = JSON.parse(xhr.responseText);
                    errorMsg = resp.message || errorMsg;
                } catch (e) {}
                handleError(errorMsg);
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
    
    // 重置文件选择状态
    function resetFileSelection() {
        uploadedFile = null;
        fileInput.val('');
        selectedFileInfo.addClass('d-none');
        startProcessingBtn.prop('disabled', true);
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