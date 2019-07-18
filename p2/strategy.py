import os
import time
import statsmodels.api as sm

import utils



'''distinct flag for stk_pairs'''
DISTINCT = False

'''acf and pacf constants'''
ACF_CONST = 0.5
PACF_CONST1 = 0.5
PACF_CONST2 = 0.1
SLEEP_DURATION = 1



'''this stk_pairs must be a sorted list!!'''
def get_distinct_stk_pairs(stk_pairs):
    '''remove the pairs which will match with others'''
    pops = []
    container = []

    for pair in stk_pairs:
        if pair[0] in container or pair[1] in container:
            pops.append(pair)
        else:
            container.extend([pair[0], pair[1]])

    for pair in pops:
        stk_pairs.remove(pair)

    return stk_pairs


'''
stk_pairs:
[(X, Y,{'pval' : pval, 'b' : b, 'distance' : distance})]
'''
def get_cointegration_pairs(stk_pairs, dataFrame):
    '''Cointegration Process'''
    get_clsprc = lambda y: [x[0] for x in dataFrame[pair[y]]]
    stk_pval_groups = []
    for pair in stk_pairs:
        pval = utils.cointegration_pair(get_clsprc(0), get_clsprc(1))
        if pval is not None:
            pair[2]['pval'] = pval
            stk_pval_groups.append((pair[0], pair[1], pair[2]))

    '''sort the stk_pval_groups list of (X, Y, pval) tuples'''
    stk_pval_groups = sorted(stk_pval_groups, key=lambda x: x[2]['pval'])

    global DISTINCT
    if DISTINCT is False:
        stk_pval_groups = get_distinct_stk_pairs(stk_pval_groups)
        DISTINCT = True

    return stk_pval_groups


def get_AR1_pairs(stk_pairs, dataFrame):
    '''AR1 Process'''
    get_clsprc = lambda y: [x[0] for x in dataFrame[pair[y]]]
    ssa_group = []
    for pair in stk_pairs:
        Xt = utils.Spread_Xt(get_clsprc(0), get_clsprc(1), pair[2]['bval'])
        acf = sm.tsa.stattools.acf(Xt)
        pacf = sm.tsa.stattools.pacf(Xt)

        '''SSA Approach conditions'''
        if pacf[1] > PACF_CONST1 and max(pacf[2:10]) < PACF_CONST2 \
                and acf[1] > ACF_CONST and acf[1] > acf[2]:
            ssa_group.append((pair[0], pair[1], pair[2]))

    return ssa_group


def get_distance_pairs(stk_pairs, dataFrame):
    '''Distance Process'''
    get_clsprc = lambda y: [x[0] for x in dataFrame[pair[y]]]
    distance_group = []
    for pair in stk_pairs:
            X = utils.Data_Normalization(get_clsprc(0))
            Y = utils.Data_Normalization(get_clsprc(1))
            dist = utils.Euclidean_Dist(X, Y)
            pair[2]['distance'] = dist
            distance_group.append((pair[0], pair[1], pair[2]))

    '''sort the distance_group according to dist value of each group'''
    distance_group = sorted(distance_group, key=lambda x:x[2]['distance'])

    global DISTINCT
    if DISTINCT is False:
        distance_group = get_distinct_stk_pairs(distance_group)
        DISTINCT = True

    return distance_group


"""For self define running sequence to run the filter functions declared above"""
def filter_pairs(dataFrame, sequence=['coint', 'AR1', 'distance'], number=0):
    get_clsprc = lambda y: [x[0] for x in dataFrame[pair[y]]]
    stk_pairs = utils.get_stkcd_pairs(dataFrame)
    stk_pairs = [(pair[0], pair[1], {}) for pair in stk_pairs]
    utils.xprint(os.linesep + 'Originally, %d pairs are created...' %(len(stk_pairs)))

    for pair in stk_pairs:
        pair[2]['bval'] = utils.Liner_Regression(get_clsprc(0), get_clsprc(1))

    #time.sleep(SLEEP_DURATION)
    container = globals()
    foo_name = None
    for item in sequence:
        for var in container.keys():
            if item in var: foo_name = var
        try:
            foo = container[foo_name]
        except KeyError, NameError:
            raise RuntimeError('Invalid filter method sequence')

        stk_pairs = foo(stk_pairs, dataFrame)
        utils.xprint('After %s, %d pairs left...' %(foo.__doc__, len(stk_pairs)))
        time.sleep(SLEEP_DURATION)

    '''Dump bval, pval, distance parameter sheet to file'''
    utils.csv_dump(stk_pairs, ftype='parameter')

    if DISTINCT is False:
        raise RuntimeError('Filtered stock pairs not distinct, do not use AR1 method only!!!')
    for pair in stk_pairs:
        Xt = utils.Spread_Xt(get_clsprc(0), get_clsprc(1), pair[2]['bval'])
        pair[2]['STD'] = utils.Standard_Deviation(Xt)
        pair[2]['EX'] = utils.Mean(Xt)

    return stk_pairs[:number]
