# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "marimo>=0.24.1",
# ]
# ///

import marimo

__generated_with = "0.24.1"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _():
    import altair as alt
    import marimo as mo
    import json
    import csv
    import datetime
    import itertools
    import re

    return alt, csv, datetime, itertools, json, mo, re


@app.cell(hide_code=True)
def admin_fees():
    admin_fees = dict(
        hostplus = dict(fixed = 78, asset = 0, asset_max = 0),
        aussuper = dict(fixed = 52, asset = 0.12/100, asset_max = 600),
        unisuper = dict(fixed = 0, asset = 2/100, asset_max = 96),
        art = dict(fixed = 0, asset = 0, asset_max = 0),
    )
    return (admin_fees,)


@app.cell(hide_code=True)
def _(art, aussuper, hostplus, itertools, unisuper):
    def all_super_funds():
        return itertools.chain(art, aussuper, hostplus, unisuper)

    return (all_super_funds,)


@app.cell(hide_code=True)
def _(alt, mo):
    def make_graph(data, *, height=500, **kwargs):
        return mo.ui.altair_chart(
            alt.Chart(alt.InlineData(data))
            # make the point bigger so its easier to trigger tooltip
            .mark_line(point={'size': 100, 'stroke': 'transparent', 'filled': False})
            .encode(**kwargs)
            .properties(width="container", height=height)
            .interactive()
        )

    return (make_graph,)


@app.function(hide_code=True)
def calc_brokerage(amount, brokerage):
    if brokerage(0) > abs(amount):
        return 0, amount

    low = 0
    high = abs(amount)
    for _ in range(100):
        value = (low + high) / 2
        if value + brokerage(value) < abs(amount):
            low = value
        else:
            high = value
    return amount - brokerage((low + high) / 2), 0


@app.function(hide_code=True)
def no_direct_investment(asset, state=None, purchase=0, numperiods=1, *, direction):
    if state is None:
        return dict(num_shares=0, pooled=purchase, total=purchase)
    state['pooled'] += purchase * direction
    state['total'] = state['pooled']
    return state


@app.function(hide_code=True)
def memberdirect(asset, state=None, purchase=0, numperiods=1, *, direction):
    if state is None:
        return dict(num_shares=(purchase-5000)/asset['value'], pooled=5000, total=purchase)

    def brokerage(amount):
        return 10 + 0.08/100 * min(max(0, amount - 12_500), 50_000) + 0.04/100 * max(0, amount - 50_000)

    state['pooled'] -= 150 / numperiods * direction

    share_diff = purchase * direction
    if state['pooled'] < 5000:
        share_diff -= 5000 - state['pooled']
        state['pooled'] = 5000
    if share_diff:
        share_diff, leftover = calc_brokerage(abs(share_diff), brokerage)
        state['num_shares'] += share_diff / asset['value'] * direction
        state['pooled'] += leftover * direction

    state['total'] = state['num_shares'] * asset['value'] + state['pooled']
    return state


@app.cell(hide_code=True)
def _(hostplus):
    def choiceplus(asset, state=None, purchase=0, numperiods=1, *, direction):
        if state is None:
            pooled = max(purchase * 0.2, 2000)
            return dict(num_shares=(purchase-pooled-200)/asset['value'], pooled=pooled, transaction=200, total=purchase)

        def total():
            return state['num_shares'] * asset['value'] + state['pooled'] + state['transaction']
        def brokerage(amount):
            return 13 + 0.1/100 * max(0, amount - 13_000)

        # interest on transaction account, use the rate from the cash option
        interest = min((x for x in hostplus if x['name'] == 'hostplus-Cash'), key=lambda x: abs(x['date'] - asset['date']))
        interest = interest['value'] ** (12 / numperiods)
        state['transaction'] += state['transaction'] * ((interest - 1) * 0.85 - 0.1/100/numperiods) * direction
        if state['transaction'] < 200:
            state['pooled'] -= 200 - state['transaction']
            state['transaction'] = 200

        state['pooled'] -= 168 / numperiods * direction
        required_pooled = max(total() * 0.2, 2000)

        share_diff = purchase * direction
        if state['pooled'] < required_pooled:
            share_diff -= required_pooled - state['pooled']
            state['pooled'] = required_pooled
        if share_diff:
            share_diff, leftover = calc_brokerage(abs(share_diff), brokerage)
            state['num_shares'] += share_diff / asset['value'] * direction
            state['pooled'] += leftover * direction

        state['total'] = total()
        return state

    return (choiceplus,)


@app.function(hide_code=True)
def read_file(path):
    if '://' in str(path):
        import urllib.request
        with urllib.request.urlopen(path) as response:
            return response.read()
    else:
        with open(path, 'rb') as file:
            return file.read()


@app.function(hide_code=True)
def fy_of_date(date):
    return date.year + (1 if date.month >= 7 else 0)


