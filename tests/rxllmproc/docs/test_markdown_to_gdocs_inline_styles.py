from rxllmproc.docs.markdown_to_gdocs import (
    convert_markdown_to_requests,
)

from test_support import fail_none  # noqa: E402


def test_italic_text():
    """Test a paragraph containing italic text."""
    markdown = "This is *italic* text."
    requests = convert_markdown_to_requests(markdown)
    # insert, italic style, para style, para bullets
    assert len(requests) == 4

    insert_req = fail_none(next(r for r in requests if r.insertText))
    italic_req = fail_none(
        next(
            r
            for r in requests
            if r.updateTextStyle and r.updateTextStyle.textStyle.italic
        )
    )

    assert fail_none(insert_req.insertText).text == "This is italic text.\n"
    style_details = fail_none(italic_req.updateTextStyle)
    assert fail_none(style_details.textStyle).italic is True
    assert style_details.range.startIndex == 8
    assert style_details.range.endIndex == 14


def test_strikethrough_text():
    """Test a paragraph containing strikethrough text."""
    markdown = "This is ~~struck~~ text."
    requests = convert_markdown_to_requests(markdown)
    assert len(requests) == 4

    insert_req = fail_none(next(r for r in requests if r.insertText))
    strike_req = fail_none(
        next(
            r
            for r in requests
            if r.updateTextStyle and r.updateTextStyle.textStyle.strikethrough
        )
    )

    assert fail_none(insert_req.insertText).text == "This is struck text.\n"
    style_details = fail_none(strike_req.updateTextStyle)
    assert fail_none(style_details.textStyle).strikethrough is True
    assert style_details.range.startIndex == 8
    assert style_details.range.endIndex == 14


def test_inline_code():
    """Test a paragraph containing inline code."""
    markdown = "Use the `code` command."
    requests = convert_markdown_to_requests(markdown)
    assert len(requests) == 4

    insert_req = fail_none(next(r for r in requests if r.insertText))
    code_req = fail_none(
        next(
            r
            for r in requests
            if r.updateTextStyle
            and r.updateTextStyle.textStyle.weightedFontFamily
        )
    )

    assert fail_none(insert_req.insertText).text == "Use the code command.\n"
    style_details = fail_none(code_req.updateTextStyle)
    font_family = fail_none(
        fail_none(style_details.textStyle).weightedFontFamily
    )
    assert font_family.fontFamily == "Courier New"
    assert font_family.weight is None
    assert style_details.range.startIndex == 8
    assert style_details.range.endIndex == 12
