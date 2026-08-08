import subprocess
import sys


def test_initial_migration_seeds_default_user_account_and_admin() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head", "--sql"],
        check=True,
        capture_output=True,
        text=True,
    )

    sql = result.stdout

    assert sql.count("INSERT INTO users") == 2
    assert "INSERT INTO accounts" in sql
    assert "user@example.com" in sql
    assert "admin@example.com" in sql
    assert "FALSE" in sql.upper()
    assert "TRUE" in sql.upper()
