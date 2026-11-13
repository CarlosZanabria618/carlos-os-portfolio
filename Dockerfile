# As a Hokie, I will conduct myself with honor and integrity at all times. I will not lie, cheat, or steal, nor will I accept the actions of those who do.
# LLM use: OpenAI Codex assisted with container setup.
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY code/ code/
COPY data/projects.json data/projects.json
RUN useradd --create-home portfolio && chown -R portfolio:portfolio /app
USER portfolio
EXPOSE 8000
CMD ["sh", "-c", "exec gunicorn --chdir code --bind 0.0.0.0:${PORT:-8000} --workers 1 --threads 4 --access-logfile - app:app"]
