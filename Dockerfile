# Базовий образ Python
FROM python:3.10-slim

# Встановлюємо системні залежності
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    python3-tk \
    && rm -rf /var/lib/apt/lists/*

# Створюємо робочий каталог у контейнері
WORKDIR /app

# Копіюємо файли в контейнер
COPY . .

# Встановлюємо залежності
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Вказуємо порт (за замовчуванням у Streamlit — 8501)
EXPOSE 8501

# Команда запуску Streamlit
CMD ["streamlit", "run", "main.py", "--server.port=8501", "--server.address=0.0.0.0"]