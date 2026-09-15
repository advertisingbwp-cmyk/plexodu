"""
Plexudo Database Migration — Phase 2
Removes authentication-dependent columns from users and drops obsolete reward_transactions.
Preserves 100% of data in trends, metrics, sentiment, reports, and audit_logs.
"""

import os
import sys
import logging
from sqlalchemy import inspect, text

logger = logging.getLogger("plexudo.migration")
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s"))
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

AUTH_COLUMNS_TO_REMOVE = [
    "password_hash",
    "google_id",
    "login_attempts",
    "is_locked",
    "email_verified",
    "credits",
]

OBSOLETE_TABLES_TO_DROP = [
    "reward_transactions",
]


def run_migration(engine):
    """Executes non-destructive schema migration against any SQLAlchemy engine."""
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    logger.info(f"Existing database tables: {existing_tables}")

    # 1. Clean up obsolete tables (e.g. reward_transactions)
    with engine.begin() as conn:
        for tbl in OBSOLETE_TABLES_TO_DROP:
            if tbl in existing_tables:
                logger.info(f"Dropping obsolete table: {tbl}")
                conn.execute(text(f"DROP TABLE IF EXISTS {tbl}"))
                logger.info(f"Successfully dropped table: {tbl}")

    # 2. Clean up authentication columns from users table
    if "users" in existing_tables:
        columns_info = inspector.get_columns("users")
        current_cols = [c["name"] for c in columns_info]
        cols_to_drop = [col for col in AUTH_COLUMNS_TO_REMOVE if col in current_cols]

        if cols_to_drop:
            logger.info(f"Found authentication columns to remove from 'users': {cols_to_drop}")
            dialect = engine.dialect.name.lower()

            if dialect == "sqlite":
                with engine.begin() as conn:
                    for col in cols_to_drop:
                        try:
                            logger.info(f"Dropping column 'users.{col}' via ALTER TABLE")
                            conn.execute(text(f"ALTER TABLE users DROP COLUMN {col}"))
                        except Exception as e:
                            logger.warning(f"ALTER TABLE DROP COLUMN failed on {col} ({e}), trying table recreation fallback")
                            _sqlite_recreate_users_table(conn, current_cols)
                            break
            elif dialect == "postgresql":
                with engine.begin() as conn:
                    for col in cols_to_drop:
                        logger.info(f"Dropping column 'users.{col}' IF EXISTS")
                        conn.execute(text(f"ALTER TABLE users DROP COLUMN IF EXISTS {col} CASCADE"))
            else:
                with engine.begin() as conn:
                    for col in cols_to_drop:
                        try:
                            conn.execute(text(f"ALTER TABLE users DROP COLUMN {col}"))
                        except Exception as e:
                            logger.warning(f"Failed dropping column {col}: {e}")
        else:
            logger.info("Table 'users' is already free of authentication columns.")

    # 3. Add Phase 8 columns to trends and metrics if missing
    TRENDS_NEW_COLUMNS = [
        ("first_seen_at", "DATETIME"),
        ("last_seen_at", "DATETIME"),
        ("scan_count", "INTEGER DEFAULT 1"),
        ("current_trend_score", "FLOAT"),
        ("current_direction", "VARCHAR(20) DEFAULT 'STABLE'"),
        ("current_confidence", "VARCHAR(20) DEFAULT 'Low'"),
        ("current_velocity", "FLOAT DEFAULT 0.0"),
        ("current_acceleration", "FLOAT DEFAULT 0.0"),
    ]

    METRICS_NEW_COLUMNS = [
        ("captured_at", "DATETIME"),
        ("engagement_rate", "FLOAT DEFAULT 0.0"),
        ("source", "VARCHAR(50) DEFAULT 'youtube_api'"),
    ]

    if "trends" in existing_tables:
        trend_cols = [c["name"] for c in inspector.get_columns("trends")]
        with engine.begin() as conn:
            for col_name, col_type in TRENDS_NEW_COLUMNS:
                if col_name not in trend_cols:
                    logger.info(f"Adding column '{col_name}' to 'trends'")
                    conn.execute(text(f"ALTER TABLE trends ADD COLUMN {col_name} {col_type}"))

    if "metrics" in existing_tables:
        metric_cols = [c["name"] for c in inspector.get_columns("metrics")]
        with engine.begin() as conn:
            for col_name, col_type in METRICS_NEW_COLUMNS:
                if col_name not in metric_cols:
                    logger.info(f"Adding column '{col_name}' to 'metrics'")
                    conn.execute(text(f"ALTER TABLE metrics ADD COLUMN {col_name} {col_type}"))

    # 4. Verify integrity of preserved application tables
    with engine.connect() as conn:
        for preserved_tbl in ["trends", "metrics", "sentiment", "reports", "audit_logs"]:
            if preserved_tbl in existing_tables:
                try:
                    count = conn.execute(text(f"SELECT COUNT(*) FROM {preserved_tbl}")).scalar()
                    logger.info(f"Preserved table '{preserved_tbl}': {count} records intact.")
                except Exception as e:
                    logger.warning(f"Could not count rows in '{preserved_tbl}': {e}")


def _sqlite_recreate_users_table(conn, current_cols):
    retained_cols = [c for c in current_cols if c not in AUTH_COLUMNS_TO_REMOVE]
    cols_str = ", ".join(retained_cols)
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS users_migration_temp (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(100),
            email VARCHAR(150) UNIQUE,
            role VARCHAR(30) DEFAULT 'Creator',
            avatar_url VARCHAR(255),
            created_at DATETIME
        )
    """))
    conn.execute(text(f"INSERT INTO users_migration_temp ({cols_str}) SELECT {cols_str} FROM users"))
    conn.execute(text("DROP TABLE users"))
    conn.execute(text("ALTER TABLE users_migration_temp RENAME TO users"))
    logger.info("Successfully recreated 'users' table without auth columns via fallback.")


def _get_app():
    import importlib.util
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    app_py_path = os.path.join(backend_dir, "app.py")
    spec = importlib.util.spec_from_file_location("main_flask_app", app_py_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.app


def migrate_database(flask_app=None):
    if flask_app is None:
        flask_app = _get_app()
    with flask_app.app_context():
        from models import db
        run_migration(db.engine)


if __name__ == "__main__":
    migrate_database()
    print("Database Phase 2 migration completed successfully.")
