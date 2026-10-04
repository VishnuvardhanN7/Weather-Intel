import asyncio

from sqlalchemy import text

from app.core.database import engine


async def main():
    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                """
                SELECT id, username, email, role
                FROM users
                ORDER BY id
                """
            )
        )

        users = result.fetchall()

        print("\n=== USERS ===")

        if not users:
            print("No users found.")

        for user in users:
            print(
                f"ID: {user.id} | "
                f"Username: {user.username} | "
                f"Email: {user.email} | "
                f"Role: {user.role}"
            )

        print("================\n")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())