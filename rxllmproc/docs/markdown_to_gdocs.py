"""Module for converting Markdown to Google Docs API requests."""

from typing import Dict, List, cast

import markdown_it
from markdown_it import (
    token as markdown_token,
)  # pyright: ignore[reportMissingTypeStubs]

from rxllmproc.docs import markdownit_indent
from rxllmproc.docs import types as docs_types

# The amount of indentation to apply for each level of a nested list.
INDENT_PER_LEVEL = 36

# A mapping from markdown-it token types to Google Docs text style fields.
STYLE_MAP: Dict[str, docs_types.TextStyle] = {
    "strong": docs_types.TextStyle(bold=True),
    "em": docs_types.TextStyle(italic=True),
    "s": docs_types.TextStyle(strikethrough=True),
    "code": docs_types.TextStyle(
        weightedFontFamily=docs_types.WeightedFontFamily(
            fontFamily="Courier New"
        ),
        foregroundColor=docs_types.ForegroundColor(
            color=docs_types.Color(
                rgbColor=docs_types.RgbColor(red=0.5, green=0.5, blue=0.5)
            )
        ),
    ),
}


def utf16_len(s: str) -> int:
    """Calculates the length of a string in UTF-16 code units."""
    # Each UTF-16 code unit is 2 bytes.
    return len(s.encode("utf-16-le")) // 2


def convert_markdown_to_requests(markdown_text: str) -> docs_types.DocsRequests:
    """Converts a Markdown string into a list of Google Docs API requests.

    This initial version handles basic paragraphs by splitting the text
    by double newlines. Each paragraph becomes a separate insertText request.

    Args:
        markdown_text: A string containing text formatted with Markdown.

    Returns:
        A list of request objects for the Google Docs batchUpdate method.
        Indices are set to start at 0, need to be updated when executing
    """
    md = markdown_it.MarkdownIt("gfm-like").use(
        markdownit_indent.indented_paragraph_plugin
    )
    tokens = md.parse(markdown_text)

    # We build requests in order, then reverse them at the end for insertion.
    block_requests: List[docs_types.DocsRequests] = []
    list_token_stack: List[markdown_token.Token] = []

    i = 0
    while i < len(tokens):
        token = tokens[i]

        if token.type in ("bullet_list_open", "ordered_list_open"):
            list_token_stack.append(token)
            i += 1
            continue
        elif token.type in ("bullet_list_close", "ordered_list_close"):
            list_token_stack.pop()
            i += 1
            continue

        if token.type == "paragraph_open":
            # The next token must be 'inline', and the one after 'paragraph_close'.
            inline_token = tokens[i + 1]
            assert inline_token.type == "inline"
            assert tokens[i + 2].type == "paragraph_close"

            if list_token_stack:
                # This paragraph is part of a list.
                paragraph_requests = _create_list_item_requests(
                    inline_token, token, list_token_stack[-1]
                )
            else:
                # This is a standard paragraph.
                paragraph_requests = _create_styled_paragraph_requests(
                    inline_token,
                    docs_types.ParagraphStyle(namedStyleType="NORMAL_TEXT"),
                )

            block_requests.append(paragraph_requests)

            # Advance the index past the paragraph_open, inline, and paragraph_close tokens.
            i += 3
        elif token.type == "indented_paragraph_open":
            inline_token = tokens[i + 1]
            assert inline_token.type == "inline"
            assert tokens[i + 2].type == "indented_paragraph_close"

            indent_level = token.meta.get("indent", 1)
            indent_magnitude = INDENT_PER_LEVEL * indent_level
            style = docs_types.ParagraphStyle(
                namedStyleType="NORMAL_TEXT",
                indentStart=docs_types.Dimension(magnitude=indent_magnitude),
                indentFirstLine=docs_types.Dimension(
                    magnitude=indent_magnitude
                ),
            )
            paragraph_requests = _create_styled_paragraph_requests(
                inline_token, style
            )
            block_requests.append(paragraph_requests)
            i += 3
        elif token.type == "heading_open":
            # The next token must be 'inline', and the one after 'heading_close'.
            inline_token = tokens[i + 1]
            assert inline_token.type == "inline"
            assert tokens[i + 2].type == "heading_close"

            heading_level = token.tag[1:]
            style = docs_types.ParagraphStyle(
                namedStyleType=f"HEADING_{heading_level}"
            )
            heading_requests = _create_styled_paragraph_requests(
                inline_token,
                style,
            )
            block_requests.append(heading_requests)

            # Advance the index past the heading_open, inline, and heading_close tokens.
            i += 3

        else:
            # Not a token we're handling in the main loop, so just advance.
            i += 1

    # Reverse the list of blocks, then flatten it into a single list of requests.
    # This ensures content is inserted from the bottom up.
    return [req for block in reversed(block_requests) for req in block]


