from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
from app.core.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False, pool_size=20, max_overflow=10)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    from app.models import User, Company, Machine, Metric, AlertRule, AlertEvent
    from app.models import WindowsService, SoftwareInventory, EventLog
    from app.core.security import hash_password

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        result = await session.execute(
            text("SELECT COUNT(*) FROM users")
        )
        count = result.scalar()
        if count == 0:
            admin = User(
                email="admin@numbers10.co.za",
                hashed_password=hash_password("admin123"),
                is_active=True,
            )
            session.add(admin)
            await session.commit()
