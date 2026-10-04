"""Reset the local experiment database to the deterministic baseline."""

from pathlib import Path

from alembic.config import Config
from sqlalchemy import text

from alembic import command
from app.db.engine import engine
from scripts.seed_db import seed


def reset() -> None:
    """Clear only the configured EvoFitBench database and reseed it."""
    database_name = engine.url.database or ""
    if "evofit" not in database_name.lower():
        raise SystemExit("Refusing reset: DATABASE_URL database name must contain 'evofit'.")
    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))
    root = Path(__file__).resolve().parents[1]
    config = Config(str(root / "alembic.ini"))
    command.upgrade(config, "head")
    seed()
    with engine.connect() as connection:
        users = connection.scalar(text("SELECT count(*) FROM users"))
        tasks = connection.scalar(text("SELECT count(*) FROM tasks"))
    if (users, tasks) != (100, 500):
        raise RuntimeError(f"Seed verification failed: users={users}, tasks={tasks}")
    print(f"Reset complete and ready: users={users}, tasks={tasks}.")


if __name__ == "__main__":
    reset()
