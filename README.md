# Carlos Zanabria's portfolio

Live at https://carlos-os-portfolio.onrender.com

A Flask and SQLite portfolio for Carlos Zanabria, a computer science student at Virginia Tech. The home page presents four projects as short chapters that play on their own. Each chapter uses a different front-end technique, written by hand in plain HTML, CSS and JavaScript with no framework or animation library.

## What's on the home page

- **Intro:** a headline split into letters that animate in and react to the pointer.
- **HokieWallet:** a clip-path circle reveal, then real screens from the app on a timed player.
- **+1 Speed Catch Animals:** play-test captures, then a 24-frame turntable of a 3D model drawn to a canvas. Drag to spin it.
- **TopSecret:** a CRT-style power-on and a text-scramble effect.
- **This site:** a horizontal track of windows driven by one clock.

Each chapter has pause, replay and per-part controls. Click anywhere to skip a part, or use the arrow keys to jump between projects. The page works without JavaScript and respects the reduced-motion setting.

## Behind it

- Searchable SQLite project catalog with category filters and a page per project.
- A compare page that puts selected projects side by side at a bookmarkable address.
- Parameterized queries and escaped output, covered by tests.
- Docker image deployed on Render, redeployed on every push.

## Run locally

Requires Python 3.12 or Docker.

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
gunicorn --chdir code --bind 127.0.0.1:8000 app:app
```

Open http://localhost:8000.

```sh
docker build -t carlos-os-portfolio .
docker run --rm -p 8000:8000 carlos-os-portfolio
```

## Test

```sh
python -m unittest discover -s tests -v
```

The suite covers navigation, the PDF download, search and filtering, escaped input, SQL safety, database-driven pages, project briefings, and database initialization and source-catalog updates.

## Deploy on Render

Create a Docker Web Service from this repository. The Dockerfile binds Gunicorn to `0.0.0.0:$PORT`, with port 8000 as the local default. Use `/` as the HTTP health check.

The read-only catalog is initialized from `data/projects.json` at startup. It needs no external database or persistent disk; a replaced SQLite file is safely recreated. Set `PORTFOLIO_DB` only to override the database location. Render's Free instance may take time to wake after inactivity.

## Project background and assistance

Originally developed for a Virginia Tech CS 2104 class project and deployed on the university's Discovery environment. This repository is a separate public copy for portfolio hosting.

Carlos supplied the concept, visual direction, personal background, project information, and resume. AI coding tools assisted with implementation, tests, documentation, and deployment preparation. Original attribution comments are retained. Project status labels distinguish prototypes, planned work, and upcoming releases.

Class reports, recordings, credentials, runtime databases, and the old address-bearing resume are excluded from this public copy.
