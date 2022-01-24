from typing import List
import streamlit as st
import pickle
from collections import defaultdict
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
    def variables(self):
        return st.session_state.variables

    @property
    def single_targets(self):
        return st.session_state.single_target

    @property
    def multi_targets(self):
        return st.session_state.multi_target

    @property
    def globals(self):
        return st.session_state.globals

    def set_variable(self, key: str, value):
        st.session_state.variables[value.__class__.__name__][key] = value

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
        self.setup()

        #page selection options
        self.sidebar_options()

        #either display selected page or inputs
        current_page = st.session_state.globals['current_page']
        current_page()

