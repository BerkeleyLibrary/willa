# Project Overview

**Willa** is an experimental retrieval-augmented generation (RAG) chatbot
developed by the Berkeley Library for use in the Oral History Center (OHC).

It is built using Python 3, Langchain, and LangGraph.  The Web frontend is
using the Chainlit framework.

## Directory Structure

* `/willa/chatbot`: Contains the "core" Chatbot implementation and CLI.
* `/willa/config`: Contains the configuration system.
* `/willa/errors`: Contains definitions for Python exception classes.
* `/willa/etl`: Contains the ETL pipeline used for transforming PDFs from
                the Oral History Center into a vector store (LanceDB).
* `/willa/tind`: Contains the source code for interfacing with the TIND
                 API, used by the Library/OHC for storing collections.
* `/willa/web`: Contains the source code for the Chainlit Web UI.

## Libraries and Frameworks

* Langchain and LangGraph for the RAG core, with Langfuse for observation.
* Chainlit for the Web frontend.
* Rich for the command line frontend.
* LanceDB for the vector store.

## Coding Standards

* Use Python's typing system.
* Lines should have a maximum length of 100.
