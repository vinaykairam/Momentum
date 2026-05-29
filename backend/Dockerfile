FROM python:3.11-slim

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app
COPY backend/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

ENV PYTHONPATH=/app
ENV DATABASE_URL=sqlite:////data/momentum.db

EXPOSE 8000

ENTRYPOINT ["/docker-entrypoint.sh"]
