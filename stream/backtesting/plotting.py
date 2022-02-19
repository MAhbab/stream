import pandas as pd
import numpy as np

import bokeh as bok
import bokeh.plotting as bkp
import bokeh.models as bkm
import itertools
from bokeh.palettes import Magma11
import scipy.stats as ss
from statsmodels.tsa.stattools import acf


HEIGHT = 400
WIDTH = 600
TOOLBAR_LOC = 'below'
SIZING_MODE = 'stretch_both'
colors = itertools.cycle(Magma11)

def default_figure(datetime_x=False, ttips=None):
    fig_kwargs = {
        'height': HEIGHT,
        'width': WIDTH,
        'toolbar_location': TOOLBAR_LOC,
        'sizing_mode': SIZING_MODE
    }
    if datetime_x:
        fig_kwargs['x_axis_type'] = 'datetime'
    fig = bkp.figure(**fig_kwargs)
    if ttips is not None:
        hover = bkm.HoverTool(tooltips=ttips, mode='vline')
        fig.add_tools(hover)
    
    return fig


def bkformat(figure, xlabel=None, ylabel=None, title=None):
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

#make an interactive time series plot
def time_series(
    dframe: pd.DataFrame,
    upper_bound: pd.DataFrame = None, #include these to plot confidence intervals
    lower_bound: pd.DataFrame = None, #NOTE: column names must be identical to :arg: dframe
    xlabel: str = None,
    ylabel: str = None,
    title: str = None
):

    #pre process data
    COLS = list(dframe.columns)

    ttips = [('Name', '@name'),('Date', '@date_str'), ('Value', '@value{0.00a}')]
    COLORS = itertools.cycle(bok.palettes.magma(len(COLS)+1))

    fig = default_figure(True, ttips)

    #set flag for confidence intervals
    if isinstance(upper_bound, pd.DataFrame) and isinstance(lower_bound, pd.DataFrame):
        conf_interval = True 
    else:
        conf_interval = False


    for c in COLS:
        df = dframe[c]

        #in case dframe has multi-index columns
        if isinstance(c, tuple):
            name = ':'.join(c)
        else:
            name = c
        df.name = 'value'
        df.index.name = 'date'
        df = df.reset_index()
        df['date_str'] = df['date'].dt.strftime('%Y-%m-%d')
        df['name'] = name

        src = bkm.ColumnDataSource(df)
        clr = next(COLORS)
        fig.line(y='value', x='date', source=src, legend_label=name, color=clr, name=name)

        if conf_interval:
            ubound = upper_bound[c]
            lbound = lower_bound[c]
            fig.varea(x=ubound.index, y1=ubound.values, y2=lbound.values, fill_color=clr, fill_alpha=0.3, name='{} 95% Confidence Interval'.format(name))
    
    fig_formatted = bkformat(fig, xlabel, ylabel, title)

    return fig_formatted



#helper function that returns bar dimensions
#to plot returns distribution
def bquad(srs, bins):
    bounds_dict = {}
    try:
        rbins = pd.cut(srs, np.linspace(srs.min(), srs.max(), bins))
    except ValueError:
        raise Exception('Error generating bins. Try decrease the bin count or setting a longer timeframe')
    rgrp = rbins.groupby(rbins).count()
    bounds_dict['top'] = [x for x in rgrp]
    bounds_dict['left'] = [x.left for x in rgrp.index]
    bounds_dict['right'] = [x.right for x in rgrp.index]
    bounds_dict['bottom'] = [0]*len(rgrp)
    return bounds_dict

def hist(dframe: pd.DataFrame, bins: int):

    ncols = len(dframe.columns)
    COLORS = itertools.cycle(bok.palettes.magma(ncols+1))
    ttips = [('Name', '$name'), ('Count', '@top'), ('Value', '$x{0,0.00}')]


    myfig = default_figure(ttips=ttips)
    for k in dframe.columns:
        kw = bquad(dframe[k], bins)
        myfig.quad(
            top=kw['top'],
            bottom=kw['bottom'],
            left=kw['left'],
            right=kw['right'],
            legend_label=k, 
            color=next(COLORS),
            name=k
            )
    return myfig


def prob_plot(rets, fig=None, **kwargs):
    data, params = ss.probplot(rets, **kwargs)
    fitted = (params[0]*data[0]+params[1])

    if not fig:
        fig = default_figure()

    if isinstance(rets, pd.Series):
        name = rets.name 
    else:
        name = 'Returns'
    
    fitted_name = ' '.join(['Fitted', name])
    clr = next(colors)
    fig.scatter(x=data[0], y=data[1], legend_label=name, line_color=clr, name=name)
    fig.line(x=data[0], y=fitted, legend_label=fitted_name, line_color=clr, name=fitted_name)
    return fig 

def acf_plot(rets, fig=None, adjusted=False, alpha=0.05, nlags=None):
        
    data, conf = acf(rets, adjusted=adjusted, alpha=alpha, nlags=nlags)
    xrange = [x for x in range(len(data))]
    if not fig:
        fig = default_figure()

    if isinstance(rets, pd.Series):
        name = rets.name 
    else:
        name = 'ACF'
    
    conf_name = ' '.join([name, '{}%'.format(int((1-alpha)*100)),'Confidence Interval'])

    clr = next(colors)
    fig.line(x=xrange, y=data, legend_label=name, line_color=clr)
    fig.varea(x=xrange, y1=conf[:, 0], y2=conf[:, 1], alpha=0.2, legend_label=conf_name, color=clr)
    return fig 

