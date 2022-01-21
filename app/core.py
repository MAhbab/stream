from typing import List
import streamlit as st
class StreamlitPage:

    def __init__(self, name=None) -> None:
        self._name = name or self.__class__.__name__
        self._group = None

    @property
    def name(self):
        return self._name

    @property
    def locals(self):
        if self._group is not None:
            return self._group.variables
        else:
            raise Exception('Page must be part of a group to access local variables')

    @property
    def globals(self):
        return st.session_state.globals

    def get_variable(self, key):
        if key in self.locals:
            return self.locals[key]
        elif key in self.globals:
            return self.globals[key]
        else:
            raise st.error(
                "The variable '{}' was not defined for page '{}'".format(key, self.name)
            )

    def __call__(self):
        raise NotImplementedError

class StreamlitPageGroup:

    def __init__(self, name, input_func, *pages):
        self._name = name
        self._input_func = input_func
        self._pages = {p.name: p for p in pages}
        for p_name in self._pages:
            self._pages[p_name]._group = self

    @property
    def name(self):
        return self._name

    @property
    def variables(self):
        return st.session_state.locals[self.name]

    @property
    def pages(self):
        return self._pages

    @property
    def inputs(self):
        return self._input_func

class StreamlitApp:

    def __init__(self, page_groups: List[StreamlitPageGroup], title_page=None, aggregate_inputs=True, **global_vars) -> None:
        self._page_groups = {p.name: p for p in page_groups}
        self._title_page = title_page
        self._aggregate_inputs = aggregate_inputs
        self._global_vars = global_vars

    @property
    def inputs(self):
        return {p: self._page_groups[p].inputs for p in self._page_groups}

    def inputs_page(self):

        if self._aggregate_inputs:
            pass

    

    

def run(page_groups: List[StreamlitPageGroup], **global_vars):
    #initalize session state
    st.session_state.globals = global_vars
    if 'locals' not in st.session_state:
        st.session_state.locals = {}

    first_run = False
    if 'first_run' not in st.session_state:
        st.session_state.first_run = False #mark as false for subsequent runs
        first_run = True

    page_group_dict = {p.name: p for p in page_groups}

    page_group_selection = st.sidebar.radio('Select Page Group', page_group_dict.keys())
    page_options = page_group_dict[page_group_selection].pages
    page_name = st.sidebar.radio('Select Page', page_options.keys())
    page_selection = page_options[page_name]

    #load inputs or load selected page
    if st.sidebar.button('Inputs') or first_run:
        local_vars = {}
        st.header('Inputs Page')
        with st.form('Inputs'):
            for p in page_groups:
                st.subheader('{} Inputs'.format(p.name))
                local_vars[p.name] = p.inputs()
            submit = st.form_submit_button('Submit', on_click=lambda x: st.session_state.locals.update(x), kwargs={'x': local_vars})
    else:
        page_selection()