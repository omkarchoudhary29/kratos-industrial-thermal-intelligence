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


def _can_connect_postgres(
    user: str, password: str, host: str, port: int, dbname: str = "postgres", connect_timeout: int = 2
) -> bool:
    """Verify that PostgreSQL accepts credentials on the target host/port and database."""
    try:
        import psycopg2
        conn = psycopg2.connect(
            user=user,
            password=password,
            host=host,
            port=port,
            dbname=dbname,
            connect_timeout=connect_timeout,
        )
        conn.close()
        return True
    except Exception:
        return False


def get_db_uri() -> str:
    app_mode = os.getenv("APP_MODE", "").strip().lower()
    env = os.getenv("ENV", "").strip().lower()
    is_production_like = app_mode in ("production", "demo") or env == "production"

    allow_fallback_env = os.getenv("ALLOW_SQLITE_FALLBACK")
    if allow_fallback_env is not None:
        allow_fallback = allow_fallback_env.strip().lower() in {"1", "true", "yes"}
    else:
        # In production or demonstration mode, never default to SQLite fallback.
        # Fallback is only allowed in local development when unconfigured.
        allow_fallback = not is_production_like

    database_url = os.getenv("DATABASE_URL", "").strip()
    if database_url:
        parsed = urlparse(database_url)
        # If PostgreSQL URL and credentials fail, allow graceful fallback only in dev
        if parsed.scheme in ("postgresql", "postgresql+psycopg2", "postgres"):
            db_target = parsed.path.lstrip("/") or "postgres"
            username = unquote(parsed.username) if parsed.username else "postgres"
            password = unquote(parsed.password) if parsed.password else ""
            host = parsed.hostname or "localhost"
            port = parsed.port or 5432

            if _can_connect_postgres(username, password, host, port, dbname=db_target) or \
               _can_connect_postgres(username, password, host, port, dbname="postgres"):
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
            raise RuntimeError(
                f"PostgreSQL connection failed for DATABASE_URL (host={host}:{port}, db={db_target}, user={username}). "
                f"SQLite fallback is disabled in {app_mode or env or 'production'} mode. "
                "Verify your database credentials and ensure PostgreSQL/PostGIS is running."
            )

    host = os.getenv("DB_HOST", "localhost")
    port = int(os.getenv("DB_PORT", "5432"))
    user = os.getenv("DB_USER", "postgres")
    password = os.getenv("DB_PASSWORD", "password")
    dbname = os.getenv("DB_NAME", "wildfire_db")

    quoted_user = quote_plus(user)
    quoted_pw = quote_plus(password)
    pg_uri = f"postgresql+psycopg2://{quoted_user}:{quoted_pw}@{host}:{port}/{dbname}"

    # If PostgreSQL host is reachable and credentials connect, use Postgres
    if _is_port_open(host, port, timeout=1.0):
        if _can_connect_postgres(user, password, host, port, dbname=dbname) or \
           _can_connect_postgres(user, password, host, port, dbname="postgres"):
            return pg_uri
        if allow_fallback:
            DEFAULT_SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
            sqlite_uri = f"sqlite:///{DEFAULT_SQLITE_PATH.as_posix()}"
            log.warning(
                "PostgreSQL port %d is open, but authentication failed for user '%s'; falling back to SQLite: %s",
                port,
                user,
                sqlite_uri,
            )
            return sqlite_uri
        raise RuntimeError(
            f"PostgreSQL port {port} is reachable at {host}, but authentication failed for user '{user}' "
            f"on database '{dbname}'. SQLite fallback is disabled in {app_mode or env or 'production'} mode."
        )

    # Graceful fallback for local development without local PostgreSQL
    if allow_fallback:
        DEFAULT_SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
        sqlite_uri = f"sqlite:///{DEFAULT_SQLITE_PATH.as_posix()}"
        log.info("PostgreSQL not reachable at %s:%s; using local SQLite: %s", host, port, sqlite_uri)
        return sqlite_uri

    raise RuntimeError(
        f"PostgreSQL server is unreachable at {host}:{port} and SQLite fallback is disabled. "
        "Check network connection and database service status."
    )


def ensure_db():
    """Create the database and enable PostGIS if they don't already exist.

    SQLAlchemy's create_all() can only create tables — not the database itself.
    This function runs before create_all() to guarantee the database exists
    and PostGIS is enabled, so the app can start without manual intervention.
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
        db_name = parsed.path.lstrip("/") or "wildfire_db"
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
            port=int(os.getenv("DB_PORT", "5432")),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", ""),
        )

    # Cloud-first strategy: Connect directly to db_name first.
    # On managed providers (e.g., Railway, Supabase, Neon), the application user
    # does NOT have privileges on or access to the default 'postgres' database.
    try:
        conn = psycopg2.connect(**conn_args, dbname=db_name)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        try:
            cur.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
            log.info("[db] PostGIS extension verified on database '%s'", db_name)
        except Exception as ext_err:
            log.warning("[db] CREATE EXTENSION postgis note: %s", ext_err)
        finally:
            cur.close()
            conn.close()
        return
    except psycopg2.OperationalError as op_err:
        err_msg = str(op_err).lower()
        if "does not exist" not in err_msg:
            log.warning("[db] Direct connect to '%s' note: %s; attempting creation via maintenance DB", db_name, op_err)

    # Step 2: If the database does not exist, connect to 'postgres' maintenance DB to create it
    try:
        conn_maint = psycopg2.connect(**conn_args, dbname="postgres")
        conn_maint.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur_maint = conn_maint.cursor()
        cur_maint.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
        if not cur_maint.fetchone():
            cur_maint.execute(f'CREATE DATABASE "{db_name}"')
            log.info("[db] created database '%s'", db_name)
        cur_maint.close()
        conn_maint.close()

        # Step 3: Now enable PostGIS on the newly created database
        conn_target = psycopg2.connect(**conn_args, dbname=db_name)
        conn_target.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur_target = conn_target.cursor()
        cur_target.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
        log.info("[db] PostGIS extension initialized on '%s'", db_name)
        cur_target.close()
        conn_target.close()
    except Exception as exc:
        log.error("[db] Unable to ensure database '%s': %s", db_name, exc)
        raise


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

