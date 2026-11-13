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
        for record in json.loads(source.read_text())['projects']:
            db.execute('INSERT OR IGNORE INTO projects VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
                       tuple(record.values()))
