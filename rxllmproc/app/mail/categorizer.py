"""Iterative mail categorizer service."""

import json
import logging
from typing import Iterable, Callable, Any, cast

from rxllmproc.llm import api as llm_api
from rxllmproc.text_processing import jinja_processing
from rxllmproc.app.mail import types, index
from rxllmproc.app.analysis import types as analysis_types

# Suggested format for the JSON output from the Gemini model.
# The model should return a list of email objects, each with a 'category' field added.
SUGGESTED_JSON_FORMAT = """
[
  {
    "id": "12345",
    "category": "ExampleCategory"
  }
]
"""

# Suggested format for the JSON output from the refinement call.
SUGGESTED_REFINEMENT_JSON_FORMAT = """
```json
{
  "id": "12345",
  "category": "RefinedCategory",
  "noteworthy_details": ["Detail 1", "Detail 2"],
  "action_items": [
      {
          "title": "Action item 1 (for <company or sender>)",
          "notes": "Additional context, requestor/sender, links, relevant details, etc. to make the item actionale.",
          "priority": "High",
          "due_date": "2025-12-12",
          "links": [
              {
                  "url": http://links.relevant.for.todo",
                  "text": "Link text"
              }
          ]
      },
      {
          "title": "Action item 2 (for <company or sender>)",
          "notes": "Additional context, requestor/sender, links, relevant details, etc. to make the item actionale.",
          "priority": "Low",
          "links": [
              {
                  "url": http://links.relevant.for.todo",
                  "text": "Link text"
              }
          ]
      }
  ]
}
```

NOTE:
* Priority can be low, medium, high
* Due date is optional. If the email suggests a date by which a todo should be done, set the due date accordingly.
"""


def _no_save(_: dict[str, types.MailSource]):
    pass


