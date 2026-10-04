import asyncio
from sqlalchemy import text
from app.core.database import engine

async def check():
    async with engine.connect() as conn:
        result = await conn.execute(text("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name
        """))
        print("\n=== NEON TABLES ===")
        for row in result:
            print(row[0])
        print("===================\n")
    await engine.dispose()

asyncio.run(check())
