import marimo

__generated_with = "0.24.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import altair as alt
    import marimo as mo
    import json
    import csv
    import datetime
    import itertools
    import re

    return alt, csv, datetime, itertools, json, mo, re


@app.cell
def admin_fees():
    admin_fees = dict(
        hostplus = dict(fixed = 78, asset = 0, asset_max = 0),
        aussuper = dict(fixed = 52, asset = 0.12/100, asset_max = 600),
        unisuper = dict(fixed = 0, asset = 2/100, asset_max = 96),
    )
    return (admin_fees,)


@app.function
def no_direct_investment(asset, state=None, purchase=0, numperiods=1):
    if state is None:
        return dict(num_shares=0, pooled=purchase, total=purchase)
    state['pooled'] += purchase
    state['total'] = state['pooled']
    return state


@app.function
def memberdirect(asset, state=None, purchase=0, numperiods=1):
    if state is None:
        return dict(num_shares=(purchase-5000)/asset['value'], pooled=5000, total=purchase)
    state['pooled'] -= 150 / numperiods
    if state['pooled'] < 5000:
        diff = min(purchase, 5000 - state['pooled'])
        purchase -= diff
        state['pooled'] += diff
    if state['pooled'] < 5000:
        # top up
        state['num_shares'] -= (5000 - state['pooled']) / asset['value']
        state['pooled'] = 5000
    if purchase > 0:
        state['num_shares'] += purchase / asset['value']
    state['total'] = state['num_shares'] * asset['value'] + state['pooled']
    return state


@app.function
def choiceplus(asset, state=None, purchase=0, numperiods=1):
    if state is None:
        pooled = max(purchase * 0.2, 2000)
        return dict(num_shares=(purchase-pooled-200)/asset['value'], pooled=pooled, transaction=200, total=purchase)

    def total():
        return state['num_shares'] * asset['value'] + state['pooled'] + state['transaction']

    state['pooled'] -= 168 / numperiods

    required_pooled = max(total() * 0.2, 2000)
    if state['pooled'] < required_pooled:
        diff = min(purchase, required_pooled - state['pooled'])
        purchase -= diff
        state['pooled'] += diff
    if state['pooled'] < required_pooled:
        # top up
        state['num_shares'] -= (required_pooled - state['pooled']) / asset['value']
        state['pooled'] = required_pooled
    if purchase > 0:
        state['num_shares'] += purchase / asset['value']
    state['total'] = total()
    return state


@app.function
def read_file(path):
    if '://' in str(path):
        import urllib.request
        with urllib.request.urlopen(path) as response:
            return response.read()
    else:
        with open(path, 'rb') as file:
            return file.read()


@app.function
def fy_of_date(date):
    return date.year + (1 if date.month >= 7 else 0)


@app.function
def cumproduct(values):
    import itertools
    return itertools.accumulate(values, lambda x, y: x * y)


@app.cell
def load_hostplus(csv, mo):
    _file = mo.notebook_location()/'public'/'hostplus.tsv'
    hostplus_raw = list(csv.DictReader(read_file(_file).decode().splitlines(), delimiter='\t'))
    return (hostplus_raw,)


@app.cell
def parse_hostplus(datetime, hostplus_raw, itertools, mo):
    _data = [{

        'fund': 'hostplus',
        'name': f'hostplus-{_x['name']}',
        'value': 1+float(_x['return'])/100,
        'return': _x['return'],
        'date': datetime.datetime.strptime(_x['date'].split('T')[0], '%Y-%m-%d'),

    } for _x in hostplus_raw if _x['return'] and float(_x['return'])]

    _data.sort(key=lambda x: x['name'])
    hostplus = []
    for _, _group in itertools.groupby(_data, key=lambda x: x['name']):
        _group = sorted({x['date']: x for x in _group}.values(), key=lambda x: x['date'])
        hostplus.extend(itertools.dropwhile(lambda x: not x['return'], _group))

    mo.ui.table(hostplus)
    return (hostplus,)


