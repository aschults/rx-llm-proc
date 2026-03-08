"""Sample document structure for testing, containing a variety of elements."""

from typing import Any

from rxllmproc.docs.types import (
    Body,
    Paragraph,
    ParagraphElement,
    ParagraphStyle,
    SectionBreak,
    StructuralElement,
    TextRun,
    TextStyle,
    Table,
    TableRow,
    TableCell,
    TableOfContents,
    DateElement,
    DateElementProperties,
    FootnoteReference,
    HorizontalRule,
    Person,
    RichLink,
    Dimension,
    ForegroundColor,
    Color,
    RgbColor,
    Link,
)
from rxllmproc.docs import docs_text

DOC_BODY = Body(
    content=[
        StructuralElement(
            startIndex=1,
            endIndex=1,
            sectionBreak=SectionBreak(
                sectionStyle={
                    "columnSeparatorStyle": "NONE",
                    "contentDirection": "LEFT_TO_RIGHT",
                    "sectionType": "CONTINUOUS",
                }
            ),
        ),
        StructuralElement(
            startIndex=1,
            endIndex=18,
            paragraph=Paragraph(
                elements=[
                    ParagraphElement(
                        startIndex=1,
                        endIndex=18,
                        textRun=TextRun(
                            content="All Elements Doc\n",
                            textStyle=TextStyle(),
                        ),
                    )
                ],
                paragraphStyle=ParagraphStyle(
                    namedStyleType="TITLE",
                    headingId="h.rusrurcqkyed",
                ),
            ),
        ),
        StructuralElement(
            startIndex=18,
            endIndex=19,
            paragraph=Paragraph(
                elements=[
                    ParagraphElement(
                        startIndex=18,
                        endIndex=19,
                        textRun=TextRun(
                            content="\n",
                            textStyle=TextStyle(),
                        ),
                    )
                ],
                paragraphStyle=ParagraphStyle(
                    namedStyleType="NORMAL_TEXT",
                ),
            ),
        ),
        StructuralElement(
            startIndex=19,
            endIndex=23,
            paragraph=Paragraph(
                elements=[
                    ParagraphElement(
                        startIndex=19,
                        endIndex=23,
                        textRun=TextRun(
                            content="TOC\n",
                            textStyle=TextStyle(),
                        ),
                    )
                ],
                paragraphStyle=ParagraphStyle(
                    namedStyleType="NORMAL_TEXT",
                ),
            ),
        ),
        StructuralElement(
            startIndex=23,
            endIndex=36,
            tableOfContents=TableOfContents(
                content=[
                    StructuralElement(
                        startIndex=24,
                        endIndex=35,
                        paragraph=Paragraph(
                            elements=[
                                ParagraphElement(
                                    startIndex=24,
                                    endIndex=33,
                                    textRun=TextRun(
                                        content="Heading2\t",
                                        textStyle=TextStyle(
                                            bold=True,
                                            foregroundColor=ForegroundColor(
                                                color=Color(rgbColor=RgbColor())
                                            ),
                                            link=Link(
                                                headingId="h.jd1elpngyb99"
                                            ),
                                        ),
                                    ),
                                ),
                                ParagraphElement(
                                    startIndex=33,
                                    endIndex=34,
                                    textRun=TextRun(
                                        content="1",
                                        textStyle=TextStyle(
                                            bold=True,
                                            link=Link(
                                                headingId="h.jd1elpngyb99"
                                            ),
                                        ),
                                    ),
                                ),
                                ParagraphElement(
                                    startIndex=34,
                                    endIndex=35,
                                    textRun=TextRun(
                                        content="\n",
                                        textStyle=TextStyle(
                                            bold=True,
                                            foregroundColor=ForegroundColor(
                                                color=Color(rgbColor=RgbColor())
                                            ),
                                        ),
                                    ),
                                ),
                            ],
                            paragraphStyle=ParagraphStyle(
                                namedStyleType="NORMAL_TEXT"
                            ),
                        ),
                    )
                ]
            ),
        ),
        StructuralElement(
            startIndex=36,
            endIndex=43,
            paragraph=Paragraph(
                elements=[
                    ParagraphElement(
                        startIndex=36,
                        endIndex=43,
                        textRun=TextRun(
                            content="EndTOC\n",
                            textStyle=TextStyle(),
                        ),
                    )
                ],
                paragraphStyle=ParagraphStyle(
                    namedStyleType="NORMAL_TEXT",
                ),
            ),
        ),
        StructuralElement(
            startIndex=43,
            endIndex=44,
            paragraph=Paragraph(
                elements=[
                    ParagraphElement(
                        startIndex=43,
                        endIndex=44,
                        textRun=TextRun(
                            content="\n",
                            textStyle=TextStyle(),
                        ),
                    )
                ],
                paragraphStyle=ParagraphStyle(
                    namedStyleType="NORMAL_TEXT",
                ),
            ),
        ),
        StructuralElement(
            startIndex=44,
            endIndex=114,
            table=Table(
                columns=3,
                rows=3,
                tableRows=[
                    TableRow(
                        startIndex=45,
                        endIndex=70,
                        tableCells=[
                            TableCell(
                                startIndex=46,
                                endIndex=56,
                                content=[
                                    StructuralElement(
                                        startIndex=47,
                                        endIndex=56,
                                        paragraph=Paragraph(
                                            elements=[
                                                ParagraphElement(
                                                    startIndex=47,
                                                    endIndex=56,
                                                    textRun=TextRun(
                                                        content="Heading2\n",
                                                        textStyle=TextStyle(),
                                                    ),
                                                )
                                            ],
                                            paragraphStyle=ParagraphStyle(
                                                namedStyleType="HEADING_2",
                                                headingId="h.jd1elpngyb99",
                                            ),
                                        ),
                                    )
                                ],
                            ),
                            TableCell(
                                startIndex=56,
                                endIndex=59,
                                content=[
                                    StructuralElement(
                                        startIndex=57,
                                        endIndex=59,
                                        paragraph=Paragraph(
                                            elements=[
                                                ParagraphElement(
                                                    startIndex=57,
                                                    endIndex=58,
                                                    dateElement=DateElement(
                                                        dateId="kix.6qqmqoxth1t4",
                                                        textStyle=TextStyle(),
                                                        dateElementProperties=DateElementProperties(
                                                            timestamp="2026-02-13T12:00:00Z",
                                                            locale="en",
                                                            dateFormat="DATE_FORMAT_MONTH_DAY_YEAR_ABBREVIATED",
                                                            timeFormat="TIME_FORMAT_DISABLED",
                                                            displayText="Feb 13, 2026",
                                                        ),
                                                    ),
                                                ),
                                                ParagraphElement(
                                                    startIndex=58,
                                                    endIndex=59,
                                                    textRun=TextRun(
                                                        content="\n",
                                                        textStyle=TextStyle(),
                                                    ),
                                                ),
                                            ],
                                            paragraphStyle=ParagraphStyle(
                                                namedStyleType="NORMAL_TEXT",
                                                indentStart=Dimension(0, "PT"),
                                                indentFirstLine=Dimension(
                                                    0, "PT"
                                                ),
                                            ),
                                        ),
                                    )
                                ],
                            ),
                            TableCell(
                                startIndex=59,
                                endIndex=70,
                                content=[
                                    StructuralElement(
                                        startIndex=60,
                                        endIndex=70,
                                        paragraph=Paragraph(
                                            elements=[
                                                ParagraphElement(
                                                    startIndex=60,
                                                    endIndex=68,
                                                    textRun=TextRun(
                                                        content="footnote",
                                                        textStyle=TextStyle(),
                                                    ),
                                                ),
                                                ParagraphElement(
                                                    startIndex=68,
                                                    endIndex=69,
                                                    footnoteReference=FootnoteReference(
                                                        footnoteId="kix.idiyz4dleh0l",
                                                        footnoteNumber="1",
                                                        textStyle=TextStyle(),
                                                    ),
                                                ),
                                                ParagraphElement(
                                                    startIndex=69,
                                                    endIndex=70,
                                                    textRun=TextRun(
                                                        content="\n",
                                                        textStyle=TextStyle(),
                                                    ),
                                                ),
                                            ],
                                            paragraphStyle=ParagraphStyle(
                                                namedStyleType="NORMAL_TEXT",
                                                indentStart=Dimension(0, "PT"),
                                                indentFirstLine=Dimension(
                                                    0, "PT"
                                                ),
                                            ),
                                        ),
                                    )
                                ],
                            ),
                        ],
                    ),
                    # Row 2 and 3 omitted for brevity as they follow similar pattern,
                    # but included in full file generation below.
                    TableRow(
                        startIndex=70,
                        endIndex=88,
                        tableCells=[
                            TableCell(
                                startIndex=71,
                                endIndex=73,
                                content=[
                                    StructuralElement(
                                        startIndex=72,
                                        endIndex=73,
                                        paragraph=Paragraph(
                                            elements=[
                                                ParagraphElement(
                                                    startIndex=72,
                                                    endIndex=73,
                                                    textRun=TextRun(
                                                        content="\n",
                                                        textStyle=TextStyle(),
                                                    ),
                                                )
                                            ],
                                            paragraphStyle=ParagraphStyle(
                                                namedStyleType="NORMAL_TEXT",
                                                indentStart=Dimension(0, "PT"),
                                                indentFirstLine=Dimension(
                                                    0, "PT"
                                                ),
                                            ),
                                        ),
                                    )
                                ],
                            ),
                            TableCell(
                                startIndex=73,
                                endIndex=86,
                                content=[
                                    StructuralElement(
                                        startIndex=74,
                                        endIndex=86,
                                        paragraph=Paragraph(
                                            elements=[
                                                ParagraphElement(
                                                    startIndex=74,
                                                    endIndex=86,
                                                    textRun=TextRun(
                                                        content="Normal text\n",
                                                        textStyle=TextStyle(),
                                                    ),
                                                )
                                            ],
                                            paragraphStyle=ParagraphStyle(
                                                namedStyleType="NORMAL_TEXT",
                                                indentStart=Dimension(0, "PT"),
                                                indentFirstLine=Dimension(
                                                    0, "PT"
                                                ),
                                            ),
                                        ),
                                    )
                                ],
                            ),
                            TableCell(
                                startIndex=86,
                                endIndex=88,
                                content=[
                                    StructuralElement(
                                        startIndex=87,
                                        endIndex=88,
                                        paragraph=Paragraph(
                                            elements=[
                                                ParagraphElement(
                                                    startIndex=87,
                                                    endIndex=88,
                                                    textRun=TextRun(
                                                        content="\n",
                                                        textStyle=TextStyle(),
                                                    ),
                                                )
                                            ],
                                            paragraphStyle=ParagraphStyle(
                                                namedStyleType="NORMAL_TEXT",
                                                indentStart=Dimension(0, "PT"),
                                                indentFirstLine=Dimension(
                                                    0, "PT"
                                                ),
                                            ),
                                        ),
                                    )
                                ],
                            ),
                        ],
                    ),
                    # Row 3
                    TableRow(
                        startIndex=88,
                        endIndex=113,
                        tableCells=[
                            TableCell(
                                startIndex=89,
                                endIndex=91,
                                content=[
                                    StructuralElement(
                                        startIndex=90,
                                        endIndex=91,
                                        paragraph=Paragraph(
                                            elements=[
                                                ParagraphElement(
                                                    startIndex=90,
                                                    endIndex=91,
                                                    textRun=TextRun(
                                                        content="\n",
                                                        textStyle=TextStyle(),
                                                    ),
                                                )
                                            ],
                                            paragraphStyle=ParagraphStyle(
                                                namedStyleType="NORMAL_TEXT",
                                                indentStart=Dimension(0, "PT"),
                                                indentFirstLine=Dimension(
                                                    0, "PT"
                                                ),
                                            ),
                                        ),
                                    )
                                ],
                            ),
                            TableCell(
                                startIndex=91,
                                endIndex=111,
                                content=[
                                    StructuralElement(
                                        startIndex=92,
                                        endIndex=93,
                                        paragraph=Paragraph(
                                            elements=[
                                                ParagraphElement(
                                                    startIndex=92,
                                                    endIndex=93,
                                                    textRun=TextRun(
                                                        content="\n",
                                                        textStyle=TextStyle(),
                                                    ),
                                                )
                                            ],
                                            paragraphStyle=ParagraphStyle(
                                                namedStyleType="NORMAL_TEXT",
                                                indentStart=Dimension(0, "PT"),
                                                indentFirstLine=Dimension(
                                                    0, "PT"
                                                ),
                                            ),
                                        ),
                                    ),
                                    StructuralElement(
                                        startIndex=93,
                                        endIndex=110,
                                        paragraph=Paragraph(
                                            elements=[
                                                ParagraphElement(
                                                    startIndex=93,
                                                    endIndex=110,
                                                    textRun=TextRun(
                                                        content="Between newlines\n",
                                                        textStyle=TextStyle(),
                                                    ),
                                                )
                                            ],
                                            paragraphStyle=ParagraphStyle(
                                                namedStyleType="NORMAL_TEXT",
                                                indentStart=Dimension(0, "PT"),
                                                indentFirstLine=Dimension(
                                                    0, "PT"
                                                ),
                                            ),
                                        ),
                                    ),
                                    StructuralElement(
                                        startIndex=110,
                                        endIndex=111,
                                        paragraph=Paragraph(
                                            elements=[
                                                ParagraphElement(
                                                    startIndex=110,
                                                    endIndex=111,
                                                    textRun=TextRun(
                                                        content="\n",
                                                        textStyle=TextStyle(),
                                                    ),
                                                )
                                            ],
                                            paragraphStyle=ParagraphStyle(
                                                namedStyleType="NORMAL_TEXT",
                                                indentStart=Dimension(0, "PT"),
                                                indentFirstLine=Dimension(
                                                    0, "PT"
                                                ),
                                            ),
                                        ),
                                    ),
                                ],
                            ),
                            TableCell(
                                startIndex=111,
                                endIndex=113,
                                content=[
                                    StructuralElement(
                                        startIndex=112,
                                        endIndex=113,
                                        paragraph=Paragraph(
                                            elements=[
                                                ParagraphElement(
                                                    startIndex=112,
                                                    endIndex=113,
                                                    textRun=TextRun(
                                                        content="\n",
                                                        textStyle=TextStyle(),
                                                    ),
                                                )
                                            ],
                                            paragraphStyle=ParagraphStyle(
                                                namedStyleType="NORMAL_TEXT",
                                                indentStart=Dimension(0, "PT"),
                                                indentFirstLine=Dimension(
                                                    0, "PT"
                                                ),
                                            ),
                                        ),
                                    )
                                ],
                            ),
                        ],
                    ),
                ],
            ),
        ),
        # Remaining paragraphs
        StructuralElement(
            startIndex=114,
            endIndex=115,
            paragraph=Paragraph(
                elements=[
                    ParagraphElement(
                        startIndex=114,
                        endIndex=115,
                        textRun=TextRun(content="\n", textStyle=TextStyle()),
                    )
                ],
                paragraphStyle=ParagraphStyle(namedStyleType="NORMAL_TEXT"),
            ),
        ),
        StructuralElement(
            startIndex=115,
            endIndex=117,
            paragraph=Paragraph(
                elements=[
                    ParagraphElement(startIndex=115, endIndex=116),
                    ParagraphElement(
                        startIndex=116,
                        endIndex=117,
                        textRun=TextRun(content="\n", textStyle=TextStyle()),
                    ),
                ],
                paragraphStyle=ParagraphStyle(namedStyleType="NORMAL_TEXT"),
            ),
        ),
        StructuralElement(
            startIndex=117,
            endIndex=118,
            paragraph=Paragraph(
                elements=[
                    ParagraphElement(
                        startIndex=117,
                        endIndex=118,
                        textRun=TextRun(content="\n", textStyle=TextStyle()),
                    )
                ],
                paragraphStyle=ParagraphStyle(namedStyleType="NORMAL_TEXT"),
            ),
        ),
        StructuralElement(
            startIndex=118,
            endIndex=128,
            paragraph=Paragraph(
                elements=[
                    ParagraphElement(
                        startIndex=118,
                        endIndex=127,
                        textRun=TextRun(
                            content="some link",
                            textStyle=TextStyle(
                                foregroundColor=ForegroundColor(
                                    color=Color(
                                        rgbColor=RgbColor(
                                            red=0.06666667,
                                            green=0.33333334,
                                            blue=0.8,
                                        )
                                    )
                                ),
                                link=Link(url="http://www.google.com"),
                            ),
                        ),
                    ),
                    ParagraphElement(
                        startIndex=127,
                        endIndex=128,
                        textRun=TextRun(content="\n", textStyle=TextStyle()),
                    ),
                ],
                paragraphStyle=ParagraphStyle(namedStyleType="NORMAL_TEXT"),
            ),
        ),
        StructuralElement(
            startIndex=128,
            endIndex=129,
            paragraph=Paragraph(
                elements=[
                    ParagraphElement(
                        startIndex=128,
                        endIndex=129,
                        textRun=TextRun(content="\n", textStyle=TextStyle()),
                    )
                ],
                paragraphStyle=ParagraphStyle(namedStyleType="NORMAL_TEXT"),
            ),
        ),
        StructuralElement(
            startIndex=129,
            endIndex=131,
            paragraph=Paragraph(
                elements=[
                    ParagraphElement(
                        startIndex=129,
                        endIndex=130,
                        horizontalRule=HorizontalRule(textStyle=TextStyle()),
                    ),
                    ParagraphElement(
                        startIndex=130,
                        endIndex=131,
                        textRun=TextRun(content="\n", textStyle=TextStyle()),
                    ),
                ],
                paragraphStyle=ParagraphStyle(namedStyleType="NORMAL_TEXT"),
            ),
        ),
        StructuralElement(
            startIndex=131,
            endIndex=132,
            paragraph=Paragraph(
                elements=[
                    ParagraphElement(
                        startIndex=131,
                        endIndex=132,
                        textRun=TextRun(content="\n", textStyle=TextStyle()),
                    )
                ],
                paragraphStyle=ParagraphStyle(namedStyleType="NORMAL_TEXT"),
            ),
        ),
        StructuralElement(
            startIndex=132,
            endIndex=134,
            paragraph=Paragraph(
                elements=[
                    ParagraphElement(
                        startIndex=132,
                        endIndex=133,
                        person=Person(
                            personProperties={
                                "name": "info@gonser.ch",
                                "email": "info@gonser.ch",
                            },
                            textStyle=TextStyle(),
                        ),
                    ),
                    ParagraphElement(
                        startIndex=133,
                        endIndex=134,
                        textRun=TextRun(content="\n", textStyle=TextStyle()),
                    ),
                ],
                paragraphStyle=ParagraphStyle(namedStyleType="NORMAL_TEXT"),
            ),
        ),
        StructuralElement(
            startIndex=134,
            endIndex=136,
            paragraph=Paragraph(
                elements=[
                    ParagraphElement(
                        startIndex=134,
                        endIndex=136,
                        textRun=TextRun(content="\n", textStyle=TextStyle()),
                    )
                ],
                paragraphStyle=ParagraphStyle(namedStyleType="NORMAL_TEXT"),
            ),
        ),
        StructuralElement(
            startIndex=136,
            endIndex=137,
            paragraph=Paragraph(
                elements=[
                    ParagraphElement(
                        startIndex=136,
                        endIndex=137,
                        textRun=TextRun(content="\n", textStyle=TextStyle()),
                    )
                ],
                paragraphStyle=ParagraphStyle(namedStyleType="NORMAL_TEXT"),
            ),
        ),
        StructuralElement(
            startIndex=137,
            endIndex=139,
            paragraph=Paragraph(
                elements=[
                    ParagraphElement(
                        startIndex=137,
                        endIndex=138,
                        richLink=RichLink(
                            richLinkProperties={
                                "title": "Text structures",
                                "uri": "https://docs.google.com/document/u/0/d/1ZS6AoQcCCydFn955A6_yj8rSSNs-JwbHl8hMQTMizV0/edit",
                                "mimeType": "application/vnd.google-apps.document",
                            },
                            textStyle=TextStyle(),
                        ),
                    ),
                    ParagraphElement(
                        startIndex=138,
                        endIndex=139,
                        textRun=TextRun(content="\n", textStyle=TextStyle()),
                    ),
                ],
                paragraphStyle=ParagraphStyle(namedStyleType="NORMAL_TEXT"),
            ),
        ),
        StructuralElement(
            startIndex=139,
            endIndex=140,
            paragraph=Paragraph(
                elements=[
                    ParagraphElement(
                        startIndex=139,
                        endIndex=140,
                        textRun=TextRun(content="\n", textStyle=TextStyle()),
                    )
                ],
                paragraphStyle=ParagraphStyle(namedStyleType="NORMAL_TEXT"),
            ),
        ),
        StructuralElement(
            startIndex=140,
            endIndex=141,
            paragraph=Paragraph(
                elements=[
                    ParagraphElement(
                        startIndex=140,
                        endIndex=141,
                        textRun=TextRun(content="\n", textStyle=TextStyle()),
                    )
                ],
                paragraphStyle=ParagraphStyle(namedStyleType="NORMAL_TEXT"),
            ),
        ),
    ]
)

