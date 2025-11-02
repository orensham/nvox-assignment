from typing import Type
import logging

from pydantic import BaseModel, ValidationError
from nvox_common.db.nvox_db_client import NvoxDBClient

from .db_models import (
    UserDB,
    SessionDB,
    UserJourneyStateDB,
    UserAnswerDB,
    StageTransitionDB,
    UserJourneyPathDB,
)

logger = logging.getLogger(__name__)


class SchemaValidationError(Exception):
    pass


async def validate_table_schema(
    db_client: NvoxDBClient,
    table_name: str,
    model_class: Type[BaseModel]
) -> None:
    try:

        row = await db_client.fetchRow(f"SELECT * FROM {table_name} LIMIT 1")

        if row is not None:

            try:
                model_class(**dict(row))
                logger.info(f"✓ Schema validation passed for table '{table_name}'")
            except ValidationError as e:
                error_msg = f"Schema mismatch for table '{table_name}': {e}"
                logger.error(error_msg)
                raise SchemaValidationError(error_msg) from e
        else:

            logger.warning(
                f"⚠ Table '{table_name}' is empty, skipping validation. "
                f"Schema will be validated when first row is inserted."
            )

    except Exception as e:
        if isinstance(e, SchemaValidationError):
            raise

        error_msg = f"Error validating schema for table '{table_name}': {e}"
        logger.error(error_msg)
        raise SchemaValidationError(error_msg) from e


async def validate_all_schemas(db_client: NvoxDBClient) -> None:
    logger.info("Starting database schema validation...")

    tables_to_validate = [
        ("users", UserDB),
        ("sessions", SessionDB),
        ("user_journey_state", UserJourneyStateDB),
        ("user_answers", UserAnswerDB),
        ("stage_transitions", StageTransitionDB),
        ("user_journey_path", UserJourneyPathDB),
    ]

    validation_errors = []

    for table_name, model_class in tables_to_validate:
        try:
            await validate_table_schema(db_client, table_name, model_class)
        except SchemaValidationError as e:
            validation_errors.append(str(e))

    if validation_errors:
        error_summary = "\n".join(validation_errors)
        raise SchemaValidationError(
            f"Schema validation failed for {len(validation_errors)} table(s):\n{error_summary}"
        )

    logger.info(f"✓ All {len(tables_to_validate)} table schemas validated successfully")
