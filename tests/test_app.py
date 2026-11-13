# As a Hokie, I will conduct myself with honor and integrity at all times. I will not lie, cheat, or steal, nor will I accept the actions of those who do.
# LLM use: OpenAI Codex assisted with these integration tests.
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMP = tempfile.TemporaryDirectory()
os.environ['PORTFOLIO_DB'] = str(Path(TEMP.name) / 'test.sqlite3')
sys.path.insert(0, str(ROOT / 'code'))
from app import app


class PortfolioTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_linked_pages_and_resume_download(self):
        for route in ['/', '/projects', '/games', '/resume', '/skills']:
            response = self.client.get(route)
            self.assertEqual(response.status_code, 200, route)
            self.assertIn(b'<main id="main"', response.data)
        with self.client.get('/static/Carlos_Zanabria_Resume_Updated.pdf') as download:
            self.assertEqual(download.status_code, 200)

    def test_search_returns_matching_database_record(self):
        text = self.client.get('/projects?q=wallet').get_data(as_text=True)
        self.assertIn('HokieWallet', text)
        self.assertNotIn('merge-a-brainrot.project', text)
        self.assertIn('1 file found', text)

    def test_category_filter_and_combined_search(self):
        text = self.client.get('/projects?category=Games&q=merge').get_data(as_text=True)
        self.assertIn('1 file found', text)
        self.assertIn('Merge a Brainrot', text)
        self.assertIn('1 file found', self.client.get('/games').get_data(as_text=True))

    def test_empty_results_and_escaped_input(self):
        self.assertIn(b'No matching files', self.client.get('/projects?q=not-a-project').data)
        response = self.client.get('/projects', query_string={'q':'<script>alert(1)</script>'})
        self.assertNotIn(b'<script>', response.data)
        self.assertIn(b'&lt;script&gt;', response.data)

    def test_queries_cannot_change_database(self):
        response = self.client.get('/projects', query_string={'q':"'; DROP TABLE projects; --"})
        self.assertEqual(response.status_code, 200)
        with sqlite3.connect(app.config['DATABASE']) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM projects').fetchone()[0], 3)

    def test_details_validation_and_missing_files(self):
        self.assertEqual(self.client.get('/projects/merge-a-brainrot').status_code, 200)
        self.assertEqual(self.client.get('/projects/not-real').status_code, 404)
        self.assertEqual(self.client.get('/missing-page').status_code, 404)
        self.assertEqual(self.client.get('/projects?category=Invalid').status_code, 400)

    def test_rendered_catalog_uses_database_not_hardcoded_html(self):
        with sqlite3.connect(app.config['DATABASE']) as db:
            db.execute("UPDATE projects SET title = ? WHERE slug = ?", ('Database proof title', 'hokiewallet'))
        try:
            self.assertIn(b'Database proof title', self.client.get('/projects/hokiewallet').data)
        finally:
            with sqlite3.connect(app.config['DATABASE']) as db:
                db.execute("UPDATE projects SET title = ? WHERE slug = ?", ('HokieWallet', 'hokiewallet'))

    def test_boot_briefing_loads_only_selected_projects(self):
        response = self.client.get(
            '/boot?launch=1&project=hokiewallet&project=merge-a-brainrot&project=hokiewallet'
        )
        self.assertEqual(response.status_code, 200)
        briefing = response.data.split(b'id="briefing"')[1]
        self.assertIn(b'2 files loaded', briefing)
        self.assertIn(b'Team of four', briefing)
        self.assertIn(b'Roblox Studio', briefing)
        self.assertNotIn(b'Trucking workflow tools', briefing)

    def test_boot_briefing_handles_missing_and_invalid_selection(self):
        self.assertNotIn(b'id="briefing"', self.client.get('/boot').data)
        for path in ('/boot?launch=1', '/boot?launch=1&project=missing'):
            self.assertIn(b'Choose at least one project file', self.client.get(path).data)

    def test_seed_is_idempotent(self):
        from database import initialize
        initialize(app.config['DATABASE'])
        with sqlite3.connect(app.config['DATABASE']) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM projects').fetchone()[0], 3)


if __name__ == '__main__':
    unittest.main(verbosity=2)
