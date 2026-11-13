# Carlos OS Portfolio

A personal portfolio for Carlos Zanabria, a Virginia Tech computer science student. The interface uses a restrained pearl-and-graphite palette, scroll-linked project illustrations, and a clear overview of projects, skills, experience, and a downloadable resume.

## Features

- Searchable SQLite project catalog, category filters, and individual project pages.
- Portfolio Boot Menu: choose multiple projects and generate a bookmarkable briefing.
- Responsive navigation, keyboard-accessible controls, reduced-motion support, and native page transitions where supported.
- Scroll-linked visual depth and progressive section reveals; content remains available without JavaScript.
- Current education, experience, skills, GitHub link, and an updated resume PDF.

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

Carlos supplied the concept, visual direction, personal background, project information, and resume. OpenAI Codex assisted with design, implementation, tests, documentation, and deployment preparation. Original attribution comments are retained. Preview illustrations are CSS artwork; project status labels distinguish prototypes, planned work, and upcoming releases.

Class reports, recordings, credentials, runtime databases, and the old address-bearing resume are excluded from this public copy.
