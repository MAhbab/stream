from unittest import result
import pandas as pd
import numpy as np
import streamlit as st
from typing import Dict, Union
from io import BytesIO
from scipy.stats import probplot
import statsmodels.api as sm
import matplotlib.pyplot as plt
import pypika
import pyodbc

from .core import Page

SERVER = "tcp:shift-{}.database.windows.net,1433" #TODO: check this follows security standards
JOINS = [x.name for x in pypika.JoinType]
MAGNA_SITE_ID = 'F88A472C-27B5-4114-B4FE-68B4D98BF60E'
MAGNA_JOB_TITLE_ID = '631AB19C-ED7A-4372-A612-7C14469A1308'

class DataBase:

    def conn(self, uid, pwd, server='prod', database='Core') -> pyodbc.Connection:
        conn_str = connect(uid, pwd, server, database)
        return pyodbc.connect(conn_str)

    def display_query_text(self, q, container=None):
        container.text(str(q))

    def query_from_text(self, container=None):
        query_text = container.text_area('Input query here')
        return query_text

class PandasPage(Page):

    DEFAULT_NAME_COUNTER = 1

    @property
    def datasets(self) -> Dict[str, pd.DataFrame]:
        if 'datasets' not in self.data:
            self.data['datasets'] = {}
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

        key = container.selectbox('Select Dataset', self.datasets.keys(), key='pandas_selectbox_{}'.format(self.identifier))
        return self.datasets[key]

    def multi_select(self, container) -> Dict[str, pd.DataFrame]:
        
        keys = container.multiselect('Select Datasets', self.datasets.keys(), key='pandas_multi_select'.format(self.identifier))
        return {k: self.datasets[k] for k in keys}

    def from_clipboard(self, container, name=None):
        if name is None:
            name = 'Dataset{}'.format(self.DEFAULT_NAME_COUNTER)
            self.DEFAULT_NAME_COUNTER += 1
        
        container.button(
            label='Upload from Clipboard',
            on_click=self.datasets.update,
            kwargs={name: pd.read_clipboard()},
            key='pandas_from_clipboard_{}_{}'.format(self.identifier, self.generate_random_key())
        )

    def to_clipboard(self, df: Union[pd.DataFrame, pd.Series], container):
        container.button(
            label='Copy to Clipboard',
            on_click=df.to_clipboard,
            key='pandas_to_clipboard_{}_{}'.format(self.identifier, self.generate_random_key())
        )

    def from_excel(self, container, sheet_name=None):
        file = container.file_uploader(
            label='Upload Excel File',
            type=['xlsx'],
            key='pandas_from_excel_{}_{}'.format(self.identifier, self.generate_random_key())
        )
        if file is not None:
            if sheet_name is None:
                name = 'Dataset{}'.format(self.DEFAULT_NAME_COUNTER)
                self.DEFAULT_NAME_COUNTER += 1
            else:
                name = sheet_name

            df = pd.read_excel(file, sheet_name)
            self.datasets[name] = df

    def to_excel(self, df: Union[pd.DataFrame, pd.Series], container, filename=None):
        if filename is None:
            filename = 'mydata.xlsx'

        output = BytesIO()
        writer = pd.ExcelWriter(output, 'xlsxwriter')
        df.to_excel(writer, 'Sheet1')
        writer.save()
        data = output.getvalue()
        
        container.download_button('Download as Excel', data, filename)


class RegressionPage(Page):

    '''
    Implements front end elements for OLS and Logit models
    '''

    @property
    def results(self):
        if 'regression_results' not in self.data:
            self.data['regression_results'] = {}
        return self.data['regression_results']

    def fit(self, model, name, **fit_kwargs):
        self.regresssion_results[name] = model.fit(**fit_kwargs)

    def variable_selection_input(self, data: pd.DataFrame, container):
        endog = container.selectbox('Endogenous Variable', data.columns)
        exog = container.multiselect('Exogenous Variable(s)', data.columns)
        return endog, exog


class OLSPage(RegressionPage):

    #TODO: refactor plotting code to another base page or a plotting element

    MEDIUM_FONT = 14
    LARGE_FONT = 16

    def residual_plot(self, result_name, container=None):
        res = self.results[result_name]

        resid = res.resid
        fig, ax = plt.subplots()

        ax.scatter(range(len(resid)), resid)
        ax.set_xlabel('Observation', fontsize=self.MEDIUM_FONT)
        ax.set_ylabel('Residual', fontsize=self.MEDIUM_FONT)
        ax.set_title('{} Regression Residuals', fontsize=self.LARGE_FONT)
        
        if container is None:
            plt.show(fig)
        else:
            container.pyplot(fig)

    def fitted_vs_obs_plot(self, result_name, container=None):
        res = self.results[result_name]
        fitted = res.fittedvalues
        obs = res.model.endog
        
        fig, ax = plt.subplots()
        ax.scatter(fitted.values, obs)
        ax.set_xlabel('Fitted', fontsize=self.MEDIUM_FONT)
        ax.set_ylabel('Observed', fontsize=self.MEDIUM_FONT)
        ax.set_title('{} Observed vs. Fitted Values', fontsize=self.LARGE_FONT)
        
        if container is None:
            plt.show(fig)
        else:
            container.pyplot(fig)

    def fitted_vs_resid_plot(self, result_name, container=None):
        res = self.results[result_name]

        fitted = res.fittedvalues
        resid = res.resid

        fig, ax = plt.subplots()
        ax.scatter(fitted.values, resid.values)
        ax.set_xlabel('Fitted', fontsize=self.MEDIUM_FONT)
        ax.set_ylabel('Residual', fontsize=self.MEDIUM_FONT)
        ax.set_title('{} Residuals vs. Fitted Values', fontsize=self.LARGE_FONT)

        if container is None:
            plt.show(fig)
        else:
            container.pyplot(fig)

    def resid_qq_plot(self, result_name, container=None):
        res = self.results[result_name]
        resid = res.resid

        line = np.linspace(-3,3,100)

        osm, osr = probplot(resid, fit=False)

        fig, ax = plt.subplots()
        ax.scatter(osm, osr)
        ax.plot(line, line, c='r')
        ax.set_xlabel('Theoretical Quantile', fontsize=self.MEDIUM_FONT)
        ax.set_ylabel('Residual', fontsize=self.MEDIUM_FONT)
        ax.set_title('{} Residual Probability Plot', fontsize=self.LARGE_FONT)

        if container is None:
            plt.show(fig)
        else:
            container.pyplot(fig)

    def summary(self, result_name, container):
        res = self.results[result_name]

        container.write(res.summary())

    

def connect(uid, pwd, server, database='Core'):
    driver = "{ODBC Driver 17 for SQL Server}"
    conn_str = 'DRIVER={};SERVER={};DATABASE={};UID={};PWD={}'.format(driver, SERVER.format(server), database, uid, pwd)
    return conn_str

    

    



