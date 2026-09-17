.ONESHELL:
.SHELLFLAGS = -eu -o pipefail -x -c
.SILENT:

FIREFOX = Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:155.0) Gecko/20100101 Firefox/155.0

all: hostplus australiansuper ;

hostplus: public/hostplus.json ;
public/hostplus.json:
	# https://hostplus.com.au/members/our-products-and-services/investment-options/investment-returns
	auth_token="$$(curl https://hostplus.com.au/content/hostplus-program/home/members/our-products-and-services/investment-options/investment-returns.irm.auth.json | jq -re .)"
	curl 'https://hostplus.com.au/content/hostplus-program/home/members/our-products-and-services/investment-options/investment-returns.irm.returnscompare.json?InvestmentProduct=13&frequencyType=2&Startdate=1980-01-01&Enddate=2026-09-16&OptionsToCompare=ALL' --compressed -H 'Content-Type: application/json' -H "IRM-Authorization: Bearer $$auth_token" --compressed --fail | jq -re '.msg.MonthlyOptions[] | [.MonthEndDate, .OptionName, .Return] | @tsv' >$@

australiansuper: public/australiansuper.csv public/australiansuper-daily.csv ;
public/australiansuper.csv:
	curl 'https://www.australiansuper.com/api/graphs/annualrates/graph/download/super' -H 'User-Agent: ${FIREFOX}' --compressed --fail -o $@
public/australiansuper-daily.csv:
	curl 'https://www.australiansuper.com//api/graphs/dailyrates/download/?start=01/07/2008&end=15/09/2026&cumulative=False&superType=super&truncateDecimalPlaces=True&outputFilename=Daily%20Rates%2001%20Jul%202008%20-%2015%20Sep%202026.csv' -H 'User-Agent: ${FIREFOX}' --compressed --fail -o $@

unisuper: public/unisuper/ public/unisuper.txt ;
public/unisuper/:
	bash extract-unisuper.sh
public/unisuper.txt: public/unisuper/
	ls public/unisuper/ -1 | sort > $@

sharesight: public/sharesight/ public/sharesight.txt ;
public/sharesight/:
	bash extract-sharesight.sh
public/sharesight.txt: public/sharesight/
	ls public/sharesight/ -1 | sort > $@
