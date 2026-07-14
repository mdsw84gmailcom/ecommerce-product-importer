from dataclasses import dataclass
from pathlib import Path

import duckdb


@dataclass
class CsvProfile:
    """Summary of a CSV dataset."""

    file_name: str
    row_count: int
    column_names: list[str]
    duplicate_rows: int


def profile_csv(file_path: Path) -> CsvProfile:
    """Analyze the basic structure and quality of a CSV file."""
    if not file_path.exists():
        raise FileNotFoundError(f"CSV file not found: {file_path}")

    if file_path.suffix.lower() != ".csv":
        raise ValueError("The profiling input must be a CSV file.")

    connection = duckdb.connect(database=":memory:")

    try:
        file_name = str(file_path).replace("\\", "/").replace("'", "''")

        connection.execute(f"""
            CREATE TEMPORARY TABLE source_data AS
            SELECT *
            FROM read_csv_auto(
                '{file_name}',
                header = true,
                all_varcher = true
            )
            """)

        row_count = connection.execute("SELECT COUNT(*) FROM source_data").fetchone()[0]

        column_names = [
            row[1]
            for row in connection.execute("PRAGMA table_info('source_data')").fetchall()
        ]

        duplicate_rows = connection.execute("""
            SELECT COALESCE(SUM(row_count - 1), 0)
            FROM (
                SELECT COUNT(*) AS row_count
                FROM source_data
                GROUP BY ALL
                HAVING COUNT(*) > 1
            )
            """).fetchone()[0]

        return CsvProfile(
            file_name=file_path.name,
            row_count=row_count,
            column_names=column_names,
            duplicate_rows=duplicate_rows,
        )
    finally:
        connection.close()
