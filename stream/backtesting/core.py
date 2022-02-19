import streamlit as st
import pandas as pd
import bt
from typing import List, Hashable, Union
from ..core import Page, Element, App
from elements import TickerSelect, BatchBacktest, BacktestDescription

class BacktestPage(Page):

    def __init__(
        self, 
        tag: str = None,
        identifier: Hashable = None,
        data: dict = None,
        elements: List[Element] = None,
        strategies: List[bt.Strategy] = None,
        backtests: List[bt.Backtest] = None,
        datasets: List[pd.DataFrame] = None,
        run_header: bool = False,
        run_footer: bool = False,
        header_kwargs: dict = None,
        footer_kwargs: dict = None
    ):
        data = data or {}
        bkt_dict = {'strategies': {}, 'backtests': {}, 'datasets': {}, 'active_backtest': None}
        if strategies is not None:
            for s in strategies:
                bkt_dict['strategies'][s.name] = s
        
        if backtests is not None:
            for b in backtests:
                bkt_dict['backtests'][b.name] = b
        
        if datasets is not None:
            for df in datasets:
                try:
                    name = df.name
                except AttributeError:
                    name = '-'.join(df.columns)
                bkt_dict['datasets'][name] = df
                
        data = dict(data, **bkt_dict)
        super().__init__(tag, identifier, data, elements, run_header, run_footer, header_kwargs, footer_kwargs)

    @property
    def strategies(self):
        return self.data['strategies']

    @property
    def backtests(self):
        return self.data['backtests']

    @property
    def datasets(self):
        return self.data['datasets']

    @property
    def active_backtest(self):
        return self.data['active_backtest']

    def set_active_backtest(self, backtest_name: str):
        self.data['active_backtest'] = self.backtests[backtest_name]

    def add_backtests(self, bkts: Union[bt.Backtest, List[bt.Backtest]], override: bool = False):
        if isinstance(bkts, bt.Backtest):
            bkts = [bkts]

        for b in bkts:
            if (b.name not in self.backtests) | (override):
                b.run()
                self.data['backtests'][b.name] = b

class BacktestLandingPage(BacktestPage):

    def __init__(self, data=None, strategies=None, backtests=None, datasets=None):
        elements = [TickerSelect(), BatchBacktest(), BacktestDescription()]
        super().__init__(data=data, strategies=strategies, backtests=backtests, datasets=datasets, elements=elements, run_header=True)

    def header(self, **kwargs):
        st.header('QIS/JSt Backtester')

class Backtester(App):

    def __init__(self, strategies=None, backtests=None, datasets=None, **global_vars) -> None:
        start_page = BacktestLandingPage(strategies=strategies, backtests=backtests, datasets=datasets)
        super().__init__('Backtester V1', start_page, **global_vars)

    def setup(self):
        pass

    def run(self, *bkts):
        root_node = self.get_node(self.root)
        root_node.add_backtests(bkts)
                
        return super().run()


