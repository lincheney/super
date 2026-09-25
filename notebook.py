# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "marimo>=0.24.1",
# ]
# ///

import marimo

__generated_with = "0.24.2"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _():
    import altair as alt
    import marimo as mo
    import json
    import csv
    import datetime
    import itertools
    import statistics
    import re

    TAX = 0.15
    CGT = 0.1

    mo._runtime.context.get_context().marimo_config["runtime"]["output_max_bytes"] = 20_000_000
    return CGT, TAX, alt, csv, datetime, itertools, json, mo, re, statistics


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Superannuation

    Graphs for super.
    Thinking about switching my super, but I want to look at not just fees but performance as well.
    Also how does memberdirect/choiceplus etc. compare to the usual pooled options?

    I'm not looking at all at insurance or additional things like that.

    Right now I've got data for:
    * Australian Super (using fees from 2026-10-10)
    * Hostplus (using fees from 2026-09-30)
    * Care Super
    * Rest Super
    * Australian Retirement Trust
    * UniSuper

    Disclaimers:
    * Not financial advice
    * Past performance is not an indication of future performance
    * My maths may be wrong. At the very least it is a simplification of what happens in reality
    * My understanding of tax may be wrong.

    Things not accounted for (yet):
    * TBC
    * Div 296

    Other great resources:
    * <https://lazykoalainvesting.com/>
    * <https://passiveinvestingaustralia.com/category/superannuation/>
    """)
    return


@app.cell
def admin_fees():
    admin_fees = dict(
        hostplus = dict(fixed = 78, asset = 0, asset_max = 0),
        aussuper = dict(fixed = 52, asset = 0.12/100, asset_max = 600),
        unisuper = dict(fixed = 0, asset = 2/100, asset_max = 96),
        art = dict(fixed = 1.1*52, asset = 0.1/100, asset_max = 0.1/100*500_000),
        stake = dict(fixed = 1319, asset = 0, asset_max = 0),
        rest = dict(fixed = 1.5*52, asset = 0.1/100, asset_max = 600),
        caresuper = dict(fixed = 67.6, asset = 0.15/100, asset_max = 750),
    )
    MEMBERDIRECT_PLATFORM_FEE = 150
    CHOICEPLUS_PLATFORM_FEE = 150
    CARESUPER_DIO_PLATFORM_FEE = 264
    return (
        CARESUPER_DIO_PLATFORM_FEE,
        CHOICEPLUS_PLATFORM_FEE,
        MEMBERDIRECT_PLATFORM_FEE,
        admin_fees,
    )


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Forward graph

    This is the "intuitive" graph that I'm not going to be using much.
    It shows "if you invested $(insert-amount) at (insert-date) how much money would you have now",
    but the problem is you have to set a reasonable start date and care about whether your super investment option
    even existed at that point. If it didn't, you can include it anyway but it will show up with an unfair handicap
    due to starting late. In fact if you go back far enough, the balanced options start looking really good -
    but only because they've been around the longest.

    The graph by default filters for "balanced" and "international shares" options.
    Change it to see other things.
    Or enable everything.

    I don't know what's up with Rest Super Balanced and why it is so different from the other super funds' Balanced options.
    """)
    return


@app.cell(hide_code=True)
def forward_graph_controls(all_super_funds, direct_investment, mo, re):
    starting_balance = mo.ui.number(start=1, value=100_000, label="Starting balance $")

    starting_contributions_input = mo.ui.number(start=0, label="Contribute extra $")
    starting_contributions_freq_input = mo.ui.number(start=0, value=12, label="into super")
    starting_direct_investment_freq_input = mo.ui.number(start=0, value=12, label="Batch direct investment trades")
    starting_direct_investment_min_input = mo.ui.number(start=0, value=1000, label='of at least $')

    _names = list(set(x['name'] for x in all_super_funds())) + list(direct_investment.keys())
    _names.sort()
    # show "best" performing funds by default
    #  _default = [name for perf, name in sorted(mean_performance)[-10:]]
    _default = [x for x in _names if re.search('international shares|overseas|^balanced$', x.lower().partition('-')[2])]
    forward_selected_options = mo.ui.multiselect(options=_names, value=_default, label='Filter')

    _start = min(x['date'] for x in all_super_funds()).date()
    _stop = max(x['date'] for x in all_super_funds()).date()
    starting_date = mo.ui.date(start=_start, stop=_stop, value='2017-01-01', label="Start Date")

    allow_missing_data = mo.ui.checkbox(label='Show even if option does not exist at start date')

    mo.vstack([
        starting_balance,
        mo.hstack([starting_contributions_input, starting_contributions_freq_input, mo.md('times per year')], justify='start'),
        mo.hstack([starting_direct_investment_freq_input, mo.md('times per year'), starting_direct_investment_min_input], justify='start'),
        starting_date,
        allow_missing_data,
        forward_selected_options,
    ])
    return (
        allow_missing_data,
        forward_selected_options,
        starting_balance,
        starting_contributions_freq_input,
        starting_contributions_input,
        starting_date,
        starting_direct_investment_freq_input,
        starting_direct_investment_min_input,
    )


