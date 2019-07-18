import os

import utils
import strategy
import trade

'''Global input file path, in relative path description'''
DATA_CSV_FILE = '.' + os.path.sep + 'Resource' + os.path.sep + 'TRD_Dalyr.csv'
VALUE_CSV_FILE = '.' + os.path.sep + 'Resource' + os.path.sep + 'value.csv'

'''Global test running parameters'''
tb = m = n = T = open_lim = loss_lim = g = U = M = None

'''Global dataFrame'''
dataFrame = None
values = None

'''Global self defined filter functions sequence'''
FILTER_SEQ = ['distance']

'''Global result dataFrame'''
resDataFrame = None


def pre_run():
    global tb, m, n, T, open_lim, loss_lim, g, U, M, dataFrame, values
    params = utils.cli_init_params()
    tb = params['tb']
    m = params['m']
    n = params['n']
    T = params['T']
    open_lim = params['open_lim']
    loss_lim = params['loss_lim']
    g = params['g']
    U = params['U']
    M = params['M']

    #tb = '2018-08-20'
    #M = 2
    #m = 3
    #n = 5
    #T = '2019-02-20'
    #open_lim = 1
    #loss_lim = 3
    #g = 0.2
    #U = 1

    dataFrame = utils.csv_open(DATA_CSV_FILE, tb=T, before=True, ftype='data')
    values = utils.csv_open(VALUE_CSV_FILE, tb=T, before=True, ftype='value')

    utils.xprint(os.linesep + 'Parameters initialized successfully!')


def run():
    stk_pairs = strategy.filter_pairs(dataFrame, sequence=FILTER_SEQ, number=n)
    global resDataFrame
    resDataFrame = trade.trade(tb, m, open_lim, loss_lim, g, U, dataFrame, values, stk_pairs, M)

    utils.xprint(os.linesep + 'Trade processed successfully!')


def post_run():
    utils.csv_dump(resDataFrame, ftype='result')

    utils.xprint(os.linesep + 'Done!')



'''********************************************************************************************************'''

if __name__ == '__main__':
    pre_run()
    run()
    post_run()
