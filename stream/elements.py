from websockets import Data
from .core import Element, Page
from pandas import DataFrame
from bokeh.models import ColumnDataSource
from typing import Union

import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import bokeh.plotting as bkp
import bokeh.models as bkm
import bokeh.palettes as bpl

class BokehPlot(Element):

    def __init__(
        self,
        data: Union[DataFrame, ColumnDataSource],
        name=None, 
        height=400,
        width=600,
        color='viridis',
        ttips=None
    ) -> None:
        super().__init__(name, False)
        self.data = data if isinstance(data, ColumnDataSource) else ColumnDataSource(data)
        self.height = height
        self.width = width
        self.color_func = getattr(bpl, color)
        self.ttips = ttips

    def _default_figure(self, datetime_x=False, ttips=None):
        fig_kwargs = {
            'height': self.height,
            'width': self.width,
            'toolbar_location': 'below',
            'sizing_mode': 'stretch_both'
        }
        if datetime_x:
            fig_kwargs['x_axis_type'] = 'datetime'
        fig = bkp.figure(**fig_kwargs)
        if ttips is not None:
            hover = bkm.HoverTool(tooltips=ttips, mode='vline')
            fig.add_tools(hover)
        
        return fig

    def _format(self, figure, xlabel=None, ylabel=None, title=None):
        figure.legend.location = 'top_left'
        figure.legend.click_policy = 'hide'

        if xlabel is not None:
            figure.xaxis.axis_label = xlabel
        if ylabel is not None:
            figure.yaxis.axis_label = ylabel
        figure.axis.axis_label_text_font_size = '12pt'
        
        if title is not None:
            figure.title.text = title
            figure.title.text_font_size = '16pt'
        return figure

    def time_series(self):
        pass