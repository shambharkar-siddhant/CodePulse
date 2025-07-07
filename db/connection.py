import os
import asyncpg


_pool: asyncpg.Pool = None


async def init_db_pool():
    global _pool
    _pool = await asyncpg.create_pool(
        host=os.getenv("PG_HOST", ""),
        port=int(os.getenv("PG_PORT", 0)),
        user=os.getenv("PG_USER", "siddhant"),
        password=os.getenv("PG_PASSWORD", ""),
        database=os.getenv("PG_DATABASE", ""),
        min_size=1,
        max_size=10,
    )


def get_db_pool() -> asyncpg.Pool:
    if not _pool:
        raise RuntimeError("DB pool not initialized")
    return _pool
