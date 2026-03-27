# LLM Safety Benchmarking Pipeline

## Overview
This project provides an automated pipeline for evaluating Large Language Models (LLMs) 
against safety benchmarks, including HarmBench and WMDP (Weapons of Mass Destruction Proxy). 
It is containerized using Docker and integrates the ELK stack for result visualization.

## Tech Stack
- Python 3.x
- Docker & Docker Compose
- ELK Stack (Elasticsearch, Logstash, Kibana)
- React (Benchmark Dashboard)
- GitHub Actions (CI/CD)

## Project Structure
- `benchmark.py` — runs HarmBench evaluations
- `benchmark_wmdp.py` — runs WMDP evaluations
- `runner.py` — orchestrates benchmark execution
- `cli.py` — command line interface
- `elk.py` — ELK stack integration
- `BenchmarkDashboard.jsx` — React visualization dashboard
- `docker-compose.yml` — container orchestration
- `questions.json` — benchmark question dataset

## Getting Started
1. Clone the repo:
   git clone https://github.com/Michel-png-crypto/docker.git

2. Configure your environment:
   cp token.env .env
   # Add your API keys to .env

3. Start the stack:
   docker-compose up

4. Run benchmarks:
   python cli.py --benchmark harmbench

5. View results in Kibana:
   http://localhost:5601

## CI/CD
GitHub Actions automatically runs benchmarks on every push via `harmbench-ci.yml`.

## Requirements
See `requirements.txt` for Python dependencies.
