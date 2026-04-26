let statusInterval = null;

// إضافة سجل
function addLog(message, type = 'info') {
    const logsContainer = document.getElementById('logsContainer');
    const logEntry = document.createElement('div');
    logEntry.className = `log-entry ${type}`;
    const time = new Date().toLocaleTimeString('ar-EG');
    logEntry.innerHTML = `[${time}] ${message}`;
    logsContainer.appendChild(logEntry);
    logsContainer.scrollTop = logsContainer.scrollHeight;
}

// تحديث الوقت
function formatTime(seconds) {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    
    if (hours > 0) {
        return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    return `${minutes}:${secs.toString().padStart(2, '0')}`;
}

// بدء البحث
async function startSearch() {
    const studentId = document.getElementById('studentId').value.trim();
    const startRange = document.getElementById('startRange').value;
    const endRange = document.getElementById('endRange').value;
    
    if (!studentId) {
        addLog('❌ الرجاء إدخال رقم الطالب', 'error');
        return;
    }
    
    if (parseInt(startRange) >= parseInt(endRange)) {
        addLog('❌ نطاق البحث غير صحيح', 'error');
        return;
    }
    
    addLog(`🔍 بدء البحث عن رقم الطالب: ${studentId}`);
    addLog(`📊 النطاق: ${startRange} - ${endRange}`);
    
    try {
        const response = await fetch('/api/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                student_id: studentId,
                start_range: startRange,
                end_range: endRange
            })
        });
        
        const data = await response.json();
        
        if (data.status === 'started') {
            addLog(`✅ بدأ البحث بنجاح - ${data.total} كلمة سر للفحص`);
            document.getElementById('startBtn').disabled = true;
            document.getElementById('stopBtn').disabled = false;
            document.getElementById('progressSection').style.display = 'block';
            document.getElementById('resultsSection').style.display = 'none';
            
            if (statusInterval) clearInterval(statusInterval);
            statusInterval = setInterval(updateStatus, 1000);
        } else if (data.error) {
            addLog(`❌ ${data.error}`, 'error');
        }
    } catch (error) {
        addLog(`❌ خطأ: ${error.message}`, 'error');
    }
}

// إيقاف البحث
async function stopSearch() {
    addLog('⏹️ جاري إيقاف البحث...');
    
    try {
        await fetch('/api/stop', { method: 'POST' });
        addLog('✅ تم إيقاف البحث');
        document.getElementById('startBtn').disabled = false;
        document.getElementById('stopBtn').disabled = true;
        
        if (statusInterval) {
            clearInterval(statusInterval);
            statusInterval = null;
        }
    } catch (error) {
        addLog(`❌ خطأ: ${error.message}`, 'error');
    }
}

// تحديث الحالة
async function updateStatus() {
    try {
        const response = await fetch('/api/status');
        const data = await response.json();
        
        const progress = data.progress || 0;
        document.getElementById('progressBar').style.width = `${progress}%`;
        document.getElementById('progressBar').textContent = `${Math.round(progress)}%`;
        
        document.getElementById('checkedCount').textContent = data.checked.toLocaleString();
        document.getElementById('remainingCount').textContent = data.remaining.toLocaleString();
        document.getElementById('speedCount').textContent = data.speed;
        document.getElementById('elapsedTime').textContent = formatTime(data.elapsed);
        document.getElementById('successCount').textContent = data.successful;
        
        if (data.eta > 0) {
            document.getElementById('etaTime').textContent = formatTime(data.eta);
        }
        
        if (data.found) {
            document.getElementById('resultsSection').style.display = 'block';
            document.getElementById('foundPassword').textContent = data.found_password;
            document.getElementById('foundLocation').textContent = data.found_location || 'تم التحويل';
            addLog(`🎉 تم العثور على كلمة السر: ${data.found_password}`, 'success');
            stopSearch();
        }
        
        if (!data.active && data.found === false && data.checked > 0) {
            addLog('⚠️ اكتمل البحث دون العثور على كلمة السر', 'info');
            stopSearch();
        }
        
    } catch (error) {
        console.error('Error fetching status:', error);
    }
}

// مسح السجلات
function clearLogs() {
    const logsContainer = document.getElementById('logsContainer');
    logsContainer.innerHTML = '<div class="log-entry info">✨ تم مسح السجل</div>';
}

// إضافة مستمعي الأحداث
document.getElementById('startBtn').addEventListener('click', startSearch);
document.getElementById('stopBtn').addEventListener('click', stopSearch);
document.getElementById('clearLogsBtn').addEventListener('click', clearLogs);

// إدخال بالضغط على Enter
document.getElementById('studentId').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') startSearch();
});

addLog('✨ النظام جاهز. أدخل رقم الطالب وابدأ البحث.');
