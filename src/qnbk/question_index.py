"""SQLite-based question index for fast metadata queries.

The .md files remain the canonical source of truth.
This index is a read-optimised cache of their metadata, enabling instant filtering
and pagination without scanning the filesystem on every interaction.
"""

import json
import sqlite3
from pathlib import Path
from typing import Any

from loguru import logger

from qnbk import DEFAULT_QUESTIONS_DIR
from qnbk.utils import read_question_file


def get_db_path(qdir: Path | str | None = None) -> Path:
    """Return the SQLite database path for the specified questions directory."""
    return (Path(qdir) if qdir else DEFAULT_QUESTIONS_DIR) / "questions_index.db"


def get_connection(db_path: Path | str) -> sqlite3.Connection:
    """Create a SQLite connection with WAL mode and row factory enabled."""
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    return conn


def init_db(db_path: Path | str) -> None:
    """Initialize the questions schema and indices if they do not exist."""
    conn = get_connection(db_path)
    try:
        with conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS questions (
                    relpath TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    full_path TEXT NOT NULL,
                    class TEXT,
                    topic TEXT,
                    difficulty TEXT,
                    answer TEXT,
                    prev_year TEXT,
                    source TEXT,
                    last_used TEXT,
                    question_text TEXT,
                    body TEXT,
                    solution TEXT,
                    options_json TEXT,
                    has_options INTEGER DEFAULT 0,
                    updated_at TEXT DEFAULT (datetime('now'))
                );
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_class ON questions(class);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_topic ON questions(topic);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_difficulty ON questions(difficulty);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_last_used ON questions(last_used);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_has_options ON questions(has_options);")
    finally:
        conn.close()


def row_to_question_dict(row: sqlite3.Row) -> dict[str, Any]:
    """Convert a database row into standard question dictionary format."""
    options = {}
    if row["options_json"]:
        try:
            options = json.loads(row["options_json"])
        except Exception:
            options = {}

    meta = {
        "class": row["class"] or "Unknown",
        "topic": row["topic"] or "Uncategorized",
        "difficulty": row["difficulty"] or "Unknown",
        "answer": row["answer"] if row["answer"] is not None else "",
        "prev_year": row["prev_year"] or "",
        "source": row["source"] or "",
        "last_used": row["last_used"] or "",
    }

    return {
        "path": row["full_path"],
        "meta": meta,
        "body": row["body"] or "",
        "solution": row["solution"] or "",
        "question_text": row["question_text"] or "",
        "options": options,
        "filename": row["filename"],
        "relpath": row["relpath"],
    }


