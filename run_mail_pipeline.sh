#!/bin/bash
set -e -x

export PYTHONPATH=. 

python rxllmproc/cli/rx_mail_categorizer.py \
  --cache .rxllmproc_cache.json \
  --categories_instructions @../personal_org/prompts/categories.md \
  --action_items_instructions @../personal_org/prompts/action_items.md \
  --context_instructions @../personal_org/prompts/personal_context.md \
  --docs_insertion_instructions @../personal_org/prompts/docs_insertion_instructions.md \
  --todo_doc_id 13kfy2CabsLPEEvkGZRAjtm6jKyJIEhiiEJxqeo_sF4Q \
  --gmail_query "newer_than:14d"  \
  "$@" \
 # >tstout.json
