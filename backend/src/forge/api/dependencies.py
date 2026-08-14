"""FastAPI dependencies shared by API routes."""

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from forge.adapters.sqlite.database import Database


def get_session(request: Request) -> Iterator[Session]:
    database: Database = request.app.state.database
    yield from database.session()


SessionDependency = Annotated[Session, Depends(get_session)]