@app.cell
def load_aussuper(csv, mo):
    _file = mo.notebook_location()/'public'/'australiansuper.csv'
    aussuper_annual_raw = list(csv.DictReader(read_file(_file).decode('latin1').splitlines()))
    _file = mo.notebook_location()/'public'/'australiansuper-daily.csv'
    aussuper_daily_raw = list(csv.DictReader(read_file(_file).decode().splitlines()))
    return aussuper_annual_raw, aussuper_daily_raw


@app.cell
def load_unisuper(csv, mo):
    _directory = mo.notebook_location()/'public'/'unisuper'
    _files = read_file(mo.notebook_location()/'public'/'unisuper.txt').decode().splitlines()
    unisuper_raw = {
        _file.removesuffix('.tsv'): list(csv.DictReader(read_file(_directory/_file).decode().splitlines(), delimiter='\t'))
        for _file in _files
    }
    return (unisuper_raw,)


@app.cell
def load_sharesight(json, mo):
    _directory = mo.notebook_location()/'public'/'sharesight'
    _files = read_file(mo.notebook_location()/'public'/'sharesight.txt').decode().splitlines()
    sharesight_raw = {
        _file.removesuffix('.json'): json.loads(read_file(_directory/_file))
        for _file in _files
        if _file
    }
    return (sharesight_raw,)


@app.cell
def parse_sharesight(datetime, sharesight_raw):
    sharesight_prices = {}
    sharesight_payouts = {}

    for _name, _data in sharesight_raw.items():
        _ticker, _kind = _name.rsplit('-', 1)
        if _kind == 'prices':
            _data = [
                (datetime.datetime.strptime(_date, '%d %b %y'), _point['y2'],)
                for _date, _point in zip(_data['xAxis']['categories'], _data['series'])
            ]
            _data = [{'date': b[0], 'value': b[1], 'return': b[1]/a[1]} for a, b in zip(_data[:-1], _data[1:])]
            sharesight_prices[_ticker] = _data
        elif _kind == 'payouts':
            sharesight_payouts[_ticker] = {datetime.datetime.strptime(_x['goes_ex_on'], '%Y-%m-%d'): _x for _x in _data}
    return sharesight_payouts, sharesight_prices


@app.cell
def parse_unisuper(datetime, itertools, mo, unisuper_raw):
    unisuper = []

    for _name, _chart in unisuper_raw.items():
        _chart = sorted(_chart, key=lambda x: x['date'])
        _monthly = []
        for _month, _group in itertools.groupby(_chart, key=lambda x: x['date'].rpartition('-')[0]):
            _group = list(_group)
            _monthly.append((_group[0], float(_group[-1]['value'])))

        _previous = float(_monthly[0][0]['value'])
        for _point, _value in _monthly:
            unisuper.append({
                'fund': 'unisuper',
                'name': f'unisuper-{_name}',
                'value': _value / _previous,
                'date': datetime.datetime.strptime(_point['date'], '%Y-%m-%d'),
            })
            _previous = _value

    mo.ui.table(unisuper)
    return (unisuper,)


