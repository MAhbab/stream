#%%
from typing import Iterable, Union
from .core import Element
from pandas import DataFrame

import bokeh.plotting as bkp
from bokeh.models import ColumnDataSource, HoverTool
import bokeh.palettes

class BokehPlot:

    def __init__(
        self,
        data: DataFrame,
        height=400,
        width=600,
        color='viridis',
        ttips=None
    ) -> None:
        self._data = data
        self.height = height
        self.width = width
        self.color_func = getattr(bokeh.palettes, color)
        self.ttips = ttips

    @property
    def data(self) -> ColumnDataSource:
        d = self._data.copy()
        d.columns = d.columns.astype(str)
        return ColumnDataSource(d)

    def default_figure(self, datetime_x=False, ttips=None):
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
            hover = HoverTool(tooltips=ttips, mode='vline')
            fig.add_tools(hover)
        
        return fig

    def format(self, figure, xlabel=None, ylabel=None, title=None):
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

    def line(self, x: str='index', y: Union[str, Iterable[str]]=None, fig=None, time_series=False):
        if fig is None:
            fig = self.default_figure(time_series, ttips=self.ttips)

        if isinstance(y, str):
            y_list = [y]
        elif isinstance(y, (Iterable)):
            y_list = y
        elif y is None:
            y_list = list(self._data.columns)

        src = self.data
        colors = self.color_func(len(y_list))

        for yl, color in zip(y_list, colors):

            fig.line(x=x, y=yl, source=src, color=color, legend_label=yl)
        return fig

    def scatter(self, x, y, fig=None):
        return NotImplemented

    def hist(self, y, fig=None):
        return NotImplemented
