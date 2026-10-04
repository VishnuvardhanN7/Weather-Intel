import asyncio

from sqlalchemy import text
from app.core.database import engine


async def main():
    async with engine.connect() as conn:
        result = await conn.execute(
            text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'weather_events'
                ORDER BY ordinal_position
            """)
        )

        print("weather_events columns:")
        for row in result:
            print(f" - {row[0]}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())