SAMPLE_DOC_JSON: Any = [
    {
        'level': 'text',
        'text': '',
        'start': 1,
        'end': 1,
        'heading_id': None,
        'subsections': [],
    },
    {
        'level': 'TITLE',
        'text': 'All Elements Doc\n',
        'start': 1,
        'end': 18,
        'heading_id': 'h.rusrurcqkyed',
        'subsections': [
            {
                'level': 'text',
                'text': '\nTOC\n\U0001ffffHeading2\t1\n\U0001ffffEndTOC\n\n\U0002ffff\U0003ffff\U0004ffffHeading2\n\U0004ffff\U0005ffff\n\U0004fffffootnote\U0006ffff\n\U0003ffff\U0004ffff\n\U0004ffffNormal text\n\U0004ffff\n\U0003ffff\U0004ffff\n\U0004ffff\nBetween newlines\n\n\U0004ffff\n\U0002ffff\n\U0006ffff\n\nsome link\n\n\U0006ffff\n\n\U0006ffff\n\ue907\n\n\U0006ffff\n\n\n',
                'start': 18,
                'end': 141,
                'heading_id': None,
                'subsections': [],
            }
        ],
    },
]

DOCS_TEXT = (
    f"{docs_text.NON_CHAR}All Elements Doc\n\nTOC\n{docs_text.NON_CHAR}Heading2\t1\n{docs_text.NON_CHAR}EndTOC\n\n"
    f"{docs_text.TABLE_START}{docs_text.TABLE_ROW}{docs_text.TABLE_CELL}Heading2\n{docs_text.TABLE_CELL}{docs_text.DATE_FILLER}\n"
    f"{docs_text.TABLE_CELL}footnote{docs_text.CHIP_FILLER}\n{docs_text.TABLE_ROW}{docs_text.TABLE_CELL}\n{docs_text.TABLE_CELL}"
    f"Normal text\n{docs_text.TABLE_CELL}\n{docs_text.TABLE_ROW}{docs_text.TABLE_CELL}\n{docs_text.TABLE_CELL}"
    f"\nBetween newlines\n\n{docs_text.TABLE_CELL}\n{docs_text.TABLE_START}\n{docs_text.CHIP_FILLER}\n\nsome link\n\n"
    f"{docs_text.CHIP_FILLER}\n\n{docs_text.CHIP_FILLER}\n\ue907\n\n{docs_text.CHIP_FILLER}\n\n\n"
)
