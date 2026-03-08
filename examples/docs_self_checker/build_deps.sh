#!/bin/bash
(cd "${CHECKOUT_DIR}" ; find docs -type f -name "*.md" ) | while read fn ; do
    base="${fn%.md}"
    base="${base//\//_}"
    echo "results/${base}_suggestions.prompt.txt: ${CHECKOUT_DIR}/${fn}"
    echo "all: results/${base}_suggestions.prompt.json"
done
