"""
Apache Spark Processing Layer for National Weather Big Data Analytics Platform.

Provides PySpark Structured Streaming processor and fallback stream processor
to consume from weather.raw, run AI Engines 1, 2, and 3, and publish to weather.clean.
"""

from app.spark.weather_stream_processor import (
    WeatherStreamProcessor,
    process_event_with_ai_engines,
    weather_stream_processor,
)

__all__ = [
    "WeatherStreamProcessor",
    "process_event_with_ai_engines",
    "weather_stream_processor",
]
