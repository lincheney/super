.ONESHELL:
.SHELLFLAGS = -eu -o pipefail -x -c
.SILENT:

all: hostplus australiansuper ;

hostplus: public/hostplus.json ;
public/hostplus.json:
	# https://hostplus.com.au/members/our-products-and-services/investment-options/investment-returns
	auth_token="$$(curl https://hostplus.com.au/content/hostplus-program/home/members/our-products-and-services/investment-options/investment-returns.irm.auth.json | jq -re .)"
	curl 'https://hostplus.com.au/content/hostplus-program/home/members/our-products-and-services/investment-options/investment-returns.irm.returnscompare.json?InvestmentProduct=13&frequencyType=2&Startdate=1980-01-01&Enddate=2026-09-16&OptionsToCompare=ALL' --compressed -H 'Content-Type: application/json' -H "IRM-Authorization: Bearer $$auth_token" --compressed --fail -o $@

australiansuper: public/australiansuper.csv ;
public/australiansuper.csv:
	curl 'https://www.australiansuper.com/api/graphs/annualrates/graph/download/super' -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:155.0) Gecko/20100101 Firefox/155.0' --compressed --fail -o $@

unisuper: public/unisuper/ ;
public/unisuper/:
	bash extract-unisuper.sh
