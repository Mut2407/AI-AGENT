FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Chạy trực tiếp file main bằng Python
CMD ["python", "app/main.py"]