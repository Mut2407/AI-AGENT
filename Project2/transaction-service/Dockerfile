# Sử dụng phiên bản Python siêu nhẹ làm nền tảng
FROM python:3.10-slim

# Cài đặt các thư viện hệ thống cần thiết (như bộ dịch C/C++ cho một số thư viện Python)
RUN apt-get update && apt-get install -y gcc libpq-dev && rm -rf /var/lib/apt/lists/*

# BƯỚC 1: Đặt thư mục làm việc GỐC bên trong Container
WORKDIR /app

# BƯỚC 2: Copy file requirements.txt vào trước để cài đặt (Giúp tận dụng Docker Cache)
COPY requirements.txt .

# BƯỚC 3: Cài đặt thư viện
RUN pip install --no-cache-dir -r requirements.txt

# BƯỚC 4: Copy toàn bộ mã nguồn vào thư mục GỐC /app
COPY . .

# BƯỚC 5: Di chuyển vào đúng thư mục chứa code chạy (phòng ngủ)
WORKDIR /app/app

# BƯỚC 6: Lệnh khởi chạy server FastAPI ở port 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]