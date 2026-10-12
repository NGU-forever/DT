from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from .config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)

class Base(DeclarativeBase):
    pass

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


# 时序表新增列 -> DDL 片段。SQLite 的 CREATE TABLE IF NOT EXISTS 不会为已存在的表补列，
# 因此这里做一次幂等的轻量迁移，保证老库（本次改动之前生成的 substation.db）也能平滑升级。
_TELEMETRY_COLUMN_MIGRATIONS = [
    ("trans1_hot_spot", "FLOAT"),
    ("trans2_oil_temp", "FLOAT"),
    ("trans2_hot_spot", "FLOAT"),
    ("gis201_current", "FLOAT"),
    ("station_load_rate", "FLOAT"),
    ("shed_mva", "FLOAT"),
]


async def init_schema() -> list:
    """建表 + 幂等补列，返回本次实际新增的列名（便于启动日志说明）。"""
    added = []
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        rows = (await conn.exec_driver_sql("PRAGMA table_info(telemetry_records)")).fetchall()
        existing = {row[1] for row in rows}
        for column, ddl_type in _TELEMETRY_COLUMN_MIGRATIONS:
            if column not in existing:
                await conn.exec_driver_sql(
                    f"ALTER TABLE telemetry_records ADD COLUMN {column} {ddl_type}"
                )
                added.append(column)
    return added
