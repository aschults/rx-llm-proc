"""Dataclasses for Google Docs API requests."""

from typing import Any, Dict, List, Optional
import pydantic


class Location(pydantic.BaseModel):
    """A location in a document."""

    model_config = pydantic.ConfigDict(extra='ignore')

    index: int


class Dimension(pydantic.BaseModel):
    """A magnitude in a single direction in the specified units."""

    model_config = pydantic.ConfigDict(extra='ignore')

    magnitude: float = 0.0
    unit: str = "pt"


class InsertTextRequest(pydantic.BaseModel):
    """Inserts text into a document."""

    model_config = pydantic.ConfigDict(extra='ignore')

    text: str
    location: Location


class RgbColor(pydantic.BaseModel):
    """An RGB color."""

    model_config = pydantic.ConfigDict(extra='ignore')

    # Set optional since REST call returns RgbColor with no fields.
    red: Optional[float] = None
    green: Optional[float] = None
    blue: Optional[float] = None


class Color(pydantic.BaseModel):
    """A color."""

    model_config = pydantic.ConfigDict(extra='ignore')

    rgbColor: RgbColor


class ForegroundColor(pydantic.BaseModel):
    """The foreground color of a text style."""

    model_config = pydantic.ConfigDict(extra='ignore')

    color: Color


class WeightedFontFamily(pydantic.BaseModel):
    """A weighted font family."""

    model_config = pydantic.ConfigDict(extra='ignore')

    fontFamily: str | None = None
    weight: int | None = None


class Link(pydantic.BaseModel):
    """A link."""

    model_config = pydantic.ConfigDict(extra='ignore')

    url: str | None = None
    headingId: str | None = None


class TextStyle(pydantic.BaseModel):
    """A text style."""

    model_config = pydantic.ConfigDict(extra='ignore')

    bold: Optional[bool] = None
    italic: Optional[bool] = None
    strikethrough: Optional[bool] = None
    weightedFontFamily: Optional[WeightedFontFamily] = None
    foregroundColor: Optional[ForegroundColor] = None
    link: Optional[Link] = None


class Range(pydantic.BaseModel):
    """A range of text in a document."""

    model_config = pydantic.ConfigDict(extra='ignore')

    startIndex: int
    endIndex: int


class UpdateTextStyleRequest(pydantic.BaseModel):
    """Updates the text style of a range of text."""

    model_config = pydantic.ConfigDict(extra='ignore')

    range: Range
    textStyle: TextStyle
    fields: str


class ParagraphStyle(pydantic.BaseModel):
    """A paragraph style."""

    model_config = pydantic.ConfigDict(extra='ignore')

    namedStyleType: str
    indentStart: Optional[Dimension] = None
    indentFirstLine: Optional[Dimension] = None
    headingId: Optional[str] = None


class UpdateParagraphStyleRequest(pydantic.BaseModel):
    """Updates the paragraph style of a range of text."""

    model_config = pydantic.ConfigDict(extra='ignore')

    range: Range
    paragraphStyle: ParagraphStyle
    fields: str


class DeleteParagraphBulletsRequest(pydantic.BaseModel):
    """Deletes bullets from a range of text."""

    model_config = pydantic.ConfigDict(extra='ignore')

    range: Range


class CreateParagraphBulletsRequest(pydantic.BaseModel):
    """Creates bullets for a range of text."""

    model_config = pydantic.ConfigDict(extra='ignore')

    range: Range
    bulletPreset: str


class DeleteContentRangeRequest(pydantic.BaseModel):
    """Deletes a range of content from a document."""

    model_config = pydantic.ConfigDict(extra='ignore')

    range: Range


class Request(pydantic.BaseModel):
    """A single request in a batch update."""

    model_config = pydantic.ConfigDict(extra='ignore')

    insertText: Optional[InsertTextRequest] = None
    updateTextStyle: Optional[UpdateTextStyleRequest] = None
    updateParagraphStyle: Optional[UpdateParagraphStyleRequest] = None
    deleteParagraphBullets: Optional[DeleteParagraphBulletsRequest] = None
    createParagraphBullets: Optional[CreateParagraphBulletsRequest] = None
    deleteContentRange: Optional[DeleteContentRangeRequest] = None


class SectionBreak(pydantic.BaseModel):
    """A section break."""

    model_config = pydantic.ConfigDict(extra='ignore')

    sectionStyle: Optional[Any] = None