@app.cell
def parse_aussuper(
    aussuper_annual_raw,
    aussuper_daily_raw,
    datetime,
    itertools,
    mo,
    re,
):
    aussuper = []

    _daily_names = aussuper_daily_raw[0].keys() - {'Rate Date'}
    _min_daily_fy = {name: fy_of_date(datetime.datetime.strptime(min(x['Rate Date'] for x in aussuper_daily_raw if x[name]), '%Y-%m-%d') - datetime.timedelta(days=1)) + 1 for name in _daily_names}
    print(_min_daily_fy)

    for _row in aussuper_annual_raw:
        _year = _row['Financial Year']
        _year = int(_year) if _year.isdigit() else 9999
        _date = datetime.datetime(_year, 6, 30)

        for _k, _v in _row.items():
            _k = re.sub(r'[^\w\s]', '', _k)
            if _k != 'Financial Year' and _v and _year < _min_daily_fy.get(_k, 9999):
                aussuper.append({
                    'fund': 'aussuper',
                    'name': f'aussuper-{_k}',
                    'value': 1+float(_v.strip('%'))/100,
                    'date': _date,
                })

    # daily is too fine grained and causes too much data, turn it down
    for _month, _group in itertools.groupby(sorted(aussuper_daily_raw, key=lambda x: x['Rate Date']), key=lambda x: x['Rate Date'].rpartition('-')[0]):
        _group = list(_group)
        _date = datetime.datetime.strptime(_group[0]['Rate Date'], '%Y-%m-%d')
        for _k in _daily_names:
            _value = list(cumproduct(1+float(x[_k] or 0)/100 for x in _group))[-1]
            aussuper.append({
                'fund': 'aussuper',
                'name': f'aussuper-{_k}',
                'value': _value,
                'date': _date,
            })

    mo.ui.table(aussuper)
    return (aussuper,)


@app.cell
def _(admin_fees, make_data):
    def make_alldata(*args, ending_balance):
        import itertools
        alldata = sorted(itertools.chain.from_iterable(args), key=lambda x: (x['name'], -x['date'].timestamp()))
        data = []
        for _, group in itertools.groupby(alldata, key=lambda x: x['name']):
            group = [x for x in group if x['value'] is not None]
            data.extend(make_data(group[0]['name'], group, admin_fees[group[0]['fund']], None, no_direct_investment, ending_balance=ending_balance))
        return data

    return (make_alldata,)


@app.cell
def _(sharesight_payouts, sharesight_prices):
    def make_data(name, pooled_returns, admin_fees, asset_code, direct_investment_func, *, ending_balance):
        import datetime
        import itertools

        pooled_returns = sorted(pooled_returns, key=lambda x: x['date'])
        pooled_returns = [{**x, 'cumulative': p} for x, p in zip(pooled_returns, cumproduct(x['value'] for x in pooled_returns))]
        asset = sharesight_prices[asset_code] if asset_code else pooled_returns
        asset = sorted(asset, reverse=True, key=lambda x: x['date'])
        mindate = min(x['date'] for x in pooled_returns)

        def interpolate(date):
            prev = max((x for x in pooled_returns if x['date'] <= date), key=lambda x: x['date'])
            next = min((x for x in pooled_returns if x['date'] >= date), key=lambda x: x['date'], default=None)
            next = next or pooled_returns[-1]
            if prev['date'] == next['date']:
                return next['cumulative']
            else:
                fraction = (date - next['date']) / (next['date'] - prev['date'])
                return prev['cumulative'] * (next['value'] ** fraction)

        # init
        state = direct_investment_func(asset[0], None, purchase=ending_balance)

        deferred_income = 0
        cost_base = 0
        data = []
        prev_date = datetime.datetime(2027, 7, 1)
        data.append({
            'fund': name.partition('-')[0],
            'name': name,
            'balance': state['total'],
            'date': prev_date,
            'deferred_income': deferred_income,
        })
        for _, group in itertools.groupby(asset, key=lambda x: fy_of_date(x['date'])):
            group = list(group)
            asset_fee_this_year = 0
            for x in group:
                if x['date'] < mindate:
                    continue

                asset_fee = min(state['total'] / len(group) * admin_fees['asset'], admin_fees['asset_max'] - asset_fee_this_year)
                state['pooled'] += admin_fees['fixed'] / len(group) + asset_fee + 150 / len(group)
                asset_fee_this_year += asset_fee

                state['pooled'] *= interpolate(x['date']) / interpolate(prev_date)
                prev_date = x['date']

                if asset_code and (payout := sharesight_payouts[asset_code].get(x['date'])):
                    au_local_dividend = payout['au_local_dividend']
                    deferred_income += au_local_dividend['deferred_income'] * state['num_shares'] / 1_000_000

                    cash = au_local_dividend['amount']
                    taxable = sum(au_local_dividend[k] for k in ['foreign_source_income', 'unfranked_amount', 'interest_payment_amount', 'franked_amount', 'non_discounted_capital_gains'])
                    discounted_taxable = au_local_dividend['discounted_capital_gains']
                    tax_credit = sum(au_local_dividend[k] for k in ['non_resident_withholding_tax', 'tax_credit'])
                    if tax_credit <= taxable:
                        taxable -= tax_credit
                        cash -= taxable * 0.15 + discounted_taxable * 0.1
                    elif tax_credit < taxable + discounted_taxable:
                        discounted_taxable -= tax_credit - taxable
                        cash -= discounted_taxable * 0.1
                    assert cash >= 0, cash

                    # drp
                    # initial + cash * initial / price == num_shares
                    # initial == num_shares / (1 + cash / price)
                    state['num_shares'] /= (1 + cash / 1_000_000 / x['value'])

                state = direct_investment_func(x, state, numperiods=len(group))

                data.append({
                    'fund': name.partition('-')[0],
                    'name': name,
                    'date': x['date'],
                    'balance': state['total'],
                    'deferred_income': deferred_income,
                })

        return data

    return (make_data,)


