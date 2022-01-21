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

    def get_variable(self, key: str, valid_types: tuple = None):
        if key in self.locals:
            var = self.locals[key]
        elif key in self.globals:
            var = self.globals[key]
        else:
            st.error(
                "The variable '{}' was not defined for page '{}'".format(key, self.name)
            )
        
        if valid_types is not None:
            if isinstance(var, valid_types):
                return var
            else:
                st.error(
                    "Variable '{}' of type '{}' is an invalid type".format(key, var.__class__.__name__)
                )


    def __call__(self):
        raise NotImplementedError()

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

    FIRST_RUN = True

    def __init__(self, page_groups: List[StreamlitPageGroup], **global_vars) -> None:
        self._page_groups = {p.name: p for p in page_groups}
        self._global_vars = global_vars

    @property
    def inputs(self):
        return {p: self._page_groups[p].inputs for p in self._page_groups}

    def inputs_page(self):
        local_vars = {}
        st.header('Inputs Page')
        for p in self._page_groups:
            st.subheader('{} Inputs'.format(p.name))
            local_vars[p.name] = p.inputs()
        submit = st.form_submit_button('Submit', on_click=lambda x: st.session_state.locals.update(x), kwargs={'x': local_vars})
    
    def run(self):
        #intialize global variables
        st.session_state.globals = self._global_vars
        if 'locals' not in st.session_state:
            st.session_state.locals = {}

        if self.FIRST_RUN:
            self.FIRST_RUN = False

        #page selection options
        page_group_selection = st.sidebar.radio('Select Page Group', self._page_groups.keys())
        page_options = self._page_groups[page_group_selection].pages
        page_name = st.sidebar.radio('Select Page', page_options.keys())
        page_selection = page_options[page_name]

        #either display selected page or inputs
        if st.sidebar.button('Go to Inputs') or self.FIRST_RUN:
            self.FIRST_RUN = False
            with st.form('input_page'):
                self.inputs_page()
        else:
            page_selection() 