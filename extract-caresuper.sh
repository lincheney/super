#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

# need a browser
# one day ill figure out how to use puppet from bash

if command -vp ffcli.py; then
    ff() { ffcli.py "$@"; }
else
    ff() { .ff "$@"; }
fi

tab="$(ff do browser.tabs.create '{"active": false}' | jq -re .id)"
trap 'ff do browser.tabs.remove "$tab"' EXIT

ff do browser.tabs.update "$tab" '{"url": "https://www.caresuper.com.au/members/investments/investment-options/balanced"}'
until url="$(ff do dom.get a href '{"attrs": {"innerText": "CSV"}}' | jq -re '.[0].result[0]')"; do
    sleep 1
done

curl --compressed --fail "$url" -o public/caresuper.csv
