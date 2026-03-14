from rxllmproc.docs.markdown_to_gdocs import convert_markdown_to_requests

import test_support

fail_none = test_support.fail_none


def test_empty_input():
    """Test that empty or whitespace-only input produces no requests."""
    assert convert_markdown_to_requests("") == []
    assert convert_markdown_to_requests("   \n   ") == []


def test_single_paragraph():
    """Test conversion of a single paragraph."""
    markdown = "Hello world."
    requests = convert_markdown_to_requests(markdown)
    assert len(requests) == 3  # insert, update para style, delete bullets

    insert_req = fail_none(next(r for r in requests if r.insertText))
    style_req = fail_none(next(r for r in requests if r.updateParagraphStyle))
    bullet_req = fail_none(
        next(r for r in requests if r.deleteParagraphBullets)
    )

    insert_text = fail_none(insert_req.insertText)
    update_style = fail_none(style_req.updateParagraphStyle)

    assert insert_text.text == "Hello world.\n"
    assert (
        fail_none(update_style.paragraphStyle).namedStyleType == "NORMAL_TEXT"
    )
    assert bullet_req is not None


def test_multiple_paragraphs():
    """Test conversion of multiple paragraphs separated by blank lines."""
    markdown = "Paragraph 1.\n\nParagraph 2."
    requests = convert_markdown_to_requests(markdown)
    # Each paragraph block has 3 requests. Total = 6.
    assert len(requests) == 6

    # Requests are reversed for insertion. First block is for "Paragraph 2".
    p2_requests = requests[0:3]
    assert any(
        r.insertText and r.insertText.text == "Paragraph 2.\n"
        for r in p2_requests
    )
    assert any(r.deleteParagraphBullets for r in p2_requests)

    # Second block is for "Paragraph 1".
    p1_requests = requests[3:6]
    assert any(
        r.insertText and r.insertText.text == "Paragraph 1.\n"
        for r in p1_requests
    )
    assert any(r.deleteParagraphBullets for r in p1_requests)


def test_single_bullet_item():
    """Test conversion of a single bullet list item."""
    markdown = "* List item 1"
    requests = convert_markdown_to_requests(
        markdown
    )  # insert, delete bullets, para style, create bullets, delete newline
    assert len(requests) == 5

    insert_req = fail_none(next(r for r in requests if r.insertText))
    style_req = fail_none(
        next(
            r
            for r in requests
            if r.updateParagraphStyle
            and r.updateParagraphStyle.paragraphStyle.namedStyleType
        )
    )
    bullet_req = fail_none(
        next(r for r in requests if r.createParagraphBullets)
    )
    delete_req = fail_none(next(r for r in requests if r.deleteContentRange))

    assert fail_none(insert_req.insertText).text == "\nList item 1\n"
    assert (
        fail_none(
            fail_none(style_req.updateParagraphStyle).paragraphStyle
        ).namedStyleType
        == "NORMAL_TEXT"
    )
    assert bullet_req is not None
    assert (
        fail_none(fail_none(delete_req.deleteContentRange).range).endIndex == 1
    )


def test_multiple_bullet_items():
    """Test conversion of a multi-item bullet list."""
    markdown = "* Item 1\n* Item 2"
    requests = convert_markdown_to_requests(
        markdown
    )  # 2 items * 5 requests each = 10
    assert len(requests) == 10

    # Check item 2 (first block in reversed list)
    item2_requests = requests[0:5]
    assert any(
        r.insertText and r.insertText.text == "\nItem 2\n"
        for r in item2_requests
    )

    # Check item 1
    item1_requests = requests[5:10]
    assert any(
        r.insertText and r.insertText.text == "\nItem 1\n"
        for r in item1_requests
    )


def test_dash_list_item():
    """Test that a dash (-) creates a bulleted list item."""
    markdown = "- List item"
    requests = convert_markdown_to_requests(markdown)
    assert len(requests) == 5

    # Check that a createParagraphBullets request was created
    bullet_req = fail_none(
        next(r for r in requests if r.createParagraphBullets)
    )
    assert bullet_req is not None
    assert (
        fail_none(bullet_req.createParagraphBullets).bulletPreset
        == "BULLET_DISC_CIRCLE_SQUARE"
    )


def test_paragraph_followed_by_bullet_list():
    """Test a paragraph followed by a bullet list, separated by a single newline."""
    markdown = "Here are some points:\n* Point 1\n* Point 2"
    requests = convert_markdown_to_requests(
        markdown
    )  # 1 para (3 reqs) + 2 bullets (5 reqs each) = 13
    assert len(requests) == 13

    # Block for "Point 2"
    point2_requests = requests[0:5]
    assert any(
        r.insertText and r.insertText.text == "\nPoint 2\n"
        for r in point2_requests
    )

    # Block for "Point 1"
    point1_requests = requests[5:10]
    assert any(
        r.insertText and r.insertText.text == "\nPoint 1\n"
        for r in point1_requests
    )

    # Block for paragraph
    para_requests = requests[10:13]
    assert any(
        r.insertText and r.insertText.text == "Here are some points:\n"
        for r in para_requests
    )


