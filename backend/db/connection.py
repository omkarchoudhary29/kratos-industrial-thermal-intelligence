import logging
import os
import socket
from datetime import date
from pathlib import Path
from urllib.parse import quote_plus, unquote, urlparse

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
log = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_SQLITE_PATH = BASE_DIR.parent / "data" / "thermal_intelligence.db"


def _is_port_open(host: str, port: int, timeout: float = 1.0) -> bool:
    """Quick check whether a TCP port is accepting connections."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (OSError, socket.error):
        return False


def _can_connect_postgres(user: str, password: str, host: str, port: int, dbname: str = "postgres") -> bool:
    """Verify that PostgreSQL accepts credentials on the target host/port."""
    try:
        import psycopg2
        conn = psycopg2.connect(
            user=user,
            password=password,
            host=host,
            port=port,
            dbname=dbname,
            connect_timeout=1,
        )
        conn.close()
        return True
    except Exception:
        return False


def get_db_uri() -> str:
    allow_fallback = os.getenv("ALLOW_SQLITE_FALLBACK", "1").strip().lower() in {"1", "true", "yes"}

    database_url = os.getenv("DATABASE_URL", "").strip()
    if database_url:
        parsed = urlparse(database_url)
        # If PostgreSQL URL and credentials fail, allow graceful fallback
        if parsed.scheme in ("postgresql", "postgresql+psycopg2", "postgres"):
            if _can_connect_postgres(
                user=unquote(parsed.username) if parsed.username else "postgres",
                password=unquote(parsed.password) if parsed.password else "",
                host=parsed.hostname or "localhost",
                port=parsed.port or 5432,
                dbname="postgres",
            ):
                if database_url.startswith("postgresql://"):
                    return database_url.replace("postgresql://", "postgresql+psycopg2://", 1)
                if database_url.startswith("postgres://"):
                    return database_url.replace("postgres://", "postgresql+psycopg2://", 1)
                return database_url
            if allow_fallback:
                DEFAULT_SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
                sqlite_uri = f"sqlite:///{DEFAULT_SQLITE_PATH.as_posix()}"
                log.warning(
                    "DATABASE_URL PostgreSQL credentials failed to authenticate; falling back to SQLite: %s",
                    sqlite_uri,
                )
                return sqlite_uri

    host = os.getenv("DB_HOST", "localhost")
    port = int(os.getenv("DB_PORT", "5432"))
    user = os.getenv("DB_USER", "postgres")
    password = os.getenv("DB_PASSWORD", "password")
    dbname = os.getenv("DB_NAME", "wildfire_db")

    quoted_pw = quote_plus(password)
    # If PostgreSQL host is reachable and credentials connect, use Postgres
    if _is_port_open(host, port, timeout=0.8):
        if _can_connect_postgres(user, password, host, port, dbname="postgres"):
            return f"postgresql+psycopg2://{user}:{quoted_pw}@{host}:{port}/{dbname}"
        if allow_fallback:
            DEFAULT_SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
            sqlite_uri = f"sqlite:///{DEFAULT_SQLITE_PATH.as_posix()}"
            log.warning(
                "PostgreSQL port 5432 is open, but authentication failed for user '%s'; falling back to SQLite: %s",
                user,
                sqlite_uri,
            )
            return sqlite_uri

    # Graceful fallback for local development without local PostgreSQL
    if allow_fallback:
        DEFAULT_SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
        sqlite_uri = f"sqlite:///{DEFAULT_SQLITE_PATH.as_posix()}"
        log.info("PostgreSQL not reachable at %s:%s; using local SQLite: %s", host, port, sqlite_uri)
        return sqlite_uri

    return f"postgresql+psycopg2://{user}:{quoted_pw}@{host}:{port}/{dbname}"


def ensure_db():
    """Create the database and enable PostGIS if they don't already exist.

    SQLAlchemy's create_all() can only create tables — not the database itself.
    This function runs before create_all() to guarantee the database exists
    and PostGIS is enabled, so the app can start without any manual setup.
    """
    db_uri = get_db_uri()
    if db_uri.startswith("sqlite"):
        # SQLite creates the file automatically on connect
        parsed = urlparse(db_uri)
        sqlite_path = Path(parsed.path.lstrip("/") if os.name == "nt" and ":" in parsed.path else parsed.path)
        sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        return

    import psycopg2
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

    database_url = os.getenv("DATABASE_URL", "").strip()
    if database_url:
        parsed = urlparse(database_url)
        db_name = parsed.path.lstrip("/")
        conn_args = dict(
            host=parsed.hostname or "localhost",
            port=parsed.port or 5432,
            user=unquote(parsed.username) if parsed.username else "postgres",
            password=unquote(parsed.password) if parsed.password else "",
        )
    else:
        db_name = os.getenv("DB_NAME", "wildfire_db")
        conn_args = dict(
            host=os.getenv("DB_HOST", "localhost"),
            port=os.getenv("DB_PORT", "5432"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", ""),
        )

    # Step 1: connect to the default 'postgres' DB to create our database
    conn = psycopg2.connect(**conn_args, dbname="postgres")
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
    if not cur.fetchone():
        cur.execute(f'CREATE DATABASE "{db_name}"')
        print(f"[db] created database '{db_name}'")
    cur.close()
    conn.close()

    # Step 2: connect to our database and enable the PostGIS extension
    conn2 = psycopg2.connect(**conn_args, dbname=db_name)
    conn2.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur2 = conn2.cursor()
    cur2.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    cur2.close()
    conn2.close()


def seed_db():
    """Insert configured demo events and synchronize their replay windows.

    Safe to call on every startup. Other fields on existing events are preserved.

    An admin credential account is created once when ADMIN_PASSWORD is set.
    """
    from db.models import FireEvent, User
    from geoalchemy2 import WKTElement

    admin_password = os.getenv("ADMIN_PASSWORD", "")
    admin_username = os.getenv("ADMIN_USERNAME", "admin").strip().lower()
    admin_email = os.getenv("ADMIN_EMAIL", "admin@enterprise.com").strip().lower()
    if admin_password:
        admin = User.query.filter(
            (User.username == admin_username) | (User.email == admin_email)
        ).first()
        if not admin:
            admin = User(username=admin_username, email=admin_email, is_admin=True)
            admin.set_password(admin_password)
            db.session.add(admin)
            db.session.commit()
            print(f"[db] seeded admin account '{admin_username}' ({admin_email})")
        else:
            updated = False
            if not admin.is_admin:
                admin.is_admin = True
                updated = True
            if admin_email and (not admin.email or admin.email != admin_email):
                admin.email = admin_email
                updated = True
            if updated:
                db.session.commit()
                print(f"[db] synchronized admin attributes for '{admin.username}' ({admin_email})")

    from pipeline.event_config import EVENT_CONFIGS

    added = []
    updated = []
    for config in EVENT_CONFIGS:
        existing = db.session.get(FireEvent, config.event_id)
        if existing is None:
            existing = FireEvent.query.filter_by(name=config.name).first()
        if existing is not None:
            configured_start = date.fromisoformat(config.start_date)
            configured_end = date.fromisoformat(config.end_date)
            # A successful live thermal refresh advances the replay window.
            # Preserve that progress across restarts instead of resetting the
            # event to the original demonstration end date.
            synchronized_end = configured_end
            if (
                config.analysis_mode == "thermal_monitoring"
                and existing.end_date is not None
                and existing.end_date > configured_end
            ):
                synchronized_end = existing.end_date
            configured_bbox = WKTElement(config.bbox_wkt, srid=4326)
            changed = (
                existing.name != config.name
                or existing.year != config.year
                or existing.start_date != configured_start
                or existing.end_date != synchronized_end
                or existing.description != config.description
            )
            existing.name = config.name
            existing.year = config.year
            existing.bbox = configured_bbox
            existing.start_date = configured_start
            existing.end_date = synchronized_end
            existing.description = config.description
            if changed:
                existing.replay_ms = None
                updated.append(config.name)
            continue
        if db.session.get(FireEvent, config.event_id) is not None:
            print(
                f"[db] cannot seed configured event {config.event_id} ({config.name}): "
                "that id is already in use"
            )
            continue
        event = FireEvent(
            id=config.event_id,
            name=config.name,
            year=config.year,
            bbox=WKTElement(config.bbox_wkt, srid=4326),
            start_date=date.fromisoformat(config.start_date) if isinstance(config.start_date, str) else config.start_date,
            end_date=date.fromisoformat(config.end_date) if isinstance(config.end_date, str) else config.end_date,
            description=config.description,
        )
        db.session.add(event)
        added.append(config.name)

    if added:
        if db.engine.dialect.name == "postgresql":
            from sqlalchemy import text
            db.session.flush()
            db.session.execute(text(
                "SELECT setval(pg_get_serial_sequence('fire_events', 'id'), "
                "MAX(id), true) FROM fire_events"
            ))
        print(f"[db] seeded {len(added)} fire event(s): {', '.join(added)}")

    if added or updated:
        db.session.commit()
    if updated:
        print(f"[db] synchronized {len(updated)} configured event(s): {', '.join(updated)}")

