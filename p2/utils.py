import os
import sys
import time
import math
import itertools

import statsmodels.api as sm


CSV_DELIMITER = ','
COINTEGRATION_CONST = 0.05
DATE_DELIMITER = '-'
DATA_RD_ATTR_LIST = ['Stkcd', 'Clsprc', 'Trddt', 'Trdsta', 'Dretnd']
VALUE_RD_ATTR_LIST = ['time1', 'neg_value', 'pos_value']
FILE_RD_SIZE = 16 * 1024 * 1024


def xprint(string=None):
    if string is None:
        if sys.version[0] < '3':
            print('')
        else:
            print()
    else:
        print(string)


'''sample date format: 2018-09-03'''
def cli_init_params():
    xprint(os.linesep + 'Collecting User Parameters:')

    def xinput(prompt=None):
        if sys.version[0] < '3':
            return raw_input(prompt)
        else:
            return input(prompt)

    '''format date parameters, for tb and T'''
    def date_format(raw_date):
        if ' ' in raw_date:
            delimiter = ' '
        elif '/' in raw_date:
            delimiter = '/'
        elif '-' in raw_date:
            delimiter = '-'
        elif '_' in raw_date:
            delimiter = '_'
        elif '.' in raw_date:
            delimiter = '.'
        else:
            return
        date = [x.strip() for x in raw_date.split(delimiter)]
        if len(date) == 3 and date[0].isdigit() and date[1].isdigit() and \
                date[1] < '13' and date[2].isdigit() and date[2] < '32':
            return DATE_DELIMITER.join(date)

    tb = date_format(xinput('Trade beginning date tb: ').strip())
    T = date_format(xinput('Trade ending date T: ').strip())
    n = xinput('Filtered stock pairs maximum n: ').strip()
    m = xinput('Estimate period m: ').strip()
    open_lim = xinput('Open limit parameter open_lim: ').strip()
    loss_lim = xinput('Loss limit parameter loss_lim: ').strip()
    g = xinput('Mean adjustment parameter g: ').strip()
    U = xinput('Sentiment adjustment parameter U: ').strip()
    M = xinput('Sentiment management parameter M: ').strip()

    xprint()

    def validate_params(tb, m, T, open_lim, loss_lim, g, U, n, M):
        if tb is None:
            xprint(os.linesep + 'Invalid date format tb!' + os.linesep)
            return False
        if T is None:
            xprint(os.linesep + 'Invalid date format T' + os.linesep)
            return False
        if tb >= T:
            xprint('Trade closing date T should be later than trade beginning date tb!')
            return False

        def decimal(val_str):
            idx = val_str.find('.')
            if idx >= 0:
                val_str = val_str[:idx] + val_str[idx+1:]
            return val_str.isdigit()

        return (decimal(m) and decimal(open_lim) and decimal(loss_lim)
                and decimal(g) and decimal(U) and decimal(n) and decimal(M))

    if validate_params(tb, m, T, open_lim, loss_lim, g, U, n, M):
        return {'tb':tb, 'm':int(float(m)), 'T':T, 'open_lim':float(open_lim), 'M':float(M), 
                'loss_lim': float(loss_lim), 'g':float(g), 'U':float(U), 'n':int(float(n))}
    else:
        xprint('Invalid numerical parameters taken!' + os.linesep)
        return cli_init_params()


'''**************************************************************************************'''