@app.function(hide_code=True)
def cumproduct(values):
    import itertools
    return itertools.accumulate(values, lambda x, y: x * y)


@app.cell(hide_code=True)
def load_hostplus(csv, mo):
    _file = mo.notebook_location()/'public'/'hostplus.tsv'
    hostplus_raw = list(csv.DictReader(read_file(_file).decode().splitlines(), delimiter='\t'))
    return (hostplus_raw,)


@app.cell(hide_code=True)
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


@app.cell(hide_code=True)
def load_aussuper(csv, mo):
    _file = mo.notebook_location()/'public'/'australiansuper.csv'
    aussuper_annual_raw = list(csv.DictReader(read_file(_file).decode('latin1').splitlines()))
    _file = mo.notebook_location()/'public'/'australiansuper-daily.csv'
    aussuper_daily_raw = list(csv.DictReader(read_file(_file).decode().splitlines()))
    return aussuper_annual_raw, aussuper_daily_raw


@app.cell(hide_code=True)
def load_unisuper(csv, mo):
    _file = mo.notebook_location()/'public'/'unisuper.tsv'
    unisuper_raw = list(csv.DictReader(read_file(_file).decode().splitlines(), delimiter='\t'))
    return (unisuper_raw,)


@app.cell(hide_code=True)
def load_sharesight(json, mo):
    _directory = mo.notebook_location()/'public'/'sharesight'
    _files = read_file(mo.notebook_location()/'public'/'sharesight.txt').decode().splitlines()
    sharesight_raw = {
        _file.removesuffix('.json'): json.loads(read_file(_directory/_file))
        for _file in _files
        if _file
    }
    return (sharesight_raw,)


@app.cell(hide_code=True)
def load_art(csv, mo):
    _file = mo.notebook_location()/'public'/'art.tsv'
    art_raw = list(csv.DictReader(read_file(_file).decode().splitlines(), delimiter='\t'))
    return (art_raw,)


@app.cell(hide_code=True)
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

    # undo the stock split
    for _row in sharesight_prices['IVV']:
        if _row['date'] >= datetime.datetime(2022, 12, 9):
            _row['value'] *= 15
    return sharesight_payouts, sharesight_prices


@app.cell(hide_code=True)
def parse_unisuper(datetime, itertools, mo, unisuper_raw):
    unisuper = []

    for _name, _chart_iter in itertools.groupby(sorted(unisuper_raw, key=lambda x: (x['name'], x['date'])), key=lambda x: x['name']):
        _chart = list(_chart_iter)
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


@app.cell(hide_code=True)
def parse_art(datetime, itertools, mo, art_raw):
    art = []

    for _name, _chart_iter in itertools.groupby(sorted(art_raw, key=lambda x: (x['name'], x['date'])), key=lambda x: x['name']):
        _chart = list(_chart_iter)
        _previous = float(_chart[0]['value'])
        for _point in _chart:
            _value = float(_point['value'])
            art.append({
                'fund': 'art',
                'name': f'art-{_name}',
                'value': _value / _previous,
                'date': datetime.datetime.strptime(_point['date'].split('T')[0], '%Y-%m-%d'),
            })
            _previous = _value

    mo.ui.table(art)
    return (art,)


@app.cell(hide_code=True)
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


@app.cell(hide_code=True)
def _(admin_fees, make_data):
    def make_alldata(*args, direction, **kwargs):
        import itertools
        alldata = sorted(itertools.chain.from_iterable(args), key=lambda x: (x['name'], x['date'].timestamp() * direction))
        data = []
        for _, group in itertools.groupby(alldata, key=lambda x: x['name']):
            group = [x for x in group if x['value'] is not None]
            data.extend(make_data(
                group[0]['name'],
                group,
                admin_fees[group[0]['fund']],
                None,
                no_direct_investment,
                direction=direction,
                **kwargs,
            ))
        return data

    return (make_alldata,)


@app.cell(hide_code=True)
def _(datetime, sharesight_payouts, sharesight_prices):
    def make_data(
        name,
        pooled_returns,
        admin_fees,
        asset_code,
        direct_investment_func,
        *,
        direction,
        balance,
        initial_date=datetime.datetime(2027, 7, 1),
    ):
        import itertools

        pooled_returns = sorted(pooled_returns, key=lambda x: x['date'])
        pooled_returns = [{**x, 'cumulative': p} for x, p in zip(pooled_returns, cumproduct(x['value'] for x in pooled_returns))]
        asset = sharesight_prices[asset_code] if asset_code else pooled_returns
        asset = sorted(asset, reverse=direction==-1, key=lambda x: x['date'])
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

        deferred_income = 0
        cost_base = 0
        data = []

        prev_date = initial_date
        if direction == 1:
            mindate = prev_date = max(prev_date, mindate)

        # init
        asset = [a for a in asset if a['date'] >= mindate]
        if not asset:
            return ()
        state = direct_investment_func(asset[0], None, purchase=balance, direction=direction)

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
                asset_fee = min(state['total'] / len(group) * admin_fees['asset'], admin_fees['asset_max'] - asset_fee_this_year)
                state['pooled'] -= (admin_fees['fixed'] / len(group) + asset_fee) * direction
                asset_fee_this_year += asset_fee

                state['pooled'] *= (interpolate(x['date']) / interpolate(prev_date))
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
                    state['num_shares'] *= (1 + cash / 1_000_000 / x['value']) ** direction

                state = direct_investment_func(x, state, numperiods=len(group), direction=direction)

                data.append({
                    'fund': name.partition('-')[0],
                    'name': name,
                    'date': x['date'],
                    'balance': state['total'],
                    'deferred_income': deferred_income,
                })

        return data

    return (make_data,)


