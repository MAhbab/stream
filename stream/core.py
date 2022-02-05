from typing import List
import pandas as pd
import streamlit as st
from collections import defaultdict
from .plotting import HEIGHT, WIDTH, TOOLBAR_LOC, SIZING_MODE
import bokeh.models as bkm
import bokeh.plotting as bkp
import numpy as np

class State:

    def setup(refresh=False):

        if ('globals' not in st.session_state) or (refresh):
            st.session_state.globals = State.reset_globals()
        
        if ('locals' not in st.session_state) or (refresh):
            st.session_state.locals = defaultdict(dict)

    def selections():
        return st.session_state.globals['selections']

    def variables():
        return st.session_state.globals['variables']

    def current_page():
        return st.session_state.globals['current_page']

    def locals():
        return st.session_state.locals

    def is_first_run():
        return st.session_state.globals['is_first_run']

    def update_current_page(page):
        st.session_state.globals['current_page'] = page

    def update_local_variables(group_name, **new_vals):
        for key in new_vals:
            st.session_state.locals[group_name][key] = new_vals[key]

    def clear_locals(group_name):
        st.session_state.locals[group_name].clear()

    def update_global_variables(base_key=None, **vals):
        for key in vals:
            obj = vals[key]
            base_key = base_key or obj.__class__.__name__
            st.session_state.globals['variables'][base_key][key] = obj

    def reset_globals():
        globals_dict = {
            'current_page':None,
            'selections': defaultdict(list),
            'variables': defaultdict(dict),
            'is_first_run': True
        }
        return globals_dict

    def get_selection(dtype_key):
        vars = State.variables[dtype_key]
        keys = State.selections[dtype_key]
        if len(keys)==1:
            obj = vars[keys[0]]
        else:
            obj = [vars[k] for k in keys]
        
        return obj

    def update_selection(dtype_key, *keys):
        st.session_state.globals['selections'][dtype_key] = list(keys)

    def clear_selection(dtype_key=None):
        if dtype_key is None:
            st.session_state.globals['selections'].clear()
        
        else:
            st.session_state.globals['selections'][dtype_key].clear()

class Page:

    def __init__(self, name=None, group_name=None, is_setup_page=False, generate_title=True) -> None:
        self._name = name or self.__class__.__name__
        self._group_name = group_name or 'Default Group'
        self._is_setup_page = is_setup_page

        self.generate_title = generate_title

    @property
    def name(self):
        return self._name

    @property
    def group(self):
        return self._group_name

    @property
    def locals(self):
        return State.locals()[self.group]

    @property
    def selections(self):
        return State.selections()
    
    def update_global_variables(self, base_key=None, **vars):
        State.update_global_variables(base_key, **vars)

    def update_local_variables(self, **vars):
        State.update_local_variables(self.group, **vars)

    def __call__(self):
        raise NotImplementedError()

class Selection(Page):

    '''
    Page to select variables which can be accessed from calling
    :func: State.variables <stream.core.State.variables>
    '''

    def __call__(self):

        with st.expander('Current Selections'):
            st.write(State.selections)

        with st.expander('Local Variables'):
            local_vars = State.locals()
            for key in local_vars:
                group_vars = local_vars[key]
                if not group_vars:
                    continue
                st.subheader(key)
                st.write(group_vars)

        for key in State.variables():
            choices = State.variables()[key]
            widg_key = 'stream_selection_{}'.format(key)

            st.multiselect(
                label='Selection: {}'.format(key), 
                options=choices.keys(), 
                default=State.selections()[key],
                key=widg_key,
                on_change=State.update_selection,
                kwargs={'dtype': key},
                args=(x for x in st.session_state[widg_key])
            )

        st.button(
            label='Clear All Selections',
            on_click=State.clear_selection
        )

        st.button(
            label='Delete All Variables',
            on_click=State.reset_globals
        )

