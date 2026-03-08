"""Dataclasses for Google Docs API requests."""

import dataclasses
from typing import Any, Dict, List, Optional


@dataclasses.dataclass
class Location:
    """A location in a document."""

    index: int


@dataclasses.dataclass
class Dimension:
    """A magnitude in a single direction in the specified units."""

    magnitude: float = 0.0
    unit: str = "pt"


@dataclasses.dataclass
class InsertTextRequest:
    """Inserts text into a document."""

    text: str
    location: Location


@dataclasses.dataclass
class RgbColor:
    """An RGB color."""

    # Set optional since REST call returns RgbColor with no fields.
    red: Optional[float] = None
    green: Optional[float] = None
    blue: Optional[float] = None


@dataclasses.dataclass
class Color:
    """A color."""

    rgbColor: RgbColor


@dataclasses.dataclass
class ForegroundColor:
    """The foreground color of a text style."""

    color: Color


@dataclasses.dataclass
class WeightedFontFamily:
    """A weighted font family."""

    fontFamily: str | None = None
    weight: int | None = None


@dataclasses.dataclass
class Link:
    """A link."""

    url: str | None = None
    headingId: str | None = None


@dataclasses.dataclass
class TextStyle:
    """A text style."""

    bold: Optional[bool] = None
    italic: Optional[bool] = None
    strikethrough: Optional[bool] = None
    weightedFontFamily: Optional[WeightedFontFamily] = None
    foregroundColor: Optional[ForegroundColor] = None
    link: Optional[Link] = None


@dataclasses.dataclass
class Range:
    """A range of text in a document."""

    startIndex: int
    endIndex: int


@dataclasses.dataclass
class UpdateTextStyleRequest:
    """Updates the text style of a range of text."""

    range: Range
    textStyle: TextStyle
    fields: str


@dataclasses.dataclass
class ParagraphStyle:
    """A paragraph style."""

    namedStyleType: str
    indentStart: Optional[Dimension] = None
    indentFirstLine: Optional[Dimension] = None
    headingId: Optional[str] = None


@dataclasses.dataclass
class UpdateParagraphStyleRequest:
    """Updates the paragraph style of a range of text."""

    range: Range
    paragraphStyle: ParagraphStyle
    fields: str


@dataclasses.dataclass
class DeleteParagraphBulletsRequest:
    """Deletes bullets from a range of text."""

    range: Range


@dataclasses.dataclass
class CreateParagraphBulletsRequest:
    """Creates bullets for a range of text."""

    range: Range
    bulletPreset: str


@dataclasses.dataclass
class DeleteContentRangeRequest:
    """Deletes a range of content from a document."""

    range: Range


@dataclasses.dataclass
class Request:
    """A single request in a batch update."""

    insertText: Optional[InsertTextRequest] = None
    updateTextStyle: Optional[UpdateTextStyleRequest] = None
    updateParagraphStyle: Optional[UpdateParagraphStyleRequest] = None
    deleteParagraphBullets: Optional[DeleteParagraphBulletsRequest] = None
    createParagraphBullets: Optional[CreateParagraphBulletsRequest] = None
    deleteContentRange: Optional[DeleteContentRangeRequest] = None


@dataclasses.dataclass
class SectionBreak:
    """A section break."""

    sectionStyle: Optional[Any] = None


@dataclasses.dataclass
class TableCell:
    """A table cell."""

    content: List["StructuralElement"]
    startIndex: int
    endIndex: int


@dataclasses.dataclass
class TableRow:
    """A table row."""

    tableCells: List[TableCell]
    startIndex: int
    endIndex: int


@dataclasses.dataclass
class Table:
    """A table."""

    tableRows: List[TableRow]
    columns: int
    rows: int


@dataclasses.dataclass
class TableOfContents:
    """A table of contents."""

    content: List["StructuralElement"]


@dataclasses.dataclass
class AutoText:
    """Auto text."""

    type: str
    textStyle: Optional["TextStyle"] = None


@dataclasses.dataclass
class PageBreak:
    """A page break."""

    textStyle: Optional["TextStyle"] = None


@dataclasses.dataclass
class ColumnBreak:
    """A column break."""

    textStyle: Optional["TextStyle"] = None


@dataclasses.dataclass
class FootnoteReference:
    """A footnote reference."""

    footnoteId: str
    footnoteNumber: Optional[str] = None
    textStyle: Optional["TextStyle"] = None


@dataclasses.dataclass
class HorizontalRule:
    """A horizontal rule."""

    textStyle: Optional["TextStyle"] = None


