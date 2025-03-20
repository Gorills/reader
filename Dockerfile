# Используем базовый образ с Python
FROM python:3.11-slim

# Установка зависимостей для Chrome и undetected_chromedriver
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    && wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Установка Python-зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование скрипта
COPY script.py /app/script.py

# Установка рабочей директории
WORKDIR /app

# Запуск скрипта с аргументами
CMD ["python", "script.py", "--session-id", "0", "--use-proxies", "--visual-mode"]