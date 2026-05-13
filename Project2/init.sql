-- Tạo Database cho các Service
CREATE DATABASE expenseowl_user_db;
CREATE DATABASE expenseowl_transaction_db;
CREATE DATABASE expenseowl_budget_db;

-- Cấp quyền (Tuỳ chọn, dùng chung user 'admin' cho dễ trong môi trường dev)
GRANT ALL PRIVILEGES ON DATABASE expenseowl_user_db TO admin;
GRANT ALL PRIVILEGES ON DATABASE expenseowl_transaction_db TO admin;
GRANT ALL PRIVILEGES ON DATABASE expenseowl_budget_db TO admin;