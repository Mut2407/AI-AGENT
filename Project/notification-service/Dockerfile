FROM python:3.10-slim

# Thiết lập thư mục làm việc
WORKDIR /app

# Copy file requirements và cài đặt thư viện
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy toàn bộ mã nguồn của service vào container
COPY . .

# Vì đây là Worker chạy ngầm, chúng ta chạy trực tiếp bằng lệnh python
CMD ["python", "main.py"]