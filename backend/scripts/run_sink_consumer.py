#!/usr/bin/env python
"""
Standalone Entry Point for Sink Consumer Background Worker (PS-26069).

Continuously consumes verified weather events from Kafka `weather.verified` topic,
filters events with alertness_score > 0.90, and persists them downstream.

Usage (Windows):
  .\\venv\\Scripts\\python.exe scripts\\run_sink_consumer.py
"""

import logging
import os
import sys

# Ensure backend directory is in sys.path when running from scripts/ or backend/
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.services.sink_consumer import sink_consumer


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    sink_consumer.run_worker()


if __name__ == "__main__":
    main()
