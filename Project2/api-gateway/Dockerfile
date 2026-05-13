# Sử dụng phiên bản Python siêu nhẹ làm nền tảng
FROM python:3.10-slim

# Cài đặt các thư viện hệ thống cần thiết (như bộ dịch C/C++ cho một số thư viện Python)
RUN apt-get update && apt-get install -y gcc libpq-dev && rm -rf /var/lib/apt/lists/*

# Đặt thư mục làm việc bên trong Container
WORKDIR /app

# Copy file requirements.txt vào trước để cài đặt (Giúp tận dụng Docker Cache)
COPY requirements.txt .

# Cài đặt thư viện
RUN pip install --no-cache-dir -r requirements.txt

# Copy toàn bộ mã nguồn vào thư mục /app
COPY . .

# Lệnh khởi chạy server FastAPI ở port 8000
# Sửa lại dòng này
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]