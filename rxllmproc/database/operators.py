"""Reactive operators for Database interactions."""

import logging
import threading
from typing import Generic, TypeVar, Any, Callable

import reactivex as rx
from reactivex import operators as ops
from reactivex.abc import observer as abc_observer
from reactivex import disposable
import sqlalchemy
import sqlalchemy.orm
from rxllmproc.database import api as database

_T = TypeVar("_T", bound=object)


class Inserter(rx.Observer[_T], Generic[_T]):
    """Observer that inserts items into a database transaction."""

    def __init__(self, transaction: 'BaseTransaction') -> None:
        """Initialize the Inserter."""
        super().__init__()
        self._transaction = transaction
        self._is_started = False

    def _ensure_started(self) -> None:
        if not self._is_started:
            self._is_started = True
            self._transaction.begin()

    def on_next(self, value: _T) -> None:
        """Handle the next item in the stream."""
        try:
            self._ensure_started()
            self._transaction.add(value)
        except Exception as e:
            self.on_error(e)

    def on_error(self, error: Exception) -> None:
        """Handle an error in the stream."""
        self._ensure_started()
        self._transaction.on_error(error)

    def on_completed(self) -> None:
        """Handle the completion of the stream."""
        try:
            self._ensure_started()
            self._transaction.on_completed()
        except Exception as e:
            self.on_error(e)


class Upserter(rx.Observer[_T], Generic[_T]):
    """Observer that upserts items into a database transaction."""

    def __init__(self, transaction: 'BaseTransaction') -> None:
        """Initialize the Upserter."""
        super().__init__()
        self._transaction = transaction
        self._is_started = False

    def _ensure_started(self) -> None:
        if not self._is_started:
            self._is_started = True
            self._transaction.begin()

    def on_next(self, value: _T) -> None:
        """Handle the next item in the stream."""
        try:
            self._ensure_started()
            self._transaction.merge(value)
        except Exception as e:
            self.on_error(e)

    def on_error(self, error: Exception) -> None:
        """Handle an error in the stream."""
        self._ensure_started()
        self._transaction.on_error(error)

    def on_completed(self) -> None:
        """Handle the completion of the stream."""
        try:
            self._ensure_started()
            self._transaction.on_completed()
        except Exception as e:
            self.on_error(e)


def insert_op(
    transaction: "BaseTransaction",
    _: type[_T],
) -> Callable[[rx.Observable[_T]], rx.Observable[_T]]:
    """Insert items into the database using the provided transaction.

    Args:
        transaction: The transaction to use.

    Returns:
        An operator function.
    """

    def _insert(source: rx.Observable[_T]) -> rx.Observable[_T]:
        first_element = True

        def _process(item: _T) -> _T:
            nonlocal first_element
            if first_element:
                transaction.begin()
                first_element = False
            transaction.add(item)
            return item

        return source.pipe(
            ops.map(_process),
            ops.do_action(
                on_error=transaction.on_error,
                on_completed=transaction.on_completed,
            ),
        )

    return _insert


def upsert_op(
    transaction: "BaseTransaction",
    _: type[_T],
) -> Callable[[rx.Observable[_T]], rx.Observable[_T]]:
    """Upsert items into the database using the provided transaction.

    Args:
        transaction: The transaction to use.

    Returns:
        An operator function.
    """

    def _upsert(source: rx.Observable[_T]) -> rx.Observable[_T]:
        first_element = True

        def _process(item: _T) -> _T:
            nonlocal first_element
            if first_element:
                transaction.begin()
                first_element = False
            return transaction.merge(item)

        return source.pipe(
            ops.map(_process),
            ops.do_action(
                on_error=transaction.on_error,
                on_completed=transaction.on_completed,
            ),
        )

    return _upsert


class QueryObservable(rx.Observable[_T], Generic[_T]):
    """Observable that loads entities from a database query."""

    def __init__(
        self,
        transaction: 'BaseTransaction',
        query: sqlalchemy.sql.expression.Executable,
    ) -> None:
        """Initialize the loader."""
        super().__init__(self._subscribe)
        self._query = query
        self._transaction = transaction

    def _subscribe(
        self, observer: abc_observer.ObserverBase[_T], scheduler: Any = None
    ) -> disposable.Disposable:
        try:
            result = self._transaction.execute(self._query).scalars().all()
            for item in result:
                observer.on_next(item)
            observer.on_completed()
        except Exception as e:
            observer.on_error(e)
        return disposable.Disposable()


def query_op(
    transaction: "BaseTransaction",
    query: (
        sqlalchemy.sql.expression.Executable
        | Callable[[Any], sqlalchemy.sql.expression.Executable]
    ),
    _: type[_T],
) -> Callable[[rx.Observable[Any]], rx.Observable[_T]]:
    """Execute a query for each item in the source stream.

    Args:
        transaction: The transaction to use for execution.
        query: The SQLAlchemy query to execute. Can be a static query object
            or a callable that takes the source item and returns a query.

    Returns:
        An operator function that transforms the source observable into a stream
        of query results.
    """

    def _execute_query(source: rx.Observable[Any]) -> rx.Observable[_T]:
        def _project(item: Any) -> rx.Observable[_T]:
            try:
                actual_query = query(item) if callable(query) else query
                return QueryObservable[_T](transaction, actual_query)
            except Exception as e:
                return rx.throw(e)

        return source.pipe(ops.flat_map(_project))

    return _execute_query