@app.cell(hide_code=True)
def forward_graph(
    all_super_funds,
    allow_missing_data,
    alt,
    datetime,
    direct_investment,
    forward_selected_options,
    itertools,
    make_alldata,
    make_graph,
    mo,
    starting_balance,
    starting_contributions_freq_input,
    starting_contributions_input,
    starting_date,
    starting_direct_investment_freq_input,
    starting_direct_investment_min_input,
):
    _initial_date = datetime.datetime(starting_date.value.year, starting_date.value.month, starting_date.value.day)
    _data = make_alldata(
        all_super_funds(),
        direct_investment,
        balance=starting_balance.value,
        direction=1,
        initial_date=_initial_date,
        filter=forward_selected_options.value,
        contributions=(starting_contributions_input.value, starting_contributions_freq_input.value),
        direct_investment_buys=(starting_direct_investment_min_input.value, starting_direct_investment_freq_input.value),
    )
    if not allow_missing_data.value:
        _data.sort(key=lambda x: (x['name'], x['date']))
        _missing_data = set()
        for _k, _g in itertools.groupby(_data, lambda x: x['name']):
            if (next(_g)['date'] - _initial_date).days > 29:
                _missing_data.add(_k)
        _data = [x for x in _data if x['name'] not in _missing_data]
    mo.ui.altair_chart(make_graph(
        _data,
        x='date:T',
        y='balance:Q',
        color=alt.Color('name:N').legend(orient='bottom', columns=3),
    ))
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Backward graph

    This graph is unintuitive but can work a bit better.
    It shows "in order to get $(insert-amount) by now, what super balance would I have needed back 1 year ago, 2 years ago etc".
    The axes are in reverse, so time goes backwards as you move to the right and the required super balance gets *lower* as you move up.
    The *lower* the required super balance the *better*, since everyone ends with $1 mil, the less money I need to start with
    the better. Its a lot more impressive to make $1 mil from a starting point of $100k than from $900k.

    Anyway, I don't look much at the specific numbers, lines at the top are better, lines at the bottom are worse.
    The main thing is this graph can go really far back in time without having to worry about a common starting date.
    """)
    return


@app.cell(hide_code=True)
def backward_graph_controls(all_super_funds, direct_investment, mo, re):
    ending_balance = mo.ui.number(start=1, value=1_000_000, label="Ending balance $")

    ending_contributions_input = mo.ui.number(start=0, label="Contribute extra $")
    ending_contributions_freq_input = mo.ui.number(start=0, value=12, label="into super")
    ending_direct_investment_freq_input = mo.ui.number(start=0, value=12, label="Batch direct investment trades")
    ending_direct_investment_min_input = mo.ui.number(start=0, value=1000, label='of at least $')

    _names = list(set(x['name'] for x in all_super_funds())) + list(direct_investment.keys())
    _names.sort()
    # show "best" performing funds by default
    #  _default = [name for perf, name in sorted(mean_performance)[-10:]]
    _default = [x for x in _names if re.search('international shares|overseas|^balanced$', x.lower().partition('-')[2])]
    backward_selected_options = mo.ui.multiselect(options=_names, value=_default, label='Filter')

    backward_y_log = mo.ui.checkbox(label='Log scale for y axis')

    mo.vstack([
        ending_balance,
        mo.hstack([ending_contributions_input, ending_contributions_freq_input, mo.md('times per year')], justify='start'),
        mo.hstack([ending_direct_investment_freq_input, mo.md('times per year'), ending_direct_investment_min_input], justify='start'),
        backward_selected_options,
        backward_y_log,
    ])
    return (
        backward_selected_options,
        backward_y_log,
        ending_balance,
        ending_contributions_freq_input,
        ending_contributions_input,
        ending_direct_investment_freq_input,
        ending_direct_investment_min_input,
    )


@app.cell(hide_code=True)
def backward_graph(backward_selected_options, make_backward_graph):
    make_backward_graph(backward_selected_options.value)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Per super fund

    A graph per super fund.
    This makes it easy to see the "levels" of performance from
    cash -> stable -> balanced -> growth -> international shares,
    which is a pattern that is pretty consistent across all the funds.
    """)
    return


@app.cell(hide_code=True)
def _(all_super_funds, mo):
    _funds = sorted(set(k['fund'] for k in all_super_funds()))
    fund_checkboxes = mo.ui.dictionary({f: mo.ui.checkbox(label=f, value=f==_funds[0]) for f in _funds})
    mo.vstack(fund_checkboxes.values())
    return (fund_checkboxes,)


