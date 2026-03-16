"""Shared environment for reactive operators."""

from typing import cast

from rxllmproc.database import operators as sql_operators
from rxllmproc.core import environment


class RxEnvArgs(environment.EnvArgs, total=False):
    """Arguments for the RxEnvironment."""

    db: sql_operators.RxDatabase


class RxEnvironment(environment.Environment):
    """Environment with database access."""

    def __init__(
        self,
        settings: RxEnvArgs,
        parent: environment.Environment | None = None,
    ) -> None:
        """Initialize the environment."""
        super().__init__(settings, parent=parent)  # type: ignore

    @property
    def db(self) -> sql_operators.RxDatabase:
        """Get the database instance."""
        settings = cast(RxEnvArgs, self._settings)
        if 'db' not in settings:
            raise ValueError("Database not set")
        return settings['db']

    def update(  # pyright: ignore[reportIncompatibleMethodOverride]
        self, settings: RxEnvArgs = {}
    ) -> 'RxEnvironment':
        """Update the environment with new settings."""
        return RxEnvironment(settings, parent=self)


def shared() -> RxEnvironment:
    """Get the shared Rx environment."""
    shared_env = environment.shared()
    if not isinstance(shared_env, RxEnvironment):
        raise ValueError("Expecting RxEnvironment instance")
    return shared_env
