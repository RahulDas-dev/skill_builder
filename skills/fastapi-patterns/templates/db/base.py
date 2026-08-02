"""ORM base only. Nothing else belongs in this file."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase): ...
