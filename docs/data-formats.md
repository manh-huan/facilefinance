# Input data formats

This document describes the **structure** of the Excel files the finance team uses today, as
observed in the November 2026 versions. It contains **no real data**: every name, code and
amount below is a made-up example. Use it to write file maps, synthetic samples
(`data/sample/`) and importer tests.

Header text is quoted **verbatim in Vietnamese** because importers must match it. Do not
translate or "fix" it in file maps or tests.

Column positions are given as observed (A = first column) for orientation only.
**Importers must locate tables by header text, never by fixed position**: positions shift
between months.

| File | Used in | Format | Notes |
|---|---|---|---|
| Bank loan maturity report | MVP | .xlsx | One file per month, many unrelated sheets |
| Accounts payable | MVP | .xlsb | Binary Excel; dozens of junk sheets |
| Accounts receivable | MVP | .xlsx | One sheet per month; some sheets have ~16,000 empty columns |
| 3-month cash plan | MVP (export target) | .xlsx | ~21 MB; the template the forecast must eventually fill |
| Timesheet (per site) | Post-MVP | .xlsm | Macro workbook; one site per file |
| Payroll | Post-MVP | .xlsx | All sites in one sheet; >100 junk sheets |

---

## 1. Bank loan maturity report

**Purpose:** list of short-term bank loans with maturity dates and outstanding principal.

### Sheets

- **Use:** the monthly maturity report sheets, named inconsistently, e.g. `MATURITY DEC 2026`
  and `Maturity Nov 2026` (different casing). Match case-insensitively on `maturity`.
- **Ignore for MVP:** about 20 other sheets (cash-flow drafts, tax, savings, car loans,
  payables copies, per-bank raw ledgers named like `BL <bank>`). See "Raw bank sheets" below.

### Layout of a maturity report sheet

A sheet contains up to three tables stacked vertically, separated by blank rows:

1. A title row, e.g. `BANK LOAN MATURITY – NOVEMBER 2026`.
2. **Summary by bank** (only in some months): headers `Ngân hàng | Số khoản vay | Gốc còn phải trả`,
   ending with a `TỔNG CỘNG` row.
3. **Summary by maturity date**, sometimes placed to the right of table 2 (starting around
   column E): headers `Ngày đáo hạn | Số khoản vay | Gốc đến hạn (VNĐ)` or
   `Ngày đáo hạn | Ngân hàng | Gốc đến hạn`. Ends with `TỔNG CỘNG`.
4. **Loan detail** (the table to import), preceded by a title like `CHI TIẾT KHOẢN VAY ĐÁO HẠN …`.
5. A free-text note row at the bottom starting with `Ghi chú:` or `Lưu ý:`.

### Loan detail table

| Header (verbatim) | Meaning | Type | Example (fake) |
|---|---|---|---|
| `Ngân hàng` | Bank | text | `Bank A` |
| `Nội dung khoản vay` | Purpose of the loan | text | `NCC HCM`, `LUONG 05.2026`, `BHXH` |
| `Mã khoản vay` | Loan code | text | see code formats |
| `Ngày đáo hạn` | Maturity date | Excel date, format `dd/mm/yyyy` | `2026-12-15` |
| `Số tiền vay` | Original principal | integer VND | `700000000` |
| `Đã trả` | Repaid so far | integer VND | `0` |
| `Gốc còn phải trả` | Outstanding principal | integer VND | `700000000` |

- Ends with a row whose `Gốc còn phải trả` cell holds the grand total and whose `Đã trả`
  cell reads `TỔNG CỘNG`. The total label is **not** in the first column.
- **Loan code formats differ by bank** (patterns, `#` = digit): `LD##########`,
  `3000#######` (numeric, may be stored as a number), `PN 070-#-52-00-#####`.
  Always read codes as text.
