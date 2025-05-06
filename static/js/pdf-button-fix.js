// 独立的PDF按钮修复脚本
document.addEventListener('DOMContentLoaded', function() {
    console.log("PDF按钮修复脚本已加载");
    
    // 初始检查PDF按钮
    var checkPdfButton = function() {
        var pdfButton = document.getElementById('generate-pdf-report-btn');
        console.log("初始检查PDF按钮:", pdfButton ? "找到按钮" : "未找到按钮");
        
        if (pdfButton) {
            // 已找到按钮，立即绑定事件
            bindPdfButtonEvent(pdfButton);
        } else {
            // 未找到按钮，可能是结果区域尚未显示
            console.log("PDF按钮未找到，将设置定期检查");
            // 设置一个周期性检查，每500ms检查一次按钮是否出现
            setInterval(function() {
                var pdfBtn = document.getElementById('generate-pdf-report-btn');
                if (pdfBtn && !pdfBtn.hasAttribute('data-event-bound')) {
                    console.log("定期检查找到了PDF按钮");
                    bindPdfButtonEvent(pdfBtn);
                }
            }, 500);
        }
    };
    
    // 绑定PDF按钮事件
    var bindPdfButtonEvent = function(button) {
        if (button.hasAttribute('data-event-bound')) {
            console.log("按钮已经绑定过事件，跳过");
            return;
        }
        
        console.log("正在绑定PDF按钮事件");
        button.setAttribute('data-event-bound', 'true');
        
        button.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            console.log("PDF按钮被点击了！");
            
            // 尝试获取计算结果数据
            var calculationResultData = window.calculationResultData;
            console.log("计算结果数据状态:", calculationResultData ? "有效" : "无效");
            
            if (!calculationResultData) {
                alert("请先计算挖矿收益再导出PDF报告。");
                return false;
            }
            
            // 如果window.generatePdfReport函数可用，则调用它
            if (typeof window.generatePdfReport === 'function') {
                console.log("调用generatePdfReport函数");
                window.generatePdfReport(calculationResultData);
            } else {
                // 否则，直接调用API
                console.log("generatePdfReport函数不可用，直接调用API");
                directGeneratePdf(calculationResultData);
            }
            
            return false;
        });
        
        // 为确保可见性，添加边框并改变颜色
        button.style.border = "2px solid red";
        
        console.log("PDF按钮事件绑定完成");
    };
    
    // 直接生成PDF的备用函数
    var directGeneratePdf = function(data) {
        console.log("直接调用PDF生成API");
        
        // 显示加载提示
        var loadingMsg = document.createElement('div');
        loadingMsg.className = 'alert alert-info position-fixed top-0 start-50 translate-middle-x mt-3';
        loadingMsg.style.zIndex = '9999';
        loadingMsg.innerHTML = '<i class="bi bi-cloud-download me-2"></i>正在生成PDF报告...';
        document.body.appendChild(loadingMsg);
        
        // 发送请求
        fetch('/generate_pdf_report', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        })
        .then(response => {
            // 移除加载提示
            document.body.removeChild(loadingMsg);
            
            if (!response.ok) {
                throw new Error('HTTP error ' + response.status);
            }
            
            // 获取文件名
            var filename = 'BTC_Mining_Report.pdf';
            var disposition = response.headers.get('Content-Disposition');
            if (disposition && disposition.indexOf('attachment') !== -1) {
                var filenameRegex = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/;
                var matches = filenameRegex.exec(disposition);
                if (matches != null && matches[1]) { 
                    filename = matches[1].replace(/['"]/g, '');
                }
            }
            
            // 处理响应
            return response.blob().then(blob => {
                return {
                    blob: blob,
                    filename: filename
                };
            });
        })
        .then(data => {
            // 创建下载链接
            var downloadUrl = window.URL.createObjectURL(data.blob);
            var a = document.createElement('a');
            a.style.display = 'none';
            a.href = downloadUrl;
            a.download = data.filename;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(downloadUrl);
            document.body.removeChild(a);
            
            // 显示成功消息
            var successMsg = document.createElement('div');
            successMsg.className = 'alert alert-success position-fixed top-0 start-50 translate-middle-x mt-3';
            successMsg.style.zIndex = '9999';
            successMsg.innerHTML = '<i class="bi bi-check-circle me-2"></i>PDF报告已成功下载！';
            document.body.appendChild(successMsg);
            
            // 3秒后自动关闭成功消息
            setTimeout(function() {
                document.body.removeChild(successMsg);
            }, 3000);
        })
        .catch(error => {
            console.error('PDF生成错误:', error);
            
            // 显示错误消息
            var errorMsg = document.createElement('div');
            errorMsg.className = 'alert alert-danger position-fixed top-0 start-50 translate-middle-x mt-3';
            errorMsg.style.zIndex = '9999';
            errorMsg.innerHTML = '<i class="bi bi-exclamation-triangle me-2"></i>PDF报告生成错误，请重试。';
            document.body.appendChild(errorMsg);
            
            // 3秒后自动关闭错误消息
            setTimeout(function() {
                document.body.removeChild(errorMsg);
            }, 3000);
        });
    };
    
    // 开始检查
    checkPdfButton();
    
    // 确保全局可访问性
    window.checkPdfButton = checkPdfButton;
    window.bindPdfButtonEvent = bindPdfButtonEvent;
    window.directGeneratePdf = directGeneratePdf;
});