# As a Hokie, I will conduct myself with honor and integrity at all times. I will not lie, cheat, or steal, nor will I accept the actions of those who do.
# LLM use: AI coding tools assisted with this file.
"""First-party visit analytics for the portfolio.

No cookies, no IP addresses and no personal data are stored. A visit is a random
id that lives only in the browser tab (sessionStorage) and is gone when it closes.

Storage: Postgres when DATABASE_URL is set (the host's filesystem is wiped on
every deploy, so production needs an outside database); otherwise the local
SQLite file, which is what development and the tests use.
"""
import os
import re
import sqlite3
import statistics
from collections import defaultdict
from datetime import datetime, timedelta, timezone

KINDS = {'view', 'click', 'section', 'leave'}
ID = re.compile(r'^[a-z0-9]{8,24}$')
BOT = re.compile(r'bot|crawl|spider|slurp|headless|preview|monitor|uptime|curl|wget|python-requests', re.I)
SECTIONS = {'intro': 'Intro', 'wallet': 'HokieWallet', 'game': '+1 Speed Catch Animals', 'secret': 'TopSecret', 'os': 'Portfolio'}
COLUMNS = ('ts', 'sid', 'pv', 'kind', 'path', 'label', 'ref', 'country', 'device', 'ms', 'depth')
SCHEMA = """CREATE TABLE IF NOT EXISTS events (
    ts TEXT NOT NULL, sid TEXT NOT NULL, pv TEXT NOT NULL, kind TEXT NOT NULL,
    path TEXT NOT NULL, label TEXT, ref TEXT, country TEXT, device TEXT,
    ms INTEGER, depth INTEGER)"""


class Store:
    def __init__(self, sqlite_path):
        self.url = os.environ.get('DATABASE_URL', '')
        self.sqlite_path = sqlite_path
        self.ready = False

    def _connect(self):
        if self.url:
            import psycopg  # only needed in production
            return psycopg.connect(self.url, connect_timeout=5)
        return sqlite3.connect(self.sqlite_path)

    def _sql(self, text):
        # Queries are written with ? placeholders; Postgres wants %s.
        return text.replace('?', '%s') if self.url else text

    def _run(self, text, parameters=(), fetch=False):
        connection = self._connect()
        try:
            cursor = connection.cursor()
            if not self.ready:
                cursor.execute(SCHEMA)
                cursor.execute('CREATE INDEX IF NOT EXISTS events_ts ON events (ts)')
                self.ready = True
            cursor.execute(self._sql(text), parameters)
            rows = cursor.fetchall() if fetch else None
            connection.commit()
            return rows
        finally:
            connection.close()

    def add(self, event):
        marks = ','.join('?' * len(COLUMNS))
        self._run(f"INSERT INTO events ({','.join(COLUMNS)}) VALUES ({marks})",
                  tuple(event[column] for column in COLUMNS))

    def query(self, text, parameters=()):
        decode = lambda value: value.decode('utf-8', 'replace') if isinstance(value, bytes) else value
        return [tuple(map(decode, row)) for row in self._run(text, parameters, fetch=True)]


def clean(payload, headers):
    """Validate one event from the browser. Returns a row, or None to drop it."""
    if not isinstance(payload, dict) or BOT.search(headers.get('User-Agent', '') or 'bot'):
        return None
    kind, path = payload.get('kind'), payload.get('path')
    sid, pv = payload.get('sid'), payload.get('pv')
    if kind not in KINDS or not isinstance(path, str) or not path.startswith('/'):
        return None
    if not (isinstance(sid, str) and ID.match(sid) and isinstance(pv, str) and ID.match(pv)):
        return None

    def text(key, limit):
        value = payload.get(key)
        return ' '.join(value.split())[:limit] if isinstance(value, str) and value.strip() else None

    def number(key, top):
        value = payload.get(key)
        return max(0, min(top, int(value))) if isinstance(value, (int, float)) and not isinstance(value, bool) else None

    width = number('w', 10000)
    device = None if width is None else 'Phone' if width < 600 else 'Tablet' if width < 1000 else 'Computer'
    country = (headers.get('CF-IPCountry') or '').upper()
    return {
        'ts': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3],
        'sid': sid, 'pv': pv, 'kind': kind, 'path': path.split('?')[0][:200],
        'label': text('label', 80), 'ref': text('ref', 100),
        'country': country if re.fullmatch(r'[A-Z]{2}', country) and country not in ('XX', 'T1') else None,
        'device': device, 'ms': number('ms', 3_600_000), 'depth': number('depth', 100),
    }