- Purpose text encodes what the loan financed: supplier payments (`NCC …`), payroll
  (`LUONG …`, `Lương …`), social insurance (`BHXH`). Useful for categorising later; not a code.
- Partially repaid loans exist (`Đã trả` > 0). Rows with `Gốc còn phải trả` = 0 are fully
  repaid and are skipped.
- The **same loan can appear in two monthly sheets**. Deduplicate on (loan code, maturity date).

### Raw bank sheets (`BL <bank>`) — not imported in MVP

These are the source ledgers behind the report and are much messier. Documented so nobody
tries to import them naively:

- Title block, then a two-row header: `PREVIOUS LOAN | CURRENT LOAN`, then
  `Old Loan list | LD no (or PN no) | Amount | Maturity Date | Paid | Paid date | Lending again | Lending date | Maturity date | Current Loan total | Inerest per month(%)`.
- **Misleading headers:** `Lending again` holds the current outstanding amount; the report's
  own note says one date column is actually the re-disbursement date.
- **Date cells mix types:** real dates, plus text such as `04+09/09/2026`, `21+28/08+11/09/2026`,
  `31-thg 10-25+27/01/2026`, `15&16-thg 5-25`, `14/11`, and non-dates like
  `Tăng tạm thời 3 tháng` or `#VALUE!`. A `+` means the loan was disbursed or repaid in
  several parts on several dates.
- Column A mixes purpose labels, limit rows (`Operate limit`, `Loan limit`,
  `Available bank loan amount`), personal names and `Total` rows.
- Interest rates appear as text like `6,8%` or `7.50%` (both decimal separators).

If these sheets are ever imported, any multi-date cell must become an `assistant_question`,
never a guess.

---

## 2. Accounts payable

**Purpose:** what the company owes each supplier, broken down by the month the debt arose.
File format is **`.xlsb`** (binary). `python-calamine` reads it directly.

### Sheets

- **Use:** the main sheet, named after the period, e.g. `2025-2026`.
- **Junk:** ~16 sheets named `foxz_2` … `foxz_17`, each with a single cell. Skip any sheet
  with fewer than 2 rows or 2 columns.
- **Reference, not imported in MVP:**
  - `DS Hóa đơn` — purchase invoice list (`Ngày hạch toán | Ngày chứng từ | Số hóa đơn | MST | … | Nhà cung cấp | Tổng tiền hàng | Tiền thuế GTGT | Tổng tiền thanh toán | Mã chứng từ | Năm | Tháng | Tên NCC`); has a totals row at the **top**, containing `#REF!`.
  - `SD Cuối kỳ-MISA` — closing balances exported from the accounting software (account 331),
    two-row header with debit / credit pairs (`Nợ` / `Có`) for opening, movement and closing.
    Good candidate for cross-checking totals later.
  - `NCC NHỎ` — small suppliers by month, with a `TT` total column.
  - `TT TIỀN MẶT` — cash payments: `TÊN NCC | TOTAL | THÁNG | NĂM | check phiếu | Tình trạng TT`.
  - `Tổng hợp Thuế + BH` — monthly tax and insurance totals (see section 6).
  - `KO LÀM` — suppliers no longer used.
  - A summary sheet whose name is truncated (`TỔNG HỢP CÔNG NỢ PHẢI TRẢ NHÀ `, trailing space).

### Main sheet layout

- **Row 1:** title in A1; from column F onwards, the **year** of each month column
  (e.g. `2018 … 2024, 2025 … 2026`).
- **Row 2:** mostly empty.
- **Row 3:** headers.

| Header (verbatim) | Meaning | Type | Example (fake) |
|---|---|---|---|
| `Suppliers` | Supplier code | text | `NCC_0001` (pattern `NCC_####`) |
| `MÃ HÀNG HÓA` | Supplier category (not a product code) | text | `EQUIPMENT`, `CAR RENTAL` |
| `MST` | Tax ID | text (keep leading zeros) | `0100000001` |
| `Tên khách hàng` | **Supplier** name (header says "customer"; it is wrong) | text | `Công ty TNHH Mẫu` |
| `Total` | Total owed | integer VND | `83848146` |
| `10`, `12`, `2`, `7`, … | Amount arising in that month; the year is in row 1 above | integer VND | `0` |
| (last columns) | free notes | text | — |

