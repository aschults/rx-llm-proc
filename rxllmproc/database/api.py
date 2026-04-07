"""Database infrastructure."""

from typing import (
    Any,
    Generic,
    Protocol,
    TypeVar,
    Callable,
    cast,
    runtime_checkable,
)
import logging
import atexit
import json

import sqlalchemy
import sqlalchemy.orm
import pydantic

_T = TypeVar("_T", bound=object)


def t(entity: type[object]) -> sqlalchemy.Table:
    """Get the SQLAlchemy Table object from an entity class."""
    if hasattr(entity, "__table__"):
        return getattr(entity, "__table__")  # type: ignore
    else:
        raise ValueError(f'Entity {entity} does not have a __table__ attribute')


@runtime_checkable
class Registerable(Protocol):
    """Protocol representing a class that can be registered with a database."""

    @classmethod
    def _register_entity(cls, registry: sqlalchemy.orm.registry) -> None:
        """Register the class with the given registry."""
        ...


class Database:
    """Database wrapper with thread-safe session and imperative mapping."""

    def __init__(
        self,
        db_url: str,
        entities: list[
            type[object] | Callable[[sqlalchemy.orm.registry], None]
        ],
        engine_args: dict[str, Any] | None = None,
    ) -> None:
        """Initialize the database connection.

        Args:
            db_url: The database connection URL.
            entities: A list of entity classes to register.
            engine_args: Additional arguments for the SQLAlchemy engine.
        """
        logging.info("Connecting to database: %s", db_url)
        self._engine = cast(  # pyright: ignore
            sqlalchemy.engine.Engine,
            sqlalchemy.create_engine(db_url, **(engine_args or {})),
        )
        self._session_factory = sqlalchemy.orm.sessionmaker(bind=self._engine)
        self._scoped_session = sqlalchemy.orm.scoped_session(
            self._session_factory
        )
        self._registry = sqlalchemy.orm.registry()
        self._entities = entities

        for entity in self._entities:
            if isinstance(entity, type):
                logging.info("Registering entitity %s", entity)
                self._register_entity(entity)
            else:
                entity(self._registry)
        self._registry.metadata.create_all(self._engine)

        atexit.register(self.close)

    @property
    def engine(self) -> Any:
        """Return the SQLAlchemy engine."""
        return self._engine

    @property
    def session(self) -> sqlalchemy.orm.Session:
        """Return a thread-local session."""
        return self._scoped_session()

    @property
    def metadata(self) -> sqlalchemy.MetaData:
        """Return the metadata from the registry."""
        return self._registry.metadata

    def close(self) -> None:
        """Close the scoped session registry."""
        self._scoped_session.remove()

    def _register_entity(
        self,
        class_: type[object],
    ) -> None:
        """Register imperative mapping for a class.

        Args:
            class_: The class to map.
        """
        if issubclass(class_, Registerable):
            class_._register_entity(self._registry)  # type: ignore
        else:
            raise ValueError(
                f'Class {class_} does not have a _register_entity method'
            )


class StringListJSON(sqlalchemy.TypeDecorator[list[str]]):
    """Serializes a list of strings to JSONB and back."""

    impl = sqlalchemy.JSON
    cache_ok = True

    def process_bind_param(self, value: list[str] | None, dialect: Any) -> Any:
        """Process the value for binding to a database parameter."""
        if value is None:
            return None
        return json.dumps(value)

    def process_result_value(
        self, value: Any, dialect: Any
    ) -> list[str] | None:
        """Process the value returned from the database."""
        if value is None:
            return None
        return json.loads(value)


class PydanticJSON(sqlalchemy.TypeDecorator[_T], Generic[_T]):
    """Serializes Pydantic models to JSON and deserializes them back."""

    impl = sqlalchemy.JSON
    cache_ok = True

    def __init__(self, pydantic_cls: type[_T], *args: Any, **kwargs: Any):
        """Initialize the PydanticJSON type decorator."""
        super().__init__(*args, **kwargs)
        self.pydantic_cls = pydantic_cls
        self._adapter = pydantic.TypeAdapter(self.pydantic_cls)

    def process_bind_param(self, value: _T | None, dialect: Any) -> Any:
        """Process the value for binding to a database parameter."""
        if value is None:
            return None
        return self._adapter.dump_json(value).decode('utf-8')

    def process_result_value(self, value: Any, dialect: Any) -> _T | None:
        """Process the value returned from the database."""
        if value is None:
            return None
        if isinstance(value, str):
            return self._adapter.validate_json(value)
        return self._adapter.validate_python(value)


class PydanticJSONList(sqlalchemy.TypeDecorator[list[_T]], Generic[_T]):
    """Serializes a list of Pydantic models to JSON and back."""

    impl = sqlalchemy.JSON
    cache_ok = True

    def __init__(self, pydantic_cls: type[_T], *args: Any, **kwargs: Any):
        """Initialize the PydanticJSONList type decorator."""
        super().__init__(*args, **kwargs)
        self.pydantic_cls = pydantic_cls
        self._adapter = pydantic.TypeAdapter(list[self.pydantic_cls])

    def process_bind_param(self, value: list[_T] | None, dialect: Any) -> Any:
        """Process the value for binding to a database parameter."""
        if value is None:
            return None
        return self._adapter.dump_json(value).decode('utf-8')

    def process_result_value(self, value: Any, dialect: Any) -> list[_T] | None:
        """Process the value returned from the database."""
        if value is None:
            return None
        if isinstance(value, str):
            return self._adapter.validate_json(value)
        return self._adapter.validate_python(value)
