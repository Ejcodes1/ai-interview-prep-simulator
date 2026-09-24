# WP-09: Deployment & Final Documentation.
# Ships the Flask app so it can be started with a single command for
# grading, per the course portfolio's docker-compose requirement.
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# The container's internal port; docker-compose.yml maps a host port to
# it. Distinct from the host-side default of 5050 in run.py, which only
# exists to dodge macOS's AirPlay Receiver on port 5000 — that conflict
# doesn't apply inside the container.
ENV PORT=5000
EXPOSE 5000

CMD ["python", "run.py"]
