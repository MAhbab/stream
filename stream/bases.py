import pandas as pd
import streamlit as st
from typing import Dict, Union

from .core import Page

class PandasPage(Page):

    DEFAULT_NAME_COUNTER = 1
    QUERY_CACHE = {}

    def setup(self):
        super().setup()
        self.data['datasets'] = {}

    @property
    def datasets(self) -> Dict[str, pd.DataFrame]:
        return self.data['datasets']

    def view(self, df: Union[pd.DataFrame, pd.Series, str], container, preview=False) -> None:
        if isinstance(df, str):
            df = self.datasets[df]

        if preview:
            df = df.head(10)

        container.dataframe(df)

    def describe(self, df: Union[pd.DataFrame, str], container) -> None:
        if isinstance(df, str):
            df = self.datasets[df]

        df_description = df.describe()
        self.view(df_description, container)

    def select(self, container) -> Union[pd.DataFrame, pd.Series]:

        key = container.selectbox('Select Dataset', self.datasets.keys())
        return self.datasets[key]

    def multi_select(self, container) -> Dict[str, pd.DataFrame]:
        
        keys = container.multiselect('Select Datasets', self.datasets.keys())
        return {k: self.datasets[k] for k in keys}

    def from_clipboard(self, container, name=None):
        if name is None:
            name = 'Dataset{}'.format(self.DEFAULT_NAME_COUNTER)
            self.DEFAULT_NAME_COUNTER += 1
        
        container.button(
            label='Upload from Clipboard',
            on_click=self.datasets.update,
            kwargs={name: pd.read_clipboard()}
        )

    def to_clipboard(self, df: Union[pd.DataFrame, pd.Series], container):
        container.button(
            label='Copy to Clipboard',
            on_click=df.to_clipboard
        )

    def from_excel(self, container, sheet_name=None):
        file = container.file_uploader(
            label='Upload Excel File',
            type=['xlsx']
        )
        if file is not None:
            if sheet_name is None:
                name = 'Dataset{}'.format(self.DEFAULT_NAME_COUNTER)
                self.DEFAULT_NAME_COUNTER += 1
            else:
                name = sheet_name

            df = pd.read_excel(file, sheet_name)
            self.datasets[name] = df

    def to_excel(self, df: Union[pd.DataFrame, pd.Series], container):
        st.download_button



