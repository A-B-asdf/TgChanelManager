import os
import sqlite3
from typing import Dict, List, Optional

from fulfillment_service.core.config import Config


def _column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(row[1] == column for row in rows)


def _add_column_if_missing(conn: sqlite3.Connection, table: str, column: str, ddl: str) -> None:
    if not _column_exists(conn, table, column):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")


def init_db():
    os.makedirs(os.path.dirname(Config.DB_PATH), exist_ok=True)
    with sqlite3.connect(Config.DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id INTEGER NOT NULL UNIQUE,
                tg_channel_id INTEGER,
                tg_access_hash INTEGER,
                title TEXT NOT NULL,
                content_type TEXT NOT NULL DEFAULT 'jokes',
                owner_account_id INTEGER NOT NULL,
                is_booked BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        _add_column_if_missing(conn, "channels", "tg_channel_id", "tg_channel_id INTEGER")
        _add_column_if_missing(conn, "channels", "tg_access_hash", "tg_access_hash INTEGER")
        _add_column_if_missing(conn, "channels", "content_type", "content_type TEXT NOT NULL DEFAULT 'jokes'")
        conn.execute("UPDATE channels SET content_type = 'jokes' WHERE content_type IS NULL OR TRIM(content_type) = ''")
        _add_column_if_missing(conn, "channels", "assigned_account_id", "assigned_account_id INTEGER")
        _add_column_if_missing(conn, "channels", "assigned_username", "assigned_username TEXT")
        _add_column_if_missing(conn, "channels", "assigned_name", "assigned_name TEXT")
        _add_column_if_missing(conn, "channels", "assigned_at", "assigned_at TIMESTAMP")
        _add_column_if_missing(conn, "channels", "invite_link", "invite_link TEXT")
        _add_column_if_missing(conn, "channels", "handoff_status", "handoff_status TEXT DEFAULT 'available'")
        _add_column_if_missing(conn, "channels", "buyer_promoted_at", "buyer_promoted_at TIMESTAMP")
        _add_column_if_missing(conn, "channels", "admin_left_at", "admin_left_at TIMESTAMP")
        _add_column_if_missing(conn, "channels", "handoff_error", "handoff_error TEXT")
        conn.execute(
            """
            UPDATE channels
            SET handoff_status = CASE
                WHEN COALESCE(is_booked, 0) = 0 THEN 'available'
                ELSE COALESCE(handoff_status, 'claimed')
            END
            WHERE handoff_status IS NULL
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS access_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_db_id INTEGER NOT NULL,
                requester_account_id INTEGER NOT NULL,
                requester_username TEXT,
                requester_name TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                invite_link TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(channel_db_id, requester_account_id),
                FOREIGN KEY(channel_db_id) REFERENCES channels(id)
            )
            """
        )


def _dict_rows(rows) -> List[Dict]:
    return [dict(row) for row in rows]


def get_all_channels_db(account_id: Optional[int] = None, only_available: bool = False) -> List[Dict]:
    with sqlite3.connect(Config.DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        sql = "SELECT * FROM channels"
        params = []
        where = []
        if account_id is not None:
            where.append("owner_account_id = ?")
            params.append(account_id)
        if only_available:
            where.append("is_booked = 0")
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY id ASC"
        rows = conn.execute(sql, tuple(params)).fetchall()
        return _dict_rows(rows)


def get_channel_by_id_db(id: int) -> Optional[Dict]:
    with sqlite3.connect(Config.DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM channels WHERE id = ?", (id,)).fetchone()
        return dict(row) if row else None


def get_assigned_channel_for_user_db(account_id: int) -> Optional[Dict]:
    with sqlite3.connect(Config.DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            """
            SELECT * FROM channels
            WHERE assigned_account_id = ? AND is_booked = 1
            ORDER BY assigned_at DESC, id DESC
            LIMIT 1
            """,
            (account_id,),
        ).fetchone()
        return dict(row) if row else None


def filter_channels_db(filters: dict) -> List[Dict]:
    account_id = filters.get("account_id")
    only_available = bool(filters.get("only_available", False))
    content_type = filters.get("content_type") or filters.get("topic")
    channels = get_all_channels_db(account_id=account_id, only_available=only_available)
    if content_type:
        channels = [ch for ch in channels if (ch.get("content_type") or "jokes") == content_type]
    return channels


def book_channel_db(id: int, owner_account_id: Optional[int] = None) -> bool:
    with sqlite3.connect(Config.DB_PATH) as conn:
        if owner_account_id is None:
            cur = conn.execute(
                "UPDATE channels SET is_booked = 1, handoff_status = COALESCE(handoff_status, 'claimed') WHERE id = ? AND is_booked = 0",
                (id,),
            )
        else:
            cur = conn.execute(
                """
                UPDATE channels
                SET is_booked = 1, handoff_status = COALESCE(handoff_status, 'claimed')
                WHERE id = ? AND owner_account_id = ? AND is_booked = 0
                """,
                (id, owner_account_id),
            )
        return cur.rowcount > 0


def release_channel_db(id: int, owner_account_id: Optional[int] = None) -> bool:
    with sqlite3.connect(Config.DB_PATH) as conn:
        params = [id]
        where_owner = ""
        if owner_account_id is not None:
            where_owner = " AND owner_account_id = ?"
            params.append(owner_account_id)
        cur = conn.execute(
            f"""
            UPDATE channels
            SET is_booked = 0,
                assigned_account_id = NULL,
                assigned_username = NULL,
                assigned_name = NULL,
                assigned_at = NULL,
                invite_link = NULL,
                handoff_status = 'available',
                buyer_promoted_at = NULL,
                admin_left_at = NULL,
                handoff_error = NULL
            WHERE id = ?{where_owner}
            """,
            tuple(params),
        )
        return cur.rowcount > 0


def create_channel_record(
    channel_service_id: int,
    tg_channel_id: int,
    title: str,
    owner_account_id: int,
    tg_access_hash: Optional[int] = None,
    content_type: str = "jokes",
):
    with sqlite3.connect(Config.DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO channels (channel_id, tg_channel_id, tg_access_hash, title, content_type, owner_account_id, is_booked, handoff_status)
            VALUES (?, ?, ?, ?, ?, ?, 0, 'available')
            """,
            (channel_service_id, tg_channel_id, tg_access_hash, title, content_type, owner_account_id),
        )


def update_channel_owner_db(id: int, new_owner_id: int):
    with sqlite3.connect(Config.DB_PATH) as conn:
        conn.execute(
            """
            UPDATE channels
            SET owner_account_id = ?,
                is_booked = 0,
                assigned_account_id = NULL,
                assigned_username = NULL,
                assigned_name = NULL,
                assigned_at = NULL,
                invite_link = NULL,
                handoff_status = 'available',
                buyer_promoted_at = NULL,
                admin_left_at = NULL,
                handoff_error = NULL
            WHERE id = ?
            """,
            (new_owner_id, id),
        )


def reserve_next_available_channel_db(
    requester_account_id: int,
    requester_username: Optional[str] = None,
    requester_name: Optional[str] = None,
) -> Optional[Dict]:
    conn = sqlite3.connect(Config.DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        conn.isolation_level = None
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            """
            SELECT * FROM channels
            WHERE is_booked = 0
            ORDER BY id ASC
            LIMIT 1
            """
        ).fetchone()
        if not row:
            conn.execute("ROLLBACK")
            return None
        channel_id = int(row["id"])
        conn.execute(
            """
            UPDATE channels
            SET is_booked = 1,
                assigned_account_id = ?,
                assigned_username = ?,
                assigned_name = ?,
                assigned_at = CURRENT_TIMESTAMP,
                handoff_status = 'claimed',
                handoff_error = NULL
            WHERE id = ? AND is_booked = 0
            """,
            (requester_account_id, requester_username, requester_name, channel_id),
        )
        updated = conn.execute("SELECT * FROM channels WHERE id = ?", (channel_id,)).fetchone()
        conn.execute("COMMIT")
        return dict(updated)
    except Exception:
        try:
            conn.execute("ROLLBACK")
        except Exception:
            pass
        raise
    finally:
        conn.close()


def set_channel_invite_link_db(id: int, invite_link: str) -> Optional[Dict]:
    with sqlite3.connect(Config.DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("UPDATE channels SET invite_link = ? WHERE id = ?", (invite_link, id))
        row = conn.execute("SELECT * FROM channels WHERE id = ?", (id,)).fetchone()
        return dict(row) if row else None


def update_channel_handoff_db(
    id: int,
    status: str,
    buyer_promoted: bool = False,
    admin_left: bool = False,
    error: Optional[str] = None,
) -> Optional[Dict]:
    with sqlite3.connect(Config.DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute(
            """
            UPDATE channels
            SET handoff_status = ?,
                buyer_promoted_at = CASE WHEN ? THEN CURRENT_TIMESTAMP ELSE buyer_promoted_at END,
                admin_left_at = CASE WHEN ? THEN CURRENT_TIMESTAMP ELSE admin_left_at END,
                handoff_error = ?
            WHERE id = ?
            """,
            (status, 1 if buyer_promoted else 0, 1 if admin_left else 0, error, id),
        )
        row = conn.execute("SELECT * FROM channels WHERE id = ?", (id,)).fetchone()
        return dict(row) if row else None


def delete_channel_db(id: int, owner_account_id: Optional[int] = None) -> Optional[Dict]:
    """Delete channel metadata from fulfillment DB and related access requests.

    Returns the deleted channel row, or None if channel does not exist / does not belong to admin.
    """
    conn = sqlite3.connect(Config.DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        conn.isolation_level = None
        conn.execute("BEGIN IMMEDIATE")
        params = [id]
        owner_clause = ""
        if owner_account_id is not None:
            owner_clause = " AND owner_account_id = ?"
            params.append(owner_account_id)
        row = conn.execute(f"SELECT * FROM channels WHERE id = ?{owner_clause}", tuple(params)).fetchone()
        if not row:
            conn.execute("ROLLBACK")
            return None
        deleted = dict(row)
        conn.execute("DELETE FROM access_requests WHERE channel_db_id = ?", (id,))
        conn.execute(f"DELETE FROM channels WHERE id = ?{owner_clause}", tuple(params))
        conn.execute("COMMIT")
        return deleted
    except Exception:
        try:
            conn.execute("ROLLBACK")
        except Exception:
            pass
        raise
    finally:
        conn.close()


def create_or_get_access_request_db(
    channel_db_id: int,
    requester_account_id: int,
    requester_username: Optional[str] = None,
    requester_name: Optional[str] = None,
) -> Dict:
    with sqlite3.connect(Config.DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        existing = conn.execute(
            """
            SELECT ar.*, c.title AS channel_title, c.channel_id AS channel_id
            FROM access_requests ar
            JOIN channels c ON c.id = ar.channel_db_id
            WHERE ar.channel_db_id = ? AND ar.requester_account_id = ?
            """,
            (channel_db_id, requester_account_id),
        ).fetchone()
        if existing:
            data = dict(existing)
            if data["status"] == "pending":
                data["status_alias"] = "pending_existing"
            else:
                data["status_alias"] = data["status"]
            return data

        cur = conn.execute(
            """
            INSERT INTO access_requests (channel_db_id, requester_account_id, requester_username, requester_name)
            VALUES (?, ?, ?, ?)
            """,
            (channel_db_id, requester_account_id, requester_username, requester_name),
        )
        request_id = cur.lastrowid
        row = conn.execute(
            """
            SELECT ar.*, c.title AS channel_title, c.channel_id AS channel_id
            FROM access_requests ar
            JOIN channels c ON c.id = ar.channel_db_id
            WHERE ar.id = ?
            """,
            (request_id,),
        ).fetchone()
        data = dict(row)
        data["status_alias"] = "pending"
        return data


def list_access_requests_db(status: Optional[str] = None, requester_account_id: Optional[int] = None) -> List[Dict]:
    with sqlite3.connect(Config.DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        sql = """
            SELECT ar.*, c.title AS channel_title, c.id AS channel_db_id, c.channel_id AS channel_id
            FROM access_requests ar
            JOIN channels c ON c.id = ar.channel_db_id
        """
        where = []
        params = []
        if status:
            where.append("ar.status = ?")
            params.append(status)
        if requester_account_id is not None:
            where.append("ar.requester_account_id = ?")
            params.append(requester_account_id)
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY ar.id DESC"
        rows = conn.execute(sql, tuple(params)).fetchall()
        return _dict_rows(rows)


def get_access_request_db(request_id: int) -> Optional[Dict]:
    with sqlite3.connect(Config.DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            """
            SELECT ar.*, c.title AS channel_title, c.id AS channel_db_id, c.channel_id AS channel_id,
                   c.owner_account_id AS owner_account_id
            FROM access_requests ar
            JOIN channels c ON c.id = ar.channel_db_id
            WHERE ar.id = ?
            """,
            (request_id,),
        ).fetchone()
        return dict(row) if row else None


def update_access_request_status_db(request_id: int, status: str, invite_link: Optional[str] = None) -> Optional[Dict]:
    with sqlite3.connect(Config.DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute(
            """
            UPDATE access_requests
            SET status = ?, invite_link = COALESCE(?, invite_link), updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (status, invite_link, request_id),
        )
        row = conn.execute(
            """
            SELECT ar.*, c.title AS channel_title, c.id AS channel_db_id, c.channel_id AS channel_id
            FROM access_requests ar
            JOIN channels c ON c.id = ar.channel_db_id
            WHERE ar.id = ?
            """,
            (request_id,),
        ).fetchone()
        return dict(row) if row else None


init_db()
