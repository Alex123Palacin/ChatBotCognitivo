FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
COPY requirements.txt requirements-production.txt ./
RUN python -m pip install -r requirements-production.txt \
    && groupadd --gid 10001 app \
    && useradd --uid 10001 --gid app --no-create-home app \
    && mkdir -p /data /app/staticfiles \
    && chown -R app:app /app /data

COPY --chown=app:app principal/ /app/
COPY --chown=app:app docker/entrypoint.sh gunicorn.conf.py /app/

USER app
EXPOSE 8000
ENTRYPOINT ["sh", "/app/entrypoint.sh"]
CMD ["gunicorn", "--config", "/app/gunicorn.conf.py", "principal.wsgi:application"]
