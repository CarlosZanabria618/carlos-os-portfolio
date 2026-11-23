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
from collections import Counter, defaultdict
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

    def since(self, start):
        rows = self._run(f"SELECT {','.join(COLUMNS)} FROM events WHERE ts >= ? ORDER BY ts LIMIT 50000",
                         (start,), fetch=True)
        text = lambda value: value.decode('utf-8', 'replace') if isinstance(value, bytes) else value
        return [dict(zip(COLUMNS, map(text, row))) for row in rows]


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
        'ts': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S'),
        'sid': sid, 'pv': pv, 'kind': kind, 'path': path.split('?')[0][:200],
        'label': text('label', 80), 'ref': text('ref', 100),
        'country': country if re.fullmatch(r'[A-Z]{2}', country) and country not in ('XX', 'T1') else None,
        'device': device, 'ms': number('ms', 3_600_000), 'depth': number('depth', 100),
    }


def summarize(rows, days):
    """Turn raw events into the numbers the stats page shows."""
    views = [r for r in rows if r['kind'] == 'view']
    visits = defaultdict(list)
    for r in views:
        visits[r['sid']].append(r)
    # A page view can report "leave" more than once (tab hidden, then closed); keep the longest.
    stay, depth = {}, {}
    for r in rows:
        if r['kind'] == 'leave':
            stay[r['pv']] = max(stay.get(r['pv'], 0), r['ms'] or 0)
            depth[r['pv']] = max(depth.get(r['pv'], 0), r['depth'] or 0)

    pages = defaultdict(lambda: {'views': 0, 'ms': [], 'depth': []})
    for r in views:
        page = pages[r['path']]
        page['views'] += 1
        if r['pv'] in stay:
            page['ms'].append(stay[r['pv']])
            page['depth'].append(depth[r['pv']])
    page_rows = sorted(({'path': path, 'views': p['views'],
                         'seconds': round(statistics.median(p['ms']) / 1000) if p['ms'] else None,
                         'depth': round(statistics.mean(p['depth'])) if p['depth'] else None}
                        for path, p in pages.items()), key=lambda p: -p['views'])

    def top(counter, limit=10):
        total = sum(counter.values()) or 1
        return [{'name': name, 'count': count, 'share': round(100 * count / total)}
                for name, count in counter.most_common(limit)]

    first = {sid: pages_seen[0] for sid, pages_seen in visits.items()}
    today = datetime.now(timezone.utc).date()
    per_day = Counter(v['ts'][:10] for v in first.values())
    daily = [{'day': (today - timedelta(days=k)).isoformat(), 'count': per_day.get((today - timedelta(days=k)).isoformat(), 0)}
             for k in range(days - 1, -1, -1)]
    visit_ms = [sum(stay.get(v['pv'], 0) for v in seen) for seen in visits.values()]
    visit_ms = [ms for ms in visit_ms if ms]
    return {
        'visits': len(visits), 'views': len(views),
        'pages_per_visit': round(len(views) / len(visits), 1) if visits else 0,
        'median_visit': round(statistics.median(visit_ms) / 1000) if visit_ms else None,
        'one_page': round(100 * sum(1 for seen in visits.values() if len(seen) == 1) / len(visits)) if visits else 0,
        'daily': daily, 'daily_max': max([d['count'] for d in daily] + [1]),
        'pages': page_rows[:15],
        'clicks': top(Counter(r['label'] for r in rows if r['kind'] == 'click' and r['label']), 15),
        'sections': top(Counter(SECTIONS.get(r['label'], r['label']) for r in rows if r['kind'] == 'section' and r['label'])),
        'exits': top(Counter(seen[-1]['path'] for seen in visits.values())),
        'sources': top(Counter(v['ref'] or 'Direct or unknown' for v in first.values())),
        'countries': top(Counter(v['country'] or 'Unknown' for v in first.values())),
        'devices': top(Counter(v['device'] or 'Unknown' for v in first.values())),
    }
