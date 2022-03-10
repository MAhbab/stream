from typing import Any, List
import streamlit as st
from treelib import Tree, Node
import pandas as pd

class Element:

    def __init__(self, name=None, pass_data_to_parent=False) -> None:
        self._name = name or self.__class__.__name__
        self._pass_to_parent = pass_data_to_parent

    @property
    def name(self):
        return self._name

    def __call__(self, target: Node, **global_vars) -> Any:
        raise NotImplementedError()

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

    @property
    def elements(self) -> List[Element]:
        return self._elements

    def __call__(self, parent: Node, **global_vars):
        
        if self._run_header:
            self.header(**self._header_kwargs)

        for e in self.elements:

            val = e(self, **global_vars)

            if e._pass_to_parent:
                parent.data[e.name] = val
            else:
                self.data[e.name] = val

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

class Session(Tree):

    def __init__(self, name=None, start_page=None, debug_mode=False, **global_vars) -> None:
        self._name = name or self.__class__.__name__
        self._globals = global_vars
        self._next_page_key = '{}_next_page'.format(self._name)
        self._debug_mode = debug_mode

        if self._name in st.session_state:
            tree = st.session_state[self._name]['locals']
            super().__init__(tree, True, Page, self._name)

            self._active_page_id = st.session_state[self._name]['active_page']
            self._is_first_run = st.session_state[self._name]['is_first_run']

        else:
            super().__init__(node_class=Page, identifier=self._name)
            self.setup()
            st.session_state[self._name] = {}
            start_page = start_page if isinstance(start_page, Page) else DefaultStartPage()
            self.add_node(start_page)
            self._active_page_id = self.root
            self._is_first_run = True
            self.update(True)

    #NOTE: necessary evil due to streamlit's widget key functionality
    def _radio_update_page(self):
        _, id = st.session_state[self._next_page_key]
        self.update_active_page(id)

    @property
    def active_page(self) -> Node:
        if self._active_page_id is not None:
            return self.get_node(self._active_page_id)
        else:
            raise Exception('No active page was set')

    @property
    def adjacent_pages(self):
        return st.session_state[self._name]['adjacent_pages']

    @property
    def globals(self):
        return self._globals

    @property
    def is_first_run(self):
        return self._is_first_run

    def setup(self):
        pass

    def add_node(self, node, parent=None):
        if (parent is None) and (self.root is not None):
            parent = self.root
        return super().add_node(node, parent)

    def update(self):
        st.session_state[self._name]['locals'] = Tree(self, True, Page, self._name)
        st.session_state[self._name]['active_page'] = self._active_page_id
        st.session_state[self._name]['is_first_run'] = self._is_first_run

        adjacent_pages = self.children(self._active_page_id)
        if not adjacent_pages: #if active page is a leaf, display siblings instead of children
            adjacent_pages = self.siblings(self._active_page_id)
        parent = self.parent(self._active_page_id)

        if parent is not None:
            adjacent_pages.append(parent)

            if parent.identifier != self.root:
                adjacent_pages.append(self.get_node(self.root))

        adjacent_pages.insert(0, self.active_page)

        st.session_state[self._name]['adjacent_pages'] = adjacent_pages

    def update_active_page(self, page_id):
        if isinstance(page_id, Page):
            page_id = page_id.identifier
        self._active_page_id = page_id
        self.update()

    def reset(self):
        for node in self.all_nodes_itr():
            node.data.clear()
        self._is_first_run = True
        self._active_page_id = self.root
        self.update()

    def sidebar(self):
        nid = self._active_page_id
        selections = self.adjacent_pages
        selection_ids = [(x.tag, x.identifier) for x in selections]

        st.sidebar.radio(
            'Contents',
            selection_ids,
            format_func=lambda x: x[0],
            key=self._next_page_key,
            on_change=self._radio_update_page
        )

        st.sidebar.button('Re-initialize', on_click=self.reset)

    def debugger(self, page: Page, **global_vars):
        with st.expander('Local Variables'):
            for key in page.data:
                val = page.data[key]
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

        with st.expander('Pages'):
            st.text('Is first run: {}'.format(self.is_first_run))
            st.text('Active page')
            active_page = self.active_page
            st.write('Tag: {}, Id: {}'.format(active_page.tag, active_page.identifier))

            st.text('Adjacent Pages')
            st.write(self.adjacent_pages)

            st.text('All pages')
            st.write(list(self.all_nodes_itr()))

    def run(self):

        if self._debug_mode:
            self.debugger(self.active_page)


        self.sidebar()
        new_active_page = self.active_page
        parent = self.parent(new_active_page.identifier)
        new_active_page(parent, **self.globals)

        if parent is not None:
            self.update_node(parent.identifier, data=parent.data)
        self.update_node(new_active_page.identifier, data=new_active_page.data)
        self.update_active_page(new_active_page.identifier)







