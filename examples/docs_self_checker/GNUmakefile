# Purpose:
# This example demonstrates how to automate documentation review using LLMs to
# generate suggestions.
#
# Prerequisites:
# Install the package in editable mode to expose the CLI tools:
# `pip install -e ../..`

ifeq ($(LLM_MODEL),)
  LLM_MODEL := gemini
endif

deps.mk: build_deps.sh
	@bash build_deps.sh > $@
	@mkdir -p results

-include deps.mk

%_suggestions.prompt.txt: templates/build_suggestions.prompt.j2
	template_cli \
		--template @templates/build_suggestions.prompt.j2 \
		--output="$@" \
		-D name="$(basename $(notdir $(filter %.md, $^)))" \
		-D doc="@$(filter %.md, $^)"

%_suggestions.json: %_suggestions.prompt.txt
	llm_cli \
		--model $(LLM_MODEL) \
		"@$(filter %.prompt.txt, $^)" \
		--output="$@" \
		$(WITH_VERBOSE) \
		--as_json


all:
	@echo hello