@app.cell(hide_code=True)
def backward_graph_for_funds(
    all_super_funds,
    fund_checkboxes,
    make_backward_graph,
):
    _graph = None
    if _visible_funds := [f for f, c in fund_checkboxes.value.items() if c]:
        _graph = make_backward_graph([k['name'] for k in all_super_funds() if k['fund'] in _visible_funds])
    _graph
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Direct investment

    Graph for Aus Super's Member Direct, Hostplus' ChoicePlus and Care Super's Direct Investment Option (DIO).
    Also Stake SMSF because its a similar idea.
    And Hostplus International Shares Indexed because its nice to use the "pooled fund benchmark" against VGS.

    If you look at it closely, Member Direct and Stake SMSF are basically the same (with Member Direct being a *pixel* better)
    and ChoicePlus and Care Super DIO slightly worse and then the pooled fund slightly worse than that.

    > There's a slew of pros and cons for SMSF that I'm not going to look at here, this is only about returns.

    If you have look at IVV instead, the differences are more pronounced.

    > I've chosen these ETFs not as an endorsement but just to illustrate behaviour, e.g. IVV is only serving
    > as an example of how each one is affected by historical outperformance vs VGS
    """)
    return


@app.cell(hide_code=True)
def etf_checkboxes(direct_investment, mo):
    _etfs = sorted(x['asset_code'] for x in direct_investment.values())
    etf_checkboxes = mo.ui.dictionary({f: mo.ui.checkbox(label=f, value=f=='VGS') for f in _etfs})
    mo.vstack(etf_checkboxes.values())
    return (etf_checkboxes,)


@app.cell(hide_code=True)
def backward_di_vgs_graph(
    direct_investment,
    etf_checkboxes,
    make_backward_graph,
):
    _graph = None
    if _visible_etfs := [f for f, c in etf_checkboxes.value.items() if c]:
        _graph = make_backward_graph([k for k, v in direct_investment.items() if v['asset_code'] in _visible_etfs] + ['hostplus-International Shares - Indexed'])
    _graph
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    The simulations here are grossly simplified, e.g. in reality you would not be able to put your entire ChoicePlus balance into VGS
    and it pretends you can use up all your money on fractional shares.

    Each option uses their own international shares pooled fund for any mandatory pooled fund balance.

    You may want to tweak the contributions and direct investment frequencies inputs from waaay above
    to see what affect brokerage has (not that much).
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Selling direct investment early

    You should hold the direct investment until moving it into pension phase,
    but what if you change your mind and sell it off and incur CGT?
    How long until the extra growth is worth the extra fees (and CGT)?

    This graph is dodgy. For each option I've taken a whole bunch of starting points
    and gotten the balance Y after X years, then plotted the confidence interval (roughly)
    against Hostplus International Shares Indexed as the benchmark.

    It *seems* to show that direct investment (with VGS) does better *on average* after a couple years
    but only starts peeling away around 5-6 years.
    """)
    return


@app.cell(hide_code=True)
def direct_investment_early_sell_graph(
    CGT,
    admin_fees,
    alt,
    datetime,
    direct_investment,
    hostplus,
    itertools,
    make_data,
    mo,
    starting_balance,
    statistics,
):
    _long_ago = datetime.datetime(1900, 1, 1)
    _name = 'hostplus-International Shares'
    _hostplus_pooled = [x for x in hostplus if x['name'] == _name]
    _hostplus_pooled = (_name, {'pooled_returns': _hostplus_pooled, 'admin_fees': admin_fees['hostplus']})

    _data = []
    _grid = list(direct_investment.items()) + [_hostplus_pooled]
    for _name, _kwargs in _grid:
        if 'VAS' in _name or 'stake' in _name or 'STW' in _name:
            continue
        _mindate = next(itertools.islice(make_data(_name, balance=starting_balance.value, direction=1, initial_date=_long_ago, **_kwargs), 1, 2))['date']
        for _year in range(fy_of_date(_mindate), fy_of_date(datetime.date.today())):
            _date = datetime.datetime(_year, 7, 1)
            for _i, _row in enumerate(make_data(_name, balance=starting_balance.value, direction=1, initial_date=_date, **_kwargs)):
                if _i < 1:
                    _mindate = _row['date']
                else:
                    # sell it all now!
                    # ignore brokerage for now
                    _row['balance'] -= (_row['capital'] - _row['cost_base'] + _row['deferred_income']) * CGT
                    _row['elapsed'] = round((_row['date'] - _mindate).days / 365, 1)
                    _data.append({'name': _row['name'], 'balance': _row['balance'], 'elapsed': _row['elapsed']})

    _data = [x for x in _data if x['elapsed'] <= 10]
    _data.sort(key=lambda x: (x['name'], x['elapsed']))
    _quantiles = []
    for _k, _g in itertools.groupby(_data, key=lambda x: (x['name'], x['elapsed'])):
        _g = [x['balance'] for x in _g]
        _mean = statistics.mean(_g)
        _z = 1.96
        _t = _z + (_z**3 + _z) / 4 / (len(_g) - 1)
        _delta = _t * statistics.stdev(_g) / len(_g) ** 0.5
        _q = [_mean - _delta, _mean + _delta]
        #  _q = statistics.quantiles((x['balance'] for x in _g), n=10, method='inclusive')
        _quantiles.append({'name': _k[0], 'elapsed': _k[1], 'upper': _q[-1], 'lower': _q[0]})

    _chart = (
        alt.Chart(alt.InlineData(_quantiles))
        .mark_area(opacity=0.5)
        .encode(
            x='elapsed:Q',
            y='lower:Q',
            y2='upper:Q',
            color=alt.Color('name:N').legend(orient='bottom', columns=3),
            stroke='name:N'
        )
    )
    mo.ui.altair_chart(
        _chart
        .properties(width="container", height=500)
        .interactive()
    )
    return


