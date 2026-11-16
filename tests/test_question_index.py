"""Unittest for the SQLite question index module."""

import json
import tempfile
import unittest
from pathlib import Path

from qnbk.question_index import (
    delete_question,
    generate_next_id_indexed,
    get_connection,
    get_db_path,
    init_db,
    load_indexed_questions,
    rebuild_index,
    upsert_question,
)
from qnbk.utils import write_md_file


class TestQuestionIndex(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.qdir = Path(self.temp_dir.name) / "questions"
        self.qdir.mkdir()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_question_index_lifecycle(self):
        # 1. Create mock question file
        topic_dir = self.qdir / "Class-XII" / "Organic"
        topic_dir.mkdir(parents=True)
        qfile = topic_dir / "q_00001.md"

        qdict = {
            "metadata": {
                "topic": "Organic",
                "class": "XII",
                "difficulty": "Easy",
                "answer": "A",
                "prev_year": "2023",
                "source": "NCERT",
                "last_used": "2024-01-01",
            },
            "body": {
                "question": "What is ethanol?",
                "options": {"A": "C2H5OH", "B": "CH3OH", "C": "C3H7OH", "D": "C4H9OH"},
                "solution": "Ethanol is ethyl alcohol.",
            },
        }
        write_md_file(qdict, str(qfile))

        # 2. Rebuild index
        db_path = get_db_path(self.qdir)
        count = rebuild_index(self.qdir, db_path)
        self.assertEqual(count, 1)
        self.assertTrue(db_path.exists())

        # 3. Load questions
        qs = load_indexed_questions(self.qdir, db_path)
        self.assertEqual(len(qs), 1)
        q = qs[0]
        self.assertEqual(q["meta"]["class"], "XII")
        self.assertEqual(q["meta"]["topic"], "Organic")
        self.assertEqual(q["meta"]["difficulty"], "Easy")
        self.assertEqual(q["meta"]["answer"], "A")
        self.assertEqual(q["options"]["A"], "C2H5OH")
        self.assertIn("Ethanol is ethyl alcohol.", q["solution"])

        # 4. Upsert an updated version
        qdict["metadata"]["difficulty"] = "Hard"
        upsert_question(qdict, str(qfile), self.qdir, db_path)

        qs_updated = load_indexed_questions(self.qdir, db_path)
        self.assertEqual(len(qs_updated), 1)
        self.assertEqual(qs_updated[0]["meta"]["difficulty"], "Hard")

        # 5. Add a second question via upsert
        qfile2 = topic_dir / "q_00002.md"
        qdict2 = {
            "meta": {
                "topic": "Organic",
                "class": "XII",
                "difficulty": "Medium",
                "answer": "B",
            },
            "question_text": "What is methanol?",
            "options": {"A": "C2H5OH", "B": "CH3OH"},
            "solution": "Methanol is wood alcohol.",
            "body": "What is methanol?",
        }
        upsert_question(qdict2, str(qfile2), self.qdir, db_path)

        qs_2 = load_indexed_questions(self.qdir, db_path)
        self.assertEqual(len(qs_2), 2)

        # 6. Delete question
        delete_question(str(qfile2), self.qdir, db_path)
        qs_after_del = load_indexed_questions(self.qdir, db_path)
        self.assertEqual(len(qs_after_del), 1)

        # 7. Next ID generation
        next_id = generate_next_id_indexed(topic_dir, self.qdir, db_path)
        self.assertEqual(next_id, "00002")


if __name__ == "__main__":
    unittest.main()
