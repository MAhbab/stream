from io import open_code
import streamlit as st
from typing import Any, Dict, List, Hashable, Union
from treelib import Tree, Node
from pandas import Series, DataFrame
from bt import Strategy, Backtest

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

    def __init__(
        self, 
        name=None, 
        identifier=None, 
        data=None, 
        elements=None, 
        show_header=False, 
        show_footer=False
    ):
        self._elements = elements if elements is not None else []
        self._show_header = show_header
        self._show_footer = show_footer
        super().__init__(name or self.__class__.__name__, identifier, None, data or {})

    @property
    def elements(self) -> List[Element]:
        return self._elements

    def __call__(self, parent: Node, **global_vars):

        if self._show_header:
            data = dict(self.data, **global_vars)
            self.header(**data)

        data = dict(self.data, **global_vars)

        for e in self.elements:

            val = e(target=self, **data)

            if e._pass_to_parent:
                parent.data[e.name] = val
            else:
                self.data[e.name] = val

        if self._show_footer:
            data = dict(self.data, **global_vars)
            self.footer(**data)

    def header(self, **kwargs):
        raise NotImplementedError

    def footer(self, **kwargs):
        raise NotImplementedError

class BacktestPage(Page):

    def __init__(
        self, 
        tag: str = None,
        identifier: Hashable = None,
        data: dict = None,
        elements: List[Element] = None,
        show_header: bool = False,
        show_footer: bool = False,
    ):
        data = data or {}
        bkt_dict = {'strategies': {}, 'backtests': {}, 'datasets': {}}
        self._active_backtest_key = None
        self._active_strategy_key = None
        self._active_dataset_key = None

        self._update = None

                
        data = dict(data, **bkt_dict)
        super().__init__(tag, identifier, data, elements, show_header, show_footer)

    @property
    def strategies(self) -> Dict[str, Strategy]:
        return self.data['strategies']

    @property
    def backtests(self) -> Dict[str, Backtest]:
        return self.data['backtests']

    @property
    def datasets(self) -> Dict[str, DataFrame]:
        return self.data['datasets']

    @property
    def active_strategy(self) -> Union[Strategy, None]:
        return self.data['strategies'][self._active_strategy_key]

    @property
    def active_backtest(self) -> Union[Backtest, None]:
        return self.data['backtests'][self._active_backtest_key]

    @property
    def active_dataset(self) -> Union[DataFrame, None]:
        df = self.data['datasets'][self._active_dataset_key]
        df.name = self._active_dataset_key
        return df

    @property
    def update(self):
        return self._update


    def _data_name(self, dta):
        try:
            return dta.name
        except AttributeError:
            return dta.__class__.__name__

    def _quick_backtest(self):
        name = 'Strategy<{}> with Data<{}>'.format(self._active_strategy_key, self._active_dataset_key)
        bkt = Backtest(self.active_strategy, self.active_dataset.dropna(), name=name)
        self._run(bkt)
        self.update()

    def _save_backtest_components(self):
        df_name = 'Data from Backtest<{}>'.format(self._active_backtest_key)
        strat = self.active_backtest.strategy
        self.datasets[df_name] = self.active_backtest.data.dropna()
        self.strategies[strat.name] = strat
        self.update()
        

    def _run(self, *bkts):
        if not bkts:
            return

        with st.spinner('Running Backtests...'):
            prg = 0
            pbar = st.progress(prg)
            increment = 1/len(bkts)

            for bk in bkts:
                bk_name = bk.name
                st.text('Running {}...'.format(bk))
                bk.run()
                st.success('Successfully Ran {}'.format(bk_name))

                prg += increment
                pbar.progress(prg)
        
        st.success('Backtests run successful')
        self.backtests.update(**{b.name: b for b in bkts})

    def __call__(self, parent: Node, **global_vars):
        self._active_backtest_key = st.sidebar.selectbox('Select Backtest', self.backtests)
        self._active_strategy_key = st.sidebar.selectbox('Select Strategy', self.strategies)
        self._active_dataset_key = st.sidebar.selectbox('Select Dataset', self.datasets)

        if all([x is not None for x in [self._active_strategy_key, self._active_dataset_key]]):
            st.sidebar.button('Quick Backtest', on_click=self._quick_backtest)

        if self._active_backtest_key is not None:
            st.sidebar.button('Save Backtest Components', on_click=self._save_backtest_components)

        
        
        return super().__call__(parent, **global_vars)

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
            self.update(start_page.identifier)

    #NOTE: necessary evil due to streamlit's widget key functionality
    def _radio_update_page(self):
        _, id = st.session_state[self._next_page_key]
        self.update(id)

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

    def update(self, page_id=None):

        if page_id is not None:
            self._active_page_id = page_id

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


    def reset(self):
        for node in self.all_nodes_itr():
            node.data.clear()
        self._is_first_run = True
        self.update(self.root)

    def sidebar(self):
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
                if isinstance(val, (DataFrame, Series)):
                    st.dataframe(val)
                else:
                    st.write(val)

        with st.expander('Global Variables'):
            for key in global_vars:
                val = global_vars[key]
                st.subheader(key)
                if isinstance(val, (DataFrame, Series)):
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

    def cleanup(self, active: Page, parent: Page):
        if parent is not None:
            self.update_node(parent.identifier, data=parent.data)
        self.update_node(active.identifier, data=active.data)
        self.update(active.identifier)

    def run(self):

        if self._debug_mode:
            self.debugger(self.active_page)


        self.sidebar()
        new_active_page = self.active_page
        parent = self.parent(new_active_page.identifier)
        new_active_page(parent, **self.globals)

        self.cleanup(new_active_page, parent)







