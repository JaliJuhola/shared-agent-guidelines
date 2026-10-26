FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    SKILLS_DIR=/skills HOST=0.0.0.0 PORT=3333
WORKDIR /app
COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir . && useradd --system --no-create-home app
USER app
EXPOSE 3333
HEALTHCHECK --interval=30s --timeout=3s \
  CMD python -c "import urllib.request,sys; urllib.request.urlopen('http://127.0.0.1:3333/health', timeout=2)" || exit 1
CMD ["agent-guidelines-server"]
