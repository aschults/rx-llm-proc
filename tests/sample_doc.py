"""Sample document structure for testing.

JQ Pre-processing: `jq 'delpaths([paths(type == "null")])|.body.content'`
"""

from typing import Any


from rxllmproc.docs.types import (
    Body,
    Dimension,
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
)

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
            endIndex=14,
            paragraph=Paragraph(
                elements=[
                    ParagraphElement(
                        startIndex=1,
                        endIndex=14,
                        textRun=TextRun(
                            content="Before Title\n",
                            textStyle=TextStyle(),
                        ),
                    )
                ],
                paragraphStyle=ParagraphStyle(
                    namedStyleType="HEADING_3",
                    headingId="h.axltrzjqoy8x",
                ),
            ),
        ),
        StructuralElement(
            startIndex=14,
            endIndex=20,
            paragraph=Paragraph(
                elements=[
                    ParagraphElement(
                        startIndex=14,
                        endIndex=20,
                        textRun=TextRun(
                            content="Text1\n",
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
            startIndex=20,
            endIndex=26,
            paragraph=Paragraph(
                elements=[
                    ParagraphElement(
                        startIndex=20,
                        endIndex=26,
                        textRun=TextRun(
                            content="TITLE\n",
                            textStyle=TextStyle(),
                        ),
                    )
                ],
                paragraphStyle=ParagraphStyle(
                    namedStyleType="TITLE",
                    headingId="h.nufxjkhsuj35",
                ),
            ),
        ),
        StructuralElement(
            startIndex=26,
            endIndex=32,
            paragraph=Paragraph(
                elements=[
                    ParagraphElement(
                        startIndex=26,
                        endIndex=32,
                        textRun=TextRun(
                            content="Text2\n",
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
            startIndex=32,
            endIndex=41,
            paragraph=Paragraph(
                elements=[
                    ParagraphElement(
                        startIndex=32,
                        endIndex=41,
                        textRun=TextRun(
                            content="Heading3\n",
                            textStyle=TextStyle(),
                        ),
                    )
                ],
                paragraphStyle=ParagraphStyle(
                    namedStyleType="HEADING_3",
                    headingId="h.3k1198kg1e4d",
                ),
            ),
        ),
        StructuralElement(
            startIndex=41,
            endIndex=48,
            paragraph=Paragraph(
                elements=[
                    ParagraphElement(
                        startIndex=41,
                        endIndex=48,
                        textRun=TextRun(
                            content="Text 3\n",
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
            startIndex=48,
            endIndex=58,
            paragraph=Paragraph(
                elements=[
                    ParagraphElement(
                        startIndex=48,
                        endIndex=58,
                        textRun=TextRun(
                            content="Heading3b\n",
                            textStyle=TextStyle(),
                        ),
                    )
                ],
                paragraphStyle=ParagraphStyle(
                    namedStyleType="HEADING_3",
                    headingId="h.c7fpjsk6w9gb",
                ),
            ),
        ),
        StructuralElement(
            startIndex=58,
            endIndex=67,
            paragraph=Paragraph(
                elements=[
                    ParagraphElement(
                        startIndex=58,
                        endIndex=67,
                        textRun=TextRun(
                            content="Heading2\n",
                            textStyle=TextStyle(),
                        ),
                    )
                ],
                paragraphStyle=ParagraphStyle(
                    namedStyleType="HEADING_2",
                    headingId="h.bm9k5iq137dy",
                ),
            ),
        ),
        StructuralElement(
            startIndex=67,
            endIndex=74,
            paragraph=Paragraph(
                elements=[
                    ParagraphElement(
                        startIndex=67,
                        endIndex=74,
                        textRun=TextRun(
                            content="Text 4\n",
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
            startIndex=74,
            endIndex=89,
            table=Table(
                columns=2,
                rows=1,
                tableRows=[
                    TableRow(
                        startIndex=75,
                        endIndex=88,
                        tableCells=[
                            TableCell(
                                startIndex=76,
                                endIndex=82,
                                content=[
                                    StructuralElement(
                                        startIndex=77,
                                        endIndex=82,
                                        paragraph=Paragraph(
                                            elements=[
                                                ParagraphElement(
                                                    startIndex=77,
                                                    endIndex=82,
                                                    textRun=TextRun(
                                                        content="Tab1\n",
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
                                startIndex=82,
                                endIndex=88,
                                content=[
                                    StructuralElement(
                                        startIndex=83,
                                        endIndex=88,
                                        paragraph=Paragraph(
                                            elements=[
                                                ParagraphElement(
                                                    startIndex=83,
                                                    endIndex=88,
                                                    textRun=TextRun(
                                                        content="Tab2\n",
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
                    )
                ],
            ),
        ),
        StructuralElement(
            startIndex=89,
            endIndex=98,
            paragraph=Paragraph(
                elements=[
                    ParagraphElement(
                        startIndex=89,
                        endIndex=98,
                        textRun=TextRun(
                            content="Heading1\n",
                            textStyle=TextStyle(),
                        ),
                    )
                ],
                paragraphStyle=ParagraphStyle(
                    namedStyleType="HEADING_1",
                    headingId="h.ijgpd5cpeqd6",
                ),
            ),
        ),
        StructuralElement(
            startIndex=98,
            endIndex=108,
            paragraph=Paragraph(
                elements=[
                    ParagraphElement(
                        startIndex=98,
                        endIndex=108,
                        textRun=TextRun(
                            content="Heading2b\n",
                            textStyle=TextStyle(),
                        ),
                    )
                ],
                paragraphStyle=ParagraphStyle(
                    namedStyleType="HEADING_2",
                    headingId="h.v5p24o5fhtqo",
                ),
            ),
        ),
        StructuralElement(
            startIndex=108,
            endIndex=114,
            paragraph=Paragraph(
                elements=[
                    ParagraphElement(
                        startIndex=108,
                        endIndex=114,
                        textRun=TextRun(
                            content="Text4\n",
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
            startIndex=114,
            endIndex=122,
            paragraph=Paragraph(
                elements=[
                    ParagraphElement(
                        startIndex=114,
                        endIndex=122,
                        textRun=TextRun(
                            content="Text4.1\n",
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
            startIndex=122,
            endIndex=132,
            paragraph=Paragraph(
                elements=[
                    ParagraphElement(
                        startIndex=122,
                        endIndex=132,
                        textRun=TextRun(
                            content="Heading3c\n",
                            textStyle=TextStyle(),
                        ),
                    )
                ],
                paragraphStyle=ParagraphStyle(
                    namedStyleType="HEADING_3",
                    headingId="h.s94p0purx9bu",
                ),
            ),
        ),
        StructuralElement(
            startIndex=132,
            endIndex=138,
            paragraph=Paragraph(
                elements=[
                    ParagraphElement(
                        startIndex=132,
                        endIndex=138,
                        textRun=TextRun(
                            content="Text5\n",
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
            startIndex=138,
            endIndex=148,
            paragraph=Paragraph(
                elements=[
                    ParagraphElement(
                        startIndex=138,
                        endIndex=148,
                        textRun=TextRun(
                            content="Heading2c\n",
                            textStyle=TextStyle(),
                        ),
                    )
                ],
                paragraphStyle=ParagraphStyle(
                    namedStyleType="HEADING_2",
                    headingId="h.ji5bd3w737r8",
                ),
            ),
        ),
        StructuralElement(
            startIndex=148,
            endIndex=154,
            paragraph=Paragraph(
                elements=[
                    ParagraphElement(
                        startIndex=148,
                        endIndex=154,
                        textRun=TextRun(
                            content="Text6\n",
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
            startIndex=154,
            endIndex=164,
            paragraph=Paragraph(
                elements=[
                    ParagraphElement(
                        startIndex=154,
                        endIndex=164,
                        textRun=TextRun(
                            content="Heading3d\n",
                            textStyle=TextStyle(),
                        ),
                    )
                ],
                paragraphStyle=ParagraphStyle(
                    namedStyleType="HEADING_3",
                    headingId="h.akk1pid3gac1",
                ),
            ),
        ),
        StructuralElement(
            startIndex=164,
            endIndex=170,
            paragraph=Paragraph(
                elements=[
                    ParagraphElement(
                        startIndex=164,
                        endIndex=170,
                        textRun=TextRun(
                            content="Text7\n",
                            textStyle=TextStyle(),
                        ),
                    )
                ],
                paragraphStyle=ParagraphStyle(
                    namedStyleType="NORMAL_TEXT",
                ),
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
        'level': 'HEADING_3',
        'text': 'Before Title\n',
        'start': 1,
        'end': 14,
        'heading_id': 'h.axltrzjqoy8x',
        'subsections': [
            {
                'level': 'text',
                'text': 'Text1\n',
                'start': 14,
                'end': 20,
                'heading_id': None,
                'subsections': [],
            }
        ],
    },
    {
        'level': 'TITLE',
        'text': 'TITLE\n',
        'start': 20,
        'end': 26,
        'heading_id': 'h.nufxjkhsuj35',
        'subsections': [
            {
                'level': 'text',
                'text': 'Text2\n',
                'start': 26,
                'end': 32,
                'heading_id': None,
                'subsections': [],
            },
            {
                'level': 'HEADING_3',
                'text': 'Heading3\n',
                'start': 32,
                'end': 41,
                'heading_id': 'h.3k1198kg1e4d',
                'subsections': [
                    {
                        'level': 'text',
                        'text': 'Text 3\n',
                        'start': 41,
                        'end': 48,
                        'heading_id': None,
                        'subsections': [],
                    }
                ],
            },
            {
                'level': 'HEADING_3',
                'text': 'Heading3b\n',
                'start': 48,
                'end': 58,
                'heading_id': 'h.c7fpjsk6w9gb',
                'subsections': [],
            },
            {
                'level': 'HEADING_2',
                'text': 'Heading2\n',
                'start': 58,
                'end': 67,
                'heading_id': 'h.bm9k5iq137dy',
                'subsections': [
                    {
                        'level': 'text',
                        'text': 'Text 4\n\U0002ffff\U0003ffff\U0004ffffTab1\n\U0004ffffTab2\n\U0002ffff',
                        'start': 67,
                        'end': 89,
                        'heading_id': None,
                        'subsections': [],
                    }
                ],
            },
            {
                'level': 'HEADING_1',
                'text': 'Heading1\n',
                'start': 89,
                'end': 98,
                'heading_id': 'h.ijgpd5cpeqd6',
                'subsections': [
                    {
                        'level': 'HEADING_2',
                        'text': 'Heading2b\n',
                        'start': 98,
                        'end': 108,
                        'heading_id': 'h.v5p24o5fhtqo',
                        'subsections': [
                            {
                                'level': 'text',
                                'text': 'Text4\nText4.1\n',
                                'start': 108,
                                'end': 122,
                                'heading_id': None,
                                'subsections': [],
                            },
                            {
                                'level': 'HEADING_3',
                                'text': 'Heading3c\n',
                                'start': 122,
                                'end': 132,
                                'heading_id': 'h.s94p0purx9bu',
                                'subsections': [
                                    {
                                        'level': 'text',
                                        'text': 'Text5\n',
                                        'start': 132,
                                        'end': 138,
                                        'heading_id': None,
                                        'subsections': [],
                                    }
                                ],
                            },
                        ],
                    },
                    {
                        'level': 'HEADING_2',
                        'text': 'Heading2c\n',
                        'start': 138,
                        'end': 148,
                        'heading_id': 'h.ji5bd3w737r8',
                        'subsections': [
                            {
                                'level': 'text',
                                'text': 'Text6\n',
                                'start': 148,
                                'end': 154,
                                'heading_id': None,
                                'subsections': [],
                            },
                            {
                                'level': 'HEADING_3',
                                'text': 'Heading3d\n',
                                'start': 154,
                                'end': 164,
                                'heading_id': 'h.akk1pid3gac1',
                                'subsections': [
                                    {
                                        'level': 'text',
                                        'text': 'Text7\n',
                                        'start': 164,
                                        'end': 170,
                                        'heading_id': None,
                                        'subsections': [],
                                    }
                                ],
                            },
                        ],
                    },
                ],
            },
        ],
    },
]
