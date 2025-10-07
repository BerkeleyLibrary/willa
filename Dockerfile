# The 'reqs' will only run when pyproject.toml is changed, so it acts as
# an efficient way to cache dependencies that won't change between app runs.
FROM python:3.13-slim AS reqs

WORKDIR /app

RUN apt-get update -y && apt-get upgrade -y \
    && rm -rf /var/lib/apt/lists/

RUN python -m venv /venv
ENV PATH=/venv/bin:$PATH
ENV VIRTUAL_ENV=/venv
RUN python -m pip install -U setuptools

COPY pyproject.toml pyproject.toml

RUN pip install --no-cache-dir -q .[dev]

FROM reqs AS app
COPY willa willa
COPY README.rst README.rst
COPY CHANGELOG.rst CHANGELOG.rst
COPY public public
COPY chainlit.md chainlit.md
COPY .chainlit .chainlit
COPY tests tests
RUN pip install --no-cache-dir -e .

CMD ["chainlit", "run", "/app/willa/web/app.py", "-h", "--host", "0.0.0.0"]
