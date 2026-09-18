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

ff do browser.tabs.update "$tab" '{"url": "https://www.australianretirementtrust.com.au/investments/performance/graphs"}'
until codes="$(ff do dom.get 'input[type=checkbox]' value '{"tabId": '$tab'}' | jq -re '.[].result[]')"; do
    sleep 1
done
codes="$(<<<"$codes" cut -d\| -f1)"

# get the subscription key
key=
urls=()
readarray -t urls < <(ff do dom.get script src '{"tabId": '$tab'}' | jq -re .[].result[] | grep '^https://www.australianretirementtrust.com.au/_next/')
if code="$(curl --compressed -- "${urls[@]}" | grep -i -o "apimSubscriptionKeyName[^a-z0-9]*[a-z0-9][a-z0-9]*[\"']")"; then
    [[ "$code" =~ ([a-z0-9]+)[\'\"]$ ]]
    key="${BASH_REMATCH[1]}"
fi
if [[ "$key" == '' ]]; then
    echo 'unable to get subscription key' >&2
    exit
fi

# get dates
joined_codes="$(<<<"$codes" paste -sd/)"
dates="$(curl "https://api.art.com.au/integration/publicweb/v1/investment/unit-price/fund/effective-dates?fundCodes=$joined_codes&hasTenYearLimit=false" --compressed -H "x-art-subscription-key: $key" -H 'x-art-initiating-application: PublicWeb' -H "x-art-correlation-id: $(uuidgen)")"
maxdate="$(<<<"$dates" jq -re '.effectiveDates | map(.maxDate) | max | split("T")[0]')"

# if you do them all at once, it gets 500
data=
while read -r code; do
    mindate="$(<<<"$dates" jq -re --arg code "$code" '.effectiveDates[] | select(.fundCode == $code).minDate | split("T")[0]')"
    data+="$(curl --compressed --fail "https://api.art.com.au/integration/publicweb/v1/investment/unit-price/investment-graph-data?unitPricesToPlot=all&investmentAmount=10000&fundCodes=$code&fromDate=$mindate&toDate=$maxdate" --compressed -H "x-art-subscription-key: $key" -H 'x-art-initiating-application: PublicWeb' -H "x-art-correlation-id: $(uuidgen)")"
done <<<"$codes"

(
    echo $'date\tname\tvalue'
    <<<"$data" jq -re '.funds[] | .name as $name | .unitPrices[] | [.date, $name, .sellPrice] | @tsv'
) > public/art.tsv
