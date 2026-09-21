# Fintech Stock Bot

Telegram Bot hỗ trợ phân tích và theo dõi cổ phiếu Việt Nam.

Dự án được xây dựng bằng Python, kết hợp dữ liệu thị trường, dữ liệu tài chính doanh nghiệp và các chỉ báo kỹ thuật để hỗ trợ nhà đầu tư trong quá trình sàng lọc và đánh giá cổ phiếu.

## Mục tiêu dự án

Fintech Stock Bot được xây dựng với các mục tiêu chính:

- Thu thập dữ liệu giá và khối lượng giao dịch cổ phiếu Việt Nam.
- Lấy dữ liệu tài chính của doanh nghiệp.
- Tính toán các chỉ số tài chính quan trọng.
- Phân tích tín hiệu mua/bán dựa trên chiến lược đầu tư định trước.
- Hỗ trợ theo dõi giá cổ phiếu theo thời gian thực.
- Backtest chiến lược trên dữ liệu lịch sử.
- So sánh hiệu suất chiến lược với VN-Index.
- Cung cấp kết quả phân tích thông qua Telegram Bot.

## Đối tượng sử dụng

Dự án hướng đến:

- Sinh viên ngành Tài chính - Ngân hàng và Fintech.
- Người học phân tích tài chính và phân tích cổ phiếu.
- Người muốn xây dựng hệ thống stock screening bằng Python.
- Nhà đầu tư cá nhân cần một công cụ hỗ trợ sàng lọc cổ phiếu.

> Lưu ý: Bot chỉ mang tính chất hỗ trợ phân tích và học tập, không phải hệ thống tư vấn đầu tư hoặc khuyến nghị đầu tư chuyên nghiệp.


## Tính năng chính

### 1. Phân tích cổ phiếu

Bot cung cấp thông tin phân tích cho từng mã cổ phiếu, bao gồm:

- Giá hiện tại.
- Khối lượng giao dịch.
- Doanh thu.
- Tăng trưởng doanh thu.
- Lợi nhuận sau thuế.
- Tăng trưởng lợi nhuận.
- EPS.
- ROE.
- Debt/Equity.
- P/E.
- P/B.
- Giá trị sổ sách trên mỗi cổ phiếu (BVPS).

### 2. Phân tích kỹ thuật

Bot sử dụng một số chỉ báo kỹ thuật để xác định xu hướng và tín hiệu giao dịch:

- Moving Average 20 phiên (MA20).
- Khối lượng giao dịch trung bình 20 phiên.
- Volume Breakout.
- Price Momentum.

### 3. Strategy 2

Chiến lược chính của Bot kết hợp phân tích cơ bản và phân tích kỹ thuật.

Điều kiện BUY:

- Revenue Growth > 15%.
- Net Income Growth > 15%.
- ROE > 15%.
- Volume >= 1.5 lần Volume Average 20 phiên.
- Close > MA20.
- Cổ phiếu chưa được nắm giữ.

### 4. Real-time Data

Bot có khả năng lấy dữ liệu giao dịch gần thời gian thực, bao gồm:

- Giá giao dịch gần nhất.
- Khối lượng giao dịch.
- Thời gian giao dịch.
- Loại khớp lệnh.
- Trade ID.

### 5. Market Overview

Bot cung cấp thông tin tổng quan thị trường thông qua VN-Index:

- Điểm số VN-Index.
- Phần trăm thay đổi.
- Khối lượng giao dịch.
- Số phiên dữ liệu.
- Market breadth.
- Top gainers.
- Top losers.

### 6. Watchlist và Alert

Người dùng có thể:

- Thêm cổ phiếu vào watchlist.
- Xóa cổ phiếu khỏi watchlist.
- Xem danh sách theo dõi.
- Đăng ký cảnh báo.
- Hủy cảnh báo.

### 7. Portfolio và Risk Monitoring

Bot hỗ trợ theo dõi vị thế cổ phiếu:

- Giá mua.
- Giá hiện tại.
- Số lượng.
- Giá trị vị thế.
- Lãi/lỗ.
- Tỷ trọng vị thế.

Bot cũng đưa ra một số cảnh báo rủi ro đơn giản đối với danh mục.

### 8. Backtest

Bot hỗ trợ kiểm tra Strategy 2 trên dữ liệu lịch sử.

Các nội dung được tính toán:

- Initial Capital.
- Final Capital.
- Total Return.
- Number of Trades.
- Winning Trades.
- Losing Trades.
- Win Rate.
- Average Return.
- Best Trade.
- Worst Trade.
- Profit Factor.
- Maximum Drawdown.
- Transaction Cost.

### 9. VN-Index Benchmark

Kết quả backtest của Strategy 2 được so sánh với VN-Index trong cùng khoảng thời gian.

Các chỉ tiêu chính:

- Strategy Return.
- VN-Index Return.
- Maximum Drawdown.
- Excess Return.


## Công nghệ sử dụng

| Thành phần | Công nghệ |
|---|---|
| Programming Language | Python |
| Telegram Bot | python-telegram-bot |
| Market Data | DNSE API |
| Financial Data | VNStock |
| Real-time Data | VNStock |
| Data Processing | Pandas |
| Testing | unittest |
| Version Control | Git / GitHub |
| Deployment | Render | 


## Kiến trúc hệ thống

Project được thiết kế theo mô hình phân tách thành các layer chính:

```text
                    Telegram User
                          |
                          v
                +-------------------+
                |   Telegram Bot    |
                | telegram_bot.py   |
                +---------+---------+
                          |
                          v
                +-------------------+
                |  Analysis Layer   |
                |                   |
                | Signal Engine     |
                | Stock Scanner     |
                | Technical Filter  |
                | Fundamental Filter|
                | Backtest Engine   |
                +---------+---------+
                          |
                          v
                +-------------------+
                |     Data Layer    |
                |                   |
                | DNSE Client       |
                | VNStock Client    |
                | Realtime Client   |
                | Data Manager      |
                +---------+---------+
                          |
                 +--------+--------+
                 |                 |
                 v                 v
             DNSE API          VNStock API