def test_bullet_list_followed_by_paragraph():
    """Test a bullet list followed by a paragraph, separated by a single newline."""
    markdown = "* Point 1\n* Point 2\n\nAnd a conclusion."
    requests = convert_markdown_to_requests(
        markdown
    )  # 2 bullets (5 reqs each) + 1 para (3 reqs) = 13
    assert len(requests) == 13
    # Block for paragraph
    para_requests = requests[0:3]
    assert any(
        r.insertText and r.insertText.text == "And a conclusion.\n"
        for r in para_requests
    )

    # Block for "Point 2"
    point2_requests = requests[3:8]
    assert any(
        r.insertText and r.insertText.text == "\nPoint 2\n"
        for r in point2_requests
    )

    # Block for "Point 1"
    point1_requests = requests[8:13]
    assert any(
        r.insertText and r.insertText.text == "\nPoint 1\n"
        for r in point1_requests
    )


def test_paragraph_with_line_breaks():
    """Test that single newlines (soft breaks) in a paragraph become spaces."""
    markdown = "Line 1\nLine 2"
    requests = convert_markdown_to_requests(markdown)
    insert_req = fail_none(next(r for r in requests if r.insertText))
    bullet_req = fail_none(
        next(r for r in requests if r.deleteParagraphBullets)
    )

    assert fail_none(insert_req.insertText).text == "Line 1 Line 2\n"
    assert bullet_req is not None


def test_paragraph_with_hard_break():
    """Test that a hard break (two spaces + newline) becomes a vertical tab."""
    markdown = "Line 1  \nLine 2"
    requests = convert_markdown_to_requests(markdown)
    assert len(requests) == 3
    insert_req = fail_none(next(r for r in requests if r.insertText))
    assert fail_none(insert_req.insertText).text == "Line 1\vLine 2\n"


def test_bold_text():
    """Test a paragraph containing bold text."""
    markdown = "This is **bold** text."
    requests = convert_markdown_to_requests(markdown)
    assert len(requests) == 4  # insert, bold style, para style, para bullets

    # Find the insertText and bold requests dynamically instead of by index.
    insert_request = fail_none(next(r for r in requests if r.insertText))
    bold_request = fail_none(
        next(
            r
            for r in requests
            if r.updateTextStyle and r.updateTextStyle.textStyle.bold
        )
    )

    assert fail_none(insert_request.insertText).text == "This is bold text.\n"

    style_details = fail_none(bold_request.updateTextStyle)
    assert fail_none(style_details.textStyle).bold is True
    assert fail_none(style_details.range).startIndex == 8
    assert fail_none(style_details.range).endIndex == 12


def test_link_text():
    """Test a paragraph containing a hyperlink."""
    markdown = "Visit [Google](https://google.com)."
    requests = convert_markdown_to_requests(markdown)
    assert len(requests) == 4  # insert, link style, para style, para bullets

    # Find the insertText and link requests dynamically.
    insert_request = fail_none(next(r for r in requests if r.insertText))
    link_request = fail_none(
        next(
            r
            for r in requests
            if r.updateTextStyle and r.updateTextStyle.textStyle.link
        )
    )

    assert fail_none(insert_request.insertText).text == "Visit Google.\n"

    style_details = fail_none(link_request.updateTextStyle)
    assert (
        fail_none(fail_none(style_details.textStyle).link).url
        == "https://google.com"
    )
    assert fail_none(style_details.range).startIndex == 6
    assert fail_none(style_details.range).endIndex == 12


def test_bold_and_link():
    """Test a paragraph with both bold and linked text."""
    markdown = "A **bold** and a [link](https://example.com)."
    requests = convert_markdown_to_requests(markdown)
    assert len(requests) == 5  # insert, bold, link, para style, para bullets

    insert_request = fail_none(next(r for r in requests if r.insertText))
    assert fail_none(insert_request.insertText).text == "A bold and a link.\n"

    # Check that both a bold and a link request were created.
    style_requests = [r for r in requests if r.updateTextStyle]
    assert len(style_requests) == 2
    assert any(
        fail_none(r.updateTextStyle).textStyle.bold for r in style_requests
    )
    assert any(
        fail_none(r.updateTextStyle).textStyle.link for r in style_requests
    )


