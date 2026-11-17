# As a Hokie, I will conduct myself with honor and integrity at all times. I will not lie, cheat, or steal, nor will I accept the actions of those who do.
# LLM use: AI coding tools assisted with this file.
import os
from pathlib import Path
from flask import Flask, abort, render_template, request
from database import connect, initialize

ROOT = Path(__file__).resolve().parent.parent
app = Flask(__name__)
app.config['DATABASE'] = os.environ.get('PORTFOLIO_DB', str(ROOT / 'data/portfolio.sqlite3'))
initialize(app.config['DATABASE'])


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
        return db.execute(sql + ' ORDER BY rowid', parameters).fetchall()


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


@app.errorhandler(404)
def not_found(error):
    return render_template('error.html', active='', title='File not found'), 404


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
