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

    return alt, csv, datetime, itertools, json, mo


@app.function
def read_file(path):
    if '://' in str(path):
        import urllib.request
        with urllib.request.urlopen(path) as response:
            return response.read()
    else:
        with open(path, 'rb') as file:
            return file.read()


@app.cell
def _(itertools):
    def cumproduct(values):
        return itertools.accumulate(values, lambda x, y: x * y)

    return


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
        'date': datetime.date.strptime(_x['MonthEndDate'].split('T')[0], '%Y-%m-%d'),

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
    aussuper_raw = list(csv.DictReader(read_file(_file).decode('latin1').splitlines()))
    return (aussuper_raw,)


@app.cell
def parse_aussuper(aussuper_raw, datetime, mo):
    aussuper = []
    for _row in aussuper_raw:
        _year = _row['Financial Year']
        if not _year.isdigit():
            continue
        _date = datetime.date(int(_year), 6, 30)

        for _k, _v in _row.items():
            if _k != 'Financial Year':
                aussuper.append({
                    'fund': 'aussuper',
                    'name': f'aussuper-{_k}',
                    'value': 1+float(_v.strip('%'))/100 if _v else None,
                    'date': _date,
                })
    mo.ui.table(aussuper)
    return (aussuper,)


@app.cell
def make_alldata(aussuper, hostplus, itertools, starting_balance):
    alldata = sorted(hostplus + aussuper, key=lambda x: (x['name'], x['date']))

    for _key, _group in itertools.groupby(alldata, key=lambda x: x['name']):
        _group = [x for x in _group if x['value'] is not None]

        _balance = starting_balance.value
        # $78 / year
        for _k, _g in itertools.groupby(_group, key=lambda x: x['date'].year + (1 if x['date'].month >= 7 else 0)):
            _g = list(_g)
            _aussuper_asset_fee = 0
            for _x in _g:
                _balance *= _x['value']
                if _key.startswith('hostplus'):
                    # $78 / year
                    _balance -= 78 / len(_g)
                elif _key.startswith('aussuper'):
                    # $52 / year + min(600, 0.12%)
                    _fee = min(0.12/100 * _balance, 600 - _aussuper_asset_fee)
                    _balance -= 52 / len(_g) + _fee
                    _aussuper_asset_fee += _fee
                else:
                    raise NotImplementedError(_key)
                _x['balance'] = _balance

        for _x in _group:
            _x['rev_balance'] = _balance - _x['balance']
    return (alldata,)


@app.cell
def filter_rev_cumproduct(aussuper, hostplus, mo):
    starting_balance = mo.ui.number(start=100_000, label="Starting balance")
    _options = sorted(set(x['name'] for x in hostplus + aussuper))
    multiselect = mo.ui.multiselect(options=_options, label='Filter')
    mo.vstack([starting_balance, multiselect])
    return multiselect, starting_balance


@app.cell(hide_code=True)
def rev_cumproduct_graph(alldata, alt, mo, multiselect):
    _selection = alt.selection_point(fields=['name'], bind='legend')
    _data = [x for x in alldata if not multiselect.value or x['name'] in multiselect.value]
    chart = (
        alt.Chart(alt.InlineData(_data))
        .mark_line()
        .encode(
            x=alt.X("date:T", scale=alt.Scale(reverse=False)),
            y='balance:Q',
            color='name:N',
            strokeOpacity=alt.when(_selection).then(alt.value(0.8)).otherwise(alt.value(0.2)),
        )
        .add_params(_selection)
    )
    mo.ui.altair_chart(chart)
    return


if __name__ == "__main__":
    app.run()
