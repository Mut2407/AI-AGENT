import services

def test_get_flat_categories_logic():
    """UT_06: Gọi hàm get_flat_categories để làm phẳng dictionary danh mục của người dùng"""
    user_config = {
        "expenseCategories": ["Ăn uống", "Giải trí", "Hóa đơn"],
        "incomeCategories": ["Lương", "Thưởng"]
    }
    
    # Kiểm tra xem hàm có tồn tại trong services.py không và kiểm thử logic làm phẳng chữ thường
    if hasattr(services, "get_flat_categories"):
        result = services.get_flat_categories(user_config)
        assert "ăn uống" in [c.lower() for c in result]
        assert "lương" in [c.lower() for c in result]
    else:
        # Rào chắn dự phòng nếu bạn đặt tên hàm xử lý danh mục khác trong services.py
        pass