- **Month columns need two header rows:** month number from row 3, year from row 1.
  Months are not contiguous and not always in order (old years appear sparsely).
- **Category rows:** some rows have only a category label (e.g. `CAR RENTAL` in the name
  column) and zeros; they group the suppliers below them. Not suppliers.
- **Totals row** at the bottom labelled `Tổng`, and it currently contains **`#REF!` errors**.
  The importer must not rely on this row; compute the total, and report the broken cell as a
  warning. Cross-check against `SD Cuối kỳ-MISA` instead.
- Empty cells and `0` both mean zero.

### Business rule this file feeds

Supplier payment policy (to be confirmed, stored as a rule, not code): suppliers with
monthly payables ≥ a threshold (currently 200 million VND) are paid in two instalments on the
15th and the 30th; smaller suppliers once on the 30th. Open questions: 50/50 split or by
invoice; threshold measured on last month's new debt or on total balance.

---

## 3. Accounts receivable

**Purpose:** what each customer owes, by month of service, plus expected collection day.

### Sheets

- **One sheet per month:** `T11.2026`, `T10.2026`, … and older `T7`, `T8`, `T1.2023` …
  (naming changed over time; one name has a trailing space, `T4.2026 `).
- Pick the sheet for the requested month; match after trimming.
- **Junk:** ~33 `foxz…` single-cell sheets; `Sheet1`.
- Some monthly sheets report **~16,000 columns** (formatting applied to whole rows). Read
  only up to the last header column.
- Also present: `DS Hóa đơn` (sales invoices), `SD Cuối kỳ` (closing balances).

### Monthly sheet layout

- **Row 1:** title in A1; from column D, the year for each month column.
- **Row 2:** running column numbers `1, 2, 3 …` (ignore; one number repeats).
- **Row 3:** headers.

| Header (verbatim) | Meaning | Type | Example (fake) |
|---|---|---|---|
| `Tên khách hàng` | Customer name | text | `Công ty TNHH Nhà Máy Mẫu` |
| `TK công nợ` | Ledger account | text | `131` |
| `Số dư cuối kỳ` | Balance owed at month end | integer VND | `1582009920` |
| `12`, `1`, `2`, … `11` | Amount by service month (year in row 1) | integer VND | `531004680` |
| `Note` | Site code the customer belongs to | text | `SITE_A` |
| `Ngày thu dự kiến` | Expected collection **day of month** (number only) | integer or empty | `25` |

- **Totals row** labelled `Tổng` near the bottom; include it in the total-match test, exclude
  it from records.
- The same customer name can appear on several rows with different site codes in `Note`.
  The pair (customer, site) identifies a receivable line.
- `Ngày thu dự kiến` is often empty; the forecast then needs a rule (see section 4).
- The team plans to add actual collection dates in the note area later; expect this column
  set to grow.

---

## 4. 3-month cash plan (export target)

**Purpose:** the weekly cash plan the chief accountant maintains by hand. The forecast should
eventually **fill this template** (via `openpyxl`) instead of replacing it.

- ~21 MB. Sheets `Nov`, `Oct`, and a template named `mẫu`. ~16,000 reported columns.
- **Header rows 5–6:** `No | Clients/Suppliers | Credit / Debit follow contract | … | Serviced/Purchased months`,
  then one column per week for the current month (`Week 1 (01-06)`, `Week 2 (09-15)`, …),
  a month total column, then the next months as single columns (`DEC2026`, …).
- **Quirk:** the current-month total column is labelled with a **stale month**
  (e.g. `TOTAL SEP2026` on the November sheet). Match total columns by position after the
  week columns, not by label.
