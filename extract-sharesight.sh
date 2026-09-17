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

if [[ "${1:-}" == '' ]]; then
    read -r tab url < <(.ff do browser.tabs.query '{}' | jq -re '.[] | select(.url | match("^https://portfolio.sharesight.com/portfolios/[0-9]+")) | [.id, .url] | @tsv')
else
    tab="$1"
    url="$(ff curl 'https://portfolio.sharesight.com/portfolios' --fail --tab "$tab" -v -o /dev/null 2>&1 | grep -i '^< location: ' | sed 's/^< [Ll]ocation: //')"
fi

if ! [[ "$url" =~ ^https://portfolio.sharesight.com/portfolios/([0-9]+) ]]; then
    echo "cannot get portfolio id from url: $location" >&2
    exit 1
fi
portfolio="${BASH_REMATCH[1]}"

holdings="$(ff curl "https://portfolio.sharesight.com/api/v3.0-internal/portfolios/$portfolio/overview.json?consolidated=false&grouping=market&report_combined=true&start_date=2009-05-04&include_sales=false" --fail --tab "$tab")"

mkdir -p public/sharesight/
today="$(date +%Y-%m-%d)"
<<<"$holdings" jq -re '.holdings[] | [.instrument.code, .id, .instrument.id] | @tsv' | while read -r code id instrument; do
    echo "$code $id $instrument" >&2
    ff curl "https://portfolio.sharesight.com/api/v3.0-internal/holdings/$id/payouts.json" --fail --tab "$tab" | jq -re --tab .payouts > "public/sharesight/$code-payouts.json"
    ff curl "https://portfolio.sharesight.com/charts/instrument_price_data.json?consolidated=false&range=IN&holding_chart=PRICE&escape=false&start_date=2000-01-01&end_date=$today&portfolio_id=$portfolio&ref_portfolio_id=$portfolio&id=$instrument" --fail --tab "$tab" | jq -re --tab '.graph | {xAxis, series: (.series[0].data|map(.marker|=empty))}' > "public/sharesight/$code-prices.json"
done
