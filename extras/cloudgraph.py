#!/usr/bin/python

import MySQLdb
from MySQLdb.cursors import DictCursor


db=MySQLdb.Connection(host='cook', user='honcho', passwd='',
                      db='misc', cursorclass=DictCursor)


curs=db.cursor()
try:
  curs.execute('select (unix_timestamp(time)-unix_timestamp(now()))/3600 as age, cloud from weathlog where time > '+
                    'from_unixtime(unix_timestamp(now())-14400) order by time' )
  res=curs.fetchallDict()     
except:
  self.weathererror="Error connecting to database for weather initialisation."

times=[]
clouds=[]
for r in res:
  times.append(float(r['age']))
  clouds.append(float(r['cloud']))

import matplotlib
matplotlib.use('Agg')
from pylab import *

plot(times,clouds)
ylabel('cloud')
xlabel('hours before present')
savefig('/tmp/clouds.png')
