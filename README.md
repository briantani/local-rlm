# local-rlm

A local implementation of the **Recursive Language Model (RLM)** agent, inspired by the research from MIT CSAIL.

**Paper:** [Recursive Language Models (arXiv:2512.24601v1)](https://arxiv.org/html/2512.24601v1)

## Overview

This project aims to replicate the core architecture of an RLM, which solves complex problems by recursively generating, executing, and refining Python code in a stateful environment. Unlike traditional Chain-of-Thought (CoT) approaches, an RLM can offload computational tasks to a REPL and manage its own context window more effectively.

## Key Features

- **Recursive Problem Solving:** Decomposes tasks into sub-problems solved via code generation.
- **Stateful Python Sandbox:** A secure, persistent REPL for executing generated code.
- **Modern Stack:** Built with **Python 3.14.2 (Free-Threaded)** and **DSPy**.
- **Local & Cloud Support:** Configurable to run with local models (Ollama) or cloud providers (Gemini).

## Getting Started

See [AGILE_PLAN.md](AGILE_PLAN.md) for the development roadmap and current status.
