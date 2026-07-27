FROM python:3.12-slim

WORKDIR /app

# منع بايثون من كتابة ملفات .pyc وعمل buffering على الـ logs
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# تثبيت مكتبات النظام المطلوبة لـ psycopg2
RUN apt-get update && apt-get upgrade -y && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]