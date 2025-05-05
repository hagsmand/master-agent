# A2A Master Agent

This project implements a master agent that uses the A2A protocol to connect with specialized agents (SQL Writer and RAG) running on localhost. The master agent receives queries from users through a Streamlit interface and routes them to the appropriate specialized agent based on the query content.

## Features

- A2A protocol integration for agent communication
- AG2 framework for agent implementation
- Streamlit-based chat interface
- Intelligent query routing between SQL and RAG agents
- Streaming responses from specialized agents

## Requirements

- Python 3.9 or higher (< 3.14)
- UV package manager (recommended)

## Installation

1. Clone this repository
2. Install dependencies using UV:

```bash
uv pip install -e .
```

Or using pip:

```bash
pip install -e .
```

3. Copy `.env.example` to `.env` and add your OpenAI API key:

```bash
cp .env.example .env
# Edit .env to add your API key
```

## Usage

1. Make sure your specialized agents are running:
   - SQL Writer Agent on `localhost:10001`
   - RAG Agent on `localhost:10002`

2. Start the Streamlit interface:

```bash
streamlit run main.py
```

3. Open your browser at `http://localhost:8501` to interact with the master agent

## Architecture

The system consists of three main components:

1. **Master Agent**: Uses AG2 framework to decide which specialized agent should handle a query
2. **A2A Client**: Implements the A2A protocol for communication with specialized agents
3. **Streamlit Interface**: Provides a user-friendly chat interface

## A2A Protocol

This project implements the [A2A protocol](https://github.com/google/A2A) for agent communication. The protocol enables:

- Agent discovery via agent cards
- Task-based communication
- Streaming responses
- Structured message formats

## Customization

You can customize the agent behavior by:

- Modifying the LLM model in `main.py`
- Adjusting the agent decision logic in `agent.py`
- Changing the specialized agent URLs in `.env`
