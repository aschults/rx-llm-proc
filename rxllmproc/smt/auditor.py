"""Resolution and Audit tools for Z3 SMT Solver."""

import logging
from typing import Dict, Any, TYPE_CHECKING, TypedDict
from rxllmproc import smt
from rxllmproc.smt import session

if TYPE_CHECKING:
    import z3
else:
    if smt.Z3_AVAILABLE:
        import z3
    else:
        z3 = None

logger = logging.getLogger(__name__)


class ConflictReportItem(TypedDict):
    """An item in the conflict report."""

    label: str
    description: str


class Z3Auditor:
    """Provides tools to resolve logic and audit contradictions in Z3."""

    def __init__(self, session_obj: "session.Z3Session") -> None:
        """Initialize the auditor with a Z3 session."""
        if not smt.Z3_AVAILABLE:
            raise ImportError(
                "z3-solver is not installed. Please install it with 'pip install z3-solver'."
            )
        self.session = session_obj

    def check_consistency(self) -> str:
        """Check if the current solver state is consistent (satisfiable).

        Returns:
            'SAT', 'UNSAT', or 'UNKNOWN'.
        """
        result = self.session.solver.check()
        status = str(result).upper()
        logger.info("Consistency check result: %s", status)
        return status

    def get_audit_trail(self) -> Dict[str, Any]:
        """Generate a conflict report if the state is UNSAT.

        Returns:
            A dictionary containing the conflict report.
        """
        status = self.check_consistency()
        if status != "UNSAT":
            return {
                "status": status,
                "message": "Audit trail is only available for UNSAT states.",
            }

        try:
            core = self.session.solver.unsat_core()
            report: list[ConflictReportItem] = []
            for label_expr in core:
                label = str(label_expr)
                description = (
                    self.session.get_description(label)
                    or "No description provided."
                )
                report.append(
                    ConflictReportItem(label=label, description=description)
                )

            logger.info("Generated conflict report with %d items.", len(report))
            return {"status": "UNSAT", "conflict_report": report}
        except Exception as e:
            logger.error("Failed to generate audit trail: %s", e)
            return {"error": str(e)}

    def get_solution(self) -> Dict[str, Any]:
        """Compute and return the solution (model).

        Returns:
            A dictionary with status and model if SAT.
        """
        status = self.check_consistency()
        if status == "UNSAT":
            return {"status": "UNSAT", "message": "No solution exists."}
        if status == "UNKNOWN":
            return {"status": "UNKNOWN", "message": "Solver in unknown state."}

        model = self.session.solver.model()

        # Check for ambiguity (generic check)
        # To truly check if there's exactly one solution for EVERYTHING is hard,
        # but we can try to see if any variable can take a different value.
        is_ambiguous = False
        decls = model.decls()
        if decls:
            blocking_terms: list[z3.BoolRef] = []
            for d in decls:
                val = model[d]
                if d.arity() == 0:  # Constant
                    blocking_terms.append(d() != val)

            if blocking_terms:
                self.session.push()
                self.session.solver.add(z3.Or(blocking_terms))
                if self.session.solver.check() == z3.sat:
                    is_ambiguous = True
                self.session.pop()

        result = {
            "status": "AMBIGUOUS" if is_ambiguous else "SAT",
            "model": {
                str(d.name()): str(model[d]) for d in decls if d.arity() == 0
            },
        }
        return result