@dataclasses.dataclass
class Equation:
    """An equation."""


@dataclasses.dataclass
class Person:
    """A person."""

    personProperties: Optional[Any] = None
    textStyle: Optional["TextStyle"] = None


@dataclasses.dataclass
class RichLink:
    """A rich link."""

    richLinkProperties: Optional[Any] = None
    textStyle: Optional["TextStyle"] = None


@dataclasses.dataclass
class DateElementProperties:
    """Properties of a date element."""

    timestamp: str
    locale: str
    dateFormat: str
    timeFormat: str
    displayText: str


@dataclasses.dataclass
class DateElement:
    """A date element."""

    dateId: str
    textStyle: Optional["TextStyle"] = None
    dateElementProperties: Optional[DateElementProperties] = None


@dataclasses.dataclass
class ParagraphElement:
    """A paragraph element."""

    startIndex: int
    endIndex: int
    textRun: Optional["TextRun"] = None
    autoText: Optional[AutoText] = None
    pageBreak: Optional[PageBreak] = None
    columnBreak: Optional[ColumnBreak] = None
    footnoteReference: Optional[FootnoteReference] = None
    horizontalRule: Optional[HorizontalRule] = None
    equation: Optional[Equation] = None
    person: Optional[Person] = None
    richLink: Optional[RichLink] = None
    dateElement: Optional[DateElement] = None


@dataclasses.dataclass
class Paragraph:
    """A paragraph."""

    elements: List[ParagraphElement]
    paragraphStyle: Optional[ParagraphStyle] = None


@dataclasses.dataclass
class StructuralElement:
    """A structural element."""

    def __post_init__(self):
        """Post-initialization to set default startIndex."""
        if self.startIndex is None:
            self.startIndex = 1

    startIndex: Optional[int] = None
    endIndex: Optional[int] = None
    paragraph: Optional[Paragraph] = None
    sectionBreak: Optional[SectionBreak] = None
    table: Optional[Table] = None
    tableOfContents: Optional[TableOfContents] = None


@dataclasses.dataclass
class Body:
    """The body of a document."""

    content: List[StructuralElement]


@dataclasses.dataclass
class TextRun:
    """A text run."""

    content: str
    textStyle: Optional[TextStyle] = None


@dataclasses.dataclass
class DocumentStyle:
    """The style of a document."""

    background: Optional[Any] = None
    defaultHeaderId: Optional[str] = None
    defaultFooterId: Optional[str] = None
    evenPageHeaderId: Optional[str] = None
    evenPageFooterId: Optional[str] = None
    firstPageHeaderId: Optional[str] = None
    firstPageFooterId: Optional[str] = None
    useFirstPageHeaderFooter: Optional[bool] = None
    useEvenPageHeaderFooter: Optional[bool] = None
    pageNumberStart: Optional[int] = None
    marginTop: Optional[Dimension] = None
    marginBottom: Optional[Dimension] = None
    marginRight: Optional[Dimension] = None
    marginLeft: Optional[Dimension] = None
    pageSize: Optional[Any] = None
    marginHeader: Optional[Dimension] = None
    marginFooter: Optional[Dimension] = None
    flipPageOrientation: Optional[bool] = None


@dataclasses.dataclass
class NamedStyle:
    """A named style."""

    textStyle: Optional[TextStyle] = None
    paragraphStyle: Optional[ParagraphStyle] = None


@dataclasses.dataclass
class NamedStyles:
    """The named styles of a document."""

    styles: List[NamedStyle]


@dataclasses.dataclass
class Document:
    """A Google Docs document."""

    documentId: str
    title: Optional[str] = None
    body: Optional[Body] = None
    headers: Optional[Dict[str, Any]] = None
    footers: Optional[Dict[str, Any]] = None
    footnotes: Optional[Dict[str, Any]] = None
    documentStyle: Optional[DocumentStyle] = None
    namedStyles: Optional[NamedStyles] = None
    namedRanges: Optional[Dict[str, Any]] = None
    revisionId: Optional[str] = None
    suggestionsViewMode: Optional[str] = None
    inlineObjects: Optional[Dict[str, Any]] = None
    positionedObjects: Optional[Dict[str, Any]] = None

    @property
    def end_of_body_index(self) -> int | None:
        """Retrieves the end index of the document's body."""
        if not self.body:
            return None
        if not self.body.content:
            return None
            # The end index of the last element in the body is what we need.
        return self.body.content[-1].endIndex


# Type aliases for Google Docs API requests
DocsRequest = Request
DocsRequests = List[DocsRequest]
