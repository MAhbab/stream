from core import Session, Page, Element, DefaultStartPage
import streamlit as st
import numpy as np
from treelib import Tree

def assertTrue(test_name, expr):
    if expr:
        st.success("'{}' ran successfully".format(test_name))
    else:
        st.error("'{}' ran and failed".format(test_name))

def assertEqual(test_name, expected_val, actual_val):
    expr = expected_val == actual_val
    if  expr:
        st.success("'{}' ran successfully".format(test_name))
    else:
        st.error("'{}' ran and failed (expected value: {}, actual value: {}".format(test_name, expected_val, actual_val))

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

class TestSession(TestCase):

    name = 'TestSession'

    def __init__(self) -> None:
        pass
    
    def test_init(self):
        new_Session = Session(self.name)
        assertTrue('Initialize Session', self.name in st.session_state)
        assertEqual('Active page is None', 'root', new_Session._active_page)
        assertTrue('No global variables present', not new_Session._globals)

    def test_update_active_page(self):
        obj = Session(self.name)
        new_page = Page('new_page', 'new_page')
        other_page = Page('other_page', 'other_page')
        obj.add_node(new_page)
        obj.add_node(other_page)
        
        assertEqual('Default page initialized', DefaultStartPage().identifier, st.session_state[self.name]['active_page'])
        obj.update_active_page(new_page.identifier)
        assertEqual('Page changed and updated', 'new_page', obj.active_page.identifier)
        obj.update_active_page(other_page.identifier)
        assertEqual('Second page change and update', 'other_page', obj.active_page.identifier)


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
        Session_obj = Session('NewSession')
        Session_obj.update_globals(True, **{'pi': 3.14, 'num_oceans': 3})
        obj.run(parent, Session_obj)
        assertTrue('Correct Variable Value #1', obj['num_continents']==7)
        assertTrue('Correct Variable Value #2', obj['num_oceans']==parent['num_oceans'])
        assertTrue('Correct Variable Value #3', obj['num_continents']!=parent['num_continents'])
        assertTrue('Correct Variable Value #3', obj['pi']==Session_obj.globals['pi'])
        st.write(Session_obj.globals['pi'])
        st.write(obj._Session.globals['pi'])

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
        
        mySession = Session('NewSession')
        obj = Page(self.page1, self.page1, elements=[SampleElement()])
        obj.run(state=mystate)
        assertTrue('Correct global data (access by Session)', mySession.globals['favorite_cat']=='Thor')
        assertTrue('Correct global data (access by Page)', obj['favorite_cat']=='Thor')
        


    
        

if __name__=='__main__':
    st.session_state.clear()
    st.header('Stream Library Tests')
    test_Session = TestSession()
    test_Session.run_tests()
    test_page = TestPage()
    test_page.run_tests()

    st.success('Tests finished')
        