def upsert_question(
    qdict: dict[str, Any],
    file_path: Path | str,
    qdir: Path | str,
    db_path: Path | str | None = None,
) -> None:
    """Insert or update a single question record in the SQLite index."""
    qdir_path = Path(qdir)
    full_path = Path(file_path).resolve()
    try:
        relpath = str(full_path.relative_to(qdir_path.resolve()))
    except ValueError:
        relpath = str(full_path.name)

    target_db = get_db_path(qdir_path) if db_path is None else Path(db_path)
    init_db(target_db)

    meta = qdict.get("meta", {}) or qdict.get("metadata", {})
    body = qdict.get("body", "")
    if isinstance(body, dict):
        q_text = body.get("question", "")
        options = body.get("options", {}) or {}
        solution = body.get("solution", "") or ""
        body_text = q_text
    else:
        q_text = qdict.get("question_text", "")
        options = qdict.get("options", {}) or {}
        solution = qdict.get("solution", "") or ""
        body_text = body

    has_options = 1 if any(bool(v and str(v).strip()) for v in options.values()) else 0
    options_json = json.dumps(options)

    conn = get_connection(target_db)
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO questions (
                    relpath, filename, full_path, class, topic, difficulty,
                    answer, prev_year, source, last_used, question_text,
                    body, solution, options_json, has_options, updated_at
                ) VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now')
                )
                ON CONFLICT(relpath) DO UPDATE SET
                    filename = excluded.filename,
                    full_path = excluded.full_path,
                    class = excluded.class,
                    topic = excluded.topic,
                    difficulty = excluded.difficulty,
                    answer = excluded.answer,
                    prev_year = excluded.prev_year,
                    source = excluded.source,
                    last_used = excluded.last_used,
                    question_text = excluded.question_text,
                    body = excluded.body,
                    solution = excluded.solution,
                    options_json = excluded.options_json,
                    has_options = excluded.has_options,
                    updated_at = datetime('now');
                """,
                (
                    relpath,
                    full_path.name,
                    str(full_path),
                    meta.get("class", ""),
                    meta.get("topic", ""),
                    meta.get("difficulty", ""),
                    str(meta.get("answer", "")) if meta.get("answer") is not None else "",
                    str(meta.get("prev_year", "")) if meta.get("prev_year") is not None else "",
                    str(meta.get("source", "")) if meta.get("source") is not None else "",
                    str(meta.get("last_used", "")) if meta.get("last_used") is not None else "",
                    q_text,
                    body_text,
                    solution,
                    options_json,
                    has_options,
                ),
            )
    except Exception as e:
        logger.error(f"Failed to upsert question {relpath} to index: {e}")
    finally:
        conn.close()


def delete_question(
    file_path: Path | str,
    qdir: Path | str,
    db_path: Path | str | None = None,
) -> None:
    """Delete a question record from the index."""
    qdir_path = Path(qdir)
    full_path = Path(file_path).resolve()
    try:
        relpath = str(full_path.relative_to(qdir_path.resolve()))
    except ValueError:
        relpath = str(full_path.name)

    target_db = get_db_path(qdir_path) if db_path is None else Path(db_path)
    if not target_db.exists():
        return

    conn = get_connection(target_db)
    try:
        with conn:
            conn.execute("DELETE FROM questions WHERE relpath = ?", (relpath,))
    except Exception as e:
        logger.error(f"Failed to delete {relpath} from index: {e}")
    finally:
        conn.close()


def rebuild_index(qdir: Path | str, db_path: Path | str | None = None) -> int:
    """Rebuild SQLite index from all .md question files in the given directory."""
    qdir_path = Path(qdir)
    target_db = get_db_path(qdir_path) if db_path is None else Path(db_path)

    init_db(target_db)

    files = sorted(qdir_path.rglob("*.md"))
    rows = []
    for f in files:
        if f.name.startswith("."):
            continue
        try:
            q = read_question_file(f, qdir_path)
            meta = q.get("meta", {})
            options = q.get("options", {}) or {}
            has_options = 1 if any(bool(v and str(v).strip()) for v in options.values()) else 0

            rows.append(
                (
                    q.get("relpath", str(f.name)),
                    f.name,
                    str(f.resolve()),
                    meta.get("class", ""),
                    meta.get("topic", ""),
                    meta.get("difficulty", ""),
                    str(meta.get("answer", "")) if meta.get("answer") is not None else "",
                    str(meta.get("prev_year", "")) if meta.get("prev_year") is not None else "",
                    str(meta.get("source", "")) if meta.get("source") is not None else "",
                    str(meta.get("last_used", "")) if meta.get("last_used") is not None else "",
                    q.get("question_text", ""),
                    q.get("body", ""),
                    q.get("solution", ""),
                    json.dumps(options),
                    has_options,
                )
            )
        except Exception as e:
            logger.warning(f"Skipping file {f} due to parse error: {e}")

    conn = get_connection(target_db)
    try:
        with conn:
            conn.execute("DELETE FROM questions;")
            conn.executemany(
                """
                INSERT INTO questions (
                    relpath, filename, full_path, class, topic, difficulty,
                    answer, prev_year, source, last_used, question_text,
                    body, solution, options_json, has_options, updated_at
                ) VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now')
                );
                """,
                rows,
            )
    finally:
        conn.close()

    logger.info(f"Rebuilt index for {qdir_path} with {len(rows)} questions at {target_db}.")
    return len(rows)


def load_indexed_questions(
    qdir: Path | str,
    db_path: Path | str | None = None,
    force_rebuild: bool = False,
) -> list[dict[str, Any]]:
    """Load all questions from the SQLite index, rebuilding if missing or empty."""
    qdir_path = Path(qdir)
    target_db = get_db_path(qdir_path) if db_path is None else Path(db_path)

    if force_rebuild or not target_db.exists():
        rebuild_index(qdir_path, target_db)

    conn = get_connection(target_db)
    try:
        rows = conn.execute("SELECT * FROM questions ORDER BY relpath ASC;").fetchall()
        if not rows and not force_rebuild:
            rebuild_index(qdir_path, target_db)
            rows = conn.execute("SELECT * FROM questions ORDER BY relpath ASC;").fetchall()
        return [row_to_question_dict(r) for r in rows]
    finally:
        conn.close()


def generate_next_id_indexed(
    directory: Path | str,
    qdir: Path | str | None = None,
    db_path: Path | str | None = None,
) -> str:
    """Generate the next 5-digit question ID for a given directory."""
    target_dir = Path(directory)
    existing_ids = []

    if target_dir.exists():
        for file in target_dir.glob("q_*.md"):
            try:
                num_part = file.stem.split("_")[1]
                existing_ids.append(int(num_part))
            except (IndexError, ValueError):
                continue

    new_id_num = max(existing_ids) + 1 if existing_ids else 1
    return f"{new_id_num:05d}"
