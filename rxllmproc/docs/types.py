"""Dataclasses for Google Docs API requests."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict


class Location(BaseModel):
    """A location in a document."""

    model_config = ConfigDict(extra='ignore')

    index: int


class Dimension(BaseModel):
    """A magnitude in a single direction in the specified units."""

    model_config = ConfigDict(extra='ignore')

    magnitude: float = 0.0
    unit: str = "pt"


class InsertTextRequest(BaseModel):
    """Inserts text into a document."""

    model_config = ConfigDict(extra='ignore')

    text: str
    location: Location


class RgbColor(BaseModel):
    """An RGB color."""

    model_config = ConfigDict(extra='ignore')

    # Set optional since REST call returns RgbColor with no fields.
    red: Optional[float] = None
    green: Optional[float] = None
    blue: Optional[float] = None


class Color(BaseModel):
    """A color."""

    model_config = ConfigDict(extra='ignore')

    rgbColor: RgbColor


class ForegroundColor(BaseModel):
    """The foreground color of a text style."""

    model_config = ConfigDict(extra='ignore')

    color: Color


class WeightedFontFamily(BaseModel):
    """A weighted font family."""

    model_config = ConfigDict(extra='ignore')

    fontFamily: str | None = None
    weight: int | None = None


class Link(BaseModel):
    """A link."""

    model_config = ConfigDict(extra='ignore')

    url: str | None = None
    headingId: str | None = None


class TextStyle(BaseModel):
    """A text style."""

    model_config = ConfigDict(extra='ignore')

    bold: Optional[bool] = None
    italic: Optional[bool] = None
    strikethrough: Optional[bool] = None
    weightedFontFamily: Optional[WeightedFontFamily] = None
    foregroundColor: Optional[ForegroundColor] = None
    link: Optional[Link] = None


class Range(BaseModel):
    """A range of text in a document."""

    model_config = ConfigDict(extra='ignore')

    startIndex: int
    endIndex: int


class UpdateTextStyleRequest(BaseModel):
    """Updates the text style of a range of text."""

    model_config = ConfigDict(extra='ignore')

    range: Range
    textStyle: TextStyle
    fields: str


class ParagraphStyle(BaseModel):
    """A paragraph style."""

    model_config = ConfigDict(extra='ignore')

    namedStyleType: str
    indentStart: Optional[Dimension] = None
    indentFirstLine: Optional[Dimension] = None
    headingId: Optional[str] = None


class UpdateParagraphStyleRequest(BaseModel):
    """Updates the paragraph style of a range of text."""

    model_config = ConfigDict(extra='ignore')

    range: Range
    paragraphStyle: ParagraphStyle
    fields: str


class DeleteParagraphBulletsRequest(BaseModel):
    """Deletes bullets from a range of text."""

    model_config = ConfigDict(extra='ignore')

    range: Range


class CreateParagraphBulletsRequest(BaseModel):
    """Creates bullets for a range of text."""

    model_config = ConfigDict(extra='ignore')

    range: Range
    bulletPreset: str


class DeleteContentRangeRequest(BaseModel):
    """Deletes a range of content from a document."""

    model_config = ConfigDict(extra='ignore')

    range: Range


class Request(BaseModel):
    """A single request in a batch update."""

    model_config = ConfigDict(extra='ignore')

    insertText: Optional[InsertTextRequest] = None
    updateTextStyle: Optional[UpdateTextStyleRequest] = None
    updateParagraphStyle: Optional[UpdateParagraphStyleRequest] = None
    deleteParagraphBullets: Optional[DeleteParagraphBulletsRequest] = None
    createParagraphBullets: Optional[CreateParagraphBulletsRequest] = None
    deleteContentRange: Optional[DeleteContentRangeRequest] = None


class SectionBreak(BaseModel):
    """A section break."""

    model_config = ConfigDict(extra='ignore')

    sectionStyle: Optional[Any] = None


class TableCell(BaseModel):
    """A table cell."""

    model_config = ConfigDict(extra='ignore')

    content: List["StructuralElement"]
    startIndex: int
    endIndex: int


class TableRow(BaseModel):
    """A table row."""

    model_config = ConfigDict(extra='ignore')

    tableCells: List[TableCell]
    startIndex: int
    endIndex: int


class Table(BaseModel):
    """A table."""

    model_config = ConfigDict(extra='ignore')

    tableRows: List[TableRow]
    columns: int
    rows: int


class TableOfContents(BaseModel):
    """A table of contents."""

    model_config = ConfigDict(extra='ignore')

    content: List["StructuralElement"]


class AutoText(BaseModel):
    """Auto text."""

    model_config = ConfigDict(extra='ignore')

    type: str
    textStyle: Optional["TextStyle"] = None


class PageBreak(BaseModel):
    """A page break."""

    model_config = ConfigDict(extra='ignore')

    textStyle: Optional["TextStyle"] = None


class ColumnBreak(BaseModel):
    """A column break."""

    model_config = ConfigDict(extra='ignore')

    textStyle: Optional["TextStyle"] = None


class FootnoteReference(BaseModel):
    """A footnote reference."""

    model_config = ConfigDict(extra='ignore')

    footnoteId: str
    footnoteNumber: Optional[str] = None
    textStyle: Optional["TextStyle"] = None


class HorizontalRule(BaseModel):
    """A horizontal rule."""

    model_config = ConfigDict(extra='ignore')

    textStyle: Optional["TextStyle"] = None


class Equation(BaseModel):
    """An equation."""

    model_config = ConfigDict(extra='ignore')


class Person(BaseModel):
    """A person."""

    model_config = ConfigDict(extra='ignore')

    personProperties: Optional[Any] = None
    textStyle: Optional["TextStyle"] = None


class RichLink(BaseModel):
    """A rich link."""

    model_config = ConfigDict(extra='ignore')

    richLinkProperties: Optional[Any] = None
    textStyle: Optional["TextStyle"] = None


class DateElementProperties(BaseModel):
    """Properties of a date element."""

    model_config = ConfigDict(extra='ignore')

    timestamp: str
    locale: str
    dateFormat: str
    timeFormat: str
    displayText: str


class DateElement(BaseModel):
    """A date element."""

    model_config = ConfigDict(extra='ignore')

    dateId: str
    textStyle: Optional["TextStyle"] = None
    dateElementProperties: Optional[DateElementProperties] = None


class ParagraphElement(BaseModel):
    """A paragraph element."""

    model_config = ConfigDict(extra='ignore')

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


class Paragraph(BaseModel):
    """A paragraph."""

    model_config = ConfigDict(extra='ignore')

    elements: List[ParagraphElement]
    paragraphStyle: Optional[ParagraphStyle] = None


class StructuralElement(BaseModel):
    """A structural element."""

    model_config = ConfigDict(extra='ignore')

    def model_post_init(self, __context: Any) -> None:
        """Post-initialization to set default startIndex."""
        if self.startIndex is None:
            self.startIndex = 1

    startIndex: Optional[int] = None
    endIndex: Optional[int] = None
    paragraph: Optional[Paragraph] = None
    sectionBreak: Optional[SectionBreak] = None
    table: Optional[Table] = None
    tableOfContents: Optional[TableOfContents] = None


class Body(BaseModel):
    """The body of a document."""

    model_config = ConfigDict(extra='ignore')

    content: List[StructuralElement]


class TextRun(BaseModel):
    """A text run."""

    model_config = ConfigDict(extra='ignore')

    content: str
    textStyle: Optional[TextStyle] = None


class DocumentStyle(BaseModel):
    """The style of a document."""

    model_config = ConfigDict(extra='ignore')

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


class NamedStyle(BaseModel):
    """A named style."""

    model_config = ConfigDict(extra='ignore')

    textStyle: Optional[TextStyle] = None
    paragraphStyle: Optional[ParagraphStyle] = None


class NamedStyles(BaseModel):
    """The named styles of a document."""

    model_config = ConfigDict(extra='ignore')

    styles: List[NamedStyle]


class Document(BaseModel):
    """A Google Docs document."""

    model_config = ConfigDict(from_attributes=True, extra='ignore')

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