'''
before: None, read the whole csv sheet, default value
        False, read the part of the csv sheet when trddt is after tb
        True, read the part of the csv sheet when trddt is before tb

ftype:  'data', read dataFrame csv sheet, default value, return dataFrame
        'value', read sentiment csv sheet, return values
'''
def csv_open(fname, tb=None, before=None, delimiter=CSV_DELIMITER, ftype='data'):
    def parse_line(line, idx_list):
        params = [x.strip() for x in line.split(delimiter)]
        return [params[i] for i in idx_list]

    '''remove non ascii characters for first attr line'''
    rmNonAscii = lambda s: ''.join(i for i in s if ord(i) < 128)

    if '.csv' != fname[-4:]:
        raise IOError('Only csv file is accepted')

    try:
        if ftype == 'data' and tb is not None:
            '''initialize dataFrame structure'''
            dataFrame = {'trddt_idx':[],}
            with open(fname, mode='r') as fh:
                dataFrame['attr'] = [x.strip() for x in rmNonAscii(fh.readline()).split(delimiter)]
                '''attr_idx_list corresponds to DATA_RD_ATTR_LIST sequence'''
                attr_idx_list = [dataFrame['attr'].index(x) for x in DATA_RD_ATTR_LIST]
                for line in fh:
                    params = parse_line(line, attr_idx_list)
                    trddt = params[2]
                    stkcd = params[0]
                    clsprc = float(params[1])
                    trdsta = params[3]
                    dretnd = float(params[4])

                    '''set conditions to determine if valid line or drop it'''
                    if trdsta != '1': continue
                    if clsprc == 0: continue
                    if DATE_DELIMITER not in trddt:
                        raise RuntimeError('inconsistent date format read from csv sheet: %s' %(trddt))
                    if before is True and trddt > tb: continue
                    if before is False and trddt < tb: continue

                    if trddt not in dataFrame['trddt_idx']:
                        dataFrame['trddt_idx'].append(trddt)
                    '''for a single stock, trddt is also its data index'''
                    if dataFrame.get(stkcd) is None:
                        dataFrame[stkcd] = [(trddt, clsprc, dretnd)]
                    else:
                        dataFrame[stkcd].append((trddt, clsprc, dretnd))

                '''sort the trddt index of dataFrame'''
                dataFrame['trddt_idx'] = sorted(dataFrame['trddt_idx'])
                '''pop the stock key not meeting requirements from dataFrame'''
                stkcds = [x for x in dataFrame.keys() if x != 'attr' and x != 'trddt_idx']
                for stk in stkcds:
                    trddt_seq = [x[0] for x in dataFrame[stk]]
                    distinction = len(set(trddt_seq))
                    if distinction < len(trddt_seq):
                        dataFrame.pop(stk)
                        continue
                    if distinction != len(dataFrame['trddt_idx']):
                        dataFrame.pop(stk)
                        continue

                    '''Sorting clsprc for each stock, make it corresponds to the trddt index sequence'''
                    sort_seq = sorted(dataFrame[stk], key=lambda x: x[0])
                    sort_trddt_idx = [x[0] for x in sort_seq]
                    if sort_trddt_idx != dataFrame['trddt_idx']:
                        raise RuntimeError('Trade date indexs not match, impossible!!!!!')
                    dataFrame[stk] = [(x[1], x[2]) for x in sort_seq]
            return dataFrame if len(dataFrame['trddt_idx']) > 0 else None

        elif ftype == 'value':
            '''initialize value structure'''
            values = {}
            with open(fname, mode='r') as fh:
                values['attr'] = [x.strip() for x in rmNonAscii(fh.readline()).split(delimiter)]
                '''attr_idx_list corresponds to VALUE_RD_ATTR_LIST sequence'''
                attr_idx_list = [values['attr'].index(x) for x in VALUE_RD_ATTR_LIST]
                for line in fh:
                    params = parse_line(line, attr_idx_list)
                    trddt = params[0]
                    if before is True and trddt > tb: continue
                    if before is False and trddt < tb: continue
                    pos_value = params[2]
                    neg_value = params[1]
                    values[trddt] = (float(pos_value), float(neg_value))
            return values if len(values.keys()) > 1 else None

        else:
            raise ValueError('Unknown csv file reading type specified, data or value')

    except IOError as err:
        raise err