# The reports below are plain SQL that runs unchanged on SQLite and Postgres.
# Every visit is ranked with window functions so one pass gives its first page
# (where it came from), its last page (where it left) and how many pages it saw.
VISITS = """WITH ranked AS (
    SELECT sid, path, ref, country, device, substr(ts, 1, 10) AS day,
           ROW_NUMBER() OVER (PARTITION BY sid ORDER BY ts, pv) AS first_rank,
           ROW_NUMBER() OVER (PARTITION BY sid ORDER BY ts DESC, pv DESC) AS last_rank,
           COUNT(*) OVER (PARTITION BY sid) AS pages
    FROM events WHERE kind = 'view' AND ts >= ?)
"""
Q_TOTALS = VISITS + """SELECT COUNT(*), COALESCE(SUM(pages), 0), COALESCE(SUM(CASE WHEN pages = 1 THEN 1 ELSE 0 END), 0)
FROM ranked WHERE first_rank = 1"""
Q_ENTRY = VISITS + """SELECT COALESCE({column}, '{blank}') AS name, COUNT(*) AS visits
FROM ranked WHERE first_rank = 1 GROUP BY 1 ORDER BY 2 DESC, 1 LIMIT {limit}"""
Q_EXITS = VISITS + """SELECT path, COUNT(*) AS visits
FROM ranked WHERE last_rank = 1 GROUP BY 1 ORDER BY 2 DESC, 1 LIMIT 10"""
Q_PAGES = """SELECT path, COUNT(*) AS views FROM events
WHERE kind = 'view' AND ts >= ? GROUP BY path ORDER BY views DESC, path LIMIT 15"""
Q_LABELS = """SELECT label, COUNT(*) AS times FROM events
WHERE kind = ? AND ts >= ? AND label IS NOT NULL GROUP BY label ORDER BY times DESC, label LIMIT 15"""
# A page can report "leave" several times (tab hidden, check-ins, close); keep the longest per page view.
Q_STAYS = """WITH stay AS (
    SELECT pv, MAX(ms) AS ms, MAX(depth) AS depth FROM events
    WHERE kind = 'leave' AND ts >= ? GROUP BY pv)
SELECT v.sid, v.path, stay.ms, stay.depth
FROM events v JOIN stay ON stay.pv = v.pv
WHERE v.kind = 'view' AND v.ts >= ?"""


def summarize(store, start, days):
    """Run the reports and shape them for the stats page."""
    def share(rows):
        total = sum(count for _, count in rows) or 1
        return [{'name': name, 'count': count, 'share': round(100 * count / total)} for name, count in rows]

    def entry(column, blank, limit=10):
        # column and blank come from the fixed calls below, never from a request
        return store.query(Q_ENTRY.format(column=column, blank=blank, limit=limit), (start,))

    # Postgres returns SUM as a Decimal; make all three plain integers
    visits, views, one_page = (int(value) for value in store.query(Q_TOTALS, (start,))[0])
    # Medians are worked out here because SQLite has no median function.
    page_ms, page_depth, visit_ms = defaultdict(list), defaultdict(list), defaultdict(int)
    for sid, path, ms, depth in store.query(Q_STAYS, (start, start)):
        page_ms[path].append(ms or 0)
        page_depth[path].append(depth or 0)
        visit_ms[sid] += ms or 0
    visit_ms = [ms for ms in visit_ms.values() if ms]
    per_day = dict(entry('day', '', limit=400))
    today = datetime.now(timezone.utc).date()
    daily = [{'day': day, 'count': per_day.get(day, 0)}
             for day in ((today - timedelta(days=k)).isoformat() for k in range(days - 1, -1, -1))]
    return {
        'visits': visits, 'views': views,
        'pages_per_visit': round(views / visits, 1) if visits else 0,
        'median_visit': round(statistics.median(visit_ms) / 1000) if visit_ms else None,
        'one_page': round(100 * one_page / visits) if visits else 0,
        'daily': daily, 'daily_max': max([d['count'] for d in daily] + [1]),
        'pages': [{'path': path, 'views': count,
                   'seconds': round(statistics.median(page_ms[path]) / 1000) if page_ms[path] else None,
                   'depth': round(statistics.mean(page_depth[path])) if page_depth[path] else None}
                  for path, count in store.query(Q_PAGES, (start,))],
        'clicks': share(store.query(Q_LABELS, ('click', start))),
        'sections': share([(SECTIONS.get(label, label), count) for label, count in store.query(Q_LABELS, ('section', start))]),
        'exits': share(store.query(Q_EXITS, (start,))),
        'sources': share(entry('ref', 'Direct or unknown')),
        'countries': share(entry('country', 'Unknown')),
        'devices': share(entry('device', 'Unknown')),
    }
