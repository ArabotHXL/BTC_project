// PDF 导出按钮修复脚本
console.log("PDF按钮修复脚本已加载");

// 在页面加载时添加事件监听器
document.addEventListener('DOMContentLoaded', function() {
    // 初始绑定PDF按钮
    addPdfExportButtonListener();
    
    // 每隔1秒检查一次结果卡片，如果显示了，确保PDF按钮仍然有监听器
    setInterval(checkAndAddPdfListener, 1000);
});

// 添加PDF导出按钮的事件监听器
function addPdfExportButtonListener() {
    // 查找PDF导出按钮
    var pdfButton = document.getElementById('export-pdf-btn');
    console.log("初始检查PDF按钮:", pdfButton ? "找到按钮" : "按钮不存在");
    
    if (pdfButton) {
        // 添加鲜明的边框以突出显示
        pdfButton.style.border = "2px solid red";
        
        // 清除现有的事件监听器，防止重复添加
        pdfButton.replaceWith(pdfButton.cloneNode(true));
        pdfButton = document.getElementById('export-pdf-btn');
        
        console.log("正在绑定PDF按钮事件");
        // 添加新的事件监听器
        pdfButton.addEventListener('click', handlePdfExport);
        console.log("PDF按钮事件绑定完成");
    }
}

// 检查结果卡片是否显示，如果显示了，确保PDF按钮有监听器
function checkAndAddPdfListener() {
    var resultsCard = document.getElementById('results-card');
    if (resultsCard && resultsCard.style.display !== 'none') {
        addPdfExportButtonListener();
    }
}

// 处理PDF导出按钮点击
function handlePdfExport(event) {
    event.preventDefault();
    console.log("PDF按钮被点击了！");
    
    // 检查是否有可用的计算结果数据
    if (!window.calculationResultData) {
        console.log("计算结果数据状态:", "不可用");
        alert("请先进行计算，然后再导出PDF报告。\nPlease calculate first before exporting the PDF report.");
        return;
    }
    
    console.log("计算结果数据状态:", "有效");
    
    // 尝试使用主脚本中的方法（如果可用）
    if (typeof generatePdfReport === 'function') {
        generatePdfReport(window.calculationResultData);
    } else {
        console.log("generatePdfReport函数不可用，直接调用API");
        // 直接调用后端API
        directPdfExport();
    }
}

// 直接调用PDF导出API
function directPdfExport() {
    console.log("直接调用PDF生成API");
    
    try {
        // 创建表单数据
        var formData = new FormData();
        formData.append('data', JSON.stringify(window.calculationResultData));
        
        // 发送请求
        var xhr = new XMLHttpRequest();
        xhr.open('POST', '/generate_pdf', true);
        xhr.responseType = 'blob'; // 设置响应类型为blob
        
        xhr.onload = function() {
            if (xhr.status === 200) {
                // 创建一个Blob对象并生成下载链接
                var blob = new Blob([xhr.response], { type: 'application/pdf' });
                var url = window.URL.createObjectURL(blob);
                
                // 创建临时下载链接并点击
                var a = document.createElement('a');
                a.href = url;
                a.download = 'mining_report_' + new Date().toISOString().slice(0, 10) + '.pdf';
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);
            } else {
                console.error("PDF生成请求失败", xhr.status);
                alert("PDF报告生成失败，请重试。\nFailed to generate PDF report, please try again.");
            }
        };
        
        xhr.onerror = function(error) {
            console.error("PDF生成错误:", error);
            alert("PDF报告生成失败，请重试。\nFailed to generate PDF report, please try again.");
        };
        
        xhr.send(formData);
        
    } catch (error) {
        console.error("PDF生成错误:", error);
        alert("PDF报告生成失败，请重试。\nFailed to generate PDF report, please try again.");
    }
}