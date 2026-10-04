import asyncio
import os
import asyncpg


async def main():
    database_url = os.environ["DATABASE_URL"]

    # asyncpg expects postgresql://, not postgresql+asyncpg://
    database_url = database_url.replace(
        "postgresql+asyncpg://",
        "postgresql://",
        1,
    )

    conn = await asyncpg.connect(database_url)

    rows = await conn.fetch(
        """
        SELECT id, username, email, role
        FROM users
        ORDER BY id
        """
    )

    print("\n=== USERS ===")

    if not rows:
        print("No users found.")

    for row in rows:
        print(
            f"ID: {row['id']} | "
            f"Username: {row['username']} | "
            f"Email: {row['email']} | "
            f"Role: {row['role']}"
        )

    print("================")

    await conn.close()


if __name__ == "__main__":
    asyncio.run(main())