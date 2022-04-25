import streamlit as st
from typing import Any, Dict, List, Hashable, Union
from treelib import Tree, Node
from pandas import DataFrame
from bt import Strategy, Backtest
from numpy.random import randn

class Element:

    def __init__(self, name=None, pass_data_to_parent=False) -> None:
        self._name = name or self.__class__.__name__
        self._pass_to_parent = pass_data_to_parent

    @property
    def name(self):
        return self._name

    def __call__(self, target: Node=None, **kwargs) -> Any:
        raise NotImplementedError

class Page(Node):

    def setup(self):
        self.temp = {}
        if self.data is None:
            self.data = {}

    def generate_random_key(self):
        return round(abs(10*randn()), 3)

    def save_obj_from_widget_key(self, key):
        val = st.session_state[key]


    def __call__(self, *args, **kwargs):
        raise NotImplementedError


class Session(Tree):

    def __init__(self, name=None, start_page=None, debug_mode=False, **global_vars) -> None:
        self._name = name or self.__class__.__name__
        self._globals = global_vars
        self._next_page_key = '{}_next_page'.format(self._name)
        self._debug_mode = debug_mode
        self._start_page = start_page

    @property
    def active_page(self) -> Page:
        if self._active_page_id is not None:
            return self.get_node(self._active_page_id)
        else:
            raise Exception('No active page was set')

    @property
    def page_options(self) -> List[Page]:
        return st.session_state[self._name]['page_options']

    @property
    def globals(self):
        return self._globals

    def add_node(self, node, parent=None):
        if (parent is None) and (self.root is not None):
            parent = self.root
        return super().add_node(node, parent)

    def setup(self):
        start_page = self._start_page

        if self._name in st.session_state:
            tree = st.session_state[self._name]['locals']
            super().__init__(tree, True, Page, self._name)

            self._active_page_id = st.session_state[self._name]['active_page']

        else:
            super().__init__(node_class=Page, identifier=self._name)
            st.session_state[self._name] = {}
            start_page = start_page if isinstance(start_page, Page) else lambda : st.header('Welcome')
            self.add_node(start_page)
            self._active_page_id = self.root
            self.update(start_page.identifier)

    def update(self, page_id=None):

        if page_id is not None:
            self._active_page_id = page_id

        st.session_state[self._name]['locals'] = Tree(self, True, Page, self._name)
        st.session_state[self._name]['active_page'] = self._active_page_id

        page_options = self.children(self._active_page_id)
        if not page_options: #if active page is a leaf, display siblings instead of children
            page_options = self.siblings(self._active_page_id)
        parent = self.parent(self._active_page_id)

        if parent is not None:
            page_options.append(parent)

            if parent.identifier != self.root:
                page_options.append(self.get_node(self.root))

        page_options.insert(0, self.active_page)

        st.session_state[self._name]['page_options'] = page_options

    def run(self):

        self.sidebar()
        active_page = self.active_page
        active_page.setup()
        active_page(**self.globals)
        
        self.cleanup(active_page)

    def sidebar(self):
        selections = self.page_options
        selection_ids = [(x.tag, x.identifier) for x in selections]

        st.sidebar.radio(
            'Contents',
            selection_ids,
            format_func=lambda x: x[0],
            key=self._next_page_key,
            on_change=self._radio_update_page
        )

        st.sidebar.button('Re-initialize', on_click=self.reset)

    #NOTE: necessary evil due to streamlit's widget key functionality
    def _radio_update_page(self):
        _, id = st.session_state[self._next_page_key]
        self.update(id)

    def reset(self):
        for node in self.all_nodes_itr():
            node.data.clear()
        self.update(self.root)

    def cleanup(self, active: Page):
        self._globals = dict(self.globals, **active.temp)
        self.update_node(active.identifier, data=active.data)
        self.update(active.identifier)