@app.cell(hide_code=True)
def _(admin_fees, aussuper, choiceplus, hostplus):
    _aussuper_pooled = [x for x in aussuper if x['name'] == 'aussuper-International Shares']
    _hostplus_pooled = [x for x in hostplus if x['name'] == 'hostplus-International Shares - Indexed']
    _memberdirect = dict(direct_investment_func=memberdirect, admin_fees=admin_fees['aussuper'], pooled_returns=_aussuper_pooled)
    _choiceplus = dict(direct_investment_func=choiceplus, admin_fees=admin_fees['hostplus'], pooled_returns=_hostplus_pooled)
    direct_investment = {
        'aussuper-memberdirect-VGS': dict(asset_code='VGS', **_memberdirect),
        'aussuper-memberdirect-VAS': dict(asset_code='VAS', **_memberdirect),
        'aussuper-memberdirect-IVV': dict(asset_code='IVV', **_memberdirect),
        'hostplus-choiceplus-VGS': dict(asset_code='VGS', **_choiceplus),
        'hostplus-choiceplus-VAS': dict(asset_code='VAS', **_choiceplus),
        'hostplus-choiceplus-IVV': dict(asset_code='IVV', **_choiceplus),
    }
    return (direct_investment,)


@app.cell(hide_code=True)
def _(art, aussuper, direct_investment, hostplus, mo, unisuper):
    ending_balance = mo.ui.number(start=1, value=1_000_000, label="Ending balance")
    _names = list(set(x['name'] for x in art + aussuper + hostplus + unisuper)) + list(direct_investment.keys())
    _names.sort()
    selected_options = mo.ui.table([{'value': v} for v in _names], page_size=25)
    mo.vstack([
        selected_options,
        ending_balance,
    ])
    return ending_balance, selected_options


@app.cell(hide_code=True)
def cumproduct_graph(
    all_super_funds,
    alt,
    direct_investment,
    ending_balance,
    itertools,
    make_alldata,
    make_data,
    make_graph,
    mo,
    selected_options,
):
    _data = make_alldata(all_super_funds(), balance=ending_balance.value, direction=-1)
    _data.extend(itertools.chain.from_iterable(make_data(
        name,
        balance=ending_balance.value,
        direction=-1,
        **kwargs
    ) for name, kwargs in direct_investment.items()))
    _data = [x for x in _data if not selected_options.value or x['name'] in (y['value'] for y in selected_options.value)]

    mo.ui.altair_chart(make_graph(
        _data,
        x=alt.X('date:T', scale=alt.Scale(reverse=True)),
        y=alt.Y('balance:Q', scale=alt.Scale(reverse=True)),
        color='name:N',
    ))
    return


@app.cell(hide_code=True)
def _(all_super_funds, mo):
    starting_balance = mo.ui.number(start=1, value=1_000_000, label="Ending balance")
    _start = min(x['date'] for x in all_super_funds()).date()
    _stop = max(x['date'] for x in all_super_funds()).date()
    starting_date = mo.ui.date(start=_start, stop=_stop, label="Start Date")
    mo.vstack([
        starting_balance,
        starting_date,
    ])
    return starting_balance, starting_date


@app.cell(hide_code=True)
def _(
    all_super_funds,
    datetime,
    direct_investment,
    itertools,
    make_alldata,
    make_data,
    make_graph,
    mo,
    selected_options,
    starting_balance,
    starting_date,
):
    _initial_date = datetime.datetime(starting_date.value.year, starting_date.value.month, starting_date.value.day)
    _data = []
    _data = make_alldata(all_super_funds(), balance=starting_balance.value, direction=1, initial_date=_initial_date)
    _data.extend(itertools.chain.from_iterable(make_data(
        name,
        balance=starting_balance.value,
        initial_date=_initial_date,
        direction=1,
        **kwargs
    ) for name, kwargs in direct_investment.items()))
    _data = [x for x in _data if not selected_options.value or x['name'] in (y['value'] for y in selected_options.value)]

    mo.ui.altair_chart(make_graph(
        _data,
        x='date:T',
        y='balance:Q',
        color='name:N',
    ))
    return


if __name__ == "__main__":
    app.run()
