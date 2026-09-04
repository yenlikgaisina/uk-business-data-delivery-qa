"""
Runs sql/07_final_delivery.sql and exports:
  - outputs/client_delivery_full.csv     the complete validated delivery
  - data/sample/client_delivery_sample.csv  a 500-row sample, committed to
                                             the repo for quick inspection
                                             without needing to run the
                                             pipeline
  - outputs/reconciliation_report.csv    month-on-month reconciliation numbers

Run from the project root, after src/validate.py: python3 src/export_delivery.py
"""
import csv
import duckdb

DB_PATH = "delivery.duckdb"


def main():
    con = duckdb.connect(DB_PATH)

    def strip_sql_comments(text):
        kept = []
        for line in text.splitlines():
            idx = line.find("--")
            kept.append(line[:idx] if idx != -1 else line)
        return "\n".join(kept)

    def split_statements(text):
        stmts, current, in_quote = [], [], False
        for ch in text:
            if ch == "'":
                in_quote = not in_quote
                current.append(ch)
            elif ch == ";" and not in_quote:
                stmts.append("".join(current))
                current = []
            else:
                current.append(ch)
        if "".join(current).strip():
            stmts.append("".join(current))
        return [s.strip() for s in stmts if s.strip()]

    with open("sql/07_final_delivery.sql") as f:
        sql_text = f.read()
    stmts = split_statements(strip_sql_comments(sql_text))
    for stmt in stmts:
        result = con.execute(stmt)
        if stmt.strip().lower().startswith(("select", "with")):
            cols = [d[0] for d in result.description]
            rows = result.fetchall()
            print(f"Sign-off counts ({', '.join(cols)}):")
            for r in rows:
                print("  ", r)

    # Full delivery
    con.execute("COPY final_client_delivery TO 'outputs/client_delivery_full.csv' (HEADER, DELIMITER ',')")
    n_full = con.execute("SELECT COUNT(*) FROM final_client_delivery").fetchone()[0]

    # 500-row sample for the repo (deterministic: first 500 by company_number)
    con.execute("""
        COPY (SELECT * FROM final_client_delivery ORDER BY company_number LIMIT 500)
        TO 'data/sample/client_delivery_sample.csv' (HEADER, DELIMITER ',')
    """)

    # Reconciliation report
    con.execute("""
        COPY (
            WITH added AS (
                SELECT cur.company_number FROM companies_current_snapshot cur
                LEFT JOIN companies_previous_snapshot prev ON prev.company_number = cur.company_number
                WHERE prev.company_number IS NULL
            ),
            removed AS (
                SELECT prev.company_number FROM companies_previous_snapshot prev
                LEFT JOIN companies_current_snapshot cur ON cur.company_number = prev.company_number
                WHERE cur.company_number IS NULL
            ),
            status_changed AS (
                SELECT cur.company_number FROM companies_current_snapshot cur
                JOIN companies_previous_snapshot prev ON prev.company_number = cur.company_number
                WHERE prev.company_status != cur.company_status
            )
            SELECT
                (SELECT COUNT(*) FROM companies_previous_snapshot) AS previous_snapshot_count,
                (SELECT COUNT(*) FROM companies_current_snapshot)  AS current_snapshot_count,
                (SELECT COUNT(*) FROM added)                       AS new_records,
                (SELECT COUNT(*) FROM removed)                     AS removed_records,
                (SELECT COUNT(*) FROM status_changed)              AS status_changed_records
        )
        TO 'outputs/reconciliation_report.csv' (HEADER, DELIMITER ',')
    """)

    print(f"\nFull delivery: {n_full} rows -> outputs/client_delivery_full.csv")
    print("Sample (500 rows) -> data/sample/client_delivery_sample.csv")
    print("Reconciliation -> outputs/reconciliation_report.csv")

    con.close()


if __name__ == "__main__":
    main()