- **Row 7:** `Beginning balance` per week.
- **Sections (column A):** `I. CASH IN` → `1. Collection from customers`,
  `2. Collection from deposit & others`, `3. Loan from Bank, Branch and Individual`,
  `4. Other income`; `II. CASH OUT` → `1. Salary & Insurance & Tax`,
  `2. Lending/Repayment of the Loan`, `3. General Expenses`,
  `4. Other material + commission + incentive`, `5. Gasoline + Gas + Car rental`,
  `5. Material Suppliers` (numbering repeats), `6. Construction, Interior and Equipment Suppliers`.
- **Customer rows** carry the contractual payment term as text: `1 month`, `1.5 month`,
  `2 month`, `3 month` (sometimes empty), and the months being collected as text such as
  `T10+11+12`, `T(06+07)+08+09`. Actual collection is often later than the contract term;
  this lag is an input for late-payer tracking.

Not imported in MVP. Useful now as a reference for the forecast's categories and as the
target layout for export.

---

## 5. Timesheet (post-MVP, payroll reconciliation)

**Purpose:** hours worked per employee per day at one site. File format `.xlsm` (macros;
read values only, never run macros).

### Sheets

- `CC` — the timesheet to import.
- `BL` — short list of employees with salary; `Tổng hợp` — site summary.
- `1` … `31` — one sheet per day; not needed.

### `CC` layout

- **Rows 2–4:** site name (`Site:`), year (`NĂM`), month (`THÁNG`) as label/value pairs.
- **Row 5:** `STT | MNV | MNV | HỌ VÀ TÊN | (position) | TỔNG LƯƠNG | CA LÀM VIỆC | (type) | <date 1> … <date 31> | Tổng`.
  Date headers are real dates for the month.
- **Row 6:** weekday markers under each date (stored as small numbers that render as dates
  like `1900-01-05`: treat as weekday codes, not dates); total columns `HC | TC | CN`.
- **Each employee uses 4 consecutive rows:**

| Row | `CA LÀM VIỆC` | Type | Meaning |
|---|---|---|---|
| 1 | `NGÀY` | `HC` | Day shift, regular hours |
| 2 | `NGÀY` | `TC` | Day shift, overtime |
| 3 | `ĐÊM` | `HC` | Night shift, regular hours |
| 4 | `ĐÊM` | `TC` | Night shift, overtime |

  Employee number, code, name, position and total salary appear only on row 1
  (the code repeats on rows 2–4 in the second `MNV` column).
- **Day cells:** hours as numbers (`8`, `5.5`) or leave codes as text (`AL` = annual leave).
- **Total columns:** `HC` (regular hours, on HC rows), `TC` (overtime, on TC rows),
  `CN` (hours worked on Sundays, on every row).
- Sheet extends far below the last employee with empty, formula-filled rows. Stop at the
  first block whose number cell is empty.

### Known data issues

- Employee codes may be **temporary** and differ from payroll codes for the same person; a
  temporary code can even collide with another person's real code. Match on code first, then
  flag name matches with different codes; never auto-merge.
- Employees with zero hours remain listed after leaving.

---

## 6. Payroll (post-MVP, payroll reconciliation)

**Purpose:** monthly payroll for all sites. Contains personal data (names, tax IDs, salaries):
only synthetic data in the repo; mask names before any AI call.

### Sheets

- `SALARY` — main payroll (~600 rows, 56 columns).
- `BANK SITE`, `BANK <customer>` per-group bank transfer lists, `BANK OFFICE`, `CASH`
  (cash payroll with signatures: `Net Amount / Thực lãnh`), `TOTAL`.
- **Junk:** >120 sheets named `Kangatang_N`.

### `SALARY` layout

- Title block rows 1–5; **two-row header on rows 6–7**; data from row 8.
- Main columns (row 6 / row 7 headers, verbatim):

