"""Logic-Compiler for Z3 SMT Solver."""

import logging
from typing import Dict, Any, Optional, List, TYPE_CHECKING
from rxllmproc import smt as z3_internal
from rxllmproc.smt import session

if TYPE_CHECKING:
    import z3
else:
    if z3_internal.Z3_AVAILABLE:
        import z3
    else:
        z3 = None

logger = logging.getLogger(__name__)


class Z3Compiler:
    """Provides tools to compile LLM-provided information into Z3 logic."""

    def __init__(
        self, session_obj: Optional["session.Z3Session"] = None
    ) -> None:
        """Initialize the compiler with a Z3 session."""
        if not z3_internal.Z3_AVAILABLE:
            raise ImportError(
                "z3-solver is not installed. Please install it with 'pip install z3-solver'."
            )
        self.session = session_obj or session.Z3Session()
        # Track declared variables/sorts to avoid re-declaration
        self.variables: Dict[str, Any] = {}
        self.sorts: Dict[str, Any] = {}

    def init_session(self, logic: str) -> str:
        """Initialize the solver with a specific SMT-LIB logic.

        Args:
            logic: The SMT-LIB logic string (e.g., 'QF_LIA', 'QF_NRA', 'QF_UF').

        Returns:
            Confirmation message.
        """
        try:
            # z3.set_param is global, but we can set logic on solver
            self.session.solver.set("logic", logic)
            logger.info("Initialized session with logic: %s", logic)
            return f"Session initialized with logic: {logic}"
        except Exception as e:
            logger.error("Failed to initialize logic %s: %s", logic, e)
            return f"Error: {e}"

    def declare_sort(self, name: str, description: Optional[str] = None) -> str:
        """Declare a new sort (uninterpreted type) in the Z3 session.

        Args:
            name: The name of the sort.
            description: Optional English description of the sort.

        Returns:
            Confirmation message.
        """
        if name in self.sorts:
            return f"Sort '{name}' already declared."

        try:
            sort = z3.DeclareSort(name)
            self.sorts[name] = sort
            if description:
                self.session.add_metadata(name, description)
            logger.info("Declared sort: %s", name)
            return f"Declared sort: {name}"
        except Exception as e:
            logger.error("Failed to declare sort %s: %s", name, e)
            return f"Error: {e}"

    def declare_variable(
        self, name: str, var_type: str, description: Optional[str] = None
    ) -> str:
        """Declare a variable in the Z3 session.

        Args:
            name: The name of the variable.
            var_type: The type of the variable ('Int', 'Real', 'Bool' or a custom sort).
            description: Optional English description of the variable.

        Returns:
            Confirmation message.
        """
        if name in self.variables:
            return f"Variable '{name}' already declared."

        try:
            if var_type == "Int":
                var = z3.Int(name)
            elif var_type == "Real":
                var = z3.Real(name)
            elif var_type == "Bool":
                var = z3.Bool(name)
            elif var_type in self.sorts:
                var = z3.Const(name, self.sorts[var_type])
            else:
                return (
                    f"Error: Unsupported type '{var_type}'. "
                    "Supported: Int, Real, Bool, or declared sorts."
                )

            self.variables[name] = var
            if description:
                self.session.add_metadata(name, description)
            logger.info("Declared variable: %s of type %s", name, var_type)
            return f"Declared variable: {name} ({var_type})"
        except Exception as e:
            logger.error("Failed to declare variable %s: %s", name, e)
            return f"Error: {e}"

    def declare_function(
        self,
        name: str,
        param_types: List[str],
        return_type: str,
        description: Optional[str] = None,
    ) -> str:
        """Declare an uninterpreted function in the Z3 session.

        Args:
            name: The name of the function.
            param_types: List of parameter types.
            return_type: The return type of the function.
            description: Optional English description of the function.

        Returns:
            Confirmation message.
        """
        if name in self.variables:
            return f"Function '{name}' already declared."

        try:
            sorts: list[z3.SortRef] = []
            for t in param_types + [return_type]:
                if t == "Int":
                    sorts.append(z3.IntSort())
                elif t == "Real":
                    sorts.append(z3.RealSort())
                elif t == "Bool":
                    sorts.append(z3.BoolSort())
                elif t in self.sorts:
                    sorts.append(self.sorts[t])
                else:
                    return (
                        f"Error: Unsupported type '{t}'. "
                        "Supported: Int, Real, Bool, or declared sorts."
                    )

            func = z3.Function(name, *sorts)
            self.variables[name] = func
            if description:
                self.session.add_metadata(name, description)
            logger.info(
                "Declared function: %s of type %s -> %s",
                name,
                param_types,
                return_type,
            )
            return f"Declared function: {name} ({param_types} -> {return_type})"
        except Exception as e:
            logger.error("Failed to declare function %s: %s", name, e)
            return f"Error: {e}"

    def assert_fact(self, label: str, smt2_code: str, description: str) -> str:
        """Assert a fact using SMT2 code and store metadata.

        Args:
            label: Unique identifier for this fact.
            smt2_code: SMT-LIBv2 assertion string (without the (assert ...)).
            description: Human-readable description of the fact.

        Returns:
            Confirmation message.
        """
        try:
            decls = self._get_declarations_smt2()

            # Use (assert ...) to parse the expression correctly
            parsed = z3.parse_smt2_string(decls + f"(assert {smt2_code})")

            if len(parsed) == 0:
                return f"Error: No expressions parsed from '{smt2_code}'"

            # Use assert_and_track for the first parsed expression to support unsat cores
            self.session.solver.assert_and_track(parsed[0], label)

            # If there are more expressions (though usually just one in smt2_code), add them
            # normally
            for i in range(1, len(parsed)):
                self.session.solver.add(parsed[i])

            self.session.add_metadata(label, description)

            logger.info("Asserted fact '%s': %s", label, description)
            return f"Asserted fact: {label}"
        except Exception as e:
            logger.error("Failed to assert fact %s: %s", label, e)
            return f"Error in SMT2 syntax: {e}"

    def add_smt2_code(self, smt_code: str) -> str:
        """Add raw SMT-LIBv2 code directly to the solver.

        Args:
            smt_code: Raw SMT2 code string.

        Returns:
            Confirmation message.
        """
        try:
            decls = self._get_declarations_smt2()
            parsed = z3.parse_smt2_string(decls + smt_code)
            self.session.solver.add(parsed)
            logger.info("Added raw SMT2 code.")
            return "Added raw SMT2 code."
        except Exception as e:
            logger.error("Failed to add raw SMT2 code: %s", e)
            return f"Error: {e}"

    def _get_declarations_smt2(self) -> str:
        """Generate SMT2 declarations for all known variables, functions, and sorts."""
        decls = ""

        # Sorts
        for name in self.sorts:
            decls += f"(declare-sort {name})\n"

        # Variables and Functions
        for name, var in self.variables.items():
            if isinstance(var, z3.FuncDeclRef):
                decl = var
            elif hasattr(var, "decl"):
                decl = var.decl()
            else:
                continue

            domain: list[str] = []
            for i in range(decl.arity()):
                domain.append(decl.domain(i).name())
            domain_str = " ".join(domain)
            range_sort = decl.range().name()
            decls += f"(declare-fun {name} ({domain_str}) {range_sort})\n"

        return decls
