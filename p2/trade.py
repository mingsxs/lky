import os
import sys
import time


import utils
import strategy


SLEEP_DURATION = 0.1

'''
dataFrame is a orgnized dict

{
    'attr'  : ['Stkcd', 'Trddt', 'Clsprc', 'Long', 'Hold'],
    'trddt_idx' : [d1, d2..],        //date index must corresponds to trade_price of each stkID one by one.
                                     //dates read from input .csv spreadsheet, which should be a completed reference.
    '<stkcd>' : {
                    'Hold' : [hold1, hold2, hold3 ..],
                    'Clsprc' : [price1, price2, ...],  //None if no price on someday
                    'Long'  : [long1, long2, long3 ...]
                }
}
'''
def trade(tb, m, open_lim, loss_lim, g, U, dataFrame, values, stk_pairs, M):

    def normal_trade(STD, EX, Xt, pair):
        open_val = open_lim*STD
        loss_val = loss_lim*STD
        g_val = g*STD
        diff = Xt[0] - EX
        X_last_hold = resDataFrame[pair[0]]['Hold'][-1] if resDataFrame[pair[0]]['Hold'] else 0
        Y_last_hold = resDataFrame[pair[1]]['Hold'][-1] if resDataFrame[pair[1]]['Hold'] else 0
        #print 'pair: %s/%s' %(pair[0], pair[1])
        #print 'diff: %f' %(diff)
        #print 'open_val: %f' %(open_val)
        #print 'loss_val: %f' %(loss_val)
        #print 'g_val: %f' %(g_val)

        if open_val < diff < loss_val:
            '''sell stock P1, aka Y, buy P2, aka X'''
            resDataFrame[pair[1]]['Hold'].append(Y_last_hold - 1.0)
            resDataFrame[pair[1]]['Long'].append(-1.0)
            resDataFrame[pair[0]]['Hold'].append(X_last_hold + pair[2]['bval'])
            resDataFrame[pair[0]]['Long'].append(pair[2]['bval'])

        elif (-loss_val) < diff < (-open_val):
            '''sell stock P2, aka X, buy P1, aka Y'''
            resDataFrame[pair[1]]['Hold'].append(Y_last_hold + 1.0)
            resDataFrame[pair[1]]['Long'].append(1.0)
            resDataFrame[pair[0]]['Hold'].append(X_last_hold - pair[2]['bval'])
            resDataFrame[pair[0]]['Long'].append(-pair[2]['bval'])

        elif abs(diff) > loss_val or abs(diff) < g_val:
            '''sell stocks in pair'''
            resDataFrame[pair[0]]['Long'].append(-X_last_hold)
            resDataFrame[pair[0]]['Hold'].append(0)
            resDataFrame[pair[1]]['Long'].append(-Y_last_hold)
            resDataFrame[pair[1]]['Hold'].append(0)
            utils.xprint(os.linesep + 'Remove pair: %s/%s' %(pair[0], pair[1]))
            utils.xprint('Current STD: %f, Xt: %f, EX: %f, diff: %f, loss_val: %f, g_val: %f' 
                         %(STD, EX, Xt[0], diff, loss_val, g_val) + os.linesep)
            stk_pairs.remove(pair)

        #print 'pair0 Long, Hold:', resDataFrame[pair[0]]['Long'], resDataFrame[pair[0]]['Hold']
        #print 'pair1 Long, Hold:', resDataFrame[pair[1]]['Long'], resDataFrame[pair[1]]['Hold']

    open_lim = open_lim
    loss_lim = loss_lim

    try:
        start_pos = pos = dataFrame['trddt_idx'].index(tb)
    except ValueError:
        raise ValueError('Invalid trade date: %s!' %(tb))
    end_pos = len(dataFrame['trddt_idx']) - 1
    #print 'start pos: %d, tb: %s' %(pos, tb)
    resDataFrame = {
        'attr' : ['Stkcd', 'Trddt', 'Clsprc', 'Long', 'Hold', 'Dretnd'],
        'trddt_idx' : dataFrame['trddt_idx'][start_pos:],
        }

    #get_pos_val = lambda t: values[t][0]
    #get_neg_val = lambda t: values[t][1]

    stkcds = [pair[0] for pair in stk_pairs] + [pair[1] for pair in stk_pairs]

    for stk in stkcds:
        resDataFrame[stk] = {'Clsprc':None, 'Hold':None, 'Long':None}
        resDataFrame[stk]['Clsprc'] = [x[0] for x in dataFrame[stk][start_pos:]]
        resDataFrame[stk]['Dretnd'] = [x[1] for x in dataFrame[stk][start_pos:]]
        resDataFrame[stk]['Hold'] = []
        resDataFrame[stk]['Long'] = []

    utils.xprint()

    while pos <= end_pos:
        if pos == end_pos:
            '''last trading date'''
            for pair in stk_pairs:
                if resDataFrame[pair[0]]['Hold']:
                    resDataFrame[pair[0]]['Long'].append(-resDataFrame[pair[0]]['Hold'][-1])
                    resDataFrame[pair[0]]['Hold'].append(0)
                if resDataFrame[pair[1]]['Hold']:
                    resDataFrame[pair[1]]['Long'].append(-resDataFrame[pair[1]]['Hold'][-1])
                    resDataFrame[pair[1]]['Hold'].append(0)
                utils.xprint(os.linesep + 'Remove pair: %s/%s' %(pair[0], pair[1]) + os.linesep)
                stk_pairs.remove(pair)

        else:
            '''Not last trading day'''
            if (pos - start_pos)%m == 0 and pos != start_pos:
                '''Updating date'''
                for pair in stk_pairs:
                    X = [x[0] for x in dataFrame[pair[0]]][:pos+1]
                    Y = [x[0] for x in dataFrame[pair[1]]][:pos+1]
                    #print 'result:',resDataFrame
                    #print 'pairs:', pair[0], pair[1]
                    #print 'X:', X
                    #print 'Y:', Y
                    if utils.cointegration_pair(X, Y) is not None:
                        pair[2]['bval'] = utils.Liner_Regression(X, Y)
                        Xt = utils.Spread_Xt(X, Y, pair[2]['bval'])
                        pair[2]['STD'] = utils.Standard_Deviation(Xt)
                        pair[2]['EX'] = utils.Mean(Xt)
                        Xt = utils.Spread_Xt([X[-1]], [Y[-1]], pair[2]['bval'])
                        normal_trade(pair[2]['STD'], pair[2]['EX'], Xt, pair)
                    else:
                        if resDataFrame[pair[0]]['Hold']:
                            resDataFrame[pair[0]]['Long'].append(0 - resDataFrame[pair[0]]['Hold'][-1])
                            resDataFrame[pair[0]]['Hold'].append(0)
                        if resDataFrame[pair[1]]['Hold']:
                            resDataFrame[pair[1]]['Long'].append(0 - resDataFrame[pair[1]]['Hold'][-1])
                            resDataFrame[pair[1]]['Hold'].append(0)
                        utils.xprint(os.linesep + 'Remove pair: %s/%s' %(pair[0], pair[1]) + os.linesep)
                        stk_pairs.remove(pair)

            else:
                '''normal trading date'''
                for pair in stk_pairs:
                    idx = pos - start_pos
                    X = [[x[0] for x in dataFrame[pair[0]]][idx]]
                    Y = [[x[0] for x in dataFrame[pair[1]]][idx]]
                    Xt = utils.Spread_Xt(X, Y, pair[2]['bval'])
                    EX = pair[2]['EX']
                    STD= pair[2]['STD']
                    normal_trade(STD, EX, Xt, pair)

        '''Update sentiment value'''
        trddt = dataFrame['trddt_idx'][pos]
        #pos_val = get_pos_val(trddt)
        #neg_val = get_neg_val(trddt)
        #if pos_val/neg_val > M: loss_lim *= U
        #elif pos_val/neg_val < M: loss_lim /= U

        utils.xprint('current pos: %d; date: %s; loss_lim: %f' %(pos, dataFrame['trddt_idx'][pos], loss_lim))

        '''Updating date'''
        pos += 1
        #time.sleep(SLEEP_DURATION)

    if stk_pairs:
        raise RuntimeError('For now, no item should be left in stk_pair!!!')

    return resDataFrame









