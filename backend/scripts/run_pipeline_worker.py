#!/usr/bin/env python
"""
Standalone Entry Point for Streaming Pipeline Worker (PS-26069).

Runs the full streaming pipeline worker loop:
1. weather.raw -> Spark processing -> AI Engines -> weather.clean
2. weather.clean -> JEV Evaluation (>= 0.60) -> weather.verified
3. weather.verified -> Sink Consumer (> 0.90 alertness score gate) -> PostgreSQL/PostGIS & WebSockets

Usage (Windows):
  .\\venv\\Scripts\\python.exe scripts\\run_pipeline_worker.py
"""

import logging
import os
import sys

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.core.config import settings
from app.services.streaming_pipeline import pipeline_orchestrator


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )

    if not settings.KAFKA_ENABLED:
        logging.warning("KAFKA_ENABLED is False in configuration. Setting KAFKA_ENABLED=True for streaming worker...")
        settings.KAFKA_ENABLED = True
        os.environ["KAFKA_ENABLED"] = "true"

    logging.info("Starting Full End-to-End Pipeline Streaming Worker...")
    pipeline_orchestrator.run_worker(poll_interval=2.0)


if __name__ == "__main__":
    main()
