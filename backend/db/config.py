import os
from typing import Mapping, Optional

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

# Project root directory (two levels up from backend/db/config.py)
_PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)


def _as_bool(value, default=False):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _resolve_ssl_ca(raw_path: Optional[str]) -> Optional[str]:
    """Resolve the ssl_ca path.

    Accepts an absolute path, a path relative to the project root, or None.
    On Streamlit Cloud the working directory is the repo root, so a plain
    filename like ``isrgrootx1.pem`` is resolved correctly.
    """
    if not raw_path:
        return None

    expanded = os.path.expanduser(raw_path)

    # Already absolute and exists → use as-is
    if os.path.isabs(expanded) and os.path.isfile(expanded):
        return expanded

    # Try relative to the project root
    relative = os.path.join(_PROJECT_ROOT, expanded)
    if os.path.isfile(relative):
        return relative

    # Try relative to current working directory (Streamlit Cloud sets cwd = repo root)
    cwd_relative = os.path.join(os.getcwd(), expanded)
    if os.path.isfile(cwd_relative):
        return cwd_relative

    # Fall back to certifi's CA bundle so TLS still works even without the file
    try:
        import certifi
        return certifi.where()
    except ImportError:
        pass

    # Return the raw value; mysql-connector will raise a clear error if it's wrong
    return expanded


def load_mysql_settings(secrets: Optional[Mapping] = None) -> dict:
    """Load MySQL-compatible connection settings from Streamlit secrets or environment."""
    secrets = secrets or {}

    def setting(secret_key, env_key, default=None):
        secret_value = secrets.get(secret_key)
        if secret_value is not None and secret_value != "":
            return secret_value
        return os.getenv(env_key) or default

    database = (
        setting("database", "DB_NAME")
        or setting("oltp_db", "DB_NAME_OLTP")
        or setting("olap_db", "DB_NAME_OLAP")
        or "hr_enterprise_oltp"
    )
    return {
        "host": setting("host", "DB_HOST", "localhost"),
        "port": int(setting("port", "DB_PORT", 3306)),
        "user": setting("user", "DB_USER", "root"),
        "password": setting("password", "DB_PASSWORD", ""),
        "database": database,
        "oltp_db": database,
        "olap_db": database,
        "pool_size": int(setting("pool_size", "DB_POOL_SIZE", 3)),
        "ssl_enabled": _as_bool(setting("ssl_enabled", "DB_SSL_ENABLED"), False),
        "ssl_verify_cert": _as_bool(setting("ssl_verify_cert", "DB_SSL_VERIFY_CERT"), True),
        "ssl_ca": setting("ssl_ca", "DB_SSL_CA"),
    }


def validate_mysql_settings(settings: Mapping) -> None:
    """Reject missing credentials before attempting an accidental localhost connection."""
    missing = [
        key
        for key in ("host", "user", "password", "database")
        if not settings.get(key)
    ]
    if missing:
        names = ", ".join(missing)
        raise RuntimeError(
            f"Database configuration is incomplete (missing: {names}). "
            "Create .streamlit/secrets.toml from .streamlit/secrets.toml.example "
            "or set the corresponding DB_HOST, DB_USER, DB_PASSWORD, and DB_NAME "
            "environment variables."
        )


def mysql_connection_kwargs(database: Optional[str] = None, secrets: Optional[Mapping] = None) -> dict:
    """Build mysql-connector-python arguments, including TiDB TLS options."""
    settings = load_mysql_settings(secrets)
    validate_mysql_settings(settings)
    kwargs = {
        "host": settings["host"],
        "port": settings["port"],
        "user": settings["user"],
        "password": settings["password"],
        "database": database or settings["database"],
        "ssl_disabled": not settings["ssl_enabled"],
    }
    if settings["ssl_enabled"]:
        kwargs["ssl_verify_cert"] = settings["ssl_verify_cert"]
        resolved_ca = _resolve_ssl_ca(settings["ssl_ca"])
        if resolved_ca:
            kwargs["ssl_ca"] = resolved_ca
    return kwargs
