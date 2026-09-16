.ONESHELL:
.SHELLFLAGS = -eu -o pipefail -x -c
.SILENT:

hostplus: public/hostplus.json ;
public/hostplus.json:
	# https://hostplus.com.au/members/our-products-and-services/investment-options/investment-returns
	auth_token="$$(curl https://hostplus.com.au/content/hostplus-program/home/members/our-products-and-services/investment-options/investment-returns.irm.auth.json | jq -re .)"
	curl 'https://hostplus.com.au/content/hostplus-program/home/members/our-products-and-services/investment-options/investment-returns.irm.returnscompare.json?InvestmentProduct=13&frequencyType=2&Startdate=1980-01-01&Enddate=2026-09-16&OptionsToCompare=ALL' --compressed -H 'Content-Type: application/json' -H "IRM-Authorization: Bearer $$auth_token" --fail -o $@
