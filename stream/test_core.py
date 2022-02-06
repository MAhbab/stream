import unittest
from xml.etree import ElementInclude
from core import State, Page, Element
import streamlit as st
import numpy as np
from treelib import Tree

def assertTrue(test_name, expr):
    if expr:
        st.success("'{}' ran successfully".format(test_name))
    else:
        st.error("'{}' ran and failed".format(test_name))

def assertFalse(test_name, expr):
    if  not expr:
        st.success("'{}' ran successfully".format(test_name))
    else:
        st.error("'{}' ran and failed".format(test_name))

class TestCase:

    def __init__(self) -> None:
        pass

    def run_tests(self):
        test_funcs = [x for x in dir(self) if x.startswith('test_')]
        with st.expander("Test Case '{}'".format(self.__class__.__name__), True):
            for f_name in test_funcs:
                st.subheader('Running {}'.format(f_name))
                st.session_state.clear()
                f = getattr(self, f_name)
                f()

class TestState(TestCase):

    name = 'TestState'

    def __init__(self) -> None:
        pass
    
    def test_init(self):
        State(self.name)
        assertTrue('Initialize State', self.name in st.session_state)

    def test_setup(self):
        obj = State(self.name)
        test_keys = set(obj.state.keys())
        correct_keys = {'globals', 'locals', 'active_page', 'is_first_run'}
        assertTrue('Setup State variables', test_keys == correct_keys)

    def test_update(self):
        obj = State(self.name)
        var_name = 'var'
        obj._state[var_name] = 5
        assertTrue('Change made but not updated', var_name not in obj.state)
        obj.update()
        assertTrue('Change made and updated', var_name in obj.state)
        assertTrue('Variable corresponds to correct value', obj.state[var_name] == 5)

    def test_update_active_page(self):
        obj = State(self.name)
        assertTrue('Default page initialized', obj.active_page is None)
        new_page = Page('new_page', 'new_page')
        obj.update_active_page(new_page, False)
        assertTrue('Page changed but not updated', obj.active_page is None)
        obj.update()
        assertTrue('Page changed and updated', obj.active_page is new_page)
        other_new_page = Page('other_new_page', 'other_new_page')
        assertTrue('Changed to correct page', obj.active_page.identifier=='new_page')
        obj.update_active_page(other_new_page, True)
        assertTrue('Second change to correct page', obj.active_page.identifier=='other_new_page')

    def test_update_and_clear_locals(self):
        obj = State(self.name)
        assertTrue('Empty Tree initialized', len(obj.locals)==0)
        mytree = Tree(obj.locals, True, Page)
        new_page = Page('new_page', 'new_page', data={'favorite_accountant': 'Oscar'})
        mytree.add_node(new_page)
        assertTrue('Change made but not updated', len(obj.locals)==0)
        obj.update_locals(mytree, True)
        assertTrue('Change made but and updated', len(obj.locals)==1)
        assertTrue('Correct Page data', obj.locals['new_page'].data['favorite_accountant']=='Oscar')
        obj.clear_locals('new_page')
        assertTrue('Cleared Page data', not obj.locals['new_page'].data)

    
    def test_update_and_clear_globals(self):
        obj = State(self.name)
        assertTrue('Initialize empty globals', not obj.globals)
        obj.update_globals(True, dog='Rufus', cat='Thor')
        assertTrue('Correct global variable value #1', obj.globals['dog']=='Rufus')
        assertTrue('Correct global variable value #2', obj.globals['cat']=='Thor')
        obj.clear_globals(True)
        assertTrue('Successfully clear globals', not obj.globals)

class TestPage(TestCase):

    page1 = 'Page 1'
    page2 = 'Page 2'
    page3 = 'Page 3'

    def test_init(self):
        obj = Page(self.page1, self.page1)
        assertTrue('Default list constructed for element', isinstance(obj._elements, list))
        assertTrue('Element list is empty', not obj._elements)
        assertTrue('Default header kwargs created', isinstance(obj._header_kwargs, dict))
        assertTrue('Header kwargs is empty', not obj._header_kwargs)
        assertTrue('Default footer kwargs created', isinstance(obj._footer_kwargs, dict))
        assertTrue('Footer kwargs is empty', not obj._footer_kwargs)

    def test_run(self):
        obj = Page(self.page1, self.page1, data={'num_continents': 7})
        parent = Page(self.page2, self.page2, {'num_oceans': 4, 'num_continents': 2})
        state_obj = State('NewState')
        state_obj.update_globals(True, **{'pi': 3.14, 'num_oceans': 3})
        obj.run(parent, state_obj)
        assertTrue('Correct Variable Value #1', obj['num_continents']==7)
        assertTrue('Correct Variable Value #2', obj['num_oceans']==parent['num_oceans'])
        assertTrue('Correct Variable Value #3', obj['num_continents']!=parent['num_continents'])
        assertTrue('Correct Variable Value #3', obj['pi']==state_obj.globals['pi'])
        st.write(state_obj.globals['pi'])
        st.write(obj._state.globals['pi'])

    def test_run_with_elements(self):
        class SampleElement(Element):

            def __call__(self, target: Page):
                target.data['favorite_receptionist'] = 'Pam'
        
        class ExampleElement(Element):

            def __call__(self, target: Page):
                target.data['favorite_accountant'] = 'Kevin'

        obj = Page(self.page1, self.page1, elements=[SampleElement(), ExampleElement()])
        obj.run()
        assertTrue('Element #1', obj.data['favorite_receptionist']=='Pam')
        assertTrue('Element #2', obj.data['favorite_accountant']=='Kevin')

    def test_update_parent_data(self):
        class SampleElement(Element):

            def __call__(self, target: Page):
                target.update_parent_data(favorite_dog='Rufus')
        
        obj = Page(self.page1, self.page1, elements=[SampleElement()])
        parent = Page(self.page2, self.page2)

        obj.run(parent)

        assertTrue('Correct parent data', parent.data['favorite_dog']=='Rufus')

    def test_update_globals(self):
        class SampleElement(Element):

            def __call__(self, target: Page):
                target.update_globals(favorite_cat='Thor')
        
        mystate = State('NewState')
        obj = Page(self.page1, self.page1, elements=[SampleElement()])
        obj.run(state=mystate)
        assertTrue('Correct global data (access by State)', mystate.globals['favorite_cat']=='Thor')
        assertTrue('Correct global data (access by Page)', obj['favorite_cat']=='Thor')
        


    
        

if __name__=='__main__':
    st.session_state.clear()
    st.header('Stream Library Tests')
    test_state = TestState()
    test_state.run_tests()
    test_page = TestPage()
    test_page.run_tests()

    st.success('Tests finished')
        