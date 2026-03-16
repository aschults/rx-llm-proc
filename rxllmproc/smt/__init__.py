"""Z3 SMT Solver integration."""

try:
    import z3 as _  # noqa: F401

    Z3_AVAILABLE = True
except ImportError:
    Z3_AVAILABLE = False  # type: ignore

__all__ = ["Z3_AVAILABLE"]
