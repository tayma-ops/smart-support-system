FROM python:3.14-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    && useradd --create-home --uid 10001 supportdesk \
    && mkdir -p /app/media /app/staticfiles \
    && chown -R supportdesk:supportdesk /app
COPY --chown=supportdesk:supportdesk . .
USER supportdesk
EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "60", "--access-logfile", "-", "--access-logformat", "%(m)s %(s)s %(L)s", "--error-logfile", "-"]
