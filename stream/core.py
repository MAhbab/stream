from typing import List
import pandas as pd
from soupsieve import select
import streamlit as st
from collections import defaultdict
import bokeh.models as bkm
import bokeh.plotting as bkp
import numpy as np
from treelib import Tree, Node

HEIGHT = 400
WIDTH = 600
TOOLBAR_LOC = 'below'
SIZING_MODE = 'stretch_both'

class State:

    def __init__(self, name=None) -> None:
        self._name = name or self.__class__.__name__

        if name in st.session_state:
            self._state = st.session_state[name]
        else:
            self.setup()

    @property
    def state(self):
        return st.session_state[self._name]

    @property
    def active_page(self) -> Node:
        return self.state['active_page']

    @property
    def locals(self) -> Tree:
        return self.state['locals']

    @property
    def globals(self):
        return self.state['globals']

    @property
    def is_first_run(self):
        return self.state['is_first_run']

    def update(self):
        st.session_state[self._name] = self._state.copy()

    def setup(self):

        self._state = {
            'globals': {},
            'locals': Tree(node_class=Page),
            'is_first_run': True,
            'active_page': None
        }

        self.update()

    def update_active_page(self, page, update=False):
        self._state['active_page'] = page
        if update:
            self.update()

    def update_locals(self, tree: Tree, update=False):
        self._state['locals'] = tree
        if update:
            self.update()

    def clear_locals(self, node, update=False):
        self._state['locals'][node].data.clear()
        if update:
            self.update()

    def update_globals(self, update=False, **kwargs):
        self._state['globals'].update(**kwargs)
        if update:
            self.update()

    def clear_globals(self, update=False):
        self._state['globals'].clear()
        if update:
            self.update()

    def set_first_run_to_false(self):
        self._state['is_first_run'] = False

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
        footer_kwargs=None
    ):
        self._parent = Node(data={})
        self._state = State()
        self._elements = elements if elements is not None else []
        self._run_header = run_header
        self._run_footer = run_footer
        self._header_kwargs = header_kwargs if header_kwargs is not None else {}
        self._footer_kwargs = footer_kwargs if footer_kwargs is not None else {}
        super().__init__(tag or self.__class__.__name__, identifier, None, data or {})

    def __getitem__(self, item):

        if item in self.data:
            st.write('pulled from class data')
            return self.data[item]

        elif item in self.locals:
            st.write('pulled from parent data')
            return self.locals[item]

        elif isinstance(self._state, State):
            if item in self.globals:
                st.write('pulled from global data')
                return self.globals[item]

        else:
            raise KeyError('{} was not found in Page<{}>'.format(item, self.tag))

    def run(self, parent=None, state=None):
        
        if isinstance(parent, Page):
            self._parent = parent
        if isinstance(state, State):
            self._state = state
        if self._run_header:
            self.header(**self._header_kwargs)

        for e in self._elements:
            e(self)

        if self._run_footer:
            self.footer(**self._footer_kwargs)

    @property
    def globals(self):
        return self._state.globals

    @property
    def locals(self):
        return self._parent.data

    def update_globals(self, **kwargs):
        self._state.update_globals(True, **kwargs)

    def update_parent_data(self, **kwargs):
        old_data = self._parent.data.update(**kwargs)

    def header(self, **kwargs):
        raise NotImplementedError()

    def footer(self, **kwargs):
        raise NotImplementedError()

class Element:

    def __init__(self, name=None) -> None:
        self._name = name or self.__class__.__name__

    def __call__(self, target: Page):
        raise NotImplementedError()

class App(Tree):

    def __init__(self, state: State=None, identifier=None):
        self._state = state or STATE
        super().__init__(None, None, Page, identifier)
        import numpy as np
        st.write(np.random.randn())

    def sidebar(self, nid):
        selections = self.children(nid)
        selections.extend(self.siblings(nid))
        active_node = self.get_node(nid)
        selections.insert(0, active_node)
        parent = self.parent(nid)
        root = self.root


        page_select = st.sidebar.radio(
            'Child Pages',
            selections,
            format_func=lambda x: x.tag
        )

        if parent is not None:
            if st.sidebar.button('Back to {}'.format(parent.tag)):
                return parent

        if nid!=root:
            if st.button('Back to {}'.format(root)):
                return self.get_node(root)

        return page_select

    def run(self):

        st.write(self._state.state)


        if self._state.is_first_run:
            active_page = self.get_node(self.root)
            self._state.update_active_page(active_page, True)
            self._state.set_first_run_to_false()

        else:
            active_page = self._state.active_page

        new_active_page = self.sidebar(active_page.identifier)
        parent = self.parent

        new_active_page.run(parent, self._state)
        st.write('Before update: {}'.format(active_page.tag))
        self._state.update_active_page(new_active_page, True)
        st.write('After update: {}'.format(active_page.tag))


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

STATE = State('SessionState')


