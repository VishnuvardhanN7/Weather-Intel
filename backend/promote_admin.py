import asyncio
import os
import asyncpg


async def main():
    database_url = os.environ["DATABASE_URL"]

    # asyncpg expects postgresql://
    database_url = database_url.replace(
        "postgresql+asyncpg://",
        "postgresql://",
        1,
    )

    conn = await asyncpg.connect(database_url)

    result = await conn.execute(
        """
        UPDATE users
        SET role = 'ADMIN'
        WHERE id = 1
        """
    )

    print("Database update:", result)

    row = await conn.fetchrow(
        """
        SELECT id, username, email, role
        FROM users
        WHERE id = 1
        """
    )

    print(
        f"ID: {row['id']} | "
        f"Username: {row['username']} | "
        f"Email: {row['email']} | "
        f"Role: {row['role']}"
    )

    await conn.close()


if __name__ == "__main__":
    asyncio.run(main())