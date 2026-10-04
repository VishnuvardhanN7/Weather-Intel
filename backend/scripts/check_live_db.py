#!/usr/bin/env python
"""
Live DB Verification Helper Script.
Prints DB count per source, verification status, and JEV scores.
"""

import asyncio
import os
import sys

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.core.database import async_session_factory
from sqlalchemy import text


async def main():
    async with async_session_factory() as db:
        res = await db.execute(text("SELECT source, count(id) FROM weather_events GROUP BY source;"))
        rows = res.all()
        print("=== DATABASE WEATHER EVENTS BY SOURCE ===")
        for src, cnt in rows:
            print(f"Source: {src:<20} | Count: {cnt}")

        res_status = await db.execute(text("SELECT verification_status, count(id) FROM weather_events GROUP BY verification_status;"))
        print("\n=== DATABASE VERIFICATION STATUS COUNTS ===")
        for st, cnt in res_status.all():
            print(f"Status: {st:<20} | Count: {cnt}")


if __name__ == "__main__":
    asyncio.run(main())
