from typing import List
import pandas as pd
import streamlit as st
from collections import defaultdict

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

    def target_page():

        st.header('Selections')

        with st.expander('Current Selections', True):
            st.write(State.selections)


        for key in State.variables():
            choices = State.variables()[key]
            widg_key = 'stream_selection_{}'.format(key)

            new_target_keys = st.multiselect(
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

    def target_page_sidebar():

        st.subheader('Selections')

        with st.expander('target_page_sidebar'):
            for key in State.variables():
                choices = State.variables()[key]
                widg_key = 'stream_selection_{}'.format(key)

                new_target_keys = st.sidebar.multiselect(
                    label='Selection: {}'.format(key), 
                    options=choices.keys(), 
                    default=State.selections()[key],
                    key=widg_key,
                    on_change=State.update_selection,
                    kwargs={'dtype': key},
                    args=(x for x in st.session_state[widg_key])
                )

            st.sidebar.button(
                label='Clear All Selections',
                on_click=State.clear_selection
            )

            st.sidebar.button(
                label='Delete All Variables',
                on_click=State.reset_globals
            )
      
class Page:

    def __init__(self, name=None, group_name=None, is_setup_page=False) -> None:
        self._name = name or self.__class__.__name__
        self._group_name = group_name or 'DefaultGroup'
        self._is_setup_page = is_setup_page

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
    
    def update_global_variables(self,base_key=None, **vars):
        State.update_global_variables(base_key, **vars)

    def update_local_variables(self, **vars):
        State.update_local_variables(self.group, **vars)

    def __call__(self):
        raise NotImplementedError()


class App:

    def __init__(self, pages: List[Page], setup_on_every_run=False, display_local_variables=False, **global_vars) -> None:
        self._global_vars = global_vars
        self._pages = pages
        self._page_groups = defaultdict(dict)
        self._setup_on_every_run = setup_on_every_run
        self._display_local_variables = display_local_variables

        self._page_groups['Main Menu']['Selections'] = State.target_page

        for p in pages:
            self._page_groups[p.group][p.name] = p

    def sidebar_options(self):
        page_group_selection = st.sidebar.radio('Select Page Group', self._page_groups.keys())
        page_options = self._page_groups[page_group_selection]
        display_page_choices = [p for p in page_options if not page_options[p]._is_setup_page]
        page_name = st.sidebar.radio('Select Page', display_page_choices)
        page_selection = page_options[page_name]
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

        if isinstance(current_page, Page):
            st.title('{}::{}'.format(current_page.group, current_page.name))

        #display local variables
        if self._display_local_variables:
            self.display_local_vars(current_page)

        #either display selected page or inputs
        current_page()


