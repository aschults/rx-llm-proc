# pyright: basic
"""Test Template CLI class."""

from unittest import mock
from pyfakefs import fake_filesystem_unittest

from rxllmproc.cli import template_cli


class TestTemplateCli(fake_filesystem_unittest.TestCase):
    """Test the template CLI class."""

    def setUp(self) -> None:
        """Set up fake filesystem and instance."""
        super().setUp()
        self.setUpPyfakefs()

        self.instance = template_cli.TemplateCli()

        def _func(s: str) -> str:
            return f'ff{s}ff'

        self.instance.processor.add_filter('func', _func)

    @mock.patch('rxllmproc.cli.cli_base.sys.stdout')
    def test_simple_expand(self, stdout_mock: mock.Mock):
        """Test a simple variable expansion."""
        self.instance.main(['-D', 'a=blah', '--template=_{{a}}_'])
        stdout_mock.write.assert_called_with('_blah_')

    @mock.patch('rxllmproc.cli.cli_base.sys.stdout')
    def test_multi_expand(self, stdout_mock: mock.Mock):
        """Test a simple variable expansion."""
        self.instance.main(
            ['-D', 'a=blah', '-D', 'b=foo', '--template=_{{a}}_{{b}}_']
        )
        stdout_mock.write.assert_called_with('_blah_foo_')

    @mock.patch('rxllmproc.cli.cli_base.sys.stdout')
    def test_expand_filter(self, stdout_mock: mock.Mock):
        """Test a simple variable expansion."""
        self.instance.main(['--template=_{{"x" | func}}_'])
        stdout_mock.write.assert_called_with('_ffxff_')

    @mock.patch('rxllmproc.cli.cli_base.sys.stdout')
    def test_expand_from_file(self, stdout_mock: mock.Mock):
        """Test getting the template from a file."""
        self.fs.create_file(  # type: ignore
            'template.j2',
            contents='_{{b}}_',
        )

        self.instance.main(['-D', 'b=xxx', '--template=@template.j2'])
        stdout_mock.write.assert_called_with('_xxx_')

    @mock.patch('rxllmproc.cli.cli_base.sys.stdout')
    def test_expand_from_json(self, stdout_mock: mock.Mock):
        """Test using JSON in template expansion."""
        self.instance.main(['-D', 'j=(json)[2,4,99]', '--template=_{{j[2]}}_'])
        stdout_mock.write.assert_called_with('_99_')

    @mock.patch('rxllmproc.cli.cli_base.sys.stdout')
    def test_expand_from_json_file(self, stdout_mock: mock.Mock):
        """Test using JSON from a file in template expansion."""
        self.fs.create_file(  # type: ignore
            'data.json',
            contents='{"foo": "bar"}',
        )
        self.instance.main(
            ['-D', 'j=()@data.json', '--template={"res": "{{j.foo}}" }']
        )
        stdout_mock.write.assert_called_with('{"res": "bar" }')

    @mock.patch('rxllmproc.cli.cli_base.sys.stdout')
    def test_expand_from_email(self, stdout_mock: mock.Mock):
        """Test using an email message in the template expansion."""
        self.fs.create_file(  # type: ignore
            'email.msg',
            contents='From blah\nSubject: the_subject\n\nthe_content',
        )

        self.instance.main(
            [
                '-D',
                'e=(email)@email.msg',
                '--template=_{{e["Subject"]}}_{{e.get_payload()}}_',
            ]
        )
        stdout_mock.write.assert_called_with('_the_subject_the_content_')

    @mock.patch('rxllmproc.cli.cli_base.sys.stdout')
    def test_expand_incl_positional(self, stdout_mock: mock.Mock):
        """Test combined variable and command line args."""
        self.fs.create_file(  # type: ignore
            'tst.json',
            contents='[1,"you",3]',
        )

        self.instance.main(
            ['--template=_{{v}}_{{args[0][1]}}_', '-D', 'v=hello', 'tst.json']
        )
        stdout_mock.write.assert_called_with('_hello_you_')
