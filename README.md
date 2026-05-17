# AI-AGENT: Ứng dụng Agentic AI trong quản lý tài chính cá nhân
## Ứng dụng Agentic AI và kiến trúc Microservice

## 🏛️ Tổng quan Kiến trúc Hệ thống

Dự án phát triển qua các giai đoạn, từ mô hình **Monolithic (Project 1)** đến **Microservices (Project 2)**, kết hợp cùng các công nghệ hiện đại nhất để xây dựng một ứng dụng tài chính thông minh, mạnh mẽ và dễ dàng mở rộng.

### 1. Project 1: Monolithic Architecture & Kubernetes
**ExpenseOwl (Project 1)** được xây dựng theo kiến trúc nguyên khối (Monolith), tập trung vào việc quản lý chi tiêu và tích hợp AI Agent cơ bản.
* **Backend & Frontend:** Tích hợp trong một dịch vụ duy nhất (viết bằng Python/FastAPI và Go).
* **Triển khai (Deployment):** Đóng gói bằng Docker và triển khai lên cụm **Kubernetes (K8s)** với các thành phần:
    * **Deployment & ConfigMap:** Quản lý cấu hình và vòng đời ứng dụng.
    * **Service & Ingress:** Điều hướng và cân bằng tải lượng truy cập từ bên ngoài.
    * **Persistent Volume Claim (PVC):** Lưu trữ dữ liệu an toàn và bền vững.
* **AI Agent:** Tích hợp dịch vụ AI (`ai-agent-service`) độc lập để xử lý các tác vụ thông minh.

### 2. Project 2: Microservices Architecture & Event-Driven
**Project 2** là bản nâng cấp toàn diện, chuyển đổi hệ thống sang kiến trúc **Microservices** hướng sự kiện (Event-Driven), tối ưu hóa tính độc lập và khả năng mở rộng.

* **API Gateway:** Điểm truy cập duy nhất (Single Point of Entry) điều phối toàn bộ yêu cầu từ client đến các dịch vụ nội bộ (Proxy, Routing, Authentication).
* **Các Dịch vụ Độc lập (Microservices):**
    * **`user-service`:** Quản lý thông tin người dùng, xác thực (JWT) và phân quyền.
    * **`transaction-service`:** Cốt lõi xử lý luồng tiền, ghi nhận thu/chi.
    * **`budget-service`:** Quản lý ngân sách (Budgets) và phân bổ dòng tiền vào các hũ tài chính (Jars).
    * **`ai-service`:** "Bộ não" của hệ thống, tích hợp **Google Gemini GenAI** để bóc tách thông tin từ tin nhắn tự nhiên (NLP), hóa đơn (OCR) và cung cấp cố vấn tài chính.
    * **`notification-service`:** Quản lý và gửi thông báo hệ thống.
* **Giao diện Người dùng (`frontend-service`):** Ứng dụng web hiện đại (HTML/JS/CSS), giao tiếp với hệ thống qua API Gateway.
* **Hạ tầng lõi & Giao tiếp:**
    * **Cơ sở dữ liệu:** **PostgreSQL** được phân chia độc lập cho từng dịch vụ để đảm bảo tính cô lập dữ liệu.
    * **Message Broker:** Sử dụng **Apache Kafka** để truyền tải thông điệp bất đồng bộ (ví dụ: `transaction-service` báo cho `budget-service` cập nhật số dư).
    * **Giám sát (Monitoring):** Tích hợp **Prometheus** và **Grafana** để theo dõi sức khỏe hệ thống.
* **Triển khai:** Toàn bộ cụm hệ thống được khởi chạy đồng bộ, cấu hình mạng nội bộ chặt chẽ thông qua `docker-compose.yml`.

### 3. Công nghệ Cốt lõi (Tech Stack)
* **Ngôn ngữ & Framework:** Python (FastAPI), JavaScript (Frontend/PWA), Go.
* **AI & ML:** Google GenAI (Gemini), NLP, OCR scanning.
* **Database & Cache:** PostgreSQL, SQLite (cho môi trường Testing).
* **DevOps & Infrastructure:** Docker, Docker Compose, Kubernetes, GitHub Actions (CI/CD).
* **Event Streaming:** Apache Kafka.

[![CI/CD Status](https://github.com/tcwiuy/ai-agent/workflows/CI/CD%20Pipeline%20for%20ExpenseOwl%20Agentic%20AI%20Project/badge.svg)](https://github.com/tcwiuy/ai-agent/actions)

---

## 📂 Cấu trúc Toàn bộ Kho lưu trữ 

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
## 🧪 Hệ thống Kiểm thử Tự động hóa 

Dự án áp dụng mô hình kiểm thử cô lập chuyên sâu cho từng phân hệ Microservice dựa trên bộ ba công cụ: **Pytest**, **FastAPI TestClient** và chiến lược **Advanced Mocking** (Giả lập thành phần phụ thuộc). Toàn bộ dữ liệu kiểm thử được đồng bộ hóa và bao phủ (Test Coverage) dựa trên các tiêu chí kiểm thử thành phần, kiểm thử tích hợp và kiểm thử hệ thống.

```text
Project2/
├── user-service/app/tests/             
├── transaction-service/app/tests/     
├── budget-service/app/tests/           
└── ai-service/tests/ 
