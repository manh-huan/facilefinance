**Tiếng Việt** · [English](README.md)

# FacileFinance

Trợ lý cá nhân cho bộ phận tài chính doanh nghiệp. Giai đoạn đầu tập trung vào quản lý dòng
tiền cho một người dùng duy nhất (kế toán trưởng của một công ty suất ăn công nghiệp với
khoảng 40 điểm phục vụ), về sau sẽ phát triển thành SaaS nhiều khách hàng.

## Chức năng (MVP)

- Nhập ba loại file Excel: khoản vay ngân hàng, công nợ phải trả, công nợ phải thu.
- Áp dụng các quy tắc nghiệp vụ có phiên bản (chính sách thanh toán nhà cung cấp, chi phí cố
  định, lương, thuế, bảo hiểm xã hội, số dư tiền tối thiểu).
- Đề xuất lịch thanh toán theo tuần kèm trạng thái phê duyệt. Con người phê duyệt mọi khoản
  thanh toán; ứng dụng không bao giờ tự thực hiện thanh toán.
- Lập dự báo dòng tiền 13 tuần với các kịch bản giả định.
- Gửi email cảnh báo lúc 07:30 sáng thứ Hai (múi giờ Asia/Ho_Chi_Minh).
- Lớp AI: báo cáo quản trị cho Ban Giám đốc và trợ lý biết hỏi lại quy tắc khi gặp tình huống
  chưa được quy định.

Nguyên tắc: quy tắc và ánh xạ file là dữ liệu, không phải mã nguồn; AI diễn giải và đặt câu
hỏi, còn Python tính mọi con số; mọi con số đều truy vết được về nguồn. Danh sách đầy đủ
trong [CLAUDE.md](CLAUDE.md). Kiến trúc: [docs/architecture.md](docs/architecture.md).

Ứng dụng hỗ trợ đầy đủ hai ngôn ngữ (tiếng Anh và tiếng Việt). Backend chỉ trả về mã và giá
trị thô; frontend quyết định toàn bộ ngôn ngữ giao diện.

## Yêu cầu

- [uv](https://docs.astral.sh/uv/) với Python 3.14
- Docker và Docker Compose (PostgreSQL 16)
- Node.js (frontend)

## Cài đặt

```bash
uv sync                    # cài các thư viện Python
cp .env.example .env       # điền các khóa bí mật (không bao giờ commit .env)
docker compose up -d db    # khởi động PostgreSQL
uv run alembic upgrade head
```

## Lệnh thường dùng

```bash
uv run uvicorn apps.api.main:app --reload   # API cổng :8000
cd apps/web && npm install && npm run dev   # web cổng :5173, proxy /api -> :8000
uv run pytest                               # kiểm thử
uv run python -m evals.run                  # đánh giá (evals)
uv run ruff check . && uv run mypy          # lint + kiểm tra kiểu
cd apps/web && npm run i18n:check           # kiểm tra khóa en/vi khớp nhau
```

Một số lệnh chỉ chạy được sau khi hoàn thành bước khởi tạo tương ứng trong CLAUDE.md mục 13
(cơ sở dữ liệu, API, web, evals).

Các kiểm thử cơ sở dữ liệu (schema, ràng buộc, view) chỉ chạy khi biến
`FACILEFINANCE_TEST_DATABASE_URL` trỏ tới một database PostgreSQL có tên kết thúc bằng `_test`;
schema `public` của database này sẽ bị xóa và tạo lại. Nếu không đặt biến, các kiểm thử này bị bỏ
qua. Cần đặt `DATABASE_URL` khi chạy các lệnh `alembic`.

## Chính sách dữ liệu

Không có dữ liệu thật trong repository. File Excel thật được giữ bên ngoài; kiểm thử, evals
và demo chỉ dùng dữ liệu tổng hợp (`data/sample/`, `evals/`).
