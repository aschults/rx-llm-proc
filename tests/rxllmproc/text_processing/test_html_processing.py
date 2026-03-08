"""Test HTML processing."""

import unittest

from rxllmproc.text_processing import html_processing


class TestHtmlCleaner(unittest.TestCase):
    """Test the HTML cleaner class."""

    def test_simple(self):
        """Simple test removing comments, unanted styles, tags."""
        input = '''<!doctype html>
<html>
    <head>
        <title></title>
        <script>blah</script>
        <!--XXXXXXX-->
        <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
        <meta name="viewport" content="width=device-width,initial-scale=1">
        <style>XXXXXX</style>
    </head>
    <body>
        <p></p>
        <div id='xxxxxx'>blah</div>
    </body>
</html>
'''

        result = html_processing.HtmlCleaner().process(input)
        expected = '''<!DOCTYPE html>

<html>
<head>






</head>
<body>

<div>blah</div>
</body>
</html>
'''
        self.assertEqual(expected, result)

    def test_empty_message(self):
        """Simple test removing comments, unanted styles, tags."""
        input = '<div dir="ltr"><br></div>\n'
        result = html_processing.HtmlCleaner().process(input)
        expected = ''
        self.assertEqual(expected, result)
