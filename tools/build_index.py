"""Migration and rebuild script for SQLite question index."""

import argparse
import sys
from pathlib import Path
from loguru import logger

# Add src to path if needed
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from qnbk import DEFAULT_QUESTIONS_DIR
from qnbk.question_index import get_db_path, rebuild_index


def main() -> None:
    parser = argparse.ArgumentParser(description="Build or rebuild SQLite question index.")
    parser.add_argument(
        "--questions-dir",
        "-d",
        type=str,
        default=str(DEFAULT_QUESTIONS_DIR),
        help="Path to questions directory (default: questions_output)",
    )
    parser.add_argument(
        "--db-path",
        type=str,
        default=None,
        help="Optional custom path for SQLite database file",
    )
    args = parser.parse_args()

    qdir = Path(args.questions_dir)
    if not qdir.exists():
        logger.error(f"Questions directory '{qdir}' does not exist.")
        sys.exit(1)

    db_path = Path(args.db_path) if args.db_path else get_db_path(qdir)
    logger.info(f"Indexing questions from {qdir} into {db_path}...")

    count = rebuild_index(qdir, db_path)
    logger.info(f"Successfully indexed {count} questions.")


if __name__ == "__main__":
    main()