class MailCategorize:
    """A service to categorize emails using an LLM."""

    def __init__(
        self,
        prompt_template: str,
        model: llm_api.LlmBase,
        emails_dir: str,
        refine_prompt_template: str | None = None,
        refine_model: llm_api.LlmBase | None = None,
        prompt_params: dict[str, str] | None = None,
        refine_categories: list[str] | None = None,
        batch_size: int = 20,
        save_interval: int = 100,
        intermediate_save_func: Callable[
            [dict[str, types.MailSource]], None
        ] = _no_save,
    ) -> None:
        """Initialize the MailCategorize service."""
        self.model = model
        self.refine_model = refine_model or model
        self.emails_dir = emails_dir
        self.prompt_params = prompt_params or {}
        self.refine_categories = (
            ["unknown", "other"]
            if refine_categories is None
            else refine_categories
        )
        self.batch_size = batch_size
        self.save_interval = save_interval
        self._intermediate_save_func = intermediate_save_func

        self.jinja_template = jinja_processing.JinjaProcessing()
        self.jinja_template.set_template(prompt_template)
        self.jinja_template.add_global("json_example", SUGGESTED_JSON_FORMAT)
        for key, value in (prompt_params or {}).items():
            self.jinja_template.add_global(key, value)

        self.refined_jinja_template = None
        if refine_prompt_template:
            self.refined_jinja_template = jinja_processing.JinjaProcessing()
            self.refined_jinja_template.set_template(refine_prompt_template)
            self.refined_jinja_template.add_global(
                "refinement_json_example", SUGGESTED_REFINEMENT_JSON_FORMAT
            )
            for key, value in (prompt_params or {}).items():
                self.refined_jinja_template.add_global(key, value)

    def _categorize_emails(
        self, email_batch: list[types.MailMetadata]
    ) -> list[types.MailSource]:
        """Sends a batch of emails to the LLM for categorization."""
        emails_json_str = json.dumps(
            [e.model_dump(mode='json') for e in email_batch], indent=2
        )
        prompt = self.jinja_template.render(email_batch=emails_json_str)

        logging.info(
            "Sending batch of %d emails for categorization...", len(email_batch)
        )

        categorized_data: Any = self.model.query_json(prompt)

        if not isinstance(categorized_data, list):
            logging.error(
                "LLM response was not a JSON list as expected. Received: %s",
                repr(categorized_data),
            )
            raise ValueError(
                f"LLM response was not a JSON list as expected: {categorized_data!r}"
            )

        categorized_data_list = cast(list[dict[str, Any]], categorized_data)

        logging.info(
            "Successfully categorized %d emails.", len(categorized_data_list)
        )

        email_map = {email.id: email for email in email_batch}

        merged_emails: list[types.MailSource] = []
        for categorized_item in categorized_data_list:
            item_id = categorized_item.get("id")
            if item_id and item_id in email_map:
                original_entry = email_map[item_id]
                analysis = analysis_types.Analysis(
                    id=item_id, category=categorized_item.get("category")
                )
                new_entry = types.MailSource(
                    mail_metadata=original_entry,
                    analysis=analysis,
                    id=original_entry.id,
                )
                merged_emails.append(new_entry)
            else:
                logging.warning(
                    "Received categorized item with missing or unknown ID: %r",
                    categorized_item,
                )
        return merged_emails

    def _refine_email_details(
        self, email_item: types.MailSource
    ) -> types.MailSource:
        """Sends a single email's content to the LLM for detailed refinement."""
        if not self.refined_jinja_template:
            raise RuntimeError("No refinement specified")

        if not email_item.mail_metadata.path:
            logging.error(
                "Email item %s is missing mail_metadata.path, cannot read content.",
                repr(email_item.id),
            )
            raise ValueError(
                f"Email item {email_item.id} is missing mail_metadata.path, cannot read content."
            )
        email_path = f"{self.emails_dir}/{email_item.mail_metadata.path}"
        try:
            with open(email_path, "r", encoding="utf-8") as f:
                email_content = f.read()
        except IOError as e:
            logging.error(
                "Failed to read email content from %s: %s", email_path, e
            )
            raise

        final_prompt_params = (self.prompt_params or {}) | {
            "email_content": email_content,
            "email_item": json.dumps(email_item.model_dump(mode='json')),
        }

        prompt = self.refined_jinja_template.render(**final_prompt_params)

        logging.info(
            "Processing email %s for refinement...", repr(email_item.id)
        )

        refined_data: Any = self.refine_model.query_json(prompt)

        if not isinstance(refined_data, dict):
            logging.error(
                "LLM refinement response was not a JSON object with an 'id'. Received: %s",
                repr(refined_data),
            )
            raise ValueError(
                f"LLM refinement response was not a JSON object with an 'id': {refined_data!r}"
            )

        refined_data_dict = cast(dict[str, Any], refined_data)

        if "id" not in refined_data_dict:
            logging.error(
                "No Id found in LLM reply %s", repr(refined_data_dict)
            )
            raise ValueError("No Id found in LLM reply")

        logging.info("Successfully refined email %s.", refined_data_dict['id'])

        analysis_data = refined_data_dict.copy()
        analysis_data.pop("id", None)
        analysis = analysis_types.Analysis.model_validate(analysis_data)
        new_email_item = email_item.model_copy(update={"analysis": analysis})

        return new_email_item

    def _categorize_in_batches(
        self, emails: list[types.MailMetadata]
    ) -> Iterable[types.MailSource]:
        """A generator that processes emails in batches and yields categorized results."""
        for i in range(0, len(emails), self.batch_size):
            try:
                newly_categorized = self._categorize_emails(
                    emails[i : i + self.batch_size]
                )
                if newly_categorized:
                    for item in newly_categorized:
                        yield item
            except Exception:
                logging.error(
                    "Failed to categorize batch starting at index %d",
                    i,
                    exc_info=True,
                )
                raise

    def run(
        self,
        email_index: index.GmailIndexManager,
        categorized_email_index: dict[str, types.MailSource],
    ):
        """Executes the categorization."""
        # Filter for uncategorized emails and sort them
        pending_emails = [
            item
            for item in email_index
            if item.id not in categorized_email_index
        ]
        pending_emails.sort(key=lambda x: (x.received_date or "", x.id))

        if not pending_emails:
            logging.info("No new emails to categorize. Exiting.")
            return

        logging.info("Found %d new emails to categorize.", len(pending_emails))

        # Process in batches
        categorized_items_generator = self._categorize_in_batches(
            pending_emails
        )

        # Process and refine categorized items
        processed_since_last_save = 0
        for entry in categorized_items_generator:
            if (
                self.refined_jinja_template
                and entry.analysis
                and entry.analysis.category in self.refine_categories
            ):
                try:
                    refined_item = self._refine_email_details(entry)
                    categorized_email_index[refined_item.id] = refined_item
                except Exception:
                    logging.error(
                        "Failed to refine email %s", entry, exc_info=True
                    )
                    # Save the unrefined item anyway
                    categorized_email_index[entry.id] = entry
            else:
                categorized_email_index[entry.id] = entry

            processed_since_last_save += 1
            if processed_since_last_save >= self.save_interval:
                logging.info(
                    "Processed %d new items, saving progress...",
                    processed_since_last_save,
                )
                self._intermediate_save_func(categorized_email_index)
                processed_since_last_save = 0

        # Final save
        if processed_since_last_save > 0:
            logging.info("Saving remaining categorized items...")
            self._intermediate_save_func(categorized_email_index)

        logging.info("Categorization process complete.")
