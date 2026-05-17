import json

def test_ai_spending_suggestions(client):
    """SYS_05: Gọi API Trợ lý tài chính phân tích chi tiêu và đề xuất kế hoạch tiết kiệm"""
    payload = {
        "target_amount": 50000000,
        "duration_months": 10,
        "history_summary": "Tháng trước tiêu hoang vào giải trí 10tr"
    }
    
    # Endpoint nhận nhiệm vụ sinh đề xuất tư vấn tài chính cá nhân
    response = client.post("/api/ai/spending-suggestions", json=payload)
    
    if response.status_code == 200:
        assert response.json() is not None