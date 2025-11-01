from fastapi import Depends
from nvox_common.db.nvox_db_client import NvoxDBClient
from repositories.user_repository import UserRepository
from repositories.session_repository import SessionRepository
from repositories.journey_repository import JourneyRepository
from dependencies.db import get_db_client


def get_user_repository(
    db_client: NvoxDBClient = Depends(get_db_client)
) -> UserRepository:
    return UserRepository(db_client)


def get_session_repository(
    db_client: NvoxDBClient = Depends(get_db_client)
) -> SessionRepository:
    return SessionRepository(db_client)


def get_journey_repository(
    db_client: NvoxDBClient = Depends(get_db_client)
) -> JourneyRepository:
    return JourneyRepository(db_client)
