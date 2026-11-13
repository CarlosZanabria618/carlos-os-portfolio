# As a Hokie, I will conduct myself with honor and integrity at all times. I will not lie, cheat, or steal, nor will I accept the actions of those who do.
# LLM use: OpenAI Codex assisted with this file.
import json
import sqlite3
from pathlib import Path


def connect(path):
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    return connection


def initialize(path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with connect(path) as db:
        db.execute("""CREATE TABLE IF NOT EXISTS projects (
            slug TEXT PRIMARY KEY, title TEXT, category TEXT, status TEXT,
            year TEXT, role TEXT, summary TEXT, detail TEXT, stack TEXT,
            url TEXT, link_label TEXT, art TEXT)""")
        source = Path(__file__).resolve().parent.parent / 'data/projects.json'
        columns = ('slug', 'title', 'category', 'status', 'year', 'role',
                   'summary', 'detail', 'stack', 'url', 'link_label', 'art')
        for record in json.loads(source.read_text())['projects']:
            # JSON owns catalog content; refresh edited projects on every startup.
            db.execute("""INSERT INTO projects (
                slug, title, category, status, year, role,
                summary, detail, stack, url, link_label, art
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(slug) DO UPDATE SET
                title = excluded.title,
                category = excluded.category,
                status = excluded.status,
                year = excluded.year,
                role = excluded.role,
                summary = excluded.summary,
                detail = excluded.detail,
                stack = excluded.stack,
                url = excluded.url,
                link_label = excluded.link_label,
                art = excluded.art""", tuple(record[column] for column in columns))
