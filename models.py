# -*- coding: utf-8 -*-
"""校园微心愿交换平台 - 数据库模型"""

import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "campus_wishes.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            avatar TEXT DEFAULT '',
            credit_score INTEGER DEFAULT 100,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS wishes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            category TEXT DEFAULT '其他',
            wish_image TEXT DEFAULT '',
            status TEXT DEFAULT 'pending'
                CHECK(status IN ('pending','claimed','fulfilled','completed','cancelled')),
            created_at TEXT DEFAULT (datetime('now','localtime')),
            updated_at TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS claims (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            wish_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            status TEXT DEFAULT 'active'
                CHECK(status IN ('active','fulfilled','completed','cancelled')),
            created_at TEXT DEFAULT (datetime('now','localtime')),
            updated_at TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (wish_id) REFERENCES wishes(id),
            FOREIGN KEY (user_id) REFERENCES users(id),
            UNIQUE(wish_id, user_id)
        );

        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            wish_id INTEGER NOT NULL,
            claim_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            content TEXT DEFAULT '',
            image TEXT DEFAULT '',
            rating INTEGER DEFAULT 5 CHECK(rating >= 1 AND rating <= 5),
            created_at TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (wish_id) REFERENCES wishes(id),
            FOREIGN KEY (claim_id) REFERENCES claims(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    """)

    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print("数据库初始化完成")