def _create_styled_paragraph_requests(
    inline_token: markdown_token.Token,
    paragraph_style: docs_types.ParagraphStyle,
) -> docs_types.DocsRequests:
    """Creates the API requests for a paragraph with a specific style.

    This handles standard paragraphs, headings, and indented paragraphs.

    Args:
        inline_token: The token containing the paragraph's text and inline styling.
        paragraph_style: The style to apply to the paragraph.

    Returns:
        A list of Google Docs API requests to create and style the paragraph.
    """
    requests: docs_types.DocsRequests = []
    insert_request, text_style_requests = _process_inline_token(inline_token)
    if not insert_request or not insert_request[0].insertText:
        return []  # Don't process empty paragraphs

    text_len = utf16_len(insert_request[0].insertText.text)

    # Always apply the named style first, if present. This prevents its defaults
    # from overwriting other style overrides like indentation.
    if paragraph_style.namedStyleType:
        style = docs_types.ParagraphStyle(
            namedStyleType=paragraph_style.namedStyleType
        )
        requests.append(
            docs_types.Request(
                updateParagraphStyle=docs_types.UpdateParagraphStyleRequest(
                    range=docs_types.Range(startIndex=0, endIndex=text_len),
                    paragraphStyle=style,
                    fields="namedStyleType",
                )
            )
        )

    # Ensure no bullets are applied. This needs to be done after applying the named style
    # and before setting the inention, as this request will also cancel out any indentions.
    requests.append(
        docs_types.Request(
            deleteParagraphBullets=docs_types.DeleteParagraphBulletsRequest(
                range=docs_types.Range(startIndex=0, endIndex=text_len)
            )
        )
    )

    # Apply any remaining style overrides (like indentation) in a separate request.
    override_style = docs_types.ParagraphStyle(
        namedStyleType=paragraph_style.namedStyleType,
        indentStart=paragraph_style.indentStart,
        indentFirstLine=paragraph_style.indentFirstLine,
    )
    if override_style.indentStart or override_style.indentFirstLine:
        fields: list[str] = []
        if override_style.indentStart:
            fields.append("indentStart")
        if override_style.indentFirstLine:
            fields.append("indentFirstLine")
        requests.append(
            docs_types.Request(
                updateParagraphStyle=docs_types.UpdateParagraphStyleRequest(
                    range=docs_types.Range(startIndex=0, endIndex=text_len),
                    paragraphStyle=override_style,
                    fields=",".join(fields),
                )
            )
        )

    # The insertText request must be first.
    # Paragraph styling should be applied next.
    # Specific text styling (bold, italic) must be applied LAST to override the paragraph's default text style.
    return insert_request + requests + text_style_requests