class PlottingPage(Page):

    '''
    :class: Page <stream.core.Page> object with helper functions to visualize DataFrames. 
    There are two ways to utilize this object:
        1) Pass it as a page to :class: App <stream.core.App> without specifying :arg: target_variable.
        PlottingPage will allow the user to choose a DataFrame from the selections under globals.
        2) Pass it as a page to :class: App <stream.core.App> while specifying :arg: target_variable.
        PlottingPage will look for the DataFrame with name :arg: target_variable under local variables.
    '''

    def __init__(
        self,
        target_variable=None,
        name=None,
        group_name=None
    ) -> None:
        super().__init__(name, group_name)   
        self._target_variable = target_variable

    def _default_figure(self, datetime_x=False, ttips=None):
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

    def _figure_format(self, figure, xlabel=None, ylabel=None, title=None):
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

    def _bquad(self, srs, bins):
        bounds_dict = {}
        try:
            rbins = pd.cut(srs, np.linspace(srs.min(), srs.max(), bins))
        except ValueError:
            st.error('Error generating bins. Try decrease the bin count or setting a longer timeframe')
        rgrp = rbins.groupby(rbins).count()
        bounds_dict['top'] = [x for x in rgrp]
        bounds_dict['left'] = [x.left for x in rgrp.index]
        bounds_dict['right'] = [x.right for x in rgrp.index]
        bounds_dict['bottom'] = 0
        return bounds_dict

    def hist(self, srs: pd.Series, bins: int, fig=None, color=None):

        if not fig:
            ttips = [('Name', '$name'), ('Count', '@top'), ('Value', '$x{0,0.00}')]
            fig = self._default_figure(ttips=ttips)

        kw = self._bquad(srs, bins)
        kw['legend_label'] = kw['name'] = srs.name
        if color is not None:
            kw['color'] = color
        fig.quad(**kw)
        return fig

    def line(self, source, y_col, x_col='Date', fig=None, color=None, is_time_series=True):

        #pre process data

        if fig is None:
            ttips = [('Name', '@{}'.format(y_col)), ('Value', '@value{0.00a}')]
            if is_time_series:
                ttips.insert(1, ('Date', '@date_str'))
            else:
                ttips.insert(1, ('Index', '@{}'.format(x_col)))

            fig = self._default_figure(is_time_series, ttips)

        #in case dframe has multi-index columns

        plt_kwargs = {
            'y': y_col,
            'x': x_col,
            'source': source,
            'legend_label': y_col, 
        }

        if color is not None:
            plt_kwargs['color'] = color

        fig.line(**plt_kwargs)

        return fig

class App:

    def __init__(self, pages: List[Page], setup_on_every_run=False, display_local_variables=False, **global_vars) -> None:
        if Selection.__name__ not in [p.__class__.__name__ for p in pages]:
            pages.append(Selection(group_name='Main Menu'))
        self._global_vars = global_vars
        self._pages = pages
        self._page_groups = defaultdict(dict)
        self._setup_on_every_run = setup_on_every_run
        self._display_local_variables = display_local_variables

        for p in pages:
            self._page_groups[p.group][p.name] = p

    def _re_init(self):
        st.session_state.globals['is_first_run'] = True

    def sidebar_options(self):
        page_group_selection = st.sidebar.radio('Select Page Group', self._page_groups.keys())
        page_options = self._page_groups[page_group_selection]
        display_page_choices = [p for p in page_options if not page_options[p]._is_setup_page]
        page_name = st.sidebar.radio('Select Page', display_page_choices)
        page_selection = page_options[page_name]
        st.sidebar.button('Re-initialize', on_click=self._re_init)
        State.update_current_page(page_selection)


    def display_local_vars(self, page):
        with st.expander('Local Variables'):
            local_vars = page.locals
            for var_name in local_vars:
                st.subheader(var_name)
                var = local_vars[var_name]
                if isinstance(var, (pd.Series, pd.DataFrame)):
                    st.dataframe(var)
                else:
                    st.write(var)

    def setup(self):
        with st.spinner('Running setup pages..'):
            for p in self._pages:
                if p._is_setup_page:
                    st.write("Setting up Page '{}' in Group '{}'...".format(p.name, p.group))
                    p()
                    st.success("Setup Page '{}' in Group '{}'!".format(p.name, p.group))
    
    def run(self):

        #initialize session state (first run only)
        State.setup()

        if State.is_first_run() or self._setup_on_every_run:
            st.session_state.globals['is_first_run'] = False
            self.setup()


        #page selection options
        self.sidebar_options()

        current_page = State.current_page()

        if isinstance(current_page, Page) and (current_page.generate_title):
            st.title('{}::{}'.format(current_page.group, current_page.name))

        #display local variables
        if self._display_local_variables:
            self.display_local_vars(current_page)

        current_page()



        