@app.cell(hide_code=True)
def extra_code_below(mo):
    mo.md(r"""
    ## extra code below
    """)
    return


@app.cell(hide_code=True)
def _(art, aussuper, caresuper, hostplus, itertools, rest, unisuper):
    def all_super_funds():
        return itertools.chain(art, aussuper, hostplus, unisuper, rest, caresuper)

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


@app.cell(hide_code=True)
def _(
    all_super_funds,
    alt,
    backward_y_log,
    direct_investment,
    ending_balance,
    ending_contributions_freq_input,
    ending_contributions_input,
    ending_direct_investment_freq_input,
    ending_direct_investment_min_input,
    make_alldata,
    make_graph,
    mo,
):
    def make_backward_graph(filter):
        _data = make_alldata(
            all_super_funds(),
            direct_investment,
            balance=ending_balance.value,
            direction=-1,
            filter=filter,
            contributions=(ending_contributions_input.value, ending_contributions_freq_input.value),
            direct_investment_buys=(ending_direct_investment_min_input.value, ending_direct_investment_freq_input.value),
        )
        _miny = min(x['balance'] for x in _data)
        _miny -= 0.1 * abs(_miny)
        return mo.ui.altair_chart(make_graph(
            _data,
            x=alt.X('date:T', scale=alt.Scale(reverse=True)),
            y=alt.Y('balance:Q', scale=alt.Scale(reverse=True, type='symlog' if backward_y_log.value else 'linear', domainMin=_miny)),
            color=alt.Color('name:N').legend(orient='bottom', columns=3),
        ))

    return (make_backward_graph,)


@app.function(hide_code=True)
def calc_brokerage(amount, brokerage):
    if amount >= 0 and brokerage(0) > amount:
        return 0, amount, 0

    low = min(amount, 0)
    high = max(amount, 0)
    while True:
        mid = (low + high) / 2
        diff = mid + brokerage(abs(mid)) - amount
        if abs(diff) < 0.01 or high - low < 0.01:
            break
        elif diff < 0:
            low = mid
        else:
            high = mid
    return mid, 0, brokerage(mid)


@app.cell(hide_code=True)
def _(CGT):
    def rebalance_pooled(state, required_pooled, direction, asset, brokerage, make_purchase):

        value = 0
        leftover = 0

        if state['pooled'] < required_pooled:
            value -= required_pooled - state['pooled']
            state['pooled'] = required_pooled
        elif make_purchase and state['pooled'] > required_pooled + make_purchase:
            value += state['pooled'] - required_pooled
            state['pooled'] = required_pooled

        value *= direction

        if value > 0:
            # buy
            value, leftover, fee = calc_brokerage(value, brokerage)
            state['cost_base'] += fee + value
        elif value < 0:
            # sell
            value, leftover, fee = calc_brokerage(value, lambda x: brokerage(x) + CGT * -x/asset['value'] * max(0, asset['value'] - (state['cost_base'] + brokerage(x)) / state['num_shares']))
            state['cost_base'] += brokerage(value)
            state['cost_base'] -= state['cost_base'] / state['num_shares'] * abs(value)/asset['value']

        state['num_shares'] += value/asset['value'] * direction
        state['pooled'] += leftover
        return state

    return (rebalance_pooled,)


@app.function(hide_code=True)
def no_direct_investment(asset, state, numperiods=1, *, direction, make_purchase=0):
    if isinstance(state, (int, float)):
        return dict(num_shares=0, pooled=state, total=state, cost_base=0)
    state['total'] = state['pooled']
    return state


