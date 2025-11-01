from fastapi import Depends
from nvox_common.db.nvox_db_client import NvoxDBClient
from repositories.user_repository import UserRepository
from dependencies.db import get_db_client


def get_user_repository(
    db_client: NvoxDBClient = Depends(get_db_client)
) -> UserRepository:

    return UserRepository(db_client)
