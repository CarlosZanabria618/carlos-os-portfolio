# As a Hokie, I will conduct myself with honor and integrity at all times. I will not lie, cheat, or steal, nor will I accept the actions of those who do.
# LLM use: AI coding tools assisted with this file.
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from flask import Flask, Response, abort, g, render_template, request, url_for
import analytics
from database import connect, initialize

ROOT = Path(__file__).resolve().parent.parent
app = Flask(__name__)
app.config['DATABASE'] = os.environ.get('PORTFOLIO_DB', str(ROOT / 'data/portfolio.sqlite3'))
initialize(app.config['DATABASE'])
app.config['MAX_CONTENT_LENGTH'] = 64 * 1024
events = analytics.Store(app.config['DATABASE'])


@app.context_processor
def csp_nonce():
    # One random value per request; only inline scripts carrying it may run.
    g.nonce = secrets.token_urlsafe(16)
    return {'csp_nonce': g.nonce}


@app.after_request
def harden(response):
    nonce = g.get('nonce', '')
    script = f"'self' 'nonce-{nonce}'" if nonce else "'self'"
    response.headers.setdefault('Content-Security-Policy',
        f"default-src 'self'; script-src {script}; style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
        "connect-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'")
    response.headers.setdefault('X-Content-Type-Options', 'nosniff')
    response.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
    response.headers.setdefault('Permissions-Policy', 'camera=(), microphone=(), geolocation=()')
    response.headers.setdefault('Strict-Transport-Security', 'max-age=31536000')
    if request.path.startswith('/static/') and response.status_code == 200:
        # Versioned files (?v=) never change, so browsers may keep them. The résumé PDF is always re-checked.
        if request.args.get('v'):
            response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
        elif request.path.endswith('.pdf'):
            response.headers['Cache-Control'] = 'no-cache'
        else:
            response.headers['Cache-Control'] = 'public, max-age=86400'
    return response


@app.get('/robots.txt')
def robots():
    lines = ['User-agent: *', 'Disallow: /stats', 'Disallow: /t', f"Sitemap: {url_for('sitemap', _external=True, _scheme='https')}"]
    return Response('\n'.join(lines) + '\n', mimetype='text/plain')


@app.get('/sitemap.xml')
def sitemap():
    paths = ['/', '/projects', '/resume', '/skills'] + [f"/projects/{item['slug']}" for item in projects()]
    host = url_for('home', _external=True, _scheme='https').rstrip('/')
    body = ''.join(f'<url><loc>{host}{path}</loc></url>' for path in paths)
    return Response(f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{body}</urlset>',
                    mimetype='application/xml')


@app.template_filter('blocks')
def blocks(text):
    # Blank lines split a case study into paragraphs; lines starting with "- " form a list of steps.
    parsed = []
    for chunk in (text or '').split('\n\n'):
        lines = [line.strip() for line in chunk.strip().splitlines() if line.strip()]
        if lines and all(line.startswith('- ') for line in lines):
            steps = [tuple(part.strip() for part in line[2:].split(' | ', 2)) for line in lines]
            parsed.append(('steps', [step for step in steps if len(step) == 3]))
        elif lines:
            parsed.append(('text', ' '.join(lines)))
    return parsed


def projects(category='', query=''):
    # Parameters keep user-supplied search text out of SQL syntax.
    sql = 'SELECT * FROM projects WHERE 1=1'
    parameters = []
    if category:
        sql += ' AND category = ?'
        parameters.append(category)
    if query:
        sql += ' AND (instr(lower(title), lower(?)) > 0 OR instr(lower(summary), lower(?)) > 0 OR instr(lower(stack), lower(?)) > 0)'
        parameters.extend([query] * 3)
    with connect(app.config['DATABASE']) as db:
        # Strongest work first; anything new falls in after, in insert order.
        order = " ORDER BY CASE slug WHEN 'hokiewallet' THEN 1 WHEN 'plus1-speed-catch-animals' THEN 2 WHEN 'topsecret' THEN 3 WHEN 'carlos-os-portfolio' THEN 4 WHEN 'merge-a-brainrot' THEN 5 WHEN 'trucking-tools' THEN 6 ELSE 7 END, rowid"
        return db.execute(sql + order, parameters).fetchall()


@app.route('/')
def home():
    return render_template('home.html', active='home', title='Software & thoughtful interfaces', items=projects())


@app.get('/boot')
def boot():
    # Keep selections in the URL so a project briefing can be bookmarked.
    selected = set(request.args.getlist('project'))
    catalog = projects()
    briefing = [item for item in catalog if item['slug'] in selected]
    return render_template('boot.html', title='Your project briefing', catalog=catalog,
                           briefing=briefing, requested='launch' in request.args)


@app.route('/projects')
def project_list():
    query = request.args.get('q', '').strip()[:100]
    category = request.args.get('category', '')
    if category not in ('', 'Software', 'Games'):
        abort(400)
    return render_template('projects.html', active='projects', title='Projects',
                           items=projects(category, query), query=query, category=category)


@app.route('/games')
def games():
    return render_template('projects.html', active='games', title='Games',
                           items=projects('Games'), query='', category='Games')


@app.route('/projects/<slug>')
def project_detail(slug):
    with connect(app.config['DATABASE']) as db:
        item = db.execute('SELECT * FROM projects WHERE slug = ?', (slug,)).fetchone()
    if item is None:
        abort(404)
    return render_template('detail.html', active='projects', title=item['title'], item=item)


@app.route('/resume')
def resume():
    return render_template('resume.html', active='resume', title='Resume')


@app.route('/skills')
def skills():
    return render_template('skills.html', active='skills', title='Skills & toolbox')


@app.post('/t')
def track():
    # Visit analytics: validated, stored without cookies or IP addresses. Always answers 204
    # so a storage problem can never break a page for a visitor.
    origin = request.headers.get('Origin')
    if origin and origin.split('://')[-1] != request.host:
        return '', 204
    event = analytics.clean(request.get_json(force=True, silent=True), request.headers)
    if event:
        try:
            events.add(event)
        except Exception:
            app.logger.exception('analytics write failed')
    return '', 204


@app.get('/stats')
def stats():
    # Private page. The password comes from the STATS_KEY setting; without it the page does not exist.
    key = os.environ.get('STATS_KEY', '')
    if not key:
        abort(404)
    given = request.authorization.password if request.authorization else ''
    if not hmac.compare_digest((given or '').encode(), key.encode()):
        return Response('Sign in to see site stats.', 401, {'WWW-Authenticate': 'Basic realm="Site stats"'})
    days = request.args.get('days', default=30, type=int)
    days = days if days in (7, 30, 90) else 30
    start = (datetime.now(timezone.utc) - timedelta(days=days)).strftime('%Y-%m-%dT%H:%M:%S')
    response = app.make_response(render_template('stats.html', active='', title='Site stats', days=days,
                                                 s=analytics.summarize(events.since(start), days)))
    response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Robots-Tag'] = 'noindex'
    return response


@app.errorhandler(404)
def not_found(error):
    return render_template('error.html', active='', title='File not found'), 404


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
