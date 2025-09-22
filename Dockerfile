# The 'reqs' will only run when pyproject.toml is changed, so it acts as
# an efficient way to cache dependencies that won't change between app runs.
FROM python:3.13-slim AS reqs

WORKDIR /app

RUN apt-get update -y && apt-get upgrade -y \
    && rm -rf /var/lib/apt/lists/

COPY pyproject.toml pyproject.toml

RUN python -m venv /venv
ENV PATH=/venv/bin:$PATH
RUN python -m pip install -U setuptools
RUN pip install -q .

FROM reqs AS app
COPY willa willa
COPY README.rst README.rst
COPY CHANGELOG.rst CHANGELOG.rst
COPY prompt_templates prompt_templates
COPY public public
COPY chainlit.md chainlit.md
COPY .chainlit .chainlit
RUN pip install -e .

ENV VIRTUAL_ENV=/venv
CMD ["chainlit", "run", "/app/willa/web/app.py", "-h", "--host", "0.0.0.0"]

FROM app AS development
COPY tests tests
RUN pip install -q .[dev]
