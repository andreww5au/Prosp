
import MySQLdb
import threading
from globals import *
import ephemint
from ephemint import isdark

CloudOpenLevel=5900   #Open if cloud < this for more than WeatherOpenDelay sec
CloudCloseLevel=6000  #Close is cloud > this or raining
WeatherOpenDelay=1800  #Wait for 1800 sec of no-rain and cloud < CloudOpenLevel

WeatherActive=0       #0 for disabled, 1 for rain only, 2 for rain and cloud.
OKforsec=86400        #Assume that it's clear when we start up

Clear=threading.Event()
Clear.set()


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
  def __init__(self):
    self.empty()
  def display(self):
    "Tells the status object to display itself"
    print "Cloud level = ",self.cloud
    print "Raining: ",_yn(self.rain)
    print "Last weather entry: ",self.lastmod,"seconds ago."

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
    self.updated()   #Call the 'updated' function to indicate fresh contents

  def updated(self):
    "Empty stub, override if desired. Called when status contents change"


def _CheckWeather():
  "Monitor Cloud and Rain data, and take action if necessary"
  global OKforsec

  if not WeatherActive:       #Don't care about weather.
    return

  elif WeatherActive==1:      #Watch out for rain, ignore clouds
    if not Clear.isSet():
      if (not status.rain) and isdark():
        OKforsec=OKforsec+5
      else:
        OKforsec=0
      if OKforsec > WeatherOpenDelay:
        Clear.set()
    else:
      if status.rain or (not isdark()):
        Clear.clear()
        OKforsec=0

  elif WeatherActive==2:      #Watch out for clouds and rain
    if not Clear.isSet():
      if (status.cloud <= CloudOpenLevel) and (not status.rain) and isdark():
        OKforsec=OKforsec+5
      else:
        OKforsec=0
      if OKforsec > WeatherOpenDelay:
        Clear.set()
    else:
      if (status.cloud >= CloudCloseLevel) or status.rain or (not isdark()):
        Clear.clear()
        OKforsec=0


def _background():
  """Function to be run in the background, updates the status object.
  """
  try:
    status.update()
    _CheckWeather()
  except:
    print "a weather exception"


db=MySQLdb.Connection(host='lear', user='honcho', passwd='',
                      db='teljoy', cursorclass=MySQLdb.DictCursor)
curs=db.cursor()
status=Weather()
status.update()

