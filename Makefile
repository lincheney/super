.ONESHELL:
.SHELLFLAGS = -eu -o pipefail -x -c
.SILENT:

FIREFOX = Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:155.0) Gecko/20100101 Firefox/155.0

all: hostplus australiansuper rest ;

hostplus: public/hostplus.tsv ;
public/hostplus.tsv:
	# https://hostplus.com.au/members/our-products-and-services/investment-options/investment-returns
	auth_token="$$(curl https://hostplus.com.au/content/hostplus-program/home/members/our-products-and-services/investment-options/investment-returns.irm.auth.json | jq -re .)"
	curl 'https://hostplus.com.au/content/hostplus-program/home/members/our-products-and-services/investment-options/investment-returns.irm.returnscompare.json?InvestmentProduct=13&frequencyType=2&Startdate=1980-01-01&Enddate=2026-09-16&OptionsToCompare=ALL' --compressed -H 'Content-Type: application/json' -H "IRM-Authorization: Bearer $$auth_token" --compressed --fail | jq -re '["date", "name", "return"], (.msg.MonthlyOptions[] | [.MonthEndDate, .OptionName, .Return]) | @tsv' >$@

australiansuper: public/australiansuper.csv public/australiansuper-daily.csv ;
public/australiansuper.csv:
	curl 'https://www.australiansuper.com/api/graphs/annualrates/graph/download/super' -H 'User-Agent: ${FIREFOX}' --compressed --fail -o $@
public/australiansuper-daily.csv:
	curl 'https://www.australiansuper.com//api/graphs/dailyrates/download/?start=01/07/2008&end=15/09/2026&cumulative=False&superType=super&truncateDecimalPlaces=True&outputFilename=Daily%20Rates%2001%20Jul%202008%20-%2015%20Sep%202026.csv' -H 'User-Agent: ${FIREFOX}' --compressed --fail -o $@

unisuper: public/unisuper.tsv ;
public/unisuper.tsv:
	bash extract-unisuper.sh

sharesight: public/sharesight/ public/sharesight.txt ;
public/sharesight/:
	bash extract-sharesight.sh
public/sharesight.txt: public/sharesight/
	ls public/sharesight/ -1 | sort > $@

art: public/art.tsv ;
public/art.tsv:
	bash -x extract-art.sh

rest: public/rest.tsv ;
public/rest.tsv:
	today="$$(date +%Y-%m-%d)"
	curl "https://prd.apis.rest.com.au/neo-prod-investments-basepath/neo/ws/investments/1.0.0/unitPrices?productType=Super&investmentOptionType=Cash,CapitalStable,Balanced,CoreStrategy,BalancedIndexed,SustainableGrowth,HighGrowth,AustralianSharesIndexed,OverseasSharesIndexed&from=1998-01-01&to=$$today" --fail --compressed | jq -re '["date", "name", "value"], (.Super[] | .validFromDate as $$date | .unitPrices[] | [$$date, .OptionCode, .Sell]) | @tsv' > $@
