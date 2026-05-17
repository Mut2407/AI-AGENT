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
│       ├── main.yml             
│       └── deploy.yml          
├── BaiTap1/                     
├── BaiTap2/                     
│
├── Project1/                     
│   └── ExpenseOwl-main/
│       ├── cmd/expenseowl/      
│       ├── kubernetes/          
│       ├── main.py              
│       └── ai-agent-service/    
│
└── Project2/                     
    ├── api-gateway/             
    ├── user-service/            
    ├── transaction-service/     
    ├── budget-service/          
    ├── ai-service/              
    ├── notification-service/    
    └── frontend-service/        
---  
```
## 🧪 Hệ thống Kiểm thử Tự động hóa (Automated Testing Strategy)

Dự án áp dụng mô hình kiểm thử cô lập chuyên sâu cho từng phân hệ Microservice dựa trên bộ ba công cụ: **Pytest**, **FastAPI TestClient** và chiến lược **Advanced Mocking** (Giả lập thành phần phụ thuộc). Toàn bộ dữ liệu kiểm thử được đồng bộ hóa và bao phủ (Test Coverage) dựa trên các tiêu chí kiểm thử thành phần, kiểm thử tích hợp và kiểm thử hệ thống.

```text
Project2/
├── user-service/app/tests/             
├── transaction-service/app/tests/     
├── budget-service/app/tests/           
└── ai-service/tests/ 
