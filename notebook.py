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
    import math
    import re
    from functools import partial

    return alt, csv, datetime, itertools, json, mo, partial, re


@app.cell
def admin_fees():
    admin_fees = dict(
        hostplus = dict(fixed = 78, asset = 0, asset_max = 0),
        aussuper = dict(fixed = 52, asset = 0.12/100, asset_max = 600),
        unisuper = dict(fixed = 0, asset = 2/100, asset_max = 96),
    )
    return (admin_fees,)


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
        'value': 1+float(_x['return'])/100 if _x['return'] else None,
        'return': _x['return'],
        'date': datetime.datetime.strptime(_x['date'].split('T')[0], '%Y-%m-%d'),

    } for _x in hostplus_raw]

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
def parse_sharesight(datetime, mo, sharesight_raw):
    sharesight_prices = {}
    sharesight_payouts = {}

    for _name, _data in sharesight_raw.items():
        _ticker, _kind = _name.rsplit('-', 1)
        if _kind == 'prices':
            _data = [
                (datetime.datetime.strptime(_date, '%d %b %y'), _point['y2'],)
                for _date, _point in zip(_data['xAxis']['categories'], _data['series'])
            ]
            _data = [(b[0], b[1], b[1]/a[1]) for a, b in zip(_data[:-1], _data[1:])]
            sharesight_prices[_ticker] = _data
        elif _kind == 'payouts':
            sharesight_payouts[_ticker] = _data

    mo.ui.table([
        {
            'ticker': _ticker,
            'date': _date,
            'amount_per_share': _payout['company_event']['amount_per_share'],
        }
        for _ticker, _payouts in sharesight_payouts.items()
        for _payout in _payouts
        for _date in [_payout['paid_on']]
    ])
    return (sharesight_prices,)


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
def _(admin_fees):
    def make_alldata(*args, ending_balance):
        import itertools
        import datetime

        alldata = sorted(itertools.chain.from_iterable(args), key=lambda x: (x['name'], -x['date'].timestamp()))

        for _key, _group in itertools.groupby(alldata, key=lambda x: x['name']):
            _group = [x for x in _group if x['value'] is not None]

            _balance = ending_balance.value
            for _k, _g in itertools.groupby(_group, key=lambda x: fy_of_date(x['date'])):
                _g = list(_g)
                _asset_fee_this_year = 0
                for _x in _g:
                    _admin_fees = admin_fees[_x['fund']]
                    _asset_fee = min(_balance / len(_g) * _admin_fees['asset'], _admin_fees['asset_max'] - _asset_fee_this_year)
                    _balance += _admin_fees['fixed'] / len(_g) + _asset_fee
                    _asset_fee_this_year += _asset_fee
                    _balance /= _x['value']
                    _x['balance'] = _balance

        alldata.extend({
            'name': name,
            'balance': ending_balance.value,
            'date': datetime.datetime(2027, 7, 1),
        } for name in set(x['name'] for x in alldata))
        return alldata

    return (make_alldata,)


@app.cell
def _(admin_fees, aussuper, sharesight_prices):
    def make_memberdirect(code, *, ending_balance):
        import datetime
        import itertools

        etf = sorted(sharesight_prices[code], reverse=True)
        _aussuper_returns = sorted(
            (_x['date'], _x['value'])
            for _x in aussuper
            if _x['name'] == 'aussuper-International Shares' and _x['value'] is not None
        )
        _aussuper_returns = [(*x, p) for x, p in zip(_aussuper_returns, cumproduct(_x[1] for _x in _aussuper_returns))]

        def interpolate(date):
            prev = max(i for i in _aussuper_returns if i[0] <= date)
            next = min((i for i in _aussuper_returns if i[0] >= date), default=None)
            next = next or _aussuper_returns[-1]
            if prev[0] == next[0]:
                fraction = 1
            else:
                fraction = (date - next[0]) / (next[0] - prev[0])
            return prev[2] * ((next[2] / prev[2]) ** fraction)

        shares = ending_balance.value - 5000
        pooled = 5000
        data = []
        prev_date = datetime.datetime(2027, 7, 1)
        for _k, _g in itertools.groupby(etf, key=lambda x: fy_of_date(x[0])):
            _g = list(_g)
            _asset_fee_this_year = 0
            for _x in _g:
                _admin_fees = admin_fees['aussuper']
                _asset_fee = min((shares + pooled) / len(_g) * _admin_fees['asset'], _admin_fees['asset_max'] - _asset_fee_this_year)
                pooled += _admin_fees['fixed'] / len(_g) + _asset_fee
                _asset_fee_this_year += _asset_fee
                shares /= _x[2]

                pooled *= interpolate(_x[0]) / interpolate(prev_date)
                prev_date = _x[0]

                data.append({
                    'fund': 'aussuper',
                    'name': f'aussuper-memberdirect-{code}',
                    'date': _x[0],
                    'balance': shares + pooled,
                })
        data.append({
            'fund': 'aussuper',
            'name': f'aussuper-memberdirect-{code}',
            'balance': ending_balance.value,
            'date': datetime.datetime(2027, 7, 1),
        })

        return data

    return (make_memberdirect,)


@app.cell
def _(make_memberdirect, partial):
    direct_investment = {
        'aussuper-memberdirect-VGS': partial(make_memberdirect, 'VGS'),
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
    mo,
    multiselect,
    unisuper,
):
    _data = make_alldata(aussuper, hostplus, unisuper, ending_balance=ending_balance)
    _data.extend(itertools.chain.from_iterable(f(ending_balance=ending_balance) for f in direct_investment.values()))
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
    )
    mo.ui.altair_chart(chart)
    return


if __name__ == "__main__":
    app.run()
