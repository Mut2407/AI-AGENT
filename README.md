# AI-AGENT: Ứng dụng Agentic AI trong quản lý tài chính cá nhân
## Ứng dụng Agentic AI và kiến trúc Microservice

[![CI/CD Status](https://github.com/tcwiuy/ai-agent/workflows/CI/CD%20Pipeline%20for%20ExpenseOwl%20Agentic%20AI%20Project/badge.svg)](https://github.com/tcwiuy/ai-agent/actions)

Kho lưu trữ (Monorepo) này chứa các dự án nghiên cứu và phát triển phần mềm ứng dụng **Agentic AI** thông minh kết hợp với kiến trúc hệ thống phân tán, DevOps chuyên sâu, phục vụ bài toán tối ưu hóa quy trình tự động và quản lý tài chính cá nhân.
---

## 📂 Cấu trúc Toàn bộ Kho lưu trữ (Monorepo Strategy)

```text
AI-AGENT/
├── .github/
│   └── workflows/
│       ├── main.yml             # CI/CD tự động chạy Pytest Matrix & Push Docker Hub (Project 2)
│       └── deploy.yml           # Workflow cấu hình bổ trợ triển khai hạ tầng
├── BaiTap1/                     # Các module bài tập nền tảng về AI Agent tra cứu phim tự động
├── BaiTap2/                     # Các module n8n workflow và cấu hình tích hợp
│
├── Project1/                     # PHÂN HỆ DỰ ÁN 1 (ExpenseOwl Monolithic-to-K8s)
│   └── ExpenseOwl-main/
│       ├── cmd/expenseowl/      # Luồng khởi tạo core service viết bằng ngôn ngữ Go
│       ├── kubernetes/          # Tệp cấu hình phân lớp Ingress, SVC, Deployment, PVC, ConfigMap
│       ├── main.py              # Backend API wrapper xử lý logic Python
│       └── ai-agent-service/    # Module AI agent nền tảng phục vụ bóc tách hóa đơn sơ bộ
│
└── Project2/                     # PHÂN HỆ DỰ ÁN 2 (Hệ thống AI Tài chính - Microservices)
    ├── api-gateway/             # API Gateway (Uvicorn Catch-all router) điều phối luồng dữ liệu (Cổng 8000)
    ├── user-service/            # Quản lý xác thực JWT OAuth2, Hồ sơ, cấu hình kiểm thử tests/
    ├── transaction-service/     # Tiếp nhận biến động số dư, đẩy bản tin Kafka Producer sang DB
    ├── budget-service/          # Quản lý ngân sách hũ tài chính, Kafka Consumer tự động đồng bộ
    ├── ai-service/              # Module tích hợp LLM (Google Gemini) xử lý OCR Ảnh/PDF/CSV Sao kê
    ├── notification-service/    # Lắng nghe sự kiện Kafka gửi thông báo cảnh báo chi tiêu vượt ngưỡng
    └── frontend-service/        # Giao diện Web hiển thị Dashboard, Chatbot tương tác trực quan (Cổng 3001)
