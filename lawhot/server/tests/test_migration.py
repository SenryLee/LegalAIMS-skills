"""老库迁移回归：v0.4 建的 items 表缺 last_edition_at，v0.5 必须能平滑补上。

这是部署时最容易炸的地方——CREATE TABLE IF NOT EXISTS 对已存在的表不补列，
而建索引语句若写在补列之前会直接报 no such column，导致 init_db 整体失败、
服务起不来。本测试用真实的 v0.4 表结构验证这两点。
"""

from __future__ import annotations

import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import db  # noqa: E402

# v0.4 形态的 items 表：字段少 last_edition_at
V4_SCHEMA = """
CREATE TABLE items (
  id TEXT PRIMARY KEY, title TEXT NOT NULL, original_title TEXT,
  summary TEXT, source_id TEXT NOT NULL, source_name TEXT NOT NULL,
  original_url TEXT NOT NULL, published_at TEXT, discovered_at TEXT NOT NULL,
  category TEXT, score REAL, selected INTEGER NOT NULL DEFAULT 0,
  track TEXT, lang TEXT, raw_json TEXT, updated_at TEXT NOT NULL
);
INSERT INTO items VALUES
  ('a','标题A',NULL,'摘要A','s1','源1','http://a','2026-10-01',
   '2026-10-01T00:00:00Z','legaltech',88.0,1,'ai_x_law','zh','{}','2026-10-01T00:00:00Z'),
  ('b','标题B',NULL,'摘要B','s2','源2','http://b','2026-10-02',
   '2026-10-02T00:00:00Z','practice',72.0,1,'ai_x_law','zh','{}','2026-10-02T00:00:00Z');
"""


class MigrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp()) / "legacy.db"
        conn = sqlite3.connect(self.tmp)
        conn.executescript(V4_SCHEMA)
        conn.commit()
        conn.close()
        self._orig_db_path = db.DB_PATH
        db.DB_PATH = self.tmp

    def tearDown(self) -> None:
        db.DB_PATH = self._orig_db_path

    def test_adds_missing_column_without_data_loss(self):
        db.init_db()
        with db.connect() as c:
            cols = {r["name"] for r in c.execute("PRAGMA table_info(items)")}
            n = c.execute("SELECT COUNT(*) FROM items").fetchone()[0]
        self.assertIn("last_edition_at", cols)
        self.assertEqual(n, 2, "迁移不得丢数据")

    def test_migration_is_idempotent(self):
        """重复执行 init_db 不应报错也不应改数据——部署重启会多次调用。"""
        db.init_db()
        db.init_db()
        with db.connect() as c:
            n = c.execute("SELECT COUNT(*) FROM items").fetchone()[0]
        self.assertEqual(n, 2)

    def test_select_star_works_after_migration(self):
        """所有查询都用 SELECT *，缺列会直接让接口 500。"""
        db.init_db()
        with db.connect() as c:
            rows = list(c.execute("SELECT * FROM items ORDER BY id"))
        self.assertEqual([r["id"] for r in rows], ["a", "b"])

    def test_mark_edition_published_writes_column(self):
        db.init_db()
        db.mark_edition_published("2026-10-08", ["a"])
        with db.connect() as c:
            row = c.execute("SELECT last_edition_at FROM items WHERE id='a'").fetchone()
        self.assertEqual(row["last_edition_at"], "2026-10-08")


class AppearanceCountTests(unittest.TestCase):
    """出现次数必须以 editions 表为唯一事实来源，不能靠累加计数。"""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp()) / "appear.db"
        self._orig = db.DB_PATH
        db.DB_PATH = self.tmp
        db.init_db()

    def tearDown(self) -> None:
        db.DB_PATH = self._orig

    def test_counts_across_editions(self):
        db.save_edition("2026-10-05", {"item_ids": ["x", "y"]})
        db.save_edition("2026-10-06", {"item_ids": ["x", "z"]})
        counts = db.count_edition_appearances(["x", "y", "z"])
        self.assertEqual(counts, {"x": 2, "y": 1, "z": 1})

    def test_before_excludes_target_date(self):
        """重编当天时，本期自身不应计入历史次数。"""
        db.save_edition("2026-10-05", {"item_ids": ["x"]})
        db.save_edition("2026-10-06", {"item_ids": ["x"]})
        self.assertEqual(db.count_edition_appearances(["x"])["x"], 2)
        self.assertEqual(
            db.count_edition_appearances(["x"], before="2026-10-06")["x"], 1
        )

    def test_recount_is_stable_after_rebuild(self):
        """反复重编同一期不应把次数刷高——这是累加计数方案的固有缺陷。"""
        db.save_edition("2026-10-05", {"item_ids": ["x"]})
        first = db.count_edition_appearances(["x"])["x"]
        db.save_edition("2026-10-05", {"item_ids": ["x"]})
        db.save_edition("2026-10-05", {"item_ids": ["x"]})
        self.assertEqual(db.count_edition_appearances(["x"])["x"], first)

    def test_empty_input(self):
        self.assertEqual(db.count_edition_appearances([]), {})


if __name__ == "__main__":
    unittest.main()