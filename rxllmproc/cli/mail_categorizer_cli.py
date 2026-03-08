"""CLI for categorizing emails using an LLM."""

import json
import logging
import os
import os.path
import argparse
import dataclasses

import dacite

from rxllmproc.cli import cli_base
from rxllmproc.cli.cli_base import require_arg
from rxllmproc.app.mail import index, categorizer, types


class MailCategorizerCli(cli_base.CliBase):
    """CLI for email categorization."""

    def _add_args(self):
        self.arg_parser.description = "Categorizes emails from an index.json in batches using the Gemini API."
        subparsers = self.arg_parser.add_subparsers(
            dest="command",
            help="Operation to perform",
            metavar="OPERATION",
            required=True,
        )

        cat_parser = subparsers.add_parser(
            "categorize",
            help="Categorize emails from an index file.",
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )

        cat_parser.add_argument(
            "--index_file",
            required=True,
            help="Path to the source index.json file from gmail_downloader.",
        )
        cat_parser.add_argument(
            "--categorized_index_file",
            required=True,
            help="Path to the categorized index file for reading existing and saving new results.",
        )
        cat_parser.add_argument(
            "--emails_dir",
            required=True,
            help="Path to the root directory where email content files are stored (for refinement).",
        )
        cat_parser.add_argument(
            "--prompt",
            required=True,
            help="The prompt template file for the initial categorization.",
        )
        cat_parser.add_argument(
            "--refine_prompt",
            help="The prompt template file for the detailed refinement step.",
        )
        cat_parser.add_argument(
            "--parameter",
            "-P",
            action="append",
            default=[],
            help="A key=value parameter to expand in the prompt templates. Use key=@file to read value from a file.",
        )
        cat_parser.add_argument(
            "--batch_size",
            type=int,
            default=20,
            help="Number of emails to process per categorization API call.",
        )
        cat_parser.add_argument(
            "--model",
            default="gemini-lite",
            help="The Gemini model for the initial categorization step.",
        )
        cat_parser.add_argument(
            "--refine_categories",
            nargs="+",
            default=["unknown", "other"],
            help="A list of categories that should be sent for a second, more detailed refinement analysis.",
        )
        cat_parser.add_argument(
            "--refine_model",
            help="The Gemini model to use for the refinement step. Defaults to the main model.",
        )
        cat_parser.add_argument(
            "--save_interval",
            type=int,
            default=100,
            help="How often to save the categorized index file (in number of new entries).",
        )
        super()._add_args()

    def __init__(self) -> None:
        """Construct the instance."""
        super().__init__()
        self.command: str | None = None
        self.index_file: str | None = None
        self.categorized_index_file: str | None = None
        self.emails_dir: str | None = None
        self.prompt: str | None = None
        self.refine_prompt: str | None = None
        self.parameter: list[str] = []
        self.batch_size: int = 20
        self.model: str = "gemini-1.5-flash-latest"
        self.refine_categories: list[str] = []
        self.refine_model: str | None = None
        self.save_interval: int = 100

    def _load_json_as_dict(
        self, filepath: str, key_field: str = "id"
    ) -> dict[str, types.MailSource]:
        """Loads a JSON file (list of dicts) and returns it as a dictionary keyed by `key_field`."""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data_list = json.load(f)
                return {
                    item[key_field]: dacite.from_dict(types.MailSource, item)
                    for item in data_list
                    if key_field in item
                }
        except FileNotFoundError:
            logging.warning(
                "File not found: %s. Returning empty dictionary.", filepath
            )
            return {}
        except (IOError, json.JSONDecodeError) as e:
            logging.error(
                "Failed to read or parse JSON file %s: %s", filepath, e
            )
            raise

    def _save_dict_as_json_list(
        self,
        filepath: str,
        data_dict: dict[str, types.MailSource],
        sort_keys: tuple[str, str] = ("received_date", "id"),
    ) -> None:
        """Converts a dictionary to a sorted list and saves it as a JSON file."""
        data_list = sorted(
            [dataclasses.asdict(item) for item in data_dict.values()],
            key=lambda x: tuple(x.get(key, "") for key in sort_keys),
        )
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data_list, f, indent=4)
            logging.info("Successfully saved data to %s", filepath)
        except IOError as e:
            logging.error("Failed to write to file %s: %s", filepath, e)
            raise

    def _run_categorize(self):
        """Handles the 'categorize' command."""
        prompt_template = self.expand_arg(require_arg(self.prompt, "prompt"))

        # 1. Initialize LLM Clients
        llm_registry = self.plugins.llm_registry
        model_instance = llm_registry.create(
            self.model, cache_instance=self.cache_instance
        )
        refine_model_instance = model_instance
        if self.refine_model:
            refine_model_instance = llm_registry.create(
                self.refine_model, cache_instance=self.cache_instance
            )
            logging.info(
                "Using model %s for category refinement",
                self.refine_model,
            )

        # Load prompts and parameters
        prompt_params = (
            self.expand_args_named(self.parameter, self.expand_args_typed)
            if self.parameter
            else {}
        )
        refine_prompt_template: str | None = None
        if self.refine_prompt:
            refine_prompt_template = self.expand_arg(self.refine_prompt)
            logging.info(
                "Refining categories enabled using %s", self.refine_prompt
            )

        index_dir = os.path.dirname(require_arg(self.index_file, "index_file"))
        index_manager = index.GmailIndexManager(index_dir)

        categorized_index_dict = self._load_json_as_dict(
            require_arg(self.categorized_index_file, "categorized_index_file")
        )

        def _intermediate_save(
            categorized_index_dict: dict[str, types.MailSource],
        ):
            self._save_dict_as_json_list(
                require_arg(
                    self.categorized_index_file, "categorized_index_file"
                ),
                categorized_index_dict,
            )

        categorizer.MailCategorize(
            prompt_template=prompt_template,
            model=model_instance,
            emails_dir=require_arg(self.emails_dir, "emails_dir"),
            refine_prompt_template=refine_prompt_template,
            refine_model=refine_model_instance,
            prompt_params=prompt_params,
            refine_categories=self.refine_categories,
            batch_size=self.batch_size,
            save_interval=self.save_interval,
            intermediate_save_func=_intermediate_save,
        ).run(
            email_index=index_manager,
            categorized_email_index=categorized_index_dict,
        )

        # Final save
        logging.info("Final save...")
        _intermediate_save(categorized_index_dict)

        logging.info("Categorization process complete.")

    def run(self):
        """Execute the action."""
        if self.command == "categorize":
            self._run_categorize()
        else:
            raise cli_base.UsageException(f"Unknown command: {self.command}")


def main():
    """Run the command line tool."""
    MailCategorizerCli().main()


if __name__ == "__main__":
    # To make this runnable, we need argparse for the subparsers

    main()
