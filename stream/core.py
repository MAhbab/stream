from typing import List
import streamlit as st
from treelib import Tree, Node
import pandas as pd

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

        with st.expander('Local Variables'):
            for key in self.data:
                val = self.data[key]
                if isinstance(val, (pd.DataFrame, pd.Series)):
                    st.dataframe(val)
                else:
                    st.write(val)

        with st.expander('Global Variables'):
            for key in global_vars:
                val = global_vars[key]
                st.subheader(key)
                if isinstance(val, (pd.DataFrame, pd.Series)):
                    st.dataframe(val)
                else:
                    st.write(val)
        
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

    def __init__(self, name=None, start_page=None, **global_vars) -> None:
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
            start_page = start_page if isinstance(start_page, Page) else DefaultStartPage()
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
        selections = self.all_nodes_itr()
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

    def setup(self):
        raise NotImplementedError()

    def run(self):

        if self.is_first_run:
            self.setup()

        last_page = self.active_page
        new_active_page = self.sidebar()
        parent = self.parent(new_active_page.identifier)

        new_active_page(parent, **self.globals)
        if parent is not None:
            self.update_node(parent.identifier, data=parent.data)
        self.update_node(new_active_page.identifier, data=new_active_page.data)
        self.update_active_page(new_active_page.identifier)