'''
dataFrame is a orgnized dict

{
    'attr'  : ['Stkcd', 'Trddt', 'Clsprc', 'Long', 'Hold', 'Dretnd'],
    'trddt_idx' : [d1, d2..],        //date index must corresponds to trade_price of each stkID one by one.
                                     //dates read from input .csv spreadsheet, which should be a completed reference.
    '<stkcd>' : {
                    'Hold' : [hold1, hold2, hold3 ..],
                    'Clsprc' : [price1, price2, ...],  //None if no price on someday
                    'Long'  : [long1, long2, long3 ...],
                    'Dretnd' : [dretnd1, dretnd2, dretnd3....],
                }
}

ftype:
data :  dumping dataFrame csv sheet file
parameter:   dumping param(bval, pval, distance) csv sheet file
'''
def csv_dump(data, delimiter=CSV_DELIMITER, ftype='result'):
    cwd = os.getcwd()
    res_dir = cwd + os.path.sep + 'Result'
    if not os.path.isdir(res_dir):
        os.mkdir(res_dir)

    now = time.localtime()
    if ftype == 'result':
        fname = 'Result' + '_' + str(now.tm_mon) + '_' + str(now.tm_mday) + '_' + str(now.tm_hour) + '_' + str(now.tm_min) + '.csv'
    elif ftype == 'parameter':
        fname = 'Param' + '_' + str(now.tm_mon) + '_' + str(now.tm_mday) + '_' + str(now.tm_hour) + '_' + str(now.tm_min) + '.csv'
    else:
        raise ValueError('Unknown csv file dumping type specified, result or parameter')

    log = res_dir + os.path.sep + fname

    if ftype == 'result':
        with open(log, mode='w') as logger:
            stkcds = [x for x in data.keys() if x != 'attr' and x != 'trddt_idx']
            if not len(stkcds):
                xprint('Warning: empty csv sheet to be dumped!')
            headline = delimiter.join(data['attr']) + os.linesep
            logger.write(headline)
            for stk in stkcds:
                if len(data[stk]['Clsprc']) != len(data['trddt_idx']):
                    raise RuntimeError('trddt idx doesn\'t correspond to stock(%s) close price sequence' %(stk))
                for idx in range(len(data['trddt_idx'])):
                    try:
                        line = stk + delimiter + data['trddt_idx'][idx] + delimiter + str(data[stk]['Clsprc'][idx]) \
                            + delimiter + str(data[stk]['Long'][idx]) + delimiter + str(data[stk]['Hold'][idx]) + \
                            delimiter + str(data[stk]['Dretnd'][idx]) + os.linesep
                    except IndexError:
                        line = stk + delimiter + data['trddt_idx'][idx] + delimiter + str(data[stk]['Clsprc'][idx]) \
                            + delimiter + '0' + delimiter + '0' + delimiter + str(data[stk]['Dretnd'][idx]) + os.linesep
                    logger.write(line)
    else:
        with open(log, mode='w') as logger:
            headline = delimiter.join(['Stk_pair', 'bval', 'pval', 'distance']) + os.linesep
            logger.write(headline)
            if not len(data):
                xprint('Warning: empty csv sheet to be dumped!')

            for pair in data:
                bval = str(pair[2]['bval']) if 'bval' in pair[2] else 'NULL'
                pval = str(pair[2]['pval']) if 'pval' in pair[2] else 'NULL'
                distance = str(pair[2]['distance']) if 'distance' in pair[2] else 'NULL'
                line = pair[0] + '/' + pair[1] + delimiter + bval + delimiter +\
                        pval + delimiter + distance + os.linesep
                logger.write(line)

    xprint(os.linesep + '%s file dump OK! file: %s' %(ftype.upper(), log))


'''*************************************************************************************************************************************'''


def Euclidean_Dist(X, Y):
    if len(X) != len(Y) or not len(X) or not len(Y):
        err = ValueError('invalid or uneven dimensions of X or Y')
        raise err

    idx = 0
    dimension = len(X)
    val = 0.0

    while idx < dimension:
        val += math.pow((X[idx] - Y[idx]), 2)
        idx += 1

    return math.sqrt(val)


def Mean(X):
    num = len(X)
    if num == 0:
        err = ValueError('Null list not accepted')
        raise err

    val = 0.0
    for x in X:
        val += x

    return val/num


def Standard_Deviation(X):
    num = len(X)
    avg = Mean(X)

    val = 0.0

    for x in X:
        val += math.pow((x - avg), 2)

    return math.sqrt(val/num)


def Data_Normalization(X):
    num = len(X)
    avg = Mean(X)
    sd = Standard_Deviation(X)

    normalization = lambda x: (x - avg)/sd

    return [normalization(x) for x in X]


def Stats_Cointegration(X, Y):
    if not len(X) or not len(Y) or len(X) != len(Y):
        err = ValueError('Null or uneven dimensions list not accepted')
        raise err

    return sm.tsa.stattools.coint(X, Y)[1]


def cointegration_pair(X, Y):
    pval = Stats_Cointegration(X, Y)

    return pval if pval < COINTEGRATION_CONST else None


def Liner_Regression(X, Y):
    if not len(X) or not len(Y) or len(X) != len(Y):
        err = ValueError('Null or uneven dimensions list not accepted')
        raise err

    XX = sm.add_constant(X)
    rs = (sm.OLS(Y, XX)).fit()
    '''b'''
    return rs.params[1]


def Spread_Xt(X, Y, b):
    if not len(X) or not len(Y) or len(X) != len(Y):
        err = ValueError('Null or uneven dimensions list not accepted')
        raise err

    spread = lambda x, y: y - b*x

    return [spread(X[i], Y[i]) for i in range(len(X))]


'''get all combinations of stock codes'''
def get_stkcd_pairs(dataFrame):
    stkcds = [x for x in dataFrame.keys() if x != 'attr' and x != 'trddt_idx']
    return list(itertools.combinations(stkcds, 2))
