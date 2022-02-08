from typing import List
import pandas as pd
from soupsieve import select
import streamlit as st
from collections import defaultdict
import bokeh.models as bkm
import bokeh.plotting as bkp
import numpy as np
from treelib import Tree, Node
from copy import deepcopy

HEIGHT = 400
WIDTH = 600
TOOLBAR_LOC = 'below'
SIZING_MODE = 'stretch_both'

import inspect

class Page(Node):

    def __init__(
        self, 
        tag=None, 
        identifier=None, 
        data=None, 
        elements=None, 
        run_header=False, 
        run_footer=False, 
        header_kwargs=None,
        footer_kwargs=None,
    ):
        self._elements = elements if elements is not None else []
        self._run_header = run_header
        self._run_footer = run_footer
        self._header_kwargs = header_kwargs if header_kwargs is not None else {}
        self._footer_kwargs = footer_kwargs if footer_kwargs is not None else {}
        super().__init__(tag or self.__class__.__name__, identifier, None, data or {})

    def __call__(self, parent, **global_vars):
        
        if self._run_header:
            self.header(**self._header_kwargs)

        for e in self._elements:
            
            e(self, **global_vars)

        if self._run_footer:
            self.footer(**self._footer_kwargs)

    def header(self, **kwargs):
        raise NotImplementedError()

    def footer(self, **kwargs):
        raise NotImplementedError()

class DefaultStartPage(Page):

    def __init__(self):
        super().__init__(tag='Home Page', identifier='root', run_header=True)

    def header(self, **kwargs):
        st.header('Welcome')
        st.text('This is the default home page')
        st.text('Use the panel on the left to navigate pages')
        st.text("In case of issues, press the Re-initialize button in the navigation panel")
        st.text('If issues persist, contact Mahfuj.')

class State(Tree):

    def __init__(self, name=None, **global_vars) -> None:
        self._name = name or self.__class__.__name__
        self._globals = global_vars

        if self._name in st.session_state:
            tree = st.session_state[self._name]['locals']

            #NOTE: a deep copy is made from the tree existing in the session state
            #this way, changes to the state are only saved upon updating via self.update
            super().__init__(tree, True, Page, self._name)
            self._active_page = st.session_state[self._name]['active_page']
            self._is_first_run = st.session_state[self._name]['is_first_run']
        else:
            super().__init__(node_class=Page, identifier=self._name)
            st.session_state[self._name] = {}
            start_page = DefaultStartPage()
            self.add_node(start_page)
            self._active_page = self.root
            self._is_first_run = True
            self.update(True)

    @property
    def active_page(self) -> Node:
        if self._active_page is not None:
            return self.get_node(self._active_page)
        else:
            raise Exception('No active page was set')

    @property
    def globals(self):
        return self._globals

    @property
    def is_first_run(self):
        return self._is_first_run

    def add_node(self, node, parent=None):
        if (parent is None) and (self.root is not None):
            parent = self.root
        return super().add_node(node, parent)

    def update(self, is_first_run=False):
        st.session_state[self._name]['locals'] = Tree(self, True, Page, self._name)
        st.session_state[self._name]['active_page'] = self._active_page
        st.session_state[self._name]['is_first_run'] = is_first_run

    def update_active_page(self, page_id):
        if isinstance(page_id, Page):
            page_id = page_id.identifier
        self._active_page = page_id
        self.update()

    def reset(self):
        for node in self.all_nodes_itr():
            node.data.clear()
        self._is_first_run = True
        self.update()
        st.write(self.all_nodes())
        st.write(st.session_state[self._name]['locals'].all_nodes())

    def run(self):
        raise NotImplementedError()


class Element:

    def __init__(self, name=None) -> None:
        self._name = name or self.__class__.__name__

    def __call__(self, target: Page, **global_vars):
        raise NotImplementedError()

class App(State):

    def sidebar(self):
        nid = self._active_page
        selections = [self.active_page]
        selections.extend(self.children(nid))
        selections.extend(self.siblings(nid))
        selection_ids = [(x.tag, x.identifier) for x in selections]
        selection_ids.sort()

        page_select = st.sidebar.radio(
            'Child Pages',
            selection_ids,
            format_func=lambda x: x[0]
        )

        st.sidebar.button('Re-initialize', on_click=self.reset)

        if nid!=self.root:
            parent = self.parent(nid)
            if st.sidebar.button('Back to {}'.format(parent.tag)):
                return parent
            
            if parent.identifier != self.root:
                if st.sidebar.button('Back to {}'.format(self.root.title())):
                    return self.root

        return self.get_node(page_select[1])

    def run(self):

        last_page = self.active_page
        new_active_page = self.sidebar()
        parent = self.parent(new_active_page.identifier)

        new_active_page(parent, **self.globals)
        if parent is not None:
            self.update_node(parent.identifier, data=parent.data)
        self.update_node(new_active_page.identifier, data=new_active_page.data)
        self.update_active_page(new_active_page.identifier)


class AppDepr:

    def __init__(self, pages: List[Page], setup_on_every_run=False, display_local_variables=False, **global_vars) -> None:
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
        State.update_active_page(page_selection)


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
        '''Helper function to calculate bounds for hist plot'''
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


