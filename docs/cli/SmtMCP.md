# `smt-reasoner`: SMT Solver Tool

## Introduction

The `smt-reasoner` tool provides a stateful interface to the Z3 SMT
(Satisfiability Modulo Theories) solver. It allows agents to formulate complex
logical problems, verify consistency of facts and rules, and find solutions
(models) for given constraints.

- **See Also**: [[SmtMCP]]

## Core Concepts

- **Logic**: SMT-LIB logic string (e.g., `QF_LIA`, `QF_UF`) that restricts the
  types of expressions the solver will handle.
- **Sort**: An uninterpreted type (analogous to a class or interface in
  programming).
- **Fact**: A logical assertion that must hold true.
- **Backtracking Point**: A saved state of the solver that can be returned to
  later.

---

## Tools and Commands

As an MCP server, the SMT solver exposes several tools that can be invoked by
agents.

### `init_session`

Initializes a new solver session with a specific logic.

**Arguments:**

- `logic`: The SMT-LIB logic string (e.g., `QF_LIA`, `QF_UF`).
- `session_name`: (Optional) A name for the session (default: `default`).

### `declare_sort`

Declares a new sort (uninterpreted type).

**Arguments:**

- `sort_name`: The name of the new sort.
- `description`: (Optional) English description of what this sort represents.

### `declare_variable`

Declares a variable of a specific type.

**Arguments:**

- `variable_name`: The name of the variable.
- `type`: The variable type (`Int`, `Real`, `Bool`, or a declared sort).

### `declare_function`

Declares an uninterpreted function.

**Arguments:**

- `function_name`: The name of the function.
- `types`: A list of argument types.
- `return_type`: The return type of the function.

### `add_fact`

Adds a new assertion (fact) to the current solver session.

**Arguments:**

- `fact_name`: A unique identifier for the fact.
- `smt2_code`: SMT-LIBv2 expression for the assertion.
- `description`: (Optional) English description of what this fact represents.

### `check_status`

Checks if the current set of assertions is consistent (Satisfiable).

**Returns:**

- `SAT`: The set of facts is consistent.
- `UNSAT`: A contradiction was found. Includes an audit trail of the conflicting
  facts.
- `UNKNOWN`: The solver cannot determine consistency.

### `get_solution`

If the status is `SAT`, returns a model (an assignment of values to variables
that satisfies all facts).

### `push` / `pop`

- `push`: Creates a new backtracking point (saves the current state).
- `pop`: Rolls back the solver state to the last `push`.

### `load_code` / `save_code`

- `load_code`: Loads a previously saved set of facts from a file.
- `save_code`: Saves the current solver state (all declarations and assertions)
  to a file.

---

## Example Usage (Conceptual)

An agent checking if two conditions are mutually exclusive:

1. `init_session("QF_LIA")`
2. `declare_variable("x", "Int")`
3. `add_fact("f1", "(> x 10)", "x must be greater than 10")`
4. `add_fact("f2", "(< x 5)", "x must be less than 5")`
5. `check_status()` -> Returns `UNSAT`
