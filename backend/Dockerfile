FROM python:3.11.11-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.lock requirements.lock
RUN pip install --no-cache-dir -r requirements.lock && useradd --uid 10001 --create-home studio && mkdir /data && chown studio:studio /data
COPY --chown=studio:studio . .
USER studio
CMD ["uvicorn", "app.api:app", "--host", "0.0.0.0", "--port", "8000"]
