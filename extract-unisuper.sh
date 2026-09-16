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

tab="$(ff do browser.tabs.create '{}' | jq -re .id)"
trap 'ff do browser.tabs.remove "$tab"' EXIT

ff do browser.tabs.update "$tab" '{"url": "https://www.unisuper.com.au/investments/our-investment-options"}'
until hrefs="$(ff do dom.get a href '{"tabId": '$tab', "attrs": {"innerText": "More details"}}' | jq -re .[].result[])"; do
    sleep 1
done

mkdir -p public/unisuper/
while read -r url; do
    echo "$url"
    name="$(basename "$url")"
    ff do browser.tabs.update "$tab" '{"url": "'$url'"}' >/dev/null
    sleep 2
    until data="$(.ff do dom.call '.tab.active figure' getAttribute data-chart '{"tabId": '$tab'}' | jq -re '.[0].result[0]')"; do
        sleep 1
    done
    printf %s "$data" >"public/unisuper/$name.json"
done <<<"$hrefs"