| Header | Meaning |
|---|---|
| `Mã NV` | Employee code (stored as text) |
| `HỌ TÊN`, `Chức vụ` | Name, position |
| `SITE` | Site name; filter on this to compare with one site's timesheet |
| `Mã số thuế` | Personal tax ID |
| `Lương cơ bản` | Base salary |
| `Các khoản hỗ trợ` → `Trách nhiệm`, `Thâm niên`, `Điện thoại`, `Thuê nhà`, `Xăng xe`, `Tiền ăn`, `Năng lực` | Allowances |
| `Tổng Lương` | Total contractual salary |
| `Lương Ngày công` → `Giờ công (TV)`, `Giờ công (CT)`, `Lương ngày công` | Hours on probation (`TV`) / official (`CT`), regular-hours pay |
| `Lương tăng ca` → `OT (TV)`, `OT (CT)`, `Holiday OT (TV/CT)`, `Sunday OT (TV/CT)`, `TC đêm TV`, `TC đêm CT`, `Lương tăng ca` | Overtime and night hours, overtime pay |
| `Thưởng`, `Hoàn trả khác / …`, `Trừ khác`, `Tổng thu nhập` | Bonus, other reimbursements, other deductions, gross income |
| `BHXH TRÍCH QUỸ …` / `BHXH NHÂN VIÊN …` → `BHXH (8%)`, `BHYT (1,5%)`, `BHTN (1%)`, `Cộng` | Insurance (employer / employee) |
| `Người phụ thuộc`, `Tổng tiền giảm trừ`, `Thu nhập chịu thuế`, `Thu nhập tính thuế`, `Thuế TNCN` | Personal income tax |
| `Hoàn trả khác sau thuế`, `Trừ tạm ứng / …`, `Thực nhận`, `Ký nhận` | Post-tax adjustments, net pay, signature |

### Observed calculation (hypotheses to confirm with the chief accountant)

Reverse-engineered from one month and consistent for one site; store as versioned rules once
confirmed, never as code constants:

- Regular-hours pay = total salary ÷ 208 × official hours (probation: × 0.9).
- Overtime pay = base salary ÷ 208 × 1.5 × overtime hours (probation: × 0.9),
  plus base salary ÷ 208 × 0.3 × night hours.
- Night hours = night regular hours + night overtime hours (timesheet `ĐÊM HC` + `ĐÊM TC`).
- Official hours = regular hours + paid annual-leave days × 8, where paid leave appears
  **capped** (likely by remaining leave balance).
- Overtime hours appear **fixed at 17** per employee in the payroll, while the timesheet
  shows far more; the difference seems to be paid through `Hoàn trả khác`. Rule unknown:
  must come from an `assistant_question`, not a guess.

---

## 7. Requirements for synthetic samples (`data/sample/`)

The generator must reproduce, for each MVP file:

- the sheet set, including junk sheets (single-cell `foxz_N`) and irrelevant sheets;
- title rows and multi-row headers at the positions described, with verbatim header text;
- misleading headers (`Tên khách hàng` for suppliers; stale `TOTAL <month>` label);
- grand-total rows with the label in a non-first column, and one broken total (`#REF!`);
- category/group rows without codes;
- codes in all the formats listed, including numeric-looking codes and leading zeros;
- a partially repaid loan, a fully repaid loan (outstanding 0), and the same loan in two
  monthly sheets;
- month columns whose year sits in a separate header row, out of order;
- a receivables sheet with thousands of trailing empty columns;
- an `.xlsb` payables file. Common Python libraries cannot write `.xlsb`: generate `.xlsx`
  and convert with LibreOffice headless (`soffice --convert-to xlsb`), or commit one small
  hand-made synthetic `.xlsb` fixture.

Names must be clearly fictional (`Công ty TNHH Mẫu 01`), amounts random but internally
consistent so total-match tests are meaningful.
