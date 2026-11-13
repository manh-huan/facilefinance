# File maps

A file map tells an importer how to read one file type. Maps are data: they carry a
`version`, are never edited once used, and a change is a new file (`loans.v2.yaml`). The same
content is stored in `file_mappings.spec` (jsonb). Structure and quirks of the real files:
`docs/data-formats.md`. Header texts are quoted verbatim in Vietnamese and must not be
translated or "fixed"; a test checks that every header here appears in that document.

Status is `proposed` until a human confirms it.

## Keys

- `file_type`, `version`, `status`, `formats`: identity and accepted file extensions.
- `as_of`: `source: parameter` means the period the data refers to is given with the upload.
  The importer never guesses it from titles or file names.
- `sheets`
  - `select`: how to find the sheet(s). `by: name_contains` (substring, `case_sensitive`,
    `multiple`), `by: name_template` (`{month}`, `{year}` from the import parameters, names
    compared after trimming), or `by: header_row` (the sheet whose table header matches;
    several matches are an error, never a guess).
  - `skip_when`: sheets below `min_rows` / `min_cols` are junk and ignored.
  - `read_columns: up_to_last_header`: never read the thousands of trailing empty columns.
- `table`
  - `header_row.contains_all`: the table is located by header text, never by position. A
    row holding all these headers is the header row.
  - `columns`: logical field -> `header` (verbatim), `type` (`text`, `integer_vnd`, `date`,
    `integer`), `required` (default true), `empty_as` (value for an empty cell).
    `text` always reads numeric-looking cells as text (leading zeros and long codes kept).
  - `month_columns`: columns whose header matches `header_pattern` hold one amount per
    month; the year comes from the cell `year_row_offset` rows above the header row, in the
    same column. Months need not be contiguous or ordered.
  - `skip_rows`: rows that are not records (group labels, fully repaid loans), counted in
    the import report.
  - `end.total_row`: the grand-total row. `label` is searched in `label_column` (or
    `any_column`), the value is read from `value_column`. The row is excluded from records
    and the importer verifies the sum of `verify.field` against it. If the total cell is
    unreadable (e.g. `#REF!`), the importer computes the total and reports a warning.
  - `duplicates`: policy when the same key appears twice in one file. `identical: merge`
    keeps one and notes it; `conflict: skip_all_and_report` skips every conflicting row and
    reports it for a human to resolve. Nothing is picked silently.
- `emit`: how rows become records (counterparty, kind, amount, period). Zero amounts never
  produce a record.

Errors always carry file, sheet, row and reason as parameters (CLAUDE.md section 9).
