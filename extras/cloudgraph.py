#!/usr/bin/python

import MySQLdb
from MySQLdb.cursors import DictCursor


db=MySQLdb.Connection(host='chef', user='honcho', passwd='',
                      db='misc', cursorclass=DictCursor)


curs=db.cursor()
try:
  curs.execute('select (unix_timestamp(time)-unix_timestamp(now()))/3600 as age, skytemp from weather where time > '+
                    'from_unixtime(unix_timestamp(now())-14400) order by time' )
  res=curs.fetchallDict()     
except:
  self.weathererror="Error connecting to database for weather initialisation."

times=[]
clouds=[]
for r in res:
  ag,st = float(r['age']), float(r['skytemp'])
  if st < -100:
    st = 0
  times.append(ag)
  clouds.append(st)

import matplotlib
matplotlib.use('Agg')
from pylab import *

plot(times,clouds)
ylabel('skytemp')
xlabel('hours before present')
savefig('/tmp/clouds.png')
