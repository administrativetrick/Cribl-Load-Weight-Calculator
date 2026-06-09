# Build from the repo root so the skill's calculation module is in context:
#   docker build -f webapp/Dockerfile -t cribl-weight-calculator .
FROM python:3.12-alpine

WORKDIR /app

# Single source of truth: the web app imports the same module the Agent Skill runs
COPY skill/cribl-weight-load-calculator/scripts/cribl_weights.py .
COPY webapp/app.py webapp/index.html ./

RUN adduser -D -H appuser
USER appuser

ENV PORT=8080
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s \
  CMD python -c "import urllib.request,os; urllib.request.urlopen(f'http://127.0.0.1:{os.environ[\"PORT\"]}/healthz', timeout=2)"

CMD ["python", "app.py"]