def test_nested_bullet_list():
    """Test conversion of a nested bullet list."""
    markdown = "* Level 1\n  * Level 2"
    requests = convert_markdown_to_requests(
        markdown
    )  # 2 items * 5 requests each = 10
    assert len(requests) == 10

    # --- Check Level 2 item (processed first due to reversal) ---
    level_2_requests = requests[:5]
    # Level 2 is nested once, so it should have one tab.
    assert any(
        r.insertText and r.insertText.text == "\n\tLevel 2\n"
        for r in level_2_requests
    )

    # --- Check Level 1 item ---
    level_1_requests = requests[5:]
    assert any(
        r.insertText and r.insertText.text == "\nLevel 1\n"
        for r in level_1_requests
    )


def test_single_indented_paragraph():
    """Test a single indented paragraph."""
    markdown = ". An indented paragraph."
    requests = convert_markdown_to_requests(markdown)
    # insert, para style (normal), delete bullets, para style (indent)
    assert len(requests) == 4

    insert_req = fail_none(next(r for r in requests if r.insertText))
    style_reqs = [r for r in requests if r.updateParagraphStyle]
    assert len(style_reqs) == 2

    assert fail_none(insert_req.insertText).text == "An indented paragraph.\n"

    # The first style request sets NORMAL_TEXT
    assert (
        fail_none(
            fail_none(style_reqs[0].updateParagraphStyle).paragraphStyle
        ).namedStyleType
        == "NORMAL_TEXT"
    )
    # The second style request sets the indentation
    indent_style = fail_none(style_reqs[1].updateParagraphStyle).paragraphStyle
    assert fail_none(fail_none(indent_style).indentStart).magnitude == 36


def test_multi_level_indented_paragraph():
    """Test multiple levels of indentation."""
    markdown = "... A deeply indented paragraph."
    requests = convert_markdown_to_requests(markdown)
    assert len(requests) == 4

    indent_req = fail_none(
        [
            r
            for r in requests
            if r.updateParagraphStyle
            and r.updateParagraphStyle.paragraphStyle.indentStart
        ][0]
    )
    style = fail_none(indent_req.updateParagraphStyle).paragraphStyle
    assert fail_none(fail_none(style).indentStart).magnitude == 108


def test_mixed_paragraphs():
    """Test indented paragraphs mixed with regular ones."""
    markdown = "Regular paragraph.\n\n. Indented one."
    requests = convert_markdown_to_requests(markdown)
    assert len(requests) == 7  # 4 for indented, 3 for regular

    # The first block of requests is for the last paragraph (indented)
    style_req_indented = fail_none(
        next(
            r
            for r in requests[:4]
            if r.updateParagraphStyle
            and r.updateParagraphStyle.paragraphStyle.indentStart
        )
    )
    assert (
        fail_none(
            fail_none(style_req_indented.updateParagraphStyle).paragraphStyle
        ).indentStart
        is not None
    )


def test_heading_level_1():
    """Test conversion of a level 1 heading."""
    markdown = "# My Heading"
    requests = convert_markdown_to_requests(markdown)
    assert len(requests) == 3  # insert, update para style, delete bullets

    insert_req = fail_none(next(r for r in requests if r.insertText))
    style_req = fail_none(next(r for r in requests if r.updateParagraphStyle))

    assert fail_none(insert_req.insertText).text == "My Heading\n"
    style = fail_none(style_req.updateParagraphStyle).paragraphStyle
    assert fail_none(style).namedStyleType == "HEADING_1"
    # Ensure it's not an indented paragraph
    assert fail_none(style).indentStart is None


def test_list_with_empty_item():
    """Test that a list with an empty item doesn't cause a crash."""
    # The empty line between the two items can cause an "insertText" KeyError if not handled.
    markdown = "* Item 1\n*\n* Item 2"
    requests = convert_markdown_to_requests(markdown)

    # Should produce requests for 2 items (5 reqs each), ignoring the empty one.
    assert len(requests) == 10
    assert any(r.insertText and "Item 1" in r.insertText.text for r in requests)
    assert any(r.insertText and "Item 2" in r.insertText.text for r in requests)


def test_single_numbered_list_item():
    """Test conversion of a single numbered list item."""
    markdown = "1. First item"
    requests = convert_markdown_to_requests(markdown)
    assert len(requests) == 5

    insert_req = fail_none(next(r for r in requests if r.insertText))
    bullet_req = fail_none(
        next(r for r in requests if r.createParagraphBullets)
    )

    assert fail_none(insert_req.insertText).text == "\nFirst item\n"
    assert bullet_req is not None
    assert (
        fail_none(bullet_req.createParagraphBullets).bulletPreset
        == "NUMBERED_DECIMAL_ALPHA_ROMAN"
    )
