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



Deployment
==========

The chatbot service is deployed via Docker Compose.  You can set up a similar
environment by running::

    docker compose build --pull
    docker compose up -d



Configuration
=============

The following keys are available for configuration in the ``.env`` file:

``TIND_API_KEY``
    The API key to use for connecting to TIND.

``TIND_API_URL``
    The URL to use for connecting to TIND.  Should end in ``/api/v1``.

``DEFAULT_STORAGE_DIR``
    The default directory to store files retrieved from TIND.
