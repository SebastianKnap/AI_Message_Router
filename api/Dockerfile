FROM python:3.13-slim

# Run as a non-root user: the container has no reason to hold root privileges.
RUN useradd --create-home --uid 1000 appuser

WORKDIR /app

# Copied separately from the source so dependency layers stay cached between builds.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
