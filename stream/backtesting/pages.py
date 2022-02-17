#%%
from stream import Page, Element
import numpy as np
import streamlit as st
import bt
from stream.backtesting.plotting import time_series, hist, bkformat, prob_plot, acf_plot
import datetime as dt
import pandas as pd
from bokeh.layouts import column, gridplot, layout
from bokeh.models import LinearAxis, Range1d
from statsmodels.regression.rolling import RollingOLS
import statsmodels.api as sm
from typing import Any, Dict, Hashable, List, Union
from stream.backtesting.elements import TickerSelect, BatchBacktest, BacktestDescription
#something new


class ResultsOverview(Page):

    def __init__(self, tag=None, identifier=None, data=None, elements=None, run_header=False, run_footer=False, header_kwargs=None, footer_kwargs=None, *bkts):
        super().__init__(tag, identifier, data, elements, run_header, run_footer, header_kwargs, footer_kwargs)
        self._bkts = bkts

    def _backtest_selection(self, parent: Page, **global_vars):
        parent_bkts = {key: parent.data[key] for key in parent.data if isinstance(parent.data[key], bt.Backtest)}
        global_bkts = {key: global_vars[key] for key in global_vars if isinstance(global_vars[key], bt.Backtest)}
        all_bkts = dict(parent_bkts, **global_bkts)
        
        bkts_selections = st.multiselect('Select Backtests', all_bkts)
        bkts = [all_bkts[key] for key in bkts_selections]

        if len(bkts) >= 3:
            st.error('Please select no more than three Backtests for comparison')

        return bkts
        

    def multi_backtest_plot(self, bkts, start_date, end_date):
        '''Returns figure with prices, turnover, and herfindahl index'''
        prices = pd.concat(
            {bk.name: bk.strategy.prices for bk in bkts},
            axis=1
        ).loc[start_date:end_date]

        turnover = pd.concat(
            {bk.name: bk.turnover for bk in bkts},
            axis=1
        ).loc[start_date:end_date]

        herfindahl = pd.concat(
            {bk.name: bk.herfindahl_index for bk in bkts},
            axis=1
        ).loc[start_date:end_date]

        rets = 100*np.log(prices/prices.shift()).fillna(0)

        prices_fig = time_series(prices, 'Time', 'Value ($)', 'Performance')
        turnover_fig = time_series(100*turnover, 'Time', 'Turnover (%)', 'Turnover')
        herfindahl_fig = time_series(herfindahl, 'Time', 'Herfindahl Index', 'Herfindahl Index')
        rets_distribution_fig = hist(rets, 20)
        rets_dist_fmt = bkformat(
            rets_distribution_fig,
            'Returns (%)',
            'Count',
            'Returns Distribution'
        )
        group_fig = column(prices_fig, turnover_fig, herfindahl_fig, rets_dist_fmt)
        return group_fig 

    def single_backtest_plot(self, start_date, end_date, bkt):
        '''Returns positions, weights, and prices of input securities'''
        positions_fig = time_series(
            bkt.positions.loc[start_date:end_date], 
            'Time', 
            'Position (Shares)', 
            '{} Security Positions'.format(bkt.name)
        )

        weights_fig = time_series(
            100*bkt.security_weights.loc[start_date:end_date],
            'Time',
            'Weight (%)',
            '{} Security Weights'.format(bkt.name)
        )

        data_fig = time_series(
            bkt.data.loc[start_date:end_date],
            'Time',
            'Price ($)',
            '{} Security Prices'.format(bkt.name)
        )

        return [positions_fig, weights_fig, data_fig]

    def returns_group_plot(self, **prob_plot_kwargs):
        bkt = self.get_variable(self._single_bkt, bt.Backtest)
        prc = bkt.strategy.prices
        prc.name = bkt.name 
        rets = np.log(prc/prc.shift()).fillna(0)

        p_plot = prob_plot(rets, **prob_plot_kwargs)
        p_plot_fmt = bkformat(
            p_plot, 
            'Theoretical Quantile', 
            'Data Quantile', 
            '{} Probability Plot'.format(bkt.name)
        )

        acf_fig = acf_plot(rets)
        acf_plt_fmt = bkformat(
            acf_fig,
            'Observation',
            'Autocorrelation',
            '{} Returns Autocorrelation'.format(bkt.name)
        )
        
        sqrd_acf_fig = acf_plot(rets**2)
        sqrd_acf_fmt = bkformat(
            sqrd_acf_fig,
            'Observation',
            'Autocorrelation',
            '{} Squared Returns Autocorrelation',
        )

        return [p_plot_fmt, acf_plt_fmt, sqrd_acf_fmt]

    def __call__(self, parent, **global_vars):
        '''Main function to generate a streamlit page'''

        if not self._bkts:
            bkts = self._backtest_selection(parent, **global_vars)
        else:
            bkts = [b for b in self._bkts if isinstance(b, bt.Backtest)]
        min_date = np.min([b.dates.min() for b in bkts])
        max_date = np.min([b.dates.max() for b in bkts])
        start = st.date_input('Select a Start Date', min_date, min_date, max_date)
        end = st.date_input('Select an End Date', max_date, min_date, max_date)

        #multi-backtest results
        with st.expander('See Aggregate Backtest Results', True):

            multi_bk_fig = self.multi_backtest_plot(start, end, *bkts)
            st.bokeh_chart(multi_bk_fig)

        #show stats table 
        with st.expander('See Backtest Statistics'):
            perf_stats = bt.backtest.Result(*bkts)
            perf_stats.set_date_range(start, end)
            st.table(perf_stats.stats.drop(['start', 'end'], axis=0))


        #show single backtest results
        with st.expander('Backtest Comparison'):
            bk_grid_plot = [self.single_backtest_plot(start, end, b) for b in bkts]

            #transpose for aesthetic purposes
            group_fig = gridplot(list(np.array(bk_grid_plot).T))
            st.bokeh_chart(group_fig)

        with st.expander('Returns Plots'):
            rets_plot = self.returns_group_plot()
            st.bokeh_chart(rets_plot)

