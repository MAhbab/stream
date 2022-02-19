#%%
import pandas as pd
from stream import Element, Page
import streamlit as st
import bt
from bt.backtest import Result
import datetime as dt
from stream.backtesting.plotting import time_series, bkformat

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


    def __call__(self, target: Page, **global_vars):
        
        with st.form(self._name):
            selection_name = st.text_input('Name this Selection')
            tkrs = st.multiselect('Select Symbols', self._symbols)
            field = st.selectbox('Select Field', self._fields, 10)
            start_date = st.date_input('Select Start Date', self._dflt_start_date)
            end_date = st.date_input('Select an End Date', self._dflt_end_date)


            submit = st.form_submit_button('Submit')

            if submit:
                if field!='Adj_Close':
                    input_ = ['{}:{}'.format(t, field) for t in tkrs]
                else:
                    input = list(tkrs)
                data = bt.get(input, start_date=start_date, end_date=end_date)
                data.columns = [x.upper() for x in data.columns]
                target.data[selection_name] = data


class BatchBacktest(Element):

    def __call__(self, target: Page, **global_vars):

        strat_selections = st.multiselect('Select a Strategy', target.strategies)
        data_selections = st.multiselect('Select Data', target.datasets)

        if st.button('Generate Backtests'):
            progress_so_far = 0
            progress_bar = st.progress(progress_so_far)
            incr = 1/(len(strat_selections)*len(data_selections))

            for s in strat_selections:

                strat = target.data[s]

                name_template = "Strategy<{s}> with Data<{d}>"
                for df_name in data_selections:
                    df = target.data[df_name]
                    name = name_template.format(s=strat.name, d=df.name)

                    bk = bt.Backtest(strat, df.dropna(), name=name)
                    bk.run()

                    target.data['backtests'][name] = bk
                    progress_so_far += incr
                    progress_bar.progress(progress_so_far)

            st.success('Backtests ran successfully!')


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

        st.subheader('General')
        st.metric('Initial Capital', '${}'.format(bk.initial_capital))
        st.metric('Starting Date', bk.dates[0].strftime('%m/%d/%Y'))
        st.metric('End Date', bk.dates[0].strftime('%m/%d/%Y'))

        st.subheader('Risk & Return')
        st.metric('CAGR', get_stat('cagr'))
        st.metric('Annualized Volatility', get_stat('yearly_vol'))
        st.metric('Annualized Sharpe Ratio', get_stat('yearly_sharpe'))
        st.metric('Annualized Sortino Ratio', get_stat('yearly_sortino'))

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

    def __call__(self, target: Page, **global_vars):
        bk_selection = st.selectbox('Select Backtest', target.backtests)
        bk = target.backtests[bk_selection]
        self.backtest_summary(bk)

