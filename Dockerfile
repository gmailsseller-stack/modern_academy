FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

# تثبيت المتطلبات الأساسية فقط
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    libssl-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# نسخ ملف المتطلبات
COPY requirements.txt .

# تثبيت المكتبات
RUN pip install --no-cache-dir -r requirements.txt

# نسخ الكود
COPY highSpeed24core.py .

# تعيين متغيرات البيئة للحد من استهلاك الموارد
ENV OMP_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1

# تشغيل الأداة
CMD ["python", "-u", "highSpeed24core.py"]
