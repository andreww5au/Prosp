
import MySQLdb
import threading
from globals import *

CloudOpenLevel=5900   #Open if cloud < this for more than WeatherOpenDelay sec
CloudCloseLevel=6000  #Close is cloud > this or raining
WeatherOpenDelay=1800  #Wait for 1800 sec of no-rain and cloud < CloudOpenLevel


def _yn(arg=0):
  if arg:
    return 'yes'
  else:
    return 'no'


class Weather:
  "Cloud and rain detector status"

  def empty(self):
    "called by __init__ or manually to clear status"
    self.lastmod=-1
    self.cloud=0
    self.rain=0
    self.OKforsec=86400   #Assume it's clear when we start up
    self.WeatherActive=0 #0 for disabled, 1 for rain only, 2 for rain and cloud
    self.Clear=threading.Event()
    self.Clear.set()

  def __init__(self):
    self.empty()

  def display(self):
    "Tells the status object to display itself"
    print "Cloud level = ",self.cloud
    print "Raining: ",_yn(self.rain)
    print "Last weather entry: ",self.lastmod,"seconds ago."
    print "Monitoring (0=none, 1=rain, 2=rain and cloud):",self.WeatherActive
    if self.WeatherActive:
      if self.Clear.isSet():
        print "Monitoring Status: Clear"
      else:
        print "Not Clear, conditions have been acceptable for ",self.OKforsec,"seconds."


  def checkweather(self):
    "Monitor Cloud and Rain data, and take action if necessary"
    if not self.WeatherActive:       #Don't care about weather.
      return
    elif self.WeatherActive==1:      #Watch out for rain, ignore clouds
      if not self.Clear.isSet():
        if (not self.rain):
          self.OKforsec=self.OKforsec+5
        else:
          self.OKforsec=0
        if self.OKforsec > WeatherOpenDelay:
          self.Clear.set()
      else:
        if self.rain:
          self.Clear.clear()
          self.OKforsec=0
    elif self.WeatherActive==2:      #Watch out for clouds and rain
      if not self.Clear.isSet():
        if (self.cloud <= CloudOpenLevel) and (not self.rain):
          self.OKforsec=self.OKforsec+5
        else:
          self.OKforsec=0
        if self.OKforsec > WeatherOpenDelay:
          self.Clear.set()
      else:
        if (self.cloud >= CloudCloseLevel) or self.rain:
          self.Clear.clear()
          self.OKforsec=0

  def update(self):
    "Connect to the database to update fields"
    curs=db.cursor()
    curs.execute('select unix_timestamp(now())-unix_timestamp(time) '+
          'as lastmod, cloud, rain from teljoy.weather order by time desc '+
          'limit 1')
                                       #Read the contents of the
                                       #'weather status' table to find
                                       #cloud voltage and rain status
    self.__dict__.update(curs.fetchallDict()[0])
    self.checkweather()
    self.updated()   #Call the 'updated' function to indicate fresh contents

  def updated(self):
    "Empty stub, override if desired. Called when status contents change"

  def __getstate__(self):   #Pickle module can't save lock objects
    "Return all attributes of the instance except for 'Clear'"
    d=self.__dict__.copy()
    del d['Clear']
    return d



def _background():
  """Function to be run in the background, updates the status object.
  """
  try:
    status.update()
  except:
    print "a weather exception"


db=MySQLdb.Connection(host='lear', user='honcho', passwd='',
                      db='teljoy', cursorclass=MySQLdb.DictCursor)
curs=db.cursor()
status=Weather()
status.update()

