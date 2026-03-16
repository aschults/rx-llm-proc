"""Session manager for Z3 SMT Solver."""

import logging
import os
import json
from typing import Dict, Any, Optional, Set, TYPE_CHECKING, TypedDict, cast

from rxllmproc import smt as z3_internal

if TYPE_CHECKING:
    import z3
else:
    if z3_internal.Z3_AVAILABLE:
        import z3
    else:
        z3 = None

logger = logging.getLogger(__name__)


class SessionState(TypedDict):
    """Represents the serialized state of a Z3 session."""

    smt2: str
    metadata: Dict[str, str]


class Z3Metadata:
    """Manages metadata for Z3 session elements."""

    def __init__(
        self, initial_metadata: Optional[Dict[str, str]] = None
    ) -> None:
        """Initialize metadata."""
        self.metadata: Dict[str, str] = (
            initial_metadata.copy() if initial_metadata else {}
        )

    def add(self, label: str, description: str) -> None:
        """Associate a label with an English description."""
        self.metadata[label] = description
        logger.debug("Added metadata for label '%s': %s", label, description)

    def get(self, label: str) -> Optional[str]:
        """Retrieve the English description for a given label."""
        return self.metadata.get(label)

    def update(self, other: Dict[str, str]) -> None:
        """Update metadata with another dictionary."""
        self.metadata.update(other)

    def copy(self) -> Dict[str, str]:
        """Return a copy of the metadata dictionary."""
        return self.metadata.copy()

    def get_commented_smt2_lines(self, smt2: str) -> str:
        """Generate SMT2 string with metadata included as comments."""
        lines = smt2.splitlines()
        commented_lines: list[str] = []
        matched_keys: Set[str] = set()

        for line in lines:
            for key, desc in self.metadata.items():
                # Use more precise matching with spaces/parentheses
                if (
                    f" {key} " in line
                    or f" {key})" in line
                    or f"({key} " in line
                    or f":named {key}" in line
                ):
                    commented_lines.append(f"; {key}: {desc}")
                    matched_keys.add(key)
            commented_lines.append(line)

        # Add unmatched metadata at the top
        unmatched = [
            f"; {k}: {v}"
            for k, v in self.metadata.items()
            if k not in matched_keys
        ]
        if unmatched:
            commented_lines = (
                ["; Unmatched metadata:"] + unmatched + [""] + commented_lines
            )

        return "\n".join(commented_lines)


class Z3Session:
    """Manages a stateful Z3 Solver session with metadata tracking."""

    def __init__(self, base_dir: str = "z3_code") -> None:
        """Initialize a new Z3 session."""
        if not z3_internal.Z3_AVAILABLE:
            raise ImportError(
                "z3-solver is not installed. Please install it with 'pip install z3-solver'."
            )
        self.solver = z3.Solver()
        # Enable unsat core tracking
        self.solver.set(unsat_core=True)
        # Manages SMT2 label/assertion IDs to original English descriptions
        self.metadata = Z3Metadata()
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)
        logger.info("Initialized new Z3 Solver session in %s.", self.base_dir)

    def _validate_path(self, filename: str) -> str:
        """Ensure filename is only in the current base_dir (no traversal)."""
        if os.path.isabs(filename) or ".." in filename:
            raise ValueError(
                f"Invalid filename: {filename}. Directory traversal not allowed."
            )
        return os.path.join(self.base_dir, filename)

    def push(self) -> None:
        """Create a new backtracking point in the solver's state."""
        self.solver.push()
        logger.debug("Pushed new solver state.")

    def pop(self) -> None:
        """Backtrack to the previous state."""
        try:
            self.solver.pop()
            logger.debug("Popped solver state.")
        except z3.Z3Exception as e:
            logger.error("Failed to pop solver state: %s", e)
            raise

    def add_metadata(self, label: str, description: str) -> None:
        """Associate a label with an English description."""
        self.metadata.add(label, description)

    def get_description(self, label: str) -> Optional[str]:
        """Retrieve the English description for a given label."""
        return self.metadata.get(label)

    def to_smt2_with_comments(self) -> str:
        """Generate SMT2 string with metadata included as comments."""
        return self.metadata.get_commented_smt2_lines(self.solver.to_smt2())

    def export_state(self) -> SessionState:
        """Serialize the current solver state and metadata."""
        return {"smt2": self.solver.to_smt2(), "metadata": self.metadata.copy()}

    def load_state(self, smt2_string: str, metadata: Dict[str, str]) -> None:
        """Rehydrate a session from SMT2 string and metadata."""
        self.solver.reset()
        self.solver.set(unsat_core=True)
        try:
            parsed = z3.parse_smt2_string(smt2_string)
            self.solver.add(parsed)
            self.metadata = Z3Metadata(metadata)
            logger.info("Successfully rehydrated Z3 session.")
        except Exception as e:
            logger.error("Failed to load state: %s", e)
            raise

    def save_to_file(self, filename: str) -> str:
        """Save the current state of the solver to a file."""
        path = self._validate_path(filename)
        try:
            if filename.endswith(".smt2"):
                # Save as pure SMT2 with comments
                smt2_content = self.to_smt2_with_comments()
                with open(path, "w", encoding="utf-8") as f:
                    f.write(smt2_content)

                # Also save metadata as a companion JSON file
                meta_path = path + ".json"
                with open(meta_path, "w", encoding="utf-8") as f:
                    json.dump(self.metadata.copy(), f, indent=2)
                return f"SMT2 saved to {filename} with metadata in {filename}.json."
            else:
                # Default to JSON session export
                state = self.export_state()
                with open(path, "w") as f:
                    json.dump(state, f, indent=2)
                return f"Session state saved to {filename} as JSON."
        except Exception as e:
            logger.error("Error saving state to %s: %s", filename, e)
            raise

    def load_from_file(self, filename: str) -> SessionState:
        """Load state from a file.

        Returns:
            Dictionary with 'smt2' and 'metadata'.
        """
        path = self._validate_path(filename)
        if not os.path.exists(path):
            raise FileNotFoundError(f"File {filename} not found.")

        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

            try:
                data = json.loads(content)
                if isinstance(data, dict) and "smt2" in data:
                    data_dict: dict[str, Any] = cast(dict[str, Any], data)
                    return {
                        "smt2": data_dict["smt2"],
                        "metadata": data_dict.get("metadata", {}),
                    }
            except json.JSONDecodeError:
                pass

            # Treat as raw SMT2
            result: SessionState = {"smt2": content, "metadata": {}}

            # Check for companion metadata file if filename ends with .smt2
            if filename.endswith(".smt2"):
                meta_path = path + ".json"
                if os.path.exists(meta_path):
                    try:
                        with open(meta_path, "r", encoding="utf-8") as mf:
                            meta_data = json.load(mf)
                            if isinstance(meta_data, dict):
                                result["metadata"] = meta_data
                    except Exception as me:
                        logger.error(
                            "Failed to load metadata from %s: %s", meta_path, me
                        )

            return result
        except Exception as e:
            logger.error("Error loading code from %s: %s", filename, e)
            raise
