# The 'reqs' will only run when pyproject.toml is changed, so it acts as
# an efficient way to cache dependencies that won't change between app runs.
FROM python:3.13-slim AS reqs

WORKDIR /app

COPY pyproject.toml pyproject.toml

RUN python -m venv /venv
RUN /venv/bin/python -m pip install -U setuptools
RUN /venv/bin/pip install -q .

FROM reqs
COPY willa willa
COPY README.rst README.rst
COPY CHANGELOG.rst CHANGELOG.rst
RUN /venv/bin/pip install .

ENTRYPOINT ["/venv/bin/python"]
