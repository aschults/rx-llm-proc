"""Shared environment for reactive operators."""

from typing import cast
from typing_extensions import Unpack

from rxllmproc.database import operators as sql_operators
from rxllmproc.core import environment


class RxEnvArgs(environment.EnvArgs, total=False):
    """Arguments for the RxEnvironment."""

    db: sql_operators.RxDatabase


class RxEnvironment(environment.Environment):
    """Environment with database access."""

    def __init__(
        self,
        parent: environment.Environment | None = None,
        **kwargs: Unpack[RxEnvArgs],
    ) -> None:
        """Initialize the environment."""
        super().__init__(parent=parent, **kwargs)

    @property
    def db(self) -> sql_operators.RxDatabase:
        """Get the database instance."""
        settings = cast(RxEnvArgs, self._settings)
        if 'db' not in settings:
            raise ValueError("Database not set")
        return settings['db']

    def update(  # pyright: ignore[reportIncompatibleMethodOverride]
        self, **kwargs: Unpack[RxEnvArgs]
    ) -> 'RxEnvironment':
        """Update the environment with new settings."""
        return RxEnvironment(parent=self, **kwargs)


def shared() -> RxEnvironment:
    """Get the shared Rx environment."""
    shared_env = environment.shared()
    if not isinstance(shared_env, RxEnvironment):
        raise ValueError("Expecting RxEnvironment instance")
    return shared_env
