====================
  README for Willa
====================

:authors: UC Berkeley Library IT
:status: In development
:copyright: © The Regents of the University of California.  MIT license.


Introduction
============

This repository contains the implementation of a proof-of-concept OHC chatbot
prototype.  This prototype is written in Python.



Setup
=====

A local development environment can be set up by running::

    pip install -e '.[dev]'

You will need to set up an ``.env`` file for configuration.  An example is
provided in ``env.example``.  Details of the configuration keys available
follow later in this document.



Linting & Testing locally
==========================
To run the tests, you can use the following command::

    python -m unittest

To run linting::

    python -m pylint willa


Deployment
==========

The chatbot service is deployed via Docker Compose.  You can set up a similar
environment by running::

    docker compose build --pull
    docker compose up -d


Then, create the application's data layer:

    docker compose exec app prisma migrate deploy


Configuration
=============

The following keys are available for configuration in the ``.env`` file:

``TIND_API_KEY``
    The API key to use for connecting to TIND.

``TIND_API_URL``
    The URL to use for connecting to TIND.  Should end in ``/api/v1``.

``DEFAULT_STORAGE_DIR``
    The default directory to store files retrieved from TIND.

``RUN_OLLAMA_TESTS``
    Set to ``true`` to run the Ollama tests.  Should only be set if Ollama is running.

``OLLAMA_URL``
    Set to the instance of Ollama to use for the Web interface.
    Defaults to ``http://localhost:11434``; you may want ``http://ollama:11434`` for Docker runs.

``CHAT_MODEL``
    The model used by the Web interface in Ollama.  Defaults to ``gemma3n:e4b``.

``CHAT_TEMPERATURE``
    Defines the "temperature" (creativeness) of the LLM.  Defaults to ``0.5``.