@app.cell
def _(admin_fees, aussuper, hostplus):
    _aussuper_pooled = [x for x in aussuper if x['name'] == 'aussuper-International Shares']
    _hostplus_pooled = [x for x in hostplus if x['name'] == 'hostplus-International Shares - Indexed']
    direct_investment = {
        'aussuper-memberdirect-VGS': dict(asset_code='VGS', direct_investment_func=memberdirect, admin_fees=admin_fees['aussuper'], pooled_returns=_aussuper_pooled),
        'aussuper-memberdirect-VAS': dict(asset_code='VAS', direct_investment_func=memberdirect, admin_fees=admin_fees['aussuper'], pooled_returns=_aussuper_pooled),
        'hostplus-choiceplus-VGS': dict(asset_code='VGS', direct_investment_func=choiceplus, admin_fees=admin_fees['hostplus'], pooled_returns=_hostplus_pooled),
        'hostplus-choiceplus-VAS': dict(asset_code='VAS', direct_investment_func=choiceplus, admin_fees=admin_fees['hostplus'], pooled_returns=_hostplus_pooled),
    }
    return (direct_investment,)


@app.cell
def filter_cumproduct(aussuper, direct_investment, hostplus, mo, unisuper):
    ending_balance = mo.ui.number(start=1, value=100_000, label="Ending balance")
    _options = sorted(set(x['name'] for x in hostplus + aussuper + unisuper) | (direct_investment.keys()))
    multiselect = mo.ui.multiselect(options=_options, label='Filter')
    mo.vstack([ending_balance, multiselect])
    return ending_balance, multiselect


@app.cell(hide_code=True)
def cumproduct_graph(
    alt,
    aussuper,
    direct_investment,
    ending_balance,
    hostplus,
    itertools,
    make_alldata,
    make_data,
    mo,
    multiselect,
    unisuper,
):
    _data = make_alldata(aussuper, hostplus, unisuper, ending_balance=ending_balance.value)
    _data.extend(itertools.chain.from_iterable(make_data(
        name,
        ending_balance=ending_balance.value,
        **kwargs
    ) for name, kwargs in direct_investment.items()))

    _data = [x for x in _data if not multiselect.value or x['name'] in multiselect.value]
    chart = (
        alt.Chart(alt.InlineData(_data))
        .mark_line()
        .encode(
            x=alt.X("date:T", scale=alt.Scale(reverse=True)),
            y=alt.Y('balance:Q', scale=alt.Scale(reverse=True)),
            color='name:N',
        )
        .properties(width="container")
        .interactive()
    )
    mo.ui.altair_chart(chart)
    return


if __name__ == "__main__":
    app.run()
