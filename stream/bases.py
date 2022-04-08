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
import bt

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

class Pandas(Page):

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

    def select(self, container, key=None, label='Select Dataset') -> Union[pd.DataFrame, pd.Series]:

        name = container.selectbox(label, self.datasets.keys(), key=key)
        return self.datasets[name]

    def multi_select(self, container, label='Select Datasets', key=None) -> Dict[str, pd.DataFrame]:
        
        keys = container.multiselect(label, self.datasets.keys(), label)
        return {k: self.datasets[k] for k in keys}

    def from_clipboard(self, container, name=None, label='Upload from Clipboard', key=None):
        if name is None:
            name = 'Dataset{}'.format(self.DEFAULT_NAME_COUNTER)
            self.DEFAULT_NAME_COUNTER += 1
        
        return container.button(
            label=label,
            on_click=self.datasets.update,
            kwargs={name: pd.read_clipboard()},
            key=key
        )

    def to_clipboard(self, df: Union[pd.DataFrame, pd.Series], container, label='Copy to Clipboard', key=None):
        return container.button(
            label='Copy to Clipboard',
            on_click=df.to_clipboard,
            key=key
        )

    def from_excel(self, container, label='Upload Excel', key=None):
        return container.file_uploader(
            label=label,
            type=['xlsx'],
            key=key
        )

    def to_excel(self, df: Union[pd.DataFrame, pd.Series], container, filename=None, label='Download Excel', key=None):
        if filename is None:
            filename = 'mydata.xlsx'

        output = BytesIO()
        writer = pd.ExcelWriter(output, 'xlsxwriter')
        df.to_excel(writer, 'Sheet1')
        writer.save()
        data = output.getvalue()
        
        return st.download_button(label, data, filename, key=key)


class StatsModels(Page):

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


class Bt(Page):

    @property
    def backtests(self):
        if 'backtests' not in self.data:
            self.data['backtests'] = {}
        return self.data['backtests']

    @property
    def strats(self):
        if 'strategies' not in self.data:
            self.data['strategies'] = {}
        return self.data['strategies']

    @property
    def algostacks(self):
        if 'algo_stacks' not in self.data:
            self.data['algo_stacks'] = {}
        return self.data

    def run(self, *bkts):
        for b in bkts:
            b.run()
            self.backtests[b.name] = b

    def select_backtest(self, container, label='Select Backtest', key=None):
        pass

    def multi_select_backtest(self, container, label='Select Backtests', key=None):
        pass

    def select_strategy(self, container, label='Select Strategy', key=None):
        pass

    def multi_select_strategy(self, container, label='Select Strategies', key=None):
        pass



class OLSPage(StatsModels):

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

    

    