class TableCell(pydantic.BaseModel):
    """A table cell."""

    model_config = pydantic.ConfigDict(extra='ignore')

    content: List["StructuralElement"]
    startIndex: int
    endIndex: int


class TableRow(pydantic.BaseModel):
    """A table row."""

    model_config = pydantic.ConfigDict(extra='ignore')

    tableCells: List[TableCell]
    startIndex: int
    endIndex: int


class Table(pydantic.BaseModel):
    """A table."""

    model_config = pydantic.ConfigDict(extra='ignore')

    tableRows: List[TableRow]
    columns: int
    rows: int


class TableOfContents(pydantic.BaseModel):
    """A table of contents."""

    model_config = pydantic.ConfigDict(extra='ignore')

    content: List["StructuralElement"]


class AutoText(pydantic.BaseModel):
    """Auto text."""

    model_config = pydantic.ConfigDict(extra='ignore')

    type: str
    textStyle: Optional["TextStyle"] = None


class PageBreak(pydantic.BaseModel):
    """A page break."""

    model_config = pydantic.ConfigDict(extra='ignore')

    textStyle: Optional["TextStyle"] = None


class ColumnBreak(pydantic.BaseModel):
    """A column break."""

    model_config = pydantic.ConfigDict(extra='ignore')

    textStyle: Optional["TextStyle"] = None


class FootnoteReference(pydantic.BaseModel):
    """A footnote reference."""

    model_config = pydantic.ConfigDict(extra='ignore')

    footnoteId: str
    footnoteNumber: Optional[str] = None
    textStyle: Optional["TextStyle"] = None


class HorizontalRule(pydantic.BaseModel):
    """A horizontal rule."""

    model_config = pydantic.ConfigDict(extra='ignore')

    textStyle: Optional["TextStyle"] = None


class Equation(pydantic.BaseModel):
    """An equation."""

    model_config = pydantic.ConfigDict(extra='ignore')


class Person(pydantic.BaseModel):
    """A person."""

    model_config = pydantic.ConfigDict(extra='ignore')

    personProperties: Optional[Any] = None
    textStyle: Optional["TextStyle"] = None


class RichLink(pydantic.BaseModel):
    """A rich link."""

    model_config = pydantic.ConfigDict(extra='ignore')

    richLinkProperties: Optional[Any] = None
    textStyle: Optional["TextStyle"] = None


class DateElementProperties(pydantic.BaseModel):
    """Properties of a date element."""

    model_config = pydantic.ConfigDict(extra='ignore')

    timestamp: str
    locale: str
    dateFormat: str
    timeFormat: str
    displayText: str


class DateElement(pydantic.BaseModel):
    """A date element."""

    model_config = pydantic.ConfigDict(extra='ignore')

    dateId: str
    textStyle: Optional["TextStyle"] = None
    dateElementProperties: Optional[DateElementProperties] = None


class ParagraphElement(pydantic.BaseModel):
    """A paragraph element."""

    model_config = pydantic.ConfigDict(extra='ignore')

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


class Paragraph(pydantic.BaseModel):
    """A paragraph."""

    model_config = pydantic.ConfigDict(extra='ignore')

    elements: List[ParagraphElement]
    paragraphStyle: Optional[ParagraphStyle] = None


class StructuralElement(pydantic.BaseModel):
    """A structural element."""

    model_config = pydantic.ConfigDict(extra='ignore')

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


class Body(pydantic.BaseModel):
    """The body of a document."""

    model_config = pydantic.ConfigDict(extra='ignore')

    content: List[StructuralElement]


class TextRun(pydantic.BaseModel):
    """A text run."""

    model_config = pydantic.ConfigDict(extra='ignore')

    content: str
    textStyle: Optional[TextStyle] = None


class DocumentStyle(pydantic.BaseModel):
    """The style of a document."""

    model_config = pydantic.ConfigDict(extra='ignore')

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


class NamedStyle(pydantic.BaseModel):
    """A named style."""

    model_config = pydantic.ConfigDict(extra='ignore')

    textStyle: Optional[TextStyle] = None
    paragraphStyle: Optional[ParagraphStyle] = None


class NamedStyles(pydantic.BaseModel):
    """The named styles of a document."""

    model_config = pydantic.ConfigDict(extra='ignore')

    styles: List[NamedStyle]


class Document(pydantic.BaseModel):
    """A Google Docs document."""

    model_config = pydantic.ConfigDict(from_attributes=True, extra='ignore')

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