class RxDatabase(database.Database):
    """Database wrapper with thread-safe session and imperative mapping."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the RxDatabase."""
        super().__init__(*args, **kwargs)
        self._scoped_session = sqlalchemy.orm.scoped_session(
            sqlalchemy.orm.sessionmaker(bind=self.engine)
        )

    @property
    def session(self) -> sqlalchemy.orm.Session:
        """Get a thread-safe session."""
        return self._scoped_session()

    def pipeline_transaction(self) -> 'ByPipelineTransaction':
        """Create a new transaction that considers an entire pipeline a transaction."""
        return ByPipelineTransaction(self)

    def element_transaction(self) -> 'ByElementTransaction':
        """Create a new transaction that commits after each element."""
        return ByElementTransaction(self)


class BaseTransaction:
    """Base class for database transactions."""

    def __init__(self, db: database.Database) -> None:
        """Initialize the BaseTransaction."""
        self._db = db
        self._transaction = None

    @property
    def session(self) -> sqlalchemy.orm.Session:
        """Get the database session."""
        return self._db.session

    def begin(self) -> None:
        """Begin the transaction."""
        raise NotImplementedError()

    def add(self, item: Any) -> None:
        """Add an item to the transaction."""
        raise NotImplementedError()

    def merge(self, item: Any) -> Any:
        """Merge an item into the transaction."""
        raise NotImplementedError()

    def execute(self, query: Any) -> Any:
        """Execute a query."""
        raise NotImplementedError()

    def on_completed(self) -> None:
        """Handle the completion of the stream."""
        raise NotImplementedError()

    def on_error(self, error: Exception) -> None:
        """Handle an error in the stream."""
        raise NotImplementedError()

    def insert_sink(self, class_: type[_T]) -> Inserter[_T]:
        """Create an Inserter sink."""
        return Inserter[_T](self)

    def upsert_sink(self, class_: type[_T]) -> Upserter[_T]:
        """Create an Upserter sink."""
        return Upserter[_T](self)

    def insert_op(
        self, class_: type[_T]
    ) -> Callable[[rx.Observable[_T]], rx.Observable[_T]]:
        """Create an insert operator."""
        return insert_op(self, class_)

    def upsert_op(
        self, class_: type[_T]
    ) -> Callable[[rx.Observable[_T]], rx.Observable[_T]]:
        """Create an upsert operator."""
        return upsert_op(self, class_)

    def query_src(self, query: Any, _type: type[_T]) -> QueryObservable[_T]:
        """Create a query source."""
        return QueryObservable[_T](self, query)

    def query_op(
        self, query: Any, _type: type[_T]
    ) -> Callable[[rx.Observable[Any]], rx.Observable[_T]]:
        """Create a query operator."""
        return query_op(self, query, _type)


class ByElementTransaction(BaseTransaction):
    """A transaction that commits after each element."""

    def __init__(self, db: database.Database) -> None:
        """Initialize the ByElementTransaction."""
        super().__init__(db)

    def begin(self) -> None:
        """Begin the transaction."""
        if not self._db.session.in_transaction():
            self._db.session.begin()

    def add(self, item: Any) -> None:
        """Add an item to the transaction and commit."""
        self.begin()
        self._db.session.add(item)
        self._db.session.flush()
        try:
            self._db.session.commit()
        except Exception as e:
            self._db.session.rollback()
            raise e

    def merge(self, item: Any) -> Any:
        """Merge an item into the transaction and commit."""
        self.begin()
        merged = self._db.session.merge(item)
        self._db.session.flush()
        try:
            self._db.session.commit()
        except Exception as e:
            self._db.session.rollback()
            raise e
        return merged

    def execute(self, query: Any) -> Any:
        """Execute a query."""
        return self._db.session.execute(query)

    def on_completed(self) -> None:
        """Handle the completion of the stream."""
        pass

    def on_error(self, error: Exception) -> None:
        """Handle an error in the stream."""
        if self._db.session.in_transaction():
            self._db.session.rollback()
        logging.exception("Transaction error: %s", error)


class ByPipelineTransaction(BaseTransaction):
    """Manages a database transaction across multiple observers."""

    def __init__(self, db: database.Database) -> None:
        """Initialize the transaction."""
        super().__init__(db)
        self._open_pipelines = 0
        self._lock = threading.Lock()

    def begin(self) -> None:
        """Signal that a new pipeline/observer has started using this transaction."""
        with self._lock:
            self._open_pipelines += 1

    def add(self, item: Any) -> None:
        """Add an item to the session."""
        self._db.session.add(item)
        self._db.session.flush()

    def merge(self, item: Any) -> Any:
        """Merge an item into the session."""
        merged = self._db.session.merge(item)
        self._db.session.flush()
        return merged

    def execute(self, query: Any) -> Any:
        """Execute a query."""
        return self._db.session.execute(query)

    def on_completed(self) -> None:
        """Signal that a pipeline completed. Commit if all are done."""
        with self._lock:
            self._open_pipelines -= 1
            should_commit = self._open_pipelines <= 0

        if should_commit:
            try:
                self._db.session.commit()
            except Exception:
                self._db.session.rollback()
                raise

    def on_error(self, error: Exception) -> None:
        """Signal that an error occurred. Rollback immediately."""
        with self._lock:
            self._open_pipelines = 0
        self._db.session.rollback()
        logging.exception("Transaction aborted due to error: %s", error)
