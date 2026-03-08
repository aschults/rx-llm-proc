#!/bin/bash

pth="$(dirname "$0")"
if [[ "${pth#/}" = "${pth}" ]] ; then
    pth="${PWD}/${pth}"
fi

echo "http://127.0.0.1:4577/README.md"
java -jar "${HOME}/gollum.war" -S gollum --host 127.0.0.1 "$@" --port 4577 --no-edit "${pth}"

# To download all docs as HTML:
#   wget --adjust-extension -X gollum/ -r -k http://127.0.0.1:4577/README.md