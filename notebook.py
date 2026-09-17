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
def load_hostplus(json, mo):
    _file = mo.notebook_location()/'public'/'hostplus.json'
    hostplus_raw = json.loads(read_file(_file))
    return (hostplus_raw,)


@app.cell
def parse_hostplus(datetime, hostplus_raw, itertools, mo):
    _data = [{

        'fund': 'hostplus',
        'name': f'hostplus-{_x['OptionName']}',
        'value': 1+_x['Return']/100 if _x['Return'] is not None else None,
        'return': _x['Return'],
        'date': datetime.datetime.strptime(_x['MonthEndDate'].split('T')[0], '%Y-%m-%d'),

    } for _x in hostplus_raw['msg']['MonthlyOptions']]

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
            if _k != 'Financial Year' and _year < _min_daily_fy.get(_k, 9999):
                aussuper.append({
                    'fund': 'aussuper',
                    'name': f'aussuper-{_k}',
                    'value': 1+float(_v.strip('%'))/100 if _v else None,
                    'date': _date,
                })

    # daily is too fine grained and causes too much data, turn it down
    for _month, _group in itertools.groupby(sorted(aussuper_daily_raw, key=lambda x: x['Rate Date']), key=lambda x: x['Rate Date'].rpartition('-')[0]):
        _group = list(_group)
        _date = datetime.datetime.strptime(_group[0]['Rate Date'], '%Y-%m-%d')
        _fy = fy_of_date(_date)
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


@app.function
def make_alldata(*args, ending_balance):
    import itertools
    import datetime

    alldata = sorted(itertools.chain.from_iterable(args), key=lambda x: (x['name'], -x['date'].timestamp()))

    for _key, _group in itertools.groupby(alldata, key=lambda x: x['name']):
        _group = [x for x in _group if x['value'] is not None]

        _balance = ending_balance.value
        for _k, _g in itertools.groupby(_group, key=lambda x: fy_of_date(x['date'])):
            _g = list(_g)
            _asset_fee = 0
            for _x in _g:
                if _key.startswith('hostplus'):
                    # $78 per year
                    _balance += 78 / len(_g)
                elif _key.startswith('aussuper'):
                    # $52 + min(600, 0.12%) per year
                    _fee = min(0.12/100 * _balance / len(_g), 600 - _asset_fee)
                    _balance += 52 / len(_g) + _fee
                    _asset_fee += _fee
                else:
                    raise NotImplementedError(_key)
                _balance /= _x['value']
                _x['balance'] = _balance

        for _x in _group:
            _x['rev_balance'] = ending_balance.value - _x['balance']

    alldata.extend({
        'name': name,
        'balance': ending_balance.value,
        'rev_balance': 0,
        'date': datetime.datetime(2027, 7, 1),
    } for name in set(x['name'] for x in alldata))
    return alldata


@app.cell
def filter_rev_cumproduct(aussuper, hostplus, mo):
    ending_balance = mo.ui.number(start=1, value=100_000, label="Ending balance")
    _options = sorted(set(x['name'] for x in hostplus + aussuper))
    multiselect = mo.ui.multiselect(options=_options, label='Filter')
    mo.vstack([ending_balance, multiselect])
    return ending_balance, multiselect


@app.cell(hide_code=True)
def rev_cumproduct_graph(
    alt,
    aussuper,
    ending_balance,
    hostplus,
    mo,
    multiselect,
):
    _data = [x for x in make_alldata(aussuper, hostplus, ending_balance=ending_balance) if not multiselect.value or x['name'] in multiselect.value]
    chart = (
        alt.Chart(alt.InlineData(_data))
        .mark_line()
        .encode(
            x=alt.X("date:T", scale=alt.Scale(reverse=True)),
            y='rev_balance:Q',
            color='name:N',
        )
        .properties(width="container")
    )
    mo.ui.altair_chart(chart)
    return


if __name__ == "__main__":
    app.run()
