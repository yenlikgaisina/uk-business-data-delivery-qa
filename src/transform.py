"""
Runs the transformation SQL (02 -> 05) against the ingested raw tables.
This includes the deliberately-broken SIC join and its fix in
sql/04_enrich_industry.sql, printed here so the incident is visible every
time the pipeline runs, not hidden away.

Run from the project root, after src/ingest.py: python3 src/transform.py
"""
import duckdb

DB_PATH = "delivery.duckdb"

STEPS = [
    "sql/02_clean_companies.sql",
    "sql/03_enrich_geography.sql",
    "sql/04_enrich_industry.sql",
    "sql/05_monthly_reconciliation.sql",
]


def strip_sql_comments(sql_text):
    """Removes full-line and trailing '--' comments before statement
    splitting, so a semicolon appearing inside a comment's prose (e.g.
    "one-to-many; the next step...") can't be mistaken for a statement
    boundary."""
    kept_lines = []
    for line in sql_text.splitlines():
        idx = line.find("--")
        kept_lines.append(line[:idx] if idx != -1 else line)
    return "\n".join(kept_lines)


def split_statements(sql_text):
    """Splits on ';' but never inside a single-quoted string literal, so a
    separator like STRING_AGG(x, '; ') can't be mistaken for a statement
    boundary either."""
    stmts, current, in_quote = [], [], False
    i = 0
    while i < len(sql_text):
        ch = sql_text[i]
        if ch == "'":
            in_quote = not in_quote
            current.append(ch)
        elif ch == ";" and not in_quote:
            stmts.append("".join(current))
            current = []
        else:
            current.append(ch)
        i += 1
    if "".join(current).strip():
        stmts.append("".join(current))
    return [s.strip() for s in stmts if s.strip()]


def run_file(con, path):
    with open(path) as f:
        sql_text = f.read()
    code_only = strip_sql_comments(sql_text)
    stmts = split_statements(code_only)
    for stmt in stmts:
        result = con.execute(stmt)
        if stmt.strip().lower().startswith(("select", "with")):
            rows = result.fetchall()
            cols = [d[0] for d in result.description]
            print(f"  -> {len(rows)} row(s) | {', '.join(cols)}")
            for r in rows[:8]:
                print("     ", r)
            if len(rows) > 8:
                print(f"      ... ({len(rows) - 8} more)")


def main():
    con = duckdb.connect(DB_PATH)
    for path in STEPS:
        print(f"\n=== {path} ===")
        run_file(con, path)
    con.close()


if __name__ == "__main__":
    main()
