"""Module for content conversion between different formats."""

import markdownify

from rxllmproc.text_processing import html_processing


def convert_html_to_markdown(html_content: str) -> str:
    """Converts HTML content to Markdown after sanitizing it."""
    sanitized_html = html_processing.HtmlCleaner().process(html_content)
    return (
        markdownify.markdownify(sanitized_html, heading_style="ATX").strip()
        + "\n"
    )
