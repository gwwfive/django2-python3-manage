from django.test import TestCase
import json
# Create your tests here.

# print(str(['1','2']))
# print(eval(str(['1','2'])))
# for key,value in ['a','b']:
#     print(key)

import datetime
import time
from decimal import Decimal
print(datetime.datetime.now().weekday())
print(datetime.datetime.fromtimestamp(time.time()-600))
print("%.2f" % float(Decimal('13.99')*Decimal('10.01')))
print( "%.4f" %(11.5/100))
print("%.4f" % float(Decimal('12.23')))
print(datetime.datetime.today().weekday())
print(Decimal('10.00')/10 !=1.000)
print(len((('1',2),(1,2))))
print(u'{0}{1}{2}'.format('a',time.strftime('%Y%m%d', time.localtime(time.time())),'dfs'))
# print('\xe6\x89\xa7\xe8\xa1\x8c\xe5\x91\xbd\xe4\xbb\xa4\xe5\xa4\xb1\xe8\xb4\xa5\xef\xbc\x8c\xe9\x87\x8d\xe6\x96\xb0\xe6\x89\xa7\xe8\xa1\x8c\r'.encode('utf-8').decode('utf-8'))