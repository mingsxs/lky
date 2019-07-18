'''
This module is writen for Liu Keyi's homework project, and I write it for fully free.
'''

import sys
import os
import re

def get_end_date(file_handle):
# Note: this method restricts that there should not be blank line in the end of file !!!!!!
    pos = -3 # start place in reverse, because the last char is always '\r\n' in size of 2 bytes
    file_handle.seek(-4, 2)
    if len(file_handle.read(1).strip()) == 0:
        print 'this src file might has blank line in the end, error!'
        sys.exit(0)
    while True:
        try:
            file_handle.seek(pos, 2)    # locate to the end of file
            if file_handle.read(1) == '\n':
                break
            else:
                pos -= 1
        except:
            file_handle.seek(0, 0)      # go to the file head
            print 'error caught while moving file point to EOF'
    end_date = file_handle.read(8).strip()
    file_handle.seek(0, 0)              # return to the file head
    return end_date

class Record(object):
    def __init__(self, linearg_str, linenum=1):
        arg_list = linearg_str.strip().split(',')
        if len(arg_list) != 14:
            print 'wrong arg number this line'
            sys.exit(0)
        self._current_line = linenum
        self.date = arg_list[0].strip()
        self.exdate = arg_list[1].strip()
        self.CP = int(arg_list[2].strip())
        self.strike_price = int(arg_list[3].strip())
        self.best_bid = float(arg_list[4].strip())
        self.best_offer = float(arg_list[5].strip())
        self.volume = int(arg_list[6].strip())
        self.open_interest = int(arg_list[7].strip())
        self.maturity_time = float(arg_list[8].strip())
        self.underlying_price = float(arg_list[9].strip())
        self.diff = float(arg_list[10].strip())
        self.option_price = float(arg_list[11].strip())
        self.rate = float(arg_list[12].strip())
        self.option_price_hat = float(arg_list[13].strip())


class Share(object):
    def __init__(self, record, isstart_date=False, isend_date=False, share_dict={}, arg_dict={}):
        if not isinstance(record, Record):
            print 'wrong type arg'
            sys.exit(0)
        self._id = '-'.join([record.exdate, str(record.CP), str(record.strike_price)])
        self._long = 0
        self._lflow = 0
        self._short = 0
        self._sflow = 0
        self._s = None
        self._flow = 0
        if share_dict.has_key(self._id):
            last_m_value = share_dict.get(self._id).m_value
            if hasattr(share_dict.get(self._id), 'record_best_offer'):
                last_best_offer = share_dict.get(self._id).record_best_offer
            if hasattr(share_dict.get(self._id), 'record_best_bid'):
                last_best_bid = share_dict.get(self._id).record_best_bid
        else:
            last_m_value = 0    # Not good actually
            last_best_offer = 0
            last_best_bid = 0
        if isstart_date:
            if record.option_price >= record.option_price_hat + arg_dict.get('UC'):
                self._long = 1
                self._lflow = (-10000)*record.best_offer
            elif record.option_price <= record.option_price_hat - arg_dict.get('LC'):
                self._short = 1
                self._sflow = 10000*record.best_offer
            else:
                pass
        elif isend_date:
            if last_m_value > 0:
                self._sflow = max(last_m_value*10000*record.best_bid, 0, record.diff*last_m_value*10000)
            elif last_m_value < 0:
                self._lflow = max(last_m_value*10000*record.best_offer, record.diff*10000*last_m_value)
            else:
                pass
        else:
            if last_m_value > 0:
                if int(record.exdate) - int(record.date) > 0:
                    if record.best_bid >= record.diff and \
                            record.best_bid >= (1 + arg_dict.get('SC'))*last_best_offer:
                        self._sflow = last_m_value*10000*record.best_bid
                    elif record.best_bid >= record.diff and \
                            record.best_bid < (1 + arg_dict.get('SC'))*last_best_offer:
                        pass
                    else:
                        self._s = 1
                        self._flow = record.diff*last_m_value*10000
                else:
                    self._flow = max(0, record.diff*last_m_value*10000)
            elif last_m_value < 0:
                if record.diff > 0:
                    self._s = -1
                    self._flow = record.diff*last_m_value*10000
                else:
                    pass
            else:
                if record.option_price >= record.option_price_hat + arg_dict.get('UC'):
                    self._long = 1
                    self._lflow = (-10000)*record.best_offer
                elif record.option_price <= record.option_price_hat - arg_dict.get('LC'):
                    self._short = 1
                    self._sflow = 10000*record.best_offer
                else:
                    pass
        if self._long == 1 or hasattr(share_dict.get(self._id), 'record_best_offer'):
            self.record_best_offer = record.best_offer
        if self._short == 1 or hasattr(share_dict.get(self._id), 'record_best_bid'):
            self.record_best_bid = record.best_bid
        self.m_value = last_m_value + (self._long - self._short)

    def update_status(self, share_dict={}):
        share_dict[self._id] = self

    def write_values(self, record, file_handle=None):
        line = ','.join([record.date, record.exdate, str(record.CP), str(record.strike_price),
            str(record.best_bid), str(record.best_offer), str(record.volume), str(record.open_interest),
            str(record.maturity_time), str(record.underlying_price), str(record.diff), str(record.option_price),
            str(record.rate), str(record.option_price_hat), str(self._long), str(self._lflow),
            str(self._short), str(self._sflow), str(self._s), str(self._flow), str(self.m_value), self._id])
        line_str = line + os.linesep
        if file_handle:
            en_line_str = line_str.encode('utf-8')
            file_handle.writelines(en_line_str)

def main():
    src_file_path = './res/test1.csv'
    des_file_path = './res/result.csv'
    pattern = re.compile(r'^[0-9]+(\.)?[0-9]*$', flags=re.U)
    arg_dict = {'UC': None, 'LC': None, 'SC': None}
    while True:
        for key in arg_dict:
            if arg_dict[key] is None:
                raw_arg = raw_input(key + ': ').strip()
                if pattern.match(raw_arg) and raw_arg.find('.') == -1:
                    arg_dict[key] = int(raw_arg)
                elif pattern.match(raw_arg) and raw_arg.find('.') != -1:
                    arg_dict[key] = float(raw_arg)
                else:
                    print 'illegal input %s, retry later' %(key)
        if None not in arg_dict.values():
            break
    share_dict = {}         # Initial a null dict to store shares
    with open(src_file_path, 'r') as src_file, open(des_file_path, 'w') as des_file:
        end_date = get_end_date(src_file)
        src_temp = src_file.readline()     # skip first line in source file
        des_temp = ','.join([src_temp.strip(), 'long', 'lflow', 'short', 'sflow', 's', 'flow', 'm_value', 'share_id'])
        des_head = des_temp.strip(',') + os.linesep
        des_file.writelines(des_head)     # write first line to result file
# collecting src file date
        linenum = 1
        for line in src_file.readlines():
            current_record = Record(line, linenum)
            if linenum == 1:
                start_date = current_record.date
            if start_date is not None and end_date is not None:
                current_item = Share(current_record, (current_record.date == start_date),
                    (current_record.date == end_date), share_dict, arg_dict)
                current_item.update_status(share_dict)
                current_item.write_values(current_record, des_file)
            else:
                print 'start_date and end_date not calculated'
                sys.exit(0)
            linenum += 1
    print 'Hi, Liu Keyi, Your sound is beautiful and I love your songs'
    #print 'This shit successfully done'

if __name__ == '__main__':
    main()