@app.cell(hide_code=True)
def _(MEMBERDIRECT_PLATFORM_FEE, TAX, aussuper, rebalance_pooled):
    def memberdirect(asset, state, numperiods=1, *, direction, make_purchase=0):
        def brokerage(amount):
            return 10 + 0.08/100 * min(max(0, amount - 12_500), 50_000) + 0.04/100 * max(0, amount - 50_000)

        if isinstance(state, (int, float)):
            shares, leftover, fee = state - 5000 - 400, 0, 0
            #  if direction == 1:
                #  shares, leftover, fee = calc_brokerage(shares, brokerage)
            return dict(
                num_shares=shares/asset['value'],
                pooled=5000 + leftover,
                transaction=400,
                total=state,
                cost_base=shares+fee,
            )

        # interest on transaction account, use the rate from the cash option
        interest = min((x for x in aussuper if x['name'] == 'aussuper-Cash'), key=lambda x: abs(x['date'] - asset['date']))
        interest = interest['value'] ** (12 / numperiods)
        state['transaction'] += state['transaction'] * (interest - 1) * (1 - TAX) * direction
        if state['transaction'] < 400:
            state['pooled'] -= 400 - state['transaction']
            state['transaction'] = 400

        state['pooled'] -= MEMBERDIRECT_PLATFORM_FEE / numperiods * direction
        state = rebalance_pooled(state, 5000, direction, asset, brokerage, make_purchase=make_purchase)

        state['total'] = state['num_shares'] * asset['value'] + state['pooled'] + state['transaction']
        return state

    return (memberdirect,)


@app.cell(hide_code=True)
def _(CHOICEPLUS_PLATFORM_FEE, TAX, hostplus, rebalance_pooled):
    def choiceplus(asset, state, numperiods=1, *, direction, make_purchase=0):
        def brokerage(amount):
            return 13 + 0.1/100 * max(0, amount - 13_000)

        if isinstance(state, (int, float)):
            pooled = max(state * 0.2, 2000)
            shares, leftover, fee = state - pooled - 200, 0, 0
            #  if direction == 1:
                #  shares, leftover, fee = calc_brokerage(shares, brokerage)
            return dict(
                num_shares=shares/asset['value'],
                pooled=pooled+leftover,
                transaction=200,
                total=state,
                cost_base=shares + fee,
            )

        def total():
            return state['num_shares'] * asset['value'] + state['pooled'] + state['transaction']

        # interest on transaction account, use the rate from the cash option
        interest = min((x for x in hostplus if x['name'] == 'hostplus-Cash'), key=lambda x: abs(x['date'] - asset['date']))
        interest = interest['value'] ** (12 / numperiods)
        state['transaction'] += state['transaction'] * ((interest - 1) * (1 - TAX) - 0.1/100/numperiods) * direction
        if state['transaction'] < 200:
            state['pooled'] -= 200 - state['transaction']
            state['transaction'] = 200

        state['pooled'] -= CHOICEPLUS_PLATFORM_FEE / numperiods * direction
        required_pooled = max(total() * 0.2, 2000)
        state = rebalance_pooled(state, required_pooled, direction, asset, brokerage, make_purchase=make_purchase)

        state['total'] = total()
        return state

    return (choiceplus,)


@app.cell(hide_code=True)
def _(CARESUPER_DIO_PLATFORM_FEE, TAX, caresuper, rebalance_pooled):
    def caresuper_dio(asset, state, numperiods=1, *, direction, make_purchase=0):
        def brokerage(amount):
            return max(11.99, 0.09225/100 * amount)

        if isinstance(state, (int, float)):
            pooled = max(state * 0.15, 6000)
            shares, leftover, fee = state - pooled - 500, 0, 0
            #  if direction == 1:
                #  shares, leftover, fee = calc_brokerage(shares, brokerage)
            return dict(
                num_shares=shares/asset['value'],
                pooled=pooled+leftover,
                transaction=500,
                total=state,
                cost_base=shares + fee,
            )

        def total():
            return state['num_shares'] * asset['value'] + state['pooled'] + state['transaction']

        # interest on transaction account, use the rate from the cash option
        interest = min((x for x in caresuper if x['name'] == 'caresuper-Cash'), key=lambda x: abs(x['date'] - asset['date']))
        interest = interest['value'] ** (12 / numperiods)
        state['transaction'] += state['transaction'] * (interest - 1) * (1 - TAX) * direction
        if state['transaction'] < 500:
            state['pooled'] -= 500 - state['transaction']
            state['transaction'] = 500

        state['pooled'] -= CARESUPER_DIO_PLATFORM_FEE / numperiods * direction
        required_pooled = max(total() * 0.15, 6000)
        state = rebalance_pooled(state, required_pooled, direction, asset, brokerage, make_purchase=make_purchase)

        state['total'] = total()
        return state

    return (caresuper_dio,)


