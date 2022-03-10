import streamlit as st
from functools import partial

from ..core import Session, Page
from .pages import BacktestPage, BacktestLandingPage


class Backtester(Session):

    def __init__(self, debug_mode=False, **global_vars) -> None:
        super().__init__('Backtest Viewer', BacktestLandingPage(), debug_mode, **global_vars)

    def _data_name(self, dta):
        try:
            return dta.name
        except AttributeError:
            return dta.__class__.__name__

    def _update_selections(self, **kwargs):
        for key in kwargs:
            self._globals[key] = kwargs[key]

    def run(self, *bkts):

        if self.is_first_run:
            root_node = self.get_node(self.root)
            root_node._run(*bkts)
            self.update(root_node.identifier)
            self._is_first_run = False

        self.sidebar()
        active = self.active_page

        active._update = partial(self.update, page_id=active.identifier)
                
        if self._debug_mode:
            self.debugger(active)

        parent = self.parent(active.identifier)
        
        active(parent, **self.globals)
        self.cleanup(active, parent)