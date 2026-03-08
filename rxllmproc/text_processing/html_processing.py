"""Functionality to process HTML and markdown."""

import logging
import re
import queue

import markdownify  # type: ignore
import bs4


class Markdownify:
    """Convert HTML into Markdown."""

    def process(self, html_str: str) -> str:
        """Convert to markdown."""
        return markdownify.markdownify(html_str)  # type: ignore


class HtmlCleaner:
    """Helper class that cleans up (simplifies) HTML.

    Used to prepare the HTML for markdown conversion.

    Removes any style and script tags, unnecessary attributes and style values
    set in HTML tags.
    """

    # Primitive style attribute parse.
    STYLE_RE_SEP = re.compile(r'\s*;\s*', re.S)

    # Primitive split for style:value pairs.
    STYLE_ITEM_SPLIT = re.compile(r'^\s*(\S+)\s*:\s*(.*?)(\s*\!.*)?$', re.S)

    # Style settings to remove from style attributes.
    STYLE_DEL_RE = re.compile(
        r'''
        (^-.*)|(word-.*)|hyphens|float|(mso-.*)|opacity|text-decoration|
        (.*(background|align|border|padding|margin|spacing|width|height|line).*)|
        overflow|visibility|font-family|white-space|font|display
        ''',
        re.I | re.X,
    )

    # Match a simple letter. Used to determine if a the text content of a HTML
    # tag is empty.
    LETTER_RE = re.compile(r'[a-z0-9]', re.I)

    def _process_styles(self, styles: str) -> str | None:
        """Process the style attribute."""
        styledict: dict[str, str] = {}
        for item in self.STYLE_RE_SEP.split(styles):
            if not item:
                continue

            match = self.STYLE_ITEM_SPLIT.match(item)
            if not match:
                logging.warning(
                    'Could not parse style: %s, %s', repr(item), repr(styles)
                )
            else:
                styledict[match.group(1)] = match.group(2)

        if styledict.get('display', '') == 'none':
            return None
        if styledict.get('visibility', '') == 'hidden':
            return None

        for key in list(styledict.keys()):
            if self.STYLE_DEL_RE.fullmatch(key):
                del styledict[key]

        return ';'.join(f'{key}:{value}' for key, value in styledict.items())

    def _process_attrs(self, attrs: dict[str, str]) -> dict[str, str] | None:
        """Process all atributes of a HTML tag."""
        result = attrs.copy()
        for attr in (
            'class',
            'align',
            'border',
            'cellpadding',
            'cellspacing',
            'id',
            'background',
            'role',
            'type',
            'valign',
        ):
            if attr in result.keys():
                del result[attr]

        if 'style' in result:
            new_style = self._process_styles(result['style'])
            if new_style is None:
                return None
            elif new_style:
                result['style'] = new_style
            else:
                del result['style']

        return result

    def _want_decompose(self, tag: bs4.Tag) -> bool:
        """Check if we want to throw away the tag (plus nested)."""
        if tag.name in ('document', 'head', 'body'):
            return False
        if tag.name in ('style', 'script'):
            return True
        if not self.LETTER_RE.search(tag.get_text()):
            return True
        return False

    def process(self, input: str) -> str:
        """Clean up the HTML input."""
        doc = bs4.BeautifulSoup(input, 'html.parser')
        q = queue.Queue[bs4.PageElement]()
        q.put(doc)

        while not q.empty():
            e = q.get()

            if isinstance(e, bs4.Tag):
                if self._want_decompose(e):
                    e.decompose()
                    continue

                for e2 in e.children:
                    q.put(e2)

                if e.attrs:
                    new_attrs = self._process_attrs(e.attrs)
                    if new_attrs is None:
                        e.decompose()
                    else:
                        e.attrs = new_attrs

            if isinstance(e, bs4.Comment):
                if not e.decomposed:
                    e.extract()

        return '' if doc.decomposed else str(doc)
