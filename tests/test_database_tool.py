import pytest

from backend.tools.database import UnsafeQueryError, query_database


def test_query_returns_seeded_companies():
    rows = query_database("SELECT * FROM companies WHERE ticker = 'TSLA'")
    assert len(rows) == 1
    assert rows[0]["name"] == "Tesla, Inc."
    assert rows[0]["shares_outstanding"] > 0


def test_query_rejects_insert():
    with pytest.raises(UnsafeQueryError):
        query_database("INSERT INTO companies VALUES ('X', 'Evil', 1, 1)")


def test_query_rejects_drop_table():
    with pytest.raises(UnsafeQueryError):
        query_database("DROP TABLE companies")


def test_query_rejects_stacked_statements():
    with pytest.raises(UnsafeQueryError):
        query_database("SELECT * FROM companies; DROP TABLE companies;")


def test_query_result_capped_at_fifty_rows():
    rows = query_database("SELECT * FROM companies")
    assert len(rows) <= 50