@app.cell(hide_code=True)
def _(rebalance_pooled):
    def stake_smsf(asset, state, numperiods=1, *, direction, make_purchase=0):
        def brokerage(amount):
            return 3 + 0.01/100 * max(0, amount - 30_000)

        if isinstance(state, (int, float)):
            shares, leftover, fee = state, 0, 0
            #  if direction == 1:
                #  shares, leftover, fee = calc_brokerage(shares, brokerage)
            return dict(
                num_shares=shares/asset['value'],
                pooled=leftover,
                total=state,
                cost_base=shares+fee,
            )

        state = rebalance_pooled(state, 0, direction, asset, brokerage, make_purchase=make_purchase)
        state['total'] = state['num_shares'] * asset['value'] + state['pooled']
        return state

    return (stake_smsf,)


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
def load_rest(csv, mo):
    _file = mo.notebook_location()/'public'/'rest.tsv'
    rest_raw = list(csv.DictReader(read_file(_file).decode().splitlines(), delimiter='\t'))
    return (rest_raw,)


@app.cell(hide_code=True)
def load_caresuper(csv, mo):
    _file = mo.notebook_location()/'public'/'caresuper.csv'
    caresuper_raw = list(csv.DictReader(read_file(_file).decode().splitlines()))
    return (caresuper_raw,)


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
    for _row in sharesight_prices['IOO']:
        if _row['date'] > datetime.datetime(2018, 5, 3):
            _row['value'] *= 2
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
def parse_art(art_raw, datetime, itertools, mo):
    art = []

    for _name, _chart_iter in itertools.groupby(sorted(art_raw, key=lambda x: (x['name'], x['date'])), key=lambda x: x['name']):
        _chart = [x for x in _chart_iter if float(x['value'])]

        # daily is too fine grained and causes too much data, turn it down
        _previous = float(_chart[0]['value'])
        for _month, _group in itertools.groupby(_chart, key=lambda x: x['date'].rpartition('-')[0]):
            _group = list(_group)
            _point = _group[-1]
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
def parse_rest(datetime, itertools, mo, rest_raw):
    rest = []

    for _name, _chart_iter in itertools.groupby(sorted(rest_raw, key=lambda x: (x['name'], x['date'])), key=lambda x: x['name']):
        _chrest = [x for x in _chart_iter if float(x['value'])]

        # daily is too fine grained and causes too much data, turn it down
        _previous = float(_chrest[0]['value'])
        for _month, _group in itertools.groupby(_chrest, key=lambda x: x['date'].rpartition('-')[0]):
            _group = list(_group)
            _point = _group[-1]
            _value = float(_point['value'])
            rest.append({
                'fund': 'rest',
                'name': f'rest-{_name}',
                'value': _value / _previous,
                'date': datetime.datetime.strptime(_point['date'].split('T')[0], '%Y-%m-%d'),
            })
            _previous = _value

    mo.ui.table(rest)
    return (rest,)


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
def parse_caresuper(caresuper_raw, datetime, itertools, mo):
    caresuper = []

    _raw = sorted(caresuper_raw, key=lambda x: x['PriceDate'])
    _previous = _raw[0]

    # weekly is too fine grained and causes too much data, turn it down
    for _month, _group in itertools.groupby(_raw, key=lambda x: x['PriceDate'].rpartition('-')[0]):
        _group = list(_group)
        _date = datetime.datetime.strptime(_group[0]['PriceDate'], '%Y-%m-%d')
        for _k in _group[0]:
            if _k != 'PriceDate' and not _k.endswith('-Pension') and _previous[_k]:
                caresuper.append({
                    'fund': 'caresuper',
                    'name': f'caresuper-{_k.removesuffix('-Superannuation')}',
                    'value': float(_group[0][_k]) / float(_previous[_k]),
                    'date': _date,
                })
        _previous = _group[0]

    mo.ui.table(caresuper)
    return (caresuper,)


@app.cell(hide_code=True)
def _(admin_fees, make_data):
    def make_alldata(pooled_funds, direct_investment, direction, filter=None, **kwargs):
        import itertools
        if filter:
            pooled_funds = [x for x in pooled_funds if x['name'] in filter]
            direct_investment = {k: v for k, v in direct_investment.items() if k in filter}
        pooled_funds = sorted(pooled_funds, key=lambda x: (x['name'], x['date'].timestamp() * direction))
        data = []
        for name, group in itertools.groupby(pooled_funds, key=lambda x: x['name']):
            group = [x for x in group if x['value'] is not None]
            data.extend(make_data(
                name,
                group,
                admin_fees[name.split('-')[0]],
                asset_code=None,
                direct_investment_func=no_direct_investment,
                direction=direction,
                **kwargs,
            ))

        data.extend(itertools.chain.from_iterable(make_data(
            name,
            direction=direction,
            **kwargs,
            **k
        ) for name, k in direct_investment.items()))

        return data

    return (make_alldata,)


