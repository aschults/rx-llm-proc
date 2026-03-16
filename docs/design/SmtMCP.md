# SMT Reasoner Design

## Overview

The SMT Reasoner is a stateful service that provides a high-level interface to
the Z3 SMT (Satisfiability Modulo Theories) solver. It allows agents to
formulate and solve complex logical problems, verify the consistency of sets of
facts, and perform hypothetical "what-if" reasoning using backtracking.

## Architecture

The reasoner is implemented as an MCP (Model Context Protocol) server, making
its logical reasoning capabilities available as a set of tools that an agent can
call.

### 1. Core Components

The reasoner is built around several key components within the `rxllmproc/smt`
package:

- **`Z3Session`**: Manages the underlying Z3 solver instance and its state. It
  handles low-level operations like pushing/popping checkpoints and
  saving/loading state to/from disk.
- **`Z3Compiler`**: Responsible for translating high-level requests (like
  declaring a sort or adding a fact) into the SMT-LIBv2 format that Z3
  understands.
- **`Z3Auditor`**: Provides methods for checking the consistency of the current
  set of assertions. If a contradiction is found (`UNSAT`), it can extract and
  return an "audit trail" that explains which facts are in conflict.

### 2. State Management and Backtracking

The reasoner is designed to be stateful, allowing an agent to build up a complex
logical model over multiple tool calls.

- **Checkpoints**: The `push` and `pop` operations allow an agent to save the
  current state of the solver and return to it later. This is essential for
  hypothetical reasoning, where an agent might add a set of "provisional" facts
  to see if they lead to a contradiction, and then roll back to the original
  state.
- **Persistence**: The `save_code` and `load_code` operations allow the entire
  state of the solver (including all declarations and assertions) to be
  persisted to the `z3_code/` directory.

### 3. Logic and Modeling

The reasoner supports a wide range of SMT-LIB logics (e.g., `QF_LIA` for linear
integer arithmetic, `QF_UF` for uninterpreted functions).

- **Sorts and Functions**: Agents can define their own uninterpreted types
  (sorts) and functions, allowing them to model domain-specific knowledge in a
  way that the solver can reason about.
- **Audit Trails**: When a set of facts is found to be inconsistent, the `UNSAT`
  status includes a list of the specific facts that form the minimal
  unsatisfiable core, providing valuable feedback to the agent.

### 4. Integration via MCP

By exposing its functionality as MCP tools (`init_session`, `declare_variable`,
`add_fact`, `check_status`, etc.), the reasoner allows agents to perform formal
logical reasoning as part of their standard decision-making process.

## Performance and Reliability

- **Z3 Performance**: The reasoner leverages the highly optimized Z3 solver for
  its core logic, ensuring that it can handle even complex problems efficiently.
- **Error Handling**: The system is designed to gracefully handle malformed
  SMT-LIB code and other errors, providing clear feedback to the agent without
  crashing the server.
- **Incremental Solving**: Z3's incremental solving capabilities are used to
  make `check_status` and `get_solution` as fast as possible, even as the model
  grows in size.

## Future Enhancements

- **Direct JSON Support**: Allowing agents to provide facts and queries as JSON
  objects that are then automatically translated to SMT-LIB, reducing the need
  for the agent to "write" raw SMT-LIB code.
- **Advanced Audit Analysis**: Providing more sophisticated tools for analyzing
  the root cause of contradictions, potentially suggesting which facts could be
  relaxed to restore consistency.
- **Multiple Solvers**: Integrating other SMT solvers (like CVC5) to provide a
  broader range of reasoning capabilities.
