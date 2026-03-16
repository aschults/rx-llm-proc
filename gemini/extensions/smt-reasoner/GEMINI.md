# Z3 Reasoner Extension

This extension provides a stateful Z3 SMT Solver interface for formal logic,
constraint satisfaction, and consistency checking.

## Role & Objectives

You have access to the `smt-reasoner` MCP tools. Use them to:

- Formulate complex logical problems.
- Verify consistency of facts and rules.
- Find solutions (models) for given constraints.
- Perform hypothetical reasoning using `push` and `pop`.

## Operational Standards

- **Incremental Reasoning**: Add facts incrementally and use `check_status` to
  ensure the model remains consistent.
- **Hypothetical Scenarios**: Always use `push` before adding facts that might
  need to be retracted or are part of a "what-if" analysis. Use `pop` to return
  to a known stable state.
- **Audit Trails**: When `check_status` returns `UNSAT`, analyze the audit trail
  to identify the conflicting facts and resolve the contradiction.
- **Logical Precision**: Ensure that SMT-LIBv2 code is syntactically correct and
  semantically accurate to the problem domain.

## Z3 Interface

Session name is optional, defaulting to `default`.

- `init_session(session_name: str)`: Create a new, named session.
- `declare_sort(sort_name: str, description: str, session_name: str)`: Declare a new type of
  variable, called sort in Z3. The `description` should be an English description of what the sort represents.
- `declare_variable(variable_name: str, type: str, description: str, session_name: str)`: Declare
  a variable of a specific type. The `description` should be an English description of what the variable represents.
- `declare_function(function_name: str, types: list[str], return_type: str, description: str, session_name: str)`:
  Declare an uninterpreted function with a given name and argument types. The `types` list
  represents the argument types, and `return_type` is the type of the function's output. 
  The `description` should be an English description of what the function represents.
- `add_fact(fact_name: str, description: str, smt2_code: str, session_name: str)`:
  Add a new fact in SMT2 format. The `smt2_code` should be a valid boolean
  SMT-LIBv2 expression, to be asserted as part of the solver.
- `add_smt2_code(smt_code: str, session_name: str)`: Add raw SMT-LIBv2 code
  directly to the solver.
- `check_status`: The call returns the new status of the solver (SAT, UNSAT,
  UNKNOWN).
  - If SAT is returned, the solver remains consistent and may still find a valid
    solution.
  - If UNSAT is returned, the call also returns the audit trail, indicating how
    the new fact resulted in a conflict. The fact added in the call is removed
    again.
  - If UNKNOWN is returned, the solver is in an unknown state and won't be able
    to determine solutions anymore, e.g. when exceeding complexity bounds or
    encountering non-linear arithmetic. The fact added in the call is removed
    again. In this case it often is better to call `init_session` again and try
    with a different logic.
- `get_solution(session_name: str)`: Computes and returns the solution (i.e. the
  Z3 model). The reply includes the state of the solver, with an additional
  `AMBIGUOUS` status, indicating that more than one solution was found. Onlz a
  status of `SAT` indicates that exactly one solution was found (and is part of
  the returned value). If the status is `UNSAT`, no solution exists under
  current constraints.
- `push(session_name: str)`: Add a checkpoint of the solver to a stack of
  checkpoints that can be rolled back to using `pop`.
- `pop(session_name: str)`: Roll back to the latest checkpoint. Multiple calls
  to `pop` roll back further in the stack.
- `load_code(filename: str, session_name: str)`: Load SMT-LIBv2 code from a file
  to the the solver. Multiple loads are supported, allowing to pre-load facts
  and rules. Note that the response again contains the solver status, with audit
  trail added if indicated. Again, unless the status is `SAT`, the load
  operation is rolled back.
- `save_code(filename: str, session_name: str)`: Save the current state of the
  solver to a file as SMT-LIBv2 code.
- `list_code(session_name: str)`: List all currently available SMT-LIBv2 code
  files.
