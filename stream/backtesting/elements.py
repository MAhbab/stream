#%%
import pandas as pd
from stream import Element, BacktestPage
import streamlit as st
import bt
import datetime as dt
from stream.backtesting.plotting import time_series
from treelib import Node
from typing import Any, List
import datetime as dt

class TickerSelect(Element):

    '''
    Pulls OHLCV Data from Quandl and stores it as a DataFrame
    in :attr: Page.data
    '''

    def __init__(self, name=None) -> None:
        super().__init__(name)
        self._symbols = tuple(pd.read_csv('EOD_metadata.csv')['code'])
        self._fields = (
            'Open',
            'High',
            'Low',
            'Close',
            'Volume',
            'Dividend',
            'Split',
            'Adj_Open',
            'Adj_High',
            'Adj_Low',
            'Adj_Close',
            'Adj_Volume'
        )
        self._dflt_end_date = dt.datetime.now()
        self._dflt_start_date = self._dflt_end_date - dt.timedelta(days=365*4)


    def __call__(self, target: BacktestPage, **global_vars):
        fmt_func = lambda x: x.replace('Adj_', 'Adjusted ')
        
        with st.form(self._name):
            selection_name = st.text_input('Name this Selection', 'My Dataset')
            tkrs = st.multiselect('Select Symbols', self._symbols, format_func=fmt_func)
            field = st.selectbox('Select Field', self._fields, 10)
            start_date = st.date_input('Select Start Date', self._dflt_start_date)
            end_date = st.date_input('Select an End Date', self._dflt_end_date)


            submit = st.form_submit_button('Submit')

            if submit:
                if field!='Adj_Close':
                    input = ['{}:{}'.format(t, field) for t in tkrs]
                else:
                    input = list(tkrs)
                data = bt.get(input, start_date=start_date, end_date=end_date)
                data.columns = [x.upper() for x in data.columns]
                target.datasets[selection_name] = data


class BatchBacktest(Element):

    def batch_backtests(self, target, strats, datasets):
        bkts = []
        for s in strats:

            strat = target.data[s]

            name_template = "Strategy<{s}> with Data<{d}>"
            for df_name in datasets:
                df = target.data[df_name]
                name = name_template.format(s=strat.name, d=df.name)

                bk = bt.Backtest(strat, df.dropna(), name=name)

                bkts.append(bk)

        name = 'Batch Backtest {}'.format(dt.datetime.now().strftime('%H:%M'))

        target._run(name, *bkts)

    def __call__(self, target: BacktestPage, **global_vars):

        strat_selections = st.multiselect('Select a Strategy', target.strategies, format_func=target._data_name)
        data_selections = st.multiselect('Select Data', target.datasets, format_func=target._data_name)

        st.button(
            label='Run Backtests',
            on_click=self.batch_backtests,
            kwargs={'target': target, 'strats': strat_selections, 'datasets': data_selections}
        )


class BacktestDescription(Element):

    def strategy_summary(self, strat: bt.Strategy):
        st.write('Strategy<{}>'.format(strat.name))
        st.write('Algos:')
        st.write([a.name for a in strat.stack.algos])

    def backtest_metrics(self, bk: bt.Backtest):
        res = bt.backtest.Result(bk)
        stats = res.stats.iloc[:, 0]
        def get_stat(x):
            try:
                return round(stats.loc[x], 2)
            except:
                return stats.loc[x]

        col1, col2, col3 = st.columns(3)

        with col1:
            st.subheader('General')
            st.metric('Initial Capital', '${}'.format(bk.initial_capital))
            st.metric('Starting Date', bk.dates[0].strftime('%m/%d/%Y'))
            st.metric('End Date', bk.dates[0].strftime('%m/%d/%Y'))

        with col2:
            st.subheader('Risk & Return')
            st.metric('CAGR', get_stat('cagr'))
            st.metric('Annualized Volatility', get_stat('yearly_vol'))
            st.metric('Annualized Sharpe Ratio', get_stat('yearly_sharpe'))
            st.metric('Annualized Sortino Ratio', get_stat('yearly_sortino'))

        with col3:
            st.subheader('Drawdown')
            st.metric('Max Drawdown', get_stat('max_drawdown'))
            st.metric('Average Drawdown', get_stat('avg_drawdown'))
            st.metric('Average Drawdown Duration (Days)', get_stat('avg_drawdown_days'))

    def backtest_summary(self, bk: bt.Backtest):
        st.header('Backtest<{}>'.format(bk.name))
        self.backtest_metrics(bk)
        st.subheader('Strategy')
        self.strategy_summary(bk.strategy)
        st.subheader('Data')
        st.dataframe(bk.data.dropna())

    def __call__(self, target: BacktestPage, **global_vars):
        bkt = target.active_backtest
        self.backtest_summary(bkt)

class SaveBacktests(Element):

    '''Goal: implement buttons to save:
        1. all backtest data to hdf
        2. save backtest prices as dataset'''

    def __init__(self, backtest_key: str=None, name=None) -> None:
        super().__init__(name, False)
        self.key = backtest_key

    def save_backtests_to_hdf(self, bkts: List[bt.Backtest], fpath: str):
        for bkt in bkts:
            bkt.strategy.prices.to_hdf('{}/prices'.format(bkt.name), fpath)
            bkt.stats.to_hdf('{}/stats'.format(bkt.name), fpath)
            bkt.weights.to_hdf('{}/weights'.format(bkt.name), fpath)
            bkt.security_weights.to_hdf('{}/security_weights'.format(bkt.name), fpath)
            bkt.positions.to_hdf('{}/positions'.format(bkt.name), fpath)
            bkt.herfindahl_index.to_hdf('{}/herfindahl_index'.format(bkt.name), fpath)
            bkt.strategy.get_transactions().to_hdf('{}/transactions'.format(bkt.name), fpath)
        st.success('Saved {}!'.format(fpath))

    def save_backtest_prices(self, target: BacktestPage, bkts: List[bt.Backtest], name: str):
        prc = bt.backtest.Result(*bkts).prices
        prc.name = name
        target.datasets.append(prc)


    def select_backtest(self, target):
        if self.key in target.data:
            val = target.data[self.key]
            if isinstance(val, bt.Backtest):
                return [val]
        
        bkts = st.multiselect('Select Backtests')
        return [target.backtests[b] for b in bkts]

    def __call__(self, target: BacktestPage, **global_vars) -> bool:
        date_str = dt.datetime.now().strftime('backtests_%Y_%m_%d_%I_%M')
        fpath = st.text_input('Name this file') or date_str
        bkts = self.select_backtest(target)

        col1, col2 = st.columns(2)

        with col1:
            st.button(
                "Save Backtests as HDF5 file ('h5')",
                on_click=self.save_backtests_to_hdf,
                kwargs={'bkts': bkts, 'fpath': fpath},
            )

        with col2:
            st.button(
                'Save Backtest Prices as Dataset',
                on_click=self.save_backtest_prices,
                kwargs={'target': target, 'bkts': bkts, 'name': fpath.split('.')[0]}
            )

        return True

class BacktestPricesAndStats(Element):

    def __call__(self, target: Node, **global_vars) -> Any:
        return super().__call__(target, **global_vars)


        

