FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml .
COPY src src
COPY migrations migrations
COPY scripts scripts
RUN pip install --no-cache-dir '.[azure]'
RUN useradd --create-home --uid 10001 appuser && chown -R appuser:appuser /app
USER appuser
EXPOSE 8000
CMD ["uvicorn","focus_cost.main:app","--host","0.0.0.0","--port","8000"]
