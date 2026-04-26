FROM python:3.11-slim

# تعيين متغيرات البيئة
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive

# تثبيت dependencies النظام المطلوبة
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    python3-dev \
    libssl-dev \
    libffi-dev \
    libgomp1 \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

# تعيين مجلد العمل
WORKDIR /app

# نسخ ملف المتطلبات أولاً (للاستفادة من caching)
COPY requirements.txt .

# تثبيت Python packages
RUN pip install --no-cache-dir -r requirements.txt

# نسخ الكود
COPY highSpeed24core.py .

# إنشاء مجلد للنتائج
RUN mkdir -p /app/results

# متغيرات البيئة للـ Python
ENV PYTHONPATH=/app

# الأمر الافتراضي
CMD ["python", "highSpeed24core.py"]