@app.cell(hide_code=True)
def _(CGT, TAX, datetime, sharesight_payouts, sharesight_prices):
    def make_data(
        name,
        pooled_returns,
        admin_fees,
        *,
        asset_code=None,
        direct_investment_func=no_direct_investment,
        direction,
        balance,
        contributions=(0, 0),
        direct_investment_buys=(0, 0),
        initial_date=datetime.datetime.today() + datetime.timedelta(days=7),
    ):
        import itertools

        pooled_returns = sorted(pooled_returns, key=lambda x: x['date'])
        pooled_returns = [{**x, 'cumulative': p} for x, p in zip(pooled_returns, cumproduct(x['value'] for x in pooled_returns))]
        asset = sharesight_prices[asset_code] if asset_code else pooled_returns
        asset = sorted(asset, reverse=direction==-1, key=lambda x: x['date'])
        mindate = min(x['date'] for x in pooled_returns)
        maxdate = max(x['date'] for x in pooled_returns)

        def interpolate(date):
            prev = max((x for x in pooled_returns if x['date'] <= date), key=lambda x: x['date'])
            next = min((x for x in pooled_returns if x['date'] >= date), key=lambda x: x['date'], default=None)
            next = next or pooled_returns[-1]
            if prev['date'] == next['date']:
                return next['cumulative']
            else:
                fraction = (date - next['date']) / (next['date'] - prev['date'])
                return prev['cumulative'] * (next['value'] ** fraction)

        def spread_over_fy(dates, frequency, value=1):
            fy = fy_of_date(dates[0])
            fy_start = datetime.datetime(fy-1, 7, 1)
            result = [0] * len(dates)
            for step in range(frequency):
                target_date = fy_start + datetime.timedelta(days=365 * step / frequency)
                closest = min(range(len(dates)), key=lambda i: abs(dates[i] - target_date))
                result[closest] += value
            return result

        prev_date = initial_date
        if direction == 1:
            mindate = prev_date = max(prev_date, mindate)
        else:
            maxdate = prev_date = min(prev_date, maxdate)

        # init
        asset = [a for a in asset if a['date'] >= mindate]
        if not asset:
            return
        state = direct_investment_func(asset[0], balance, direction=direction)
        state.setdefault('deferred_income', 0)

        yield {
            'fund': name.partition('-')[0],
            'name': name,
            'balance': state['total'],
            'date': prev_date,
            'deferred_income': state['deferred_income'],
            'cost_base': state['cost_base'],
            'capital': state['num_shares'] * asset[0]['value'],
        }
        for fy, group in itertools.groupby(asset, key=lambda x: fy_of_date(x['date'])):
            group = list(group)
            asset_fee_this_year = 0

            contribution_amounts = spread_over_fy([x['date'] for x in group], contributions[1], contributions[0])
            direct_invest = [x * direct_investment_buys[0] for x in spread_over_fy([x['date'] for x in group], direct_investment_buys[1])]

            for x, contribution, direct_invest_purchase in zip(group, contribution_amounts, direct_invest):
                state['pooled'] += contribution * direction

                asset_fee = min(state['total'] / len(group) * admin_fees['asset'], admin_fees['asset_max'] - asset_fee_this_year)
                state['pooled'] -= (admin_fees['fixed'] / len(group) + asset_fee) * direction
                asset_fee_this_year += asset_fee

                state['pooled'] *= (interpolate(x['date']) / interpolate(prev_date))
                prev_date = x['date']

                if asset_code and (payout := sharesight_payouts[asset_code].get(x['date'])):
                    au_local_dividend = payout['au_local_dividend']
                    state['deferred_income'] += au_local_dividend['deferred_income'] * state['num_shares'] / 1_000_000

                    cash = au_local_dividend['amount']
                    taxable = sum(au_local_dividend[k] for k in ['foreign_source_income', 'unfranked_amount', 'interest_payment_amount', 'franked_amount', 'non_discounted_capital_gains'])
                    discounted_taxable = au_local_dividend['discounted_capital_gains']
                    tax_credit = sum(au_local_dividend[k] for k in ['non_resident_withholding_tax', 'tax_credit'])
                    if tax_credit <= taxable:
                        taxable -= tax_credit
                        cash -= taxable * TAX + discounted_taxable * CGT
                    elif tax_credit < taxable + discounted_taxable:
                        discounted_taxable -= tax_credit - taxable
                        cash -= discounted_taxable * CGT
                    assert cash >= 0, cash

                    state['cost_base'] += au_local_dividend['amit_increase_amount'] * state['num_shares'] / 1_000_000
                    state['cost_base'] -= au_local_dividend['amit_decrease_amount'] * state['num_shares'] / 1_000_000

                    # drp - no brokerage
                    # initial + cash * initial / price == num_shares
                    # initial == num_shares / (1 + cash / price)
                    state['num_shares'] *= (1 + cash / 1_000_000 / x['value']) ** direction
                    state['cost_base'] += cash / 1_000_000 * direction

                state = direct_investment_func(x, state, numperiods=len(group), direction=direction, make_purchase=direct_invest_purchase)

                yield {
                    'fund': name.partition('-')[0],
                    'name': name,
                    'date': x['date'],
                    'balance': state['total'],
                    'deferred_income': state['deferred_income'],
                    'cost_base': state['cost_base'],
                    'capital': state['num_shares'] * x['value'],
                }

    return (make_data,)


