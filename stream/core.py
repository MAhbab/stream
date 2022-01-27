from ssl import OP_SINGLE_ECDH_USE
from typing import List
import streamlit as st
import pickle
from collections import defaultdict

class State:

    def setup(refresh=False):

        if ('globals' not in st.session_state) or (refresh):
            st.session_state.globals = State.clear_globals()
        if('locals' not in st.session_state) or (refresh):
            st.session_state.locals = defaultdict(dict)

    def selections():
        return st.session_state.globals['selections']

    def variables():
        return st.session_state.globals['variables']

    def current_page():
        return st.session_state.globals['current_page']

    def locals():
        return st.session_state.locals

    def update_local_variables(group_name, **new_vals):
        for key in new_vals:
            st.session_state.locals[group_name][key] = new_vals[key]

    def clear_locals(group_name):
        st.session_state.locals[group_name].clear()

    def update_global_variables(**vals):
        for key in vals:
            obj = vals[key]
            obj_type = obj.__class__.__name__
            st.session_state.globals['variables'][obj_type][key] = obj

    def clear_globals():
        globals_dict = {
            'current_page': State.target_page,
            'selections': defaultdict(list),
            'variables': defaultdict(dict),
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


        for key in State.variables:
            choices = State.variables[key]
            widg_key = 'stream_selection_{}'.format(key)

            new_target_keys = st.multiselect(
                label='Selection: {}'.format(key), 
                options=choices.keys(), 
                default=State.selections[key],
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
                on_click=State.clear_globals
            )

        
class Page:

    def __init__(self, name=None, group_name=None) -> None:
        self._name = name or self.__class__.__name__
        self._group_name = group_name or 'DefaultGroup'

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
    
    def update_global_variables(self, **vars):
        State.update_global_variables(**vars)

    def update_local_variables(self, **vars):
        State.update_local_variables(self.group, **vars)

    def __call__(self):
        raise NotImplementedError()


class App:

    def __init__(self, pages: List[Page], **global_vars) -> None:
        self._global_vars = global_vars
        self._page_groups = defaultdict(dict)
        self._page_groups['Main Menu']['Selections'] = self.target_page
        for p in pages:
            self._page_groups[p.group][p.name] = p


    def setup(self):

        if 'variables' not in st.session_state:
            st.session_state.variables = defaultdict(dict)

        if 'single_target' not in st.session_state:
            st.session_state.single_target = defaultdict(lambda: None)

        if 'multi_target' not in st.session_state:
            st.session_state.multi_target = defaultdict(list)

        if 'globals' not in st.session_state:
            st.session_state.globals = self._global_vars
            st.session_state.globals['current_page'] = self.target_page

    def _update_variable(self, key, choices, multi=False):
        if not multi:
            obj_key = st.session_state['single_target_{}'.format(key)]
            st.session_state.single_target[key] = choices[obj_key]
        else:
            obj_keys = st.session_state['multi_target_{}'.format(key)]
            st.session_state.multi_target[key] = [choices[x] for x in obj_keys]
        st.success('Variables sucessfully updated!')

    def _update_current_page(self, page: Page):
        st.session_state.globals['current_page'] = page
        
    def target_page(self):

        st.header('Selections')

        with st.expander('Current Targets', True):
            st.markdown('Single Targets')
            st.write(st.session_state.single_target)

            st.markdown('Multi Targets')
            st.write(st.session_state.multi_target)


        for key in st.session_state.variables:
            choices = st.session_state.variables[key]
            new_target_key = st.selectbox(
                label='Single Target Select: {}'.format(key), 
                options=choices.keys(), 
                key='single_target_{}'.format(key),
                on_change=self._update_variable,
                kwargs={'key': key, 'choices': choices, 'multi': False}
            )
            new_target_keys = st.multiselect(
                label='Multi Target Select: {}'.format(key), 
                options=choices.keys(), 
                key='multi_target_{}'.format(key),
                on_change=self._update_variable,
                kwargs={'key': key, 'choices': choices, 'multi': True}
            )

    def sidebar_options(self):
        page_group_selection = st.sidebar.radio('Select Page Group', self._page_groups.keys())
        page_options = self._page_groups[page_group_selection]
        page_name = st.sidebar.radio('Select Page', page_options.keys())
        page_selection = page_options[page_name]
        self._update_current_page(page_selection)
    
    def run(self):
        #initialize session state
        State.setup()

        #page selection options
        self.sidebar_options()

        #either display selected page or inputs
        current_page = st.session_state.globals['current_page']
        current_page()


