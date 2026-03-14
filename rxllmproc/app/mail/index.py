"""Handles the JSON index for downloaded GMail messages."""

import json
import logging
import dataclasses
from os import path
from typing import Any

from rxllmproc.gmail import types as gmail_types
from rxllmproc.core.infra import utilities
from rxllmproc.app.mail import types


class GmailIndexManager:
    """Manages the JSON index of downloaded emails."""

    def __init__(self, output_dir: str):
        """Construct the instance."""
        self.output_dir = output_dir
        self.index_file = path.join(self.output_dir, "index.json")
        logging.info("Loading email index from %s", self.index_file)
        self.current_file_content = ""
        self.email_index: dict[str, types.MailMetadata] = self._load_index()

    def _load_index(self) -> dict[str, types.MailMetadata]:
        """Loads the email index from a JSON file if it exists."""
        email_index: dict[str, types.MailMetadata] = {}
        if path.exists(self.index_file):
            try:
                with open(self.index_file, "r", encoding="utf-8") as f:
                    self.current_file_content = f.read()
                    for item in json.loads(self.current_file_content):
                        # For backward compatibility with old indexes
                        item.pop("url", None)
                        # Filter fields to avoid TypeError on extra fields (mimic pydantic ignore)
                        valid_fields = {
                            f.name
                            for f in dataclasses.fields(types.MailMetadata)
                        }
                        filtered_item = {
                            k: v for k, v in item.items() if k in valid_fields
                        }
                        email_index[str(item["id"])] = types.MailMetadata(
                            **filtered_item
                        )
            except Exception:
                logging.error(
                    "Failed to load index file: %s",
                    self.index_file,
                    exc_info=True,
                )
                raise
        else:
            logging.info("Starting blank Index as file not found")

        return email_index

    def save_index(self):
        """Saves the email index to a JSON file."""
        logging.info("Saving email index to %s", self.index_file)
        try:
            sorted_index = sorted(
                self.email_index.values(),
                key=lambda x: (x.received_date, x.id),
            )
            new_file_content = json.dumps(
                [utilities.asdict(entry) for entry in sorted_index],
                indent=2,
            )
            if new_file_content == self.current_file_content:
                logging.info(
                    'Skipping to write index file as identical content.'
                )
                return

            with open(self.index_file, "w", encoding="utf-8") as index_file_:
                index_file_.write(new_file_content)
            self.current_file_content = new_file_content
        except Exception:
            logging.exception("Failed to save index file: %s", self.index_file)
            raise

    def add(self, gmail_msg: gmail_types.Message, path: str | None = None):
        """Creates and adds a dictionary entry for the email index."""
        if not gmail_msg.id:
            raise ValueError("Message has no ID, cannot add to index.")
        try:
            entry = types.MailMetadata.from_msg(gmail_msg, path=path)
            self.email_index[entry.id] = entry
        except ValueError as e:
            logging.exception(f"Could not create index entry: {e}")
            raise

    def __contains__(self, item: Any) -> bool:
        """Checks if a message ID is in the index."""
        item_id: str | None = None
        if isinstance(item, str):
            item_id = item
        elif hasattr(item, "id") and item.id:
            item_id = item.id
        return item_id in self.email_index if item_id else False

    def __iter__(self):
        """Iterates over the email index."""
        return iter(self.email_index.values())

    def __len__(self):
        """Returns the number of entries in the index."""
        return len(self.email_index)
