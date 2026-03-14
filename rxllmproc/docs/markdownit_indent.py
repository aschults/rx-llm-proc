"""A markdown-it-py plugin for indented paragraphs."""

import markdown_it
from markdown_it import rules_block


def _get_indent_level(state: rules_block.StateBlock, start_line: int) -> int:
    """Gets the indentation level of a line."""
    pos = state.bMarks[start_line] + state.tShift[start_line]
    pos_max = state.eMarks[start_line]

    if state.src[pos] != ".":
        return 0

    indent_level = 1
    pos += 1
    while pos < pos_max and state.src[pos] == ".":
        indent_level += 1
        pos += 1

    if pos >= pos_max or state.src[pos] != " ":
        return 0

    return indent_level


def _scan_paragraph_end(
    state: rules_block.StateBlock,
    start_line: int,
    end_line: int,
    initial_indent_level: int,
) -> int:
    """Scans for the end of a paragraph."""
    next_line = start_line + 1
    while next_line < end_line:
        pos = state.bMarks[next_line] + state.tShift[next_line]
        pos_max = state.eMarks[next_line]

        if pos >= pos_max:
            break

        current_indent = 0
        while pos < pos_max and state.src[pos] == ".":
            current_indent += 1
            pos += 1

        is_different_indent = current_indent != initial_indent_level
        is_not_indented_line = pos < pos_max and state.src[pos] != " "
        if is_different_indent or is_not_indented_line:
            break

        next_line += 1
    return next_line


def _create_tokens(
    state: rules_block.StateBlock,
    start_line: int,
    next_line: int,
    initial_indent_level: int,
):
    """Creates the tokens for the indented paragraph."""
    content = ""
    for i in range(start_line, next_line):
        line_start = (
            state.bMarks[i] + state.tShift[i] + initial_indent_level + 1
        )
        line_end = state.eMarks[i]
        content += state.src[line_start:line_end].strip() + " "

    token = state.push("indented_paragraph_open", "p", 1)
    token.meta = {"indent": initial_indent_level}

    token = state.push("inline", "", 0)
    token.content = content.strip()
    token.children = []

    state.push("indented_paragraph_close", "p", -1)


def indented_paragraph_plugin(md: markdown_it.MarkdownIt):
    """A markdown-it-py plugin for indented paragraphs.

    Syntax:
    .   Indented paragraph.
    ..  Double-indented paragraph.
    """

    def indented_paragraph_rule(
        state: rules_block.StateBlock,
        start_line: int,
        end_line: int,
        silent: bool,
    ):
        initial_indent_level = _get_indent_level(state, start_line)
        if not initial_indent_level:
            return False

        if silent:
            return True

        next_line = _scan_paragraph_end(
            state, start_line, end_line, initial_indent_level
        )
        _create_tokens(state, start_line, next_line, initial_indent_level)
        state.line = next_line
        return True

    md.block.ruler.before(
        "paragraph", "indented_paragraph", indented_paragraph_rule
    )
