FROM python:3.11-slim

WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*

# Копирование и установка Python-зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование всего проекта
COPY . .

# Railway использует переменную PORT (по умолчанию 8080)
ENV PORT=8080

# Запуск единого сервера FastAPI + бот
CMD uvicorn main:app --host 0.0.0.0 --port $PORT
