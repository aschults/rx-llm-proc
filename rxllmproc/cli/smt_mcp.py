"""MCP server for Z3 SMT Solver."""

import logging
import os
from typing import Any, Dict, List, Optional
import json

from rxllmproc.cli import mcp_base
from rxllmproc import smt as z3_internal
from rxllmproc.smt import session, compiler, auditor

logger = logging.getLogger(__name__)


class Z3Context:
    """Groups Z3 components for a single session."""

    def __init__(self) -> None:
        """Initialize the Z3 context."""
        self.session = session.Z3Session()
        self.compiler = compiler.Z3Compiler(self.session)
        self.auditor = auditor.Z3Auditor(self.session)


class SmtMcp(mcp_base.McpCliBase):
    """MCP server that provides a stateful interface to the Z3 SMT Solver."""

    def __init__(
        self,
        creds: Any = None,
        config_objects: List[Any] | None = None,
    ) -> None:
        """Initialize the Z3 MCP server."""
        super().__init__(
            "smt-reasoner", creds=creds, config_objects=config_objects
        )

        if not z3_internal.Z3_AVAILABLE:
            logger.error("z3-solver is not installed.")

        self.contexts: Dict[str, Z3Context] = {}
        self._setup_handlers()

    def _get_context(self, session_name: str) -> Z3Context:
        """Retrieve or create a context for the given session_name."""
        if session_name not in self.contexts:
            self.contexts[session_name] = Z3Context()
            logger.info("Created new Z3 context for session: %s", session_name)
        return self.contexts[session_name]

    def _setup_handlers(self):
        """Set up MCP tool handlers."""
        if not z3_internal.Z3_AVAILABLE:
            return

        self.server.tool()(self.init_session)
        self.server.tool()(self.declare_sort)
        self.server.tool()(self.declare_variable)
        self.server.tool()(self.declare_function)
        self.server.tool()(self.add_fact)
        self.server.tool()(self.add_smt2_code)
        self.server.tool()(self.check_status)
        self.server.tool()(self.get_solution)
        self.server.tool()(self.push)
        self.server.tool()(self.pop)
        self.server.tool()(self.load_code)
        self.server.tool()(self.save_code)
        self.server.tool()(self.list_code)

        logger.info("Z3 MCP tools registered.")

    async def init_session(
        self, logic: str, session_name: str = "default"
    ) -> str:
        """Initialize the solver with a specific SMT-LIB logic.

        Args:
            logic: The SMT-LIB logic string (e.g., 'QF_LIA', 'QF_UF').
            session_name: Optional name for the session.
        """
        return self._get_context(session_name).compiler.init_session(logic)

    async def declare_sort(
        self,
        sort_name: str,
        description: Optional[str] = None,
        session_name: str = "default",
    ) -> str:
        """Declare a new sort (uninterpreted type).

        Args:
            sort_name: Name of the sort.
            description: English description of what this sort represents.
            session_name: Optional name for the session.
        """
        return self._get_context(session_name).compiler.declare_sort(
            sort_name, description
        )

    async def declare_variable(
        self,
        variable_name: str,
        type: str,
        description: Optional[str] = None,
        session_name: str = "default",
    ) -> str:
        """Declare a variable of a specific type.

        Args:
            variable_name: Variable name.
            type: Variable type ('Int', 'Real', 'Bool' or declared sort).
            description: English description of what this variable represents.
            session_name: Optional name for the session.
        """
        return self._get_context(session_name).compiler.declare_variable(
            variable_name, type, description
        )

    async def declare_function(
        self,
        function_name: str,
        types: List[str],
        return_type: str,
        description: Optional[str] = None,
        session_name: str = "default",
    ) -> str:
        """Declare an uninterpreted function.

        Args:
            function_name: Function name.
            types: List of argument types (e.g. ['Int', 'Int']).
            return_type: Return type ('Int', 'Real', 'Bool' or declared sort).
            description: English description of what this function represents.
            session_name: Optional name for the session.
        """
        return self._get_context(session_name).compiler.declare_function(
            function_name, types, return_type, description
        )

    async def add_fact(
        self,
        fact_name: str,
        description: str,
        smt2_code: str,
        session_name: str = "default",
    ) -> str:
        """Add a new fact in SMT2 format.

        Args:
            fact_name: Unique name for the fact (e.g., 'fact_001').
            description: English description of what this fact represents.
            smt2_code: SMT-LIBv2 code for the assertion.
            session_name: Optional name for the session.
        """
        return self._get_context(session_name).compiler.assert_fact(
            fact_name, smt2_code, description
        )

    async def add_smt2_code(
        self, smt_code: str, session_name: str = "default"
    ) -> str:
        """Add raw SMT-LIBv2 code directly to the solver.

        Args:
            smt_code: Raw SMT2 code string.
            session_name: Optional name for the session.
        """
        return self._get_context(session_name).compiler.add_smt2_code(smt_code)

    async def check_status(self, session_name: str = "default") -> str:
        """Check the status of the solver (SAT, UNSAT, UNKNOWN).

        If UNSAT, returns audit trail. If not SAT, the solver should be rolled back
        (handled by agent using push/pop as per guidelines).

        Args:
            session_name: Optional name for the session.
        """
        status = self._get_context(session_name).auditor.check_consistency()
        if status == "UNSAT":
            audit = self._get_context(session_name).auditor.get_audit_trail()
            return json.dumps(
                {"status": "UNSAT", "audit_trail": audit}, indent=2
            )
        return json.dumps({"status": status}, indent=2)

    async def get_solution(self, session_name: str = "default") -> str:
        """Compute and return the solution (model).

        Args:
            session_name: Optional name for the session.
        """
        result = self._get_context(session_name).auditor.get_solution()
        return json.dumps(result, indent=2)

    async def push(self, session_name: str = "default") -> str:
        """Push a new backtracking point.

        Args:
            session_name: Optional name for the session.
        """
        self._get_context(session_name).session.push()
        return f"Pushed new solver state for {session_name}."

    async def pop(self, session_name: str = "default") -> str:
        """Roll back to the latest checkpoint.

        Args:
            session_name: Optional name for the session.
        """
        self._get_context(session_name).session.pop()
        return f"Popped solver state for {session_name}."

    async def load_code(
        self, filename: str, session_name: str = "default"
    ) -> str:
        """Load SMT-LIBv2 code from a file.

        Multiple loads are supported. If the resulting state is not SAT,
        the load operation is rolled back.

        Args:
            filename: Name of the file in the z3_code directory.
            session_name: Optional name for the session.
        """
        ctx = self._get_context(session_name)
        ctx.session.push()

        try:
            data = ctx.session.load_from_file(filename)
            ctx.compiler.add_smt2_code(data["smt2"])
            if data["metadata"]:
                ctx.session.metadata.update(data["metadata"])

            # MD says it returns status after load
            status_text = await self.check_status(session_name)
            status_data = json.loads(status_text)
            if status_data.get("status") != "SAT":
                ctx.session.pop()
                return f"Load failed (not SAT), rolled back.\n{status_text}"

            return f"Code loaded from {filename}.\n{status_text}"
        except Exception as e:
            ctx.session.pop()
            return f"Error loading code: {e}"

    async def save_code(
        self, filename: str, session_name: str = "default"
    ) -> str:
        """Save the current state of the solver to a file.

        Args:
            filename: Name of the file to save in the z3_code directory.
            session_name: Optional name for the session.
        """
        try:
            return self._get_context(session_name).session.save_to_file(
                filename
            )
        except Exception as e:
            return f"Error saving state: {e}"

    async def list_code(self, session_name: str = "default") -> str:
        """List all currently available SMT-LIBv2 code files.

        Args:
            session_name: Optional name for the session.
        """
        ctx = self._get_context(session_name)
        files = os.listdir(ctx.session.base_dir)
        return json.dumps(files, indent=2)


def main():
    """Run the Z3 MCP server."""
    SmtMcp().main()


if __name__ == "__main__":
    main()
