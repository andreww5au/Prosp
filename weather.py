
import MySQLdb
import threading
from globals import *

#These are the initial defaults, copied to the status object on module init.
_CloudOpenLevel=5900   #Open if cloud < this for more than WeatherOpenDelay sec
_CloudCloseLevel=6000  #Close is cloud > this or raining
_WeatherOpenDelay=1800  #Wait for 1800 sec of no-rain and cloud < CloudOpenLevel


def _yn(arg=0):
  if arg:
    return 'yes'
  else:
    return 'no'


class _Weather:
  "Cloud and rain detector status"

  def empty(self):
    "called by __init__ or manually to clear status"
    self.lastmod=-1
    self.cloud=0
    self.rain=0
    self.CloudCloseLevel=_CloudCloseLevel
    self.CloudOpenLevel=_CloudOpenLevel
    self.WeatherOpenDelay=_WeatherOpenDelay
    self.OKforsec=86400   #Assume it's clear when we start up
    self.clear=1

  def __init__(self):
    self.empty()

  def display(self):
    "Tells the status object to display itself"
    print "Cloud level = ",self.cloud
    print "Raining: ",_yn(self.rain)
    print "Last weather entry: ",self.lastmod,"seconds ago."
    print "Not clear if cloud greater than:",self.CloudCloseLevel
    print "Clear if cloud less than",self.CloudOpenLevel,"for",
    print self.WeatherOpenDelay,"seconds or more."
    if self.clear:
      print "Monitoring Status: Clear"
    else:
      print "Not Clear, conditions have been acceptable for ",self.OKforsec,"seconds."


  def checkweather(self):
    "Monitor Cloud and Rain data, and take action if necessary"
    if not self.clear:
      if (self.cloud <= self.CloudOpenLevel) and (not self.rain):
        self.OKforsec=self.OKforsec+5
      else:
        self.OKforsec=0
      if self.OKforsec > self.WeatherOpenDelay:
        self.clear=1
    else:
      if (self.cloud >= self.CloudCloseLevel) or self.rain:
        self.clear=0
        self.OKforsec=0

  def update(self):
    "Connect to the database to update fields"
    curs=_db.cursor()
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



def _background():
  """Function to be run in the background, updates the status object.
  """
  try:
    status.update()
  except:
    print "a weather exception"





_db=MySQLdb.Connection(host='lear', user='honcho', passwd='',
                      db='teljoy', cursorclass=MySQLdb.DictCursor)
status=_Weather()
status.update()

