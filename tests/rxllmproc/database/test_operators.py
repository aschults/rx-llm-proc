# pyright: reportPrivateUsage=false
# pyright: reportUnknownLambdaType=false
"""Test the SQL reactive operators."""

import unittest
import dataclasses
from unittest import mock
from typing import Any, Optional

import sqlalchemy
import sqlalchemy.orm
import sqlalchemy.sql
import reactivex as rx
from reactivex import operators as ops

from rxllmproc.database import operators as sql_operators
from rxllmproc.database import api as database
import test_support


class TestSqlOperators(unittest.TestCase):
    """Test the SQL reactive operators."""

    def setUp(self):
        self.db_mock = mock.Mock(spec=database.Database)
        self.session_mock = self.db_mock.session
        # Default behavior for in_transaction to avoid auto-true from Mock
        self.session_mock.in_transaction.return_value = False

    def test_inserter_flow(self):
        """Test the Inserter observer flow."""
        transaction = sql_operators.ByPipelineTransaction(self.db_mock)
        inserter = sql_operators.Inserter[str](transaction)

        # Test on_next triggers begin and add
        inserter.on_next("item")
        self.session_mock.add.assert_called_once_with("item")

        # Test on_completed triggers complete
        inserter.on_completed()
        self.session_mock.commit.assert_called_once()

    def test_inserter_error(self):
        """Test the Inserter observer error flow."""
        transaction = sql_operators.ByPipelineTransaction(self.db_mock)
        inserter = sql_operators.Inserter[str](transaction)

        error = ValueError("test")
        inserter.on_error(error)
        self.session_mock.rollback.assert_called_once()

    def test_upserter_flow(self):
        """Test the Upserter observer flow."""
        transaction = sql_operators.ByPipelineTransaction(self.db_mock)
        upserter = sql_operators.Upserter[str](transaction)

        # Test on_next triggers begin and merge
        upserter.on_next("item")
        self.session_mock.merge.assert_called_once_with("item")

        # Test on_completed triggers complete
        upserter.on_completed()
        self.session_mock.commit.assert_called_once()

    def test_upserter_error(self):
        """Test the Upserter observer error flow."""
        transaction = sql_operators.ByPipelineTransaction(self.db_mock)
        upserter = sql_operators.Upserter[str](transaction)

        error = ValueError("test")
        upserter.on_error(error)
        self.session_mock.rollback.assert_called_once()

    def test_by_element_transaction(self):
        """Test ByElementTransaction."""
        tx = sql_operators.ByElementTransaction(self.db_mock)

        # Test begin
        tx.begin()
        self.session_mock.begin.assert_called_once()

        # Test add (commit per element)
        tx.add("item")
        self.session_mock.add.assert_called_with("item")
        self.session_mock.flush.assert_called()
        self.session_mock.commit.assert_called()

        # Test error
        error = ValueError("boom")
        # Simulate transaction active for rollback
        self.session_mock.in_transaction.return_value = True
        tx.on_error(error)
        self.session_mock.rollback.assert_called()

    def test_by_pipeline_transaction(self):
        """Test ByPipelineTransaction."""
        tx = sql_operators.ByPipelineTransaction(self.db_mock)

        # Test begin (increments counter)
        tx.begin()
        self.assertEqual(tx._open_pipelines, 1)

        # Test add
        tx.add("item")
        self.session_mock.add.assert_called_with("item")
        self.session_mock.flush.assert_called()
        # Should not commit yet
        self.session_mock.commit.assert_not_called()

        # Test on_completed (decrements counter)
        tx.on_completed()
        self.assertEqual(tx._open_pipelines, 0)
        self.session_mock.commit.assert_called_once()

    def test_by_pipeline_transaction_nested(self):
        """Test ByPipelineTransaction with multiple streams."""
        tx = sql_operators.ByPipelineTransaction(self.db_mock)

        tx.begin()  # 1
        tx.begin()  # 2

        tx.on_completed()  # 1
        self.session_mock.commit.assert_not_called()

        tx.on_completed()  # 0
        self.session_mock.commit.assert_called_once()

    def test_by_pipeline_transaction_error(self):
        """Test ByPipelineTransaction error handling."""
        tx = sql_operators.ByPipelineTransaction(self.db_mock)
        tx.begin()

        tx.on_error(ValueError("fail"))
        self.session_mock.rollback.assert_called()
        self.assertEqual(tx._open_pipelines, 0)

    def test_rx_database_factory(self):
        """Test RxDatabase factory method."""
        rx_db = sql_operators.RxDatabase("sqlite:///:memory:", [])
        tx = rx_db.pipeline_transaction()
        self.assertIsInstance(tx, sql_operators.ByPipelineTransaction)
        self.assertEqual(tx._db, rx_db)

    def test_insert_op_flow(self):
        """Test the insert_op operator flow."""
        transaction = sql_operators.ByPipelineTransaction(self.db_mock)
        insert_operator = sql_operators.insert_op(transaction, str)

        source = rx.from_iterable(["item1", "item2"])

        result: list[str] = []
        source.pipe(insert_operator).subscribe(on_next=result.append)

        self.assertEqual(self.session_mock.add.call_count, 2)
        self.session_mock.add.assert_has_calls(
            [mock.call("item1"), mock.call("item2")]
        )
        self.session_mock.commit.assert_called_once()
        self.assertEqual(result, ["item1", "item2"])

    def test_insert_op_error(self):
        """Test the insert_op operator error flow."""
        transaction = sql_operators.ByPipelineTransaction(self.db_mock)
        insert_operator = sql_operators.insert_op(transaction, str)

        error = ValueError("test")
        source = rx.throw(error)

        source.pipe(insert_operator).subscribe(on_error=lambda e: None)

        self.session_mock.rollback.assert_called_once()

    def test_upsert_op_flow(self):
        """Test the upsert_op operator flow."""
        transaction = sql_operators.ByPipelineTransaction(self.db_mock)
        upsert_operator = sql_operators.upsert_op(transaction, str)

        source = rx.from_iterable(["item1", "item2"])

        # Mock merge to return the item
        self.session_mock.merge.side_effect = lambda x: f"merged_{x}"

        result: list[str] = []
        source.pipe(upsert_operator).subscribe(on_next=result.append)

        self.assertEqual(self.session_mock.merge.call_count, 2)
        self.session_mock.merge.assert_has_calls(
            [mock.call("item1"), mock.call("item2")]
        )
        self.session_mock.commit.assert_called_once()
        self.assertEqual(result, ["merged_item1", "merged_item2"])

    def test_upsert_op_error(self):
        """Test the upsert_op operator error flow."""
        transaction = sql_operators.ByPipelineTransaction(self.db_mock)
        upsert_operator = sql_operators.upsert_op(transaction, str)

        error = ValueError("test")
        source = rx.throw(error)

        source.pipe(upsert_operator).subscribe(on_error=lambda e: None)

        self.session_mock.rollback.assert_called_once()

    def test_query_op_static(self):
        """Test query_op with static query."""
        transaction = sql_operators.ByPipelineTransaction(self.db_mock)
        query_obj = mock.NonCallableMock(spec=sqlalchemy.sql.Executable)
        self.session_mock.execute.return_value.scalars.return_value.all.return_value = [
            "result1",
            "result2",
        ]

        query_operator = sql_operators.query_op(transaction, query_obj, str)

        source = rx.just("trigger")
        result: list[str] = []
        source.pipe(query_operator).subscribe(result.append)

        self.session_mock.execute.assert_called_once_with(query_obj)
        self.assertEqual(result, ["result1", "result2"])

    def test_query_op_dynamic(self):
        """Test query_op with dynamic query factory."""
        transaction = sql_operators.ByPipelineTransaction(self.db_mock)

        def _query_factory(item: Any) -> sqlalchemy.sql.Executable:
            return f"query_for_{item}"  # type: ignore

        def _side_effect(q: Any) -> sqlalchemy.sql.Executable:
            m = mock.Mock()
            m.scalars.return_value.all.return_value = [f"result_{q}"]
            return m

        self.session_mock.execute.side_effect = _side_effect

        query_operator = sql_operators.query_op(
            transaction, _query_factory, str
        )

        source = rx.from_iterable(["a", "b"])
        result: list[str] = []
        source.pipe(query_operator).subscribe(result.append)

        self.assertEqual(self.session_mock.execute.call_count, 2)
        self.session_mock.execute.assert_has_calls(
            [mock.call("query_for_a"), mock.call("query_for_b")]
        )
        self.assertEqual(result, ["result_query_for_a", "result_query_for_b"])

    def test_query_op_error(self):
        """Test query_op error handling."""
        transaction = sql_operators.ByPipelineTransaction(self.db_mock)
        query_obj = mock.NonCallableMock()
        error = ValueError("db error")
        self.session_mock.execute.side_effect = error

        query_operator = sql_operators.query_op(transaction, query_obj, str)

        source = rx.just("trigger")
        errors: list[Exception] = []
        source.pipe(query_operator).subscribe(on_error=errors.append)

        self.session_mock.execute.assert_called_once_with(query_obj)
        self.assertEqual(errors, [error])

    def test_query_op_creation_error(self):
        """Test query_op error handling when query creation fails."""
        transaction = sql_operators.ByPipelineTransaction(self.db_mock)
        error = ValueError("creation error")

        def _query_factory(item: Any) -> sqlalchemy.sql.Executable:
            raise error

        query_operator = sql_operators.query_op(
            transaction, _query_factory, str
        )

        source = rx.just("trigger")
        errors: list[Exception] = []

        def _error_handler(e: Exception):
            errors.append(e)

        source.pipe(query_operator).subscribe(on_error=_error_handler)

        self.assertEqual(errors, [error])

    def test_query_op_execution_error(self):
        """Test query_op error handling when execution chain fails."""
        transaction = sql_operators.ByPipelineTransaction(self.db_mock)
        query_obj = mock.NonCallableMock()
        error = ValueError("execution error")

        self.session_mock.execute.return_value.scalars.return_value.all.side_effect = (
            error
        )

        query_operator = sql_operators.query_op(transaction, query_obj, str)

        source = rx.just("trigger")
        errors: list[Exception] = []
        source.pipe(query_operator).subscribe(on_error=errors.append)

        self.assertEqual(errors, [error])

    def test_integration_sqlite(self):
        """Test integration with an in-memory SQLite database."""

        @dataclasses.dataclass
        class User:
            id: Optional[int] = None
            name: str = ""

            @classmethod
            def _register_entity(cls, registry: sqlalchemy.orm.registry):
                table = sqlalchemy.Table(
                    "user",
                    registry.metadata,
                    sqlalchemy.Column(
                        "id", sqlalchemy.Integer, primary_key=True
                    ),
                    sqlalchemy.Column("name", sqlalchemy.String),
                )
                registry.map_imperatively(cls, table)

        db = sql_operators.RxDatabase(
            "sqlite:///:memory:",
            [User],
        )

        # Use ByPipelineTransaction
        tx = db.pipeline_transaction()
        inserter = tx.insert_sink(User)

        rx.from_iterable(['Frank', 'Bob']).pipe(
            ops.map(lambda name_: User(name=name_))
        ).subscribe(inserter)

        users = db.session.query(User).all()
        self.assertEqual(list(user.name for user in users), ["Frank", "Bob"])

    def test_integration_sqlite_pipeline_ops(self):
        """Test integration with SQLite using insert_op and query_op."""

        @dataclasses.dataclass
        class UserOp:
            id: int = 0
            name: str = ""

            @classmethod
            def _register_entity(cls, registry: sqlalchemy.orm.registry):
                table = sqlalchemy.Table(
                    "user_op",
                    registry.metadata,
                    sqlalchemy.Column(
                        "id", sqlalchemy.Integer, primary_key=True
                    ),
                    sqlalchemy.Column("name", sqlalchemy.String),
                )
                registry.map_imperatively(cls, table)

        db = sql_operators.RxDatabase(
            "sqlite:///:memory:",
            [UserOp],
        )

        # 1. Test insert_op
        tx_insert = db.pipeline_transaction()
        users = [UserOp(id=1, name="Amber"), UserOp(id=2, name="Bob")]

        insert_results: list[Any] = []
        rx.from_iterable(users).pipe(tx_insert.insert_op(UserOp)).subscribe(
            on_next=insert_results.append,
            on_error=lambda e: insert_results.append(e),
        )

        # Verify insertion
        session = db.session
        stored = session.query(UserOp).order_by(database.t(UserOp).c.id).all()
        self.assertEqual(len(stored), 2)
        self.assertEqual(stored[0].name, "Amber")
        self.assertEqual(stored[1].name, "Bob")
        self.assertEqual(len(insert_results), 2)

        # 2. Test query_op
        tx_query = db.pipeline_transaction()
        query_results: list[Any] = []

        # Query for Bob
        def _query(name: str) -> sqlalchemy.sql.Executable:
            return sqlalchemy.select(UserOp).where(
                database.t(UserOp).c.name == name
            )

        rx.of("Bob").pipe(
            tx_query.query_op(_query, UserOp),
        ).subscribe(query_results.append)

        self.assertEqual(len(query_results), 1)
        self.assertEqual(query_results[0].name, "Bob")

        # 3. Test upsert_op
        tx_upsert = db.pipeline_transaction()
        # Update Bob's name
        updated_user = UserOp(id=2, name="Bobby")

        upsert_results: list[Any] = []
        rx.of(updated_user).pipe(tx_upsert.upsert_op(UserOp)).subscribe(
            upsert_results.append
        )

        # Verify update
        stored_bob = (
            session.query(UserOp).filter(database.t(UserOp).c.id == 2).one()
        )
        self.assertEqual(test_support.fail_none(stored_bob).name, "Bobby")
        self.assertEqual(len(upsert_results), 1)
        self.assertEqual(upsert_results[0].name, "Bobby")
