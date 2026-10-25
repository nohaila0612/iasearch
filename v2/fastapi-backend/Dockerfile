FROM ghcr.io/astral-sh/uv:python3.12-trixie

WORKDIR /app

ENV UV_PYTHON_DOWNLOADS=never
ENV UV_PYTHON=python3.12

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY . .

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]