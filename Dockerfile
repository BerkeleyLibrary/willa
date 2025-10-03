# The 'reqs' will only run when pyproject.toml is changed, so it acts as
# an efficient way to cache dependencies that won't change between app runs.
FROM python:3.13-slim AS reqs

WORKDIR /app

RUN apt-get update -y && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
        nodejs \
        npm \
        openssl && \
    rm -rf /var/lib/apt/lists/

COPY pyproject.toml pyproject.toml

RUN python -m venv /venv
ENV PATH=/venv/bin:$PATH
RUN python -m pip install -U setuptools
RUN pip install -q .

FROM reqs AS prisma
COPY package*.json ./
RUN npm install

FROM reqs AS app
COPY willa willa
COPY pyproject.toml pyproject.toml
RUN pip install -e .
COPY README.rst README.rst
COPY CHANGELOG.rst CHANGELOG.rst
COPY prisma prisma
COPY public public
COPY chainlit.md chainlit.md
COPY .chainlit .chainlit
COPY --from=prisma /app/node_modules node_modules

ENV VIRTUAL_ENV=/venv
CMD ["chainlit", "run", "/app/willa/web/app.py", "-h", "--host", "0.0.0.0"]

FROM app AS development
COPY tests tests
RUN pip install -q .[dev]
