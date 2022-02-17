'''Simple example to illustrate using the backtester'''
import pandas as pd
import bt 
import numpy as np 
import datetime as dt
from backtester import Backtester


#make sample data
def make_data(cols=5, rows=500):
    returns = np.random.normal(scale=0.01,size=(rows, cols))
    prices = pd.DataFrame(returns)+1
    prices.iloc[0, :] = 100 
    prices = prices.cumprod()
    dates = pd.date_range(start=dt.datetime(2017,10,1), periods=rows)
    prices.index = dates
    prices.columns = [str(x) for x in prices.columns]
    return prices 

#make sample strategies
def make_strat(wt_schm: str):
    if wt_schm == 'inv_vol':
        wt = bt.algos.WeighInvVol()
    elif wt_schm == 'mean_var':
        wt = bt.algos.WeighMeanVar()
    elif wt_schm == 'erc':
        wt = bt.algos.WeighERC()
    else:
        wt = bt.algos.WeighEqually()

    algos = [
        bt.algos.RunAfterDays(20),
        bt.algos.RunDaily(),
        bt.algos.SelectAll(),
        wt,
        bt.algos.Rebalance()
    ]

    strat = bt.Strategy(wt_schm, algos)
    return strat 

#run backtests
def run_bks():
    bks = []
    data = make_data(rows=300)
    data.columns = [
        'YEET',
        'HAHA',
        'REKT',
        'YOLO',
        'DAWG'
    ]
    for wtschm in ['equal', 'inv_vol']:
        strat = make_strat(wtschm)
        bk = bt.Backtest(strat, data)
        bk.run()
        bks.append(bk)
    return bks

mybks = run_bks()

#pass list of backtests as argument and run
mybacktester = Backtester(backtests=mybks)
mybacktester.run()
        


