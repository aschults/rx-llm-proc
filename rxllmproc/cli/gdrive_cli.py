"""Google Drive upload/download CLI."""

from typing import Literal, Dict, Any, Tuple
import logging
import csv
import json
import os
import sys
import mimetypes
import io

from googleapiclient.errors import HttpError
from rxllmproc.drive import types
from rxllmproc.cli import cli_base
from rxllmproc.text_processing import converters
from rxllmproc.core.auth import CredentialsFactory
from rxllmproc.drive.api import DriveWrap


class DriveFileNotFoundException(Exception):
    """Exception raised for the CLI when a drive file is not found."""


class DriveCli(cli_base.CommonFileOutputCli):
    """Command line implementation for GDrive wrapper."""

    def _add_args(self):
        self.arg_parser.description = (
            'Access Google Drive files via Command ' 'line.'
        )

        subparsers = self.arg_parser.add_subparsers(
            dest='command',
            help='Operation to perform on GDrive',
            metavar='OPERATION',
            description='Operation to perform on GDrive.',
        )
        get_subcommand = subparsers.add_parser(
            'get',
            help='Get a file from Drive.',
            description='Get a file from Drive by ID.',
        )
        get_subcommand.add_argument(
            '--id', metavar='DRIVE_ID', help='The Google Drive ID of the file.'
        )
        format_group = get_subcommand.add_mutually_exclusive_group()
        format_group.add_argument(
            '--export_as',
            metavar='MIME_TYPE',
            help='Convert to specific Mime type during download.',
        )
        format_group.add_argument(
            '--as_html',
            action='store_true',
            help='Download as HTML, i.e. text/html',
        )
        format_group.add_argument(
            '--as_markdown',
            action='store_true',
            help='Download as Markdown, converting from HTML.',
        )
        get_subcommand.add_argument(
            '--output', metavar='FILENAME', help='Redirect output to FILENAME'
        )
        get_subcommand.add_argument(
            '--dry_run',
            action='store_true',
            help='Execute but don\'t change anything',
        )

        get_all_subcommand = subparsers.add_parser(
            'get_all',
            help='Get all files from Drive matching a query.',
            description='Get all files from Drive matching a query and save them to a directory.',
        )
        get_all_subcommand.add_argument(
            'query',
            metavar='DRIVE_QUERY',
            help='Drive query as used for Drive API',
        )
        get_all_subcommand.add_argument(
            '--output_dir',
            required=True,
            metavar='DIR_PATH',
            help='Directory under which the results are written.',
        )
        get_all_subcommand.add_argument(
            '--force',
            '-f',
            action='store_true',
            help='If set, overwrite existing files.',
        )
        get_all_subcommand.add_argument(
            '--dry_run',
            action='store_true',
            help="Execute but don't change anything",
        )
        format_group_all = get_all_subcommand.add_mutually_exclusive_group()
        format_group_all.add_argument(
            '--export_as',
            metavar='MIME_TYPE',
            help='Convert to specific Mime type during download.',
        )
        format_group_all.add_argument(
            '--as_html',
            action='store_true',
            help='Download as HTML, i.e. text/html',
        )
        format_group_all.add_argument(
            '--as_markdown',
            action='store_true',
            help='Download as Markdown, converting from HTML.',
        )

        put_subcommand = subparsers.add_parser(
            'put',
            help='Create or upload a file to Drive.',
            description=(
                'Create a file by name, or replace an existing file by '
                'name or Drive ID. Lists the drive ID of the file that '
                'was changed.'
            ),
        )
        target_group = put_subcommand.add_mutually_exclusive_group()
        target_group.add_argument(
            '--update_id',
            metavar='DRIVE_ID',
            help='Drive ID of the file to modify/replace.',
        )
        target_group.add_argument(
            '--update_name',
            metavar='DRIVE_FILENAME',
            help='Modify/replace Drive file named DRIVE_FILENAME',
        )
        target_group.add_argument(
            '--create_name',
            metavar='DRIVE_FILENAME',
            help='Create a new Drive file named DRIVE_FILENAME',
        )
        put_subcommand.add_argument(
            '--mime_type',
            metavar='MIME_TYPE',
            help='Mime type for the new/replaced file',
        )
        put_subcommand.add_argument(
            'file',
            nargs='?',
            metavar='INPUT_FILE',
            help='Read content to upload from file, not STDIN',
        )
        put_subcommand.add_argument(
            '--dry_run',
            action='store_true',
            help='Execute but don\'t change anything',
        )
        list_subcommand = subparsers.add_parser(
            'list',
            help='List Drive files by query',
            description=(
                'Search for Drive files using query syntax and '
                'return a list of matching IDs with attributes.'
            ),
        )
        list_subcommand.add_argument(
            'query',
            metavar='DRIVE_QUERY',
            help='Drive query as used for Drive API',
        )
        list_subcommand.add_argument(
            '--output',
            metavar='FILENAME',
            help='Filename to write the output to, not STDOUT',
        )
        list_format_group = list_subcommand.add_mutually_exclusive_group()
        list_format_group.add_argument(
            '--delimiter',
            default='\t',
            metavar='SINGLE_CHAR',
            help='Put SINGLE_CHAR between fields in query output.',
        )
        list_format_group.add_argument(
            '--as_json',
            action='store_true',
            help=(
                'Output the list of files as a JSON array, '
                'mutually exclusive with --delimiter'
            ),
        )
        # Note: Skipping the output option as we're adding directly.
        cli_base.CliBase._add_args(self)

    def _exception_to_status(self, e: Exception) -> Tuple[int, str] | None:
        if isinstance(e, HttpError):
            return 30, f'Could not get file: {e}'
        if isinstance(e, DriveFileNotFoundException):
            return 30, f'Drive file not found: {e}'
        super()._exception_to_status(e)

    def __init__(
        self,
        creds: CredentialsFactory | None = None,
        drive_wrap: DriveWrap | None = None,
    ) -> None:
        """Construct the instance, allowing for mocks (testing)."""
        super().__init__(creds)

        self.command: Literal['get', 'put', 'list', 'get_all'] | None = None
        self.id: str | None = None
        self.update_id: str | None = None
        self.as_markdown = False
        self.as_html = False
        self.as_json = False
        self.file: str | None = None
        self.update_name: str | None = None
        self.create_name: str | None = None
        self.mime_type: str | None = None
        self.export_as: str | None = None
        self.output: str | None = None
        self.query: str | None = None
        self.delimiter: str = '\t'
        self.output_dir: str | None = None
        self.force: bool = False

        self._wrapper = drive_wrap

    @property
    def wrapper(self) -> DriveWrap:
        """Get the Drive wrapper."""
        if self._wrapper is None:
            self._wrapper = DriveWrap(self._get_credentials())
        return self._wrapper

    def run_get_all(self):
        """Handles the 'get_all' command."""
        if not self.query:
            raise cli_base.UsageException(
                'Query is required for get_all command'
            )
        if not self.output_dir:
            raise cli_base.UsageException(
                'Output directory is required for get_all command'
            )

        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

        files = self.wrapper.list(self.query)
        logging.info('Found %d files matching query.', len(files))

        for file_info in files:
            if 'id' not in file_info:
                raise DriveFileNotFoundException(
                    f"File info missing 'id': {file_info}"
                )
            file_id = file_info['id']
            file_name = file_info.get('name', file_id)
            output_path = os.path.join(self.output_dir, file_name)

            if self.as_markdown:
                output_path = f'{os.path.splitext(output_path)[0]}.md'

            if not self.force and os.path.exists(output_path):
                logging.info('Skipping existing file: %s', output_path)
                continue

            log_message = (
                f"Downloading {file_id} ('{file_name}') to {output_path}"
            )
            if self.dry_run:
                self._log_dry_run(log_message)
                continue

            logging.info(log_message)
            self.id = file_id
            self.output = output_path
            # Temporarily set output to file path for write_output
            self.run_get()
            self.output = None  # Reset for next iteration

    def run_get(self):
        """Perform a get operation, download from Drive."""
        if not self.id:
            raise cli_base.UsageException('need ID')

        logging.info('Getting Drive file with id %s', self.id)

        if self.export_as:
            content = self.wrapper.get_doc(self.id, mime_type=self.export_as)
        elif self.as_html:
            content = self.wrapper.get_doc(self.id)
        elif self.as_markdown:
            html_content = self.wrapper.get_doc(self.id)
            content = converters.convert_html_to_markdown(html_content)
        else:
            content = self.wrapper.get_doc(self.id)
        self.write_output(content)

    def _update_file(self, inbuf: io.BytesIO):
        if not self.mime_type:
            raise Exception('should not happen')

        logging.info(
            'Updating Drive file with id %s, type: %s', self.id, self.mime_type
        )

        file_info = self.wrapper.get_file(self.update_id, self.update_name)
        if not file_info:
            raise DriveFileNotFoundException(
                'Could not find file on Drive:'
                f' {self.update_id}, {self.update_name}'
            )
        file_id = file_info.get('id', '--None--')
        if self.dry_run:
            self._log_dry_run(f'Uploading to Drive, id={file_id}')
        else:
            self.wrapper.update_file(inbuf, file_id, self.mime_type)
        return file_id

    def _create_file(self, inbuf: io.BytesIO):
        if not self.mime_type:
            raise Exception('should not happen')

        logging.info('Updating Drive file with  type: %s', self.mime_type)

        file_id = '--new-file--'
        if not self.create_name:
            raise cli_base.UsageException(
                'Cannot determine the target filename'
            )
        if self.dry_run:
            self._log_dry_run(f'Uploading to Drive, id={self.update_id}')
        else:
            file_info = self.wrapper.create_file(
                inbuf, self.create_name, self.mime_type
            )
            file_id = file_info.get('id', '--None--')

        logging.info('Created Drive file with id %s', self.id)
        return file_id

    def run_put(self):
        """Perform an upload to Drive."""
        update_file = self.update_name or self.update_id
        if self.file:
            if not self.mime_type:
                self.mime_type, _ = mimetypes.guess_type(self.file)

            if not update_file and not self.create_name:
                self.create_name = self.file

        if not self.mime_type:
            raise cli_base.UsageException(
                'Could not determine Mime Type from file or option.'
            )

        if self.file:
            with open(self.file, 'rb') as infile:
                inbuf = io.BytesIO(infile.read())
        else:
            inbuf = io.BytesIO(sys.stdin.buffer.read())

        if update_file:
            print(self._update_file(inbuf))
        else:
            print(self._create_file(inbuf))

    LIST_FIELDS = [
        'id',
        'name',
        'fileExtension',
        'mimeType',
        'description',
        'md5Checksum',
        'modifiedTime',
    ]

    def run_list(self):
        """List files on Drive by query."""
        csv_content = io.StringIO()
        if self.query is None:
            raise cli_base.UsageException('Need to pass query')
        result_list = self.wrapper.list(self.query)

        if self.as_json:
            self.write_output(json.dumps(result_list, indent=2))
            return

        writer = csv.DictWriter(
            csv_content,
            self.LIST_FIELDS,
            delimiter=self.delimiter,
            lineterminator='\n',
        )

        writer.writeheader()

        def _build_row(entry: types.File) -> Dict[str, Any]:
            result = {k: entry.get(k, '') for k in self.LIST_FIELDS}
            if not result.get('fileExtension', None):
                result.update(
                    fileExtension=mimetypes.guess_extension(
                        entry.get('mimeType', '')
                    )
                )
            return result

        writer.writerows(_build_row(entry) for entry in result_list)

        self.write_output(csv_content.getvalue())

    def run(self):
        """Execute the action according to args."""
        mimetypes.add_type('application/vnd.google-apps.document', '.gdoc.json')
        mimetypes.add_type(
            'application/vnd.google-apps.spreadsheet', '.gsheet.json'
        )

        if self.command == 'get':
            self.run_get()
        elif self.command == 'put':
            self.run_put()
        elif self.command == 'get_all':
            self.run_get_all()
        elif self.command == 'list':
            self.run_list()
        else:
            raise cli_base.UsageException('No command given')


def main():
    """Run the command line tool."""
    DriveCli().main()


if __name__ == '__main__':
    main()
