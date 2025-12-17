/**
 * HashInsight Enterprise - Batch Import JavaScript
 * 批量导入前端交互
 */

// 上传区域元素
const uploadZone = document.getElementById('uploadZone');
const fileInput = document.getElementById('fileInput');

// 进度元素
const progressSection = document.getElementById('progressSection');
const progressBar = document.getElementById('progressBar');
const progressMessage = document.getElementById('progressMessage');
const progressDetails = document.getElementById('progressDetails');

// 结果元素
const resultSection = document.getElementById('resultSection');
const successCount = document.getElementById('successCount');
const errorCount = document.getElementById('errorCount');
const totalRows = document.getElementById('totalRows');
const elapsedTime = document.getElementById('elapsedTime');

// 错误列表
const errorSection = document.getElementById('errorSection');
const errorList = document.getElementById('errorList');

// 拖拽事件
uploadZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadZone.classList.add('drag-over');
});

uploadZone.addEventListener('dragleave', () => {
    uploadZone.classList.remove('drag-over');
});

uploadZone.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadZone.classList.remove('drag-over');
    
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        handleFile(files[0]);
    }
});

// 点击上传区域
uploadZone.addEventListener('click', () => {
    fileInput.click();
});

// 文件选择
fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
        handleFile(e.target.files[0]);
    }
});

/**
 * 处理文件上传
 */
function handleFile(file) {
    // 验证文件类型
    if (!file.name.endsWith('.csv')) {
        alert('Please upload a CSV file');
        return;
    }
    
    // 显示进度区
    progressSection.style.display = 'block';
    resultSection.style.display = 'none';
    errorSection.style.display = 'none';
    
    // 重置进度
    updateProgress(0, 'Uploading file...');
    
    // 创建FormData
    const formData = new FormData();
    formData.append('file', file);
    
    // 上传文件
    fetch('/batch/api/upload', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            handleSuccess(data);
        } else {
            handleError(data.error);
        }
    })
    .catch(error => {
        handleError(error.message);
    });
}

/**
 * 更新进度条
 */
function updateProgress(percent, message, details = '') {
    progressBar.style.width = percent + '%';
    progressBar.textContent = Math.round(percent) + '%';
    progressMessage.textContent = message;
    progressDetails.textContent = details;
}

/**
 * 处理成功响应
 */
function handleSuccess(data) {
    // 更新进度到100%
    updateProgress(100, 'Import completed!');
    
    // 显示结果
    setTimeout(() => {
        progressSection.style.display = 'none';
        resultSection.style.display = 'block';
        
        successCount.textContent = data.success_count || 0;
        errorCount.textContent = data.error_count || 0;
        totalRows.textContent = data.total_rows || 0;
        elapsedTime.textContent = (data.elapsed_time || 0) + 's';
        
        // 显示错误列表（如果有）
        if (data.errors && data.errors.length > 0) {
            displayErrors(data.errors);
        }
    }, 500);
}

/**
 * 显示错误列表
 */
function displayErrors(errors) {
    errorSection.style.display = 'block';
    errorList.innerHTML = '';
    
    errors.forEach(error => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${error.row}</td>
            <td><span class="badge bg-danger">${error.error_type}</span></td>
            <td>${error.error}</td>
            <td class="text-muted">${error.suggestion || 'N/A'}</td>
        `;
        errorList.appendChild(row);
    });
}

/**
 * 处理错误
 */
function handleError(message) {
    progressSection.style.display = 'none';
    alert('Import failed: ' + message);
}

/**
 * 下载模板
 */
function downloadTemplate(lang) {
    window.location.href = `/batch/api/template/download?lang=${lang}&examples=true`;
}

/**
 * 下载大批量测试模板
 */
function downloadBulkTemplate() {
    const count = prompt('Enter number of rows (max 10000):', '5000');
    if (count && !isNaN(count)) {
        window.location.href = `/batch/api/template/bulk?count=${count}&lang=en`;
    }
}