class RollingOLS(Page):

    def __init__(self, group_name='output'):
        super().__init__(group_name=group_name)

    def __call__(self):
        endog = self.get_variable(self._endog, pd.Series)
        exog = self.get_variable(self._exog, (list, pd.DataFrame))

        if isinstance(exog, list):
            exog = pd.concat(exog, axis=1).dropna()

        #filter variables by shared index
        idx = endog.index.intersection(exog.index)
        if len(idx)==0:
            self.index_error(endog, exog)
            st.stop()

        endog = endog.loc[idx]
        exog = exog.loc[idx]


        window = st.number_input('Rolling Window Length', len(exog.columns)+1, len(endog), len(exog.columns)-1)
        min_nobs = st.number_input('Minimum Number of Observations', window-1, max_value=window-1)
        add_constant = st.checkbox('Add constant', True)

        if add_constant:
            exog = sm.add_constant(exog)

        mod = RollingOLS(endog, exog, window=window, min_nobs=min_nobs)
        res = mod.fit()
        fig = self.hepta_plot(res)
        st.bokeh_chart(fig)

    def index_error(self, endog, exog):
            dt_fmt = lambda x: x.strftime('%Y/%m/%d')
            min_endog = dt_fmt(endog.index.min())
            max_endog = dt_fmt(endog.index.max())
            min_exog = dt_fmt(exog.index.min())
            max_exog = dt_fmt(exog.index.max())
            err_message = '''
            The chosen exogenous and endogenous variables have no time overlap.
            The date range for the exogenous variable(s) is {}-{} and the date range for the endogenous
            variable is {}-{}'''.format(min_exog, max_exog, min_endog, max_endog)
            return st.error(err_message)


    def hepta_plot(self, res):

        make_df = lambda srs, title: pd.DataFrame(srs, columns=[title])

        ubound = res.params + 2*res.bse
        lbound = res.params - 2*res.bse
        params_fig = time_series(res.params, ubound, lbound, 'Time', 'Parameter Value', 'Regression Parameter Estimate')

        pval_df = pd.DataFrame(res.pvalues, index=res.params.index, columns=res.params.columns)
        pval_fig = time_series(pval_df, xlabel='Time', title='Parameter Estimate P Value')

        residual_df = make_df(res.mse_resid, 'Residual MSE')
        resid_fig = time_series(residual_df, xlabel='Time', title='Model Residual MSE')

        rsquared_df = make_df(res.rsquared_adj, 'Adjusted R-Squared')
        rsquared_fig = time_series(rsquared_df, xlabel='Time', title='Adjusted R-Squared')

        fstat_df = make_df(res.fvalue, 'F Statistic')
        fstat_fig = time_series(fstat_df, xlabel='Time', title='F Statistic')
        fstat_fig.extra_y_ranges = {'P Value': Range1d(start=0.9*res.f_pvalue.min(), end=1.1*res.f_pvalue.max())}
        fstat_fig.add_layout(LinearAxis(y_range_name='P Value'), 'right')
        fstat_fig.line(x=res.f_pvalue.index, y=res.f_pvalue, color='black', y_range_name='P Value', legend_label='P Value')

        aic_bic_df = pd.concat({'AIC': res.aic, 'BIC': res.bic}, axis=1)
        aic_bic_fig = time_series(aic_bic_df, xlabel='Time', title='Aikaike and Bayesian Information Criteria')

        log_likelihood = make_df(res.llf, 'Log-Likelihood')
        log_likelihood_fig = time_series(log_likelihood, xlabel='Time', title='Model Log Likelihood')

        big_fig = layout(
            [
                [params_fig],
                [pval_fig, resid_fig],
                [rsquared_fig],
                [aic_bic_fig, log_likelihood_fig]
            ]
        )

        return big_fig 