def _create_list_item_requests(
    inline_token: markdown_token.Token,
    paragraph_open_token: markdown_token.Token,
    list_open_token: markdown_token.Token,
) -> docs_types.DocsRequests:
    """Creates the API requests for a bulleted or numbered list item.

    Args:
        inline_token: The token containing the list item's text and inline styling.
        paragraph_open_token: The `paragraph_open` token associated with this list item,
                              used to determine the nesting level.
        list_open_token: The `bullet_list_open` or `ordered_list_open` token for the
                         current list, used to determine the bullet preset.

    Returns:
        A list of Google Docs API requests to create and style the list item.
    """
    requests: docs_types.DocsRequests = []
    insert_request, text_style_requests = _process_inline_token(inline_token)

    if not insert_request or not insert_request[0].insertText:
        return []  # Don't process empty list items

    # The nesting level for a paragraph in a list is based on the token's level.
    # A top-level list item's paragraph_open token has a level of 2.
    # Each level of indentation increases the token level by 2. We want a 0-based index for nesting.
    nesting_level = (paragraph_open_token.level // 2) - 1

    # Prepend tab characters for indentation instead of using style requests.
    # The API automatically converts tabs to indentation levels for bulleted lists.
    # A leading newline is added to ensure Docs recognizes the tabs correctly,
    # and it will be removed by a subsequent deleteContentRange request.
    text_to_insert = insert_request[0].insertText.text
    text_with_tabs = "\n" + ("\t" * nesting_level) + text_to_insert
    insert_request[0].insertText.text = text_with_tabs
    paragraph_text_len = utf16_len(text_with_tabs)

    # Always delete bullets before going through the process.
    # Only then can the tab based mechanism take hold and convert it into indented bullets.
    requests.append(
        docs_types.Request(
            deleteParagraphBullets=docs_types.DeleteParagraphBulletsRequest(
                range=docs_types.Range(
                    startIndex=0, endIndex=paragraph_text_len
                )
            )
        )
    )

    requests.append(
        docs_types.Request(
            updateParagraphStyle=docs_types.UpdateParagraphStyleRequest(
                range=docs_types.Range(
                    startIndex=0, endIndex=paragraph_text_len
                ),
                paragraphStyle=docs_types.ParagraphStyle(
                    namedStyleType="NORMAL_TEXT"
                ),
                fields="namedStyleType",
            )
        )
    )

    list_preset = "BULLET_GLYPH_PRESET_UNSPECIFIED"
    if list_open_token.type == "bullet_list_open":
        list_preset = "BULLET_DISC_CIRCLE_SQUARE"
    elif list_open_token.type == "ordered_list_open":
        list_preset = "NUMBERED_DECIMAL_ALPHA_ROMAN"

    requests.append(
        docs_types.Request(
            createParagraphBullets=docs_types.CreateParagraphBulletsRequest(
                range=docs_types.Range(
                    startIndex=0, endIndex=paragraph_text_len
                ),
                bulletPreset=list_preset,
            )
        )
    )

    requests.append(
        docs_types.Request(
            deleteContentRange=docs_types.DeleteContentRangeRequest(
                range=docs_types.Range(startIndex=0, endIndex=1)
            )
        )
    )

    # The inline requests (including insertText) should come first.
    return insert_request + requests + text_style_requests


def _process_child_token(
    child: markdown_token.Token,
    content: str,
    all_requests: docs_types.DocsRequests,
    request_stack: docs_types.DocsRequests,
) -> str:
    """Processes a single child token from an inline token."""
    if child.type == "text":
        content += child.content.replace("\n", " ")
    elif child.type == "softbreak":
        content += " "
    elif child.type == "hardbreak":
        content += "\v"
    elif child.type.endswith("_open"):
        style_type = child.type.replace("_open", "")
        if style_type not in STYLE_MAP and style_type != "link":
            return content

        start_index = utf16_len(content)
        text_style = (
            docs_types.TextStyle(
                link=docs_types.Link(url=cast(str, child.attrs.get("href", "")))
            )
            if style_type == "link"
            else STYLE_MAP[style_type]
        )

        request = docs_types.Request(
            updateTextStyle=docs_types.UpdateTextStyleRequest(
                range=docs_types.Range(startIndex=start_index, endIndex=-1),
                textStyle=text_style,
                fields=",".join(
                    [
                        f
                        for f in text_style.__dataclass_fields__
                        if getattr(text_style, f) is not None
                    ]
                ),
            )
        )
        request_stack.append(request)
    elif child.type.endswith("_close"):
        if request_stack:
            open_request = request_stack.pop()
            if open_request.updateTextStyle:
                open_request.updateTextStyle.range.endIndex = utf16_len(content)
                all_requests.append(open_request)
    elif child.type == "code_inline":
        start_index = utf16_len(content)
        content += child.content
        style = STYLE_MAP["code"]
        all_requests.append(
            _create_inline_style_request(style, start_index, utf16_len(content))
        )
    return content


def _process_inline_token(
    inline_token: markdown_token.Token,
) -> tuple[docs_types.DocsRequests, docs_types.DocsRequests]:
    """Processes an 'inline' token to extract text and generate styling requests.

    Args:
        inline_token: The `inline` token to process, which contains text and styling children.

    Returns:
        A tuple containing two lists of requests:
        1. A list with a single `insertText` request for the entire paragraph's content.
        2. A list of `updateTextStyle` requests for inline styles like bold, italic, links, and code.
    """
    content = ""
    all_requests: docs_types.DocsRequests = []
    request_stack: docs_types.DocsRequests = []

    for child in inline_token.children or []:
        content = _process_child_token(
            child, content, all_requests, request_stack
        )

    insert_request = [
        docs_types.Request(
            insertText=docs_types.InsertTextRequest(
                location=docs_types.Location(index=0), text=content + "\n"
            )
        )
    ]
    all_requests.sort(
        key=lambda r: (
            r.updateTextStyle.range.startIndex if r.updateTextStyle else 0
        )
    )

    return (insert_request, all_requests)


def _create_inline_style_request(
    style: docs_types.TextStyle, start: int, end: int
) -> docs_types.DocsRequest:
    """Helper to create a single updateTextStyle request.

    Args:
        style: The TextStyle to apply.
        start: The start index (UTF-16) of the range.
        end: The end index (UTF-16) of the range.

    Returns:
        A DocsRequest object for updating the text style.
    """
    return docs_types.Request(
        updateTextStyle=docs_types.UpdateTextStyleRequest(
            range=docs_types.Range(startIndex=start, endIndex=end),
            textStyle=style,
            fields=",".join(
                [
                    f
                    for f in style.__dataclass_fields__
                    if getattr(style, f) is not None
                ]
            ),
        )
    )