@app.cell(hide_code=True)
def make_direct_investment(
    admin_fees,
    aussuper,
    caresuper,
    caresuper_dio,
    choiceplus,
    datetime,
    hostplus,
    memberdirect,
    stake_smsf,
):

    _aussuper_int = [x for x in aussuper if x['name'] == 'aussuper-International Shares']
    _hostplus_int = [x for x in hostplus if x['name'] == 'hostplus-International Shares']
    _caresuper_int = [x for x in caresuper if x['name'] == 'caresuper-Overseas Shares']
    _aussuper_aus = [x for x in aussuper if x['name'] == 'aussuper-Australian Shares']
    _hostplus_aus = [x for x in hostplus if x['name'] == 'hostplus-Australian Shares']
    _caresuper_aus = [x for x in caresuper if x['name'] == 'caresuper-Australian Shares']
    _stake_pooled = [{'date': datetime.datetime.min, 'value': 1}, {'date': datetime.datetime.max, 'value': 1}]

    _memberdirect_int = dict(direct_investment_func=memberdirect, admin_fees=admin_fees['aussuper'], pooled_returns=_aussuper_int)
    _choiceplus_int = dict(direct_investment_func=choiceplus, admin_fees=admin_fees['hostplus'], pooled_returns=_hostplus_int)
    _caresuper_dio_int = dict(direct_investment_func=caresuper_dio, admin_fees=admin_fees['caresuper'], pooled_returns=_caresuper_int)
    _memberdirect_aus = {**_memberdirect_int, 'pooled_returns': _aussuper_aus}
    _choiceplus_aus = {**_choiceplus_int, 'pooled_returns': _hostplus_aus}
    _caresuper_dio_aus = {**_caresuper_dio_int, 'pooled_returns': _caresuper_aus}
    _stake = dict(direct_investment_func=stake_smsf, admin_fees=admin_fees['stake'], pooled_returns=_stake_pooled)

    direct_investment = {
        'aussuper-memberdirect-VGS': dict(asset_code='VGS', **_memberdirect_int),
        'aussuper-memberdirect-VAS': dict(asset_code='VAS', **_memberdirect_int),
        'aussuper-memberdirect-IVV': dict(asset_code='IVV', **_memberdirect_int),
        'aussuper-memberdirect-IOO': dict(asset_code='IOO', **_memberdirect_int),
        #  'aussuper-memberdirect-STW': dict(asset_code='STW', **_memberdirect_aus),
        'hostplus-choiceplus-VGS': dict(asset_code='VGS', **_choiceplus_int),
        'hostplus-choiceplus-VAS': dict(asset_code='VAS', **_choiceplus_int),
        'hostplus-choiceplus-IVV': dict(asset_code='IVV', **_choiceplus_int),
        'hostplus-choiceplus-IOO': dict(asset_code='IOO', **_choiceplus_int),
        #  'hostplus-choiceplus-STW': dict(asset_code='STW', **_choiceplus_aus),
        'caresuper-dio-VGS': dict(asset_code='VGS', **_caresuper_dio_int),
        'caresuper-dio-VAS': dict(asset_code='VAS', **_caresuper_dio_int),
        'caresuper-dio-IVV': dict(asset_code='IVV', **_caresuper_dio_int),
        'caresuper-dio-IOO': dict(asset_code='IOO', **_caresuper_dio_int),
        #  'caresuper-dio-STW': dict(asset_code='STW', **_caresuper_dio_aus),
        'stake-smsf-VGS': dict(asset_code='VGS', **_stake),
        'stake-smsf-VAS': dict(asset_code='VAS', **_stake),
        'stake-smsf-IVV': dict(asset_code='IVV', **_stake),
        'stake-smsf-IOO': dict(asset_code='IOO', **_stake),
        #  'stake-smsf-STW': dict(asset_code='STW', **_stake),
    }
    return (direct_investment,)


@app.cell(hide_code=True)
def calc_mean_perforance(all_super_funds, itertools):
    mean_performance = []
    _data = sorted(all_super_funds(), key=lambda x: (x['name'], x['date']))
    for _k, _g in itertools.groupby(_data, key=lambda x: x['name']):
        _g = list(_g)
        _days = (_g[-1]['date'] - _g[0]['date']).days
        if _days > 365 * 5:
            _perf = list(cumproduct(x['value'] for x in _g))[-1]
            mean_performance.append((_perf ** (365 / _days), _k))
    return


if __name__ == "__main__":
    app.run()
