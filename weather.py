
import MySQLdb
from globals import *

#These are the initial defaults, copied to the status object on module init.
_CloudOpenLevel=100   #Open if cloud < this for more than WeatherOpenDelay sec
_CloudCloseLevel=150  #Close is cloud > this or raining
_WeatherOpenDelay=300  #Wait for 1800 sec of no-rain and cloud < CloudOpenLevel


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
    self.sky=0
    self.rain=0
    self.weathererror=""
    self.CloudCloseLevel=_CloudCloseLevel
    self.CloudOpenLevel=_CloudOpenLevel
    self.WeatherOpenDelay=_WeatherOpenDelay
    self.OKforsec=86400   #Assume it's clear when we start up
    self.clear=1

  def __init__(self):
    self.empty()
    curs=_db.cursor()
    #Set the reference time for selecting a sky value to be 300 seconds before 'now'
    #If we don't subtract 300sec, the first query called will return no records.
    if curs.execute('select from_unixtime(unix_timestamp(now())-300) as tnow'):
      self.starttime=curs.fetchallDict()[0]['tnow']
    self.update()

  def display(self):
    "Tells the status object to display itself"
    print "Cloud level = ",self.cloud
    print "Raining: ",_yn(self.rain)
    print "Last weather entry: ",self.lastmod,"seconds ago."
    print "Current clear-sky value: ",self.sky
    print "Becomes 'not clear' if cloud greater than:",self.sky+self.CloudCloseLevel
    print "Becomes 'clear' if cloud less than",self.sky+self.CloudOpenLevel,"for",
    print self.WeatherOpenDelay,"seconds or more."
    if self.weathererror:
      print self.weathererror
    if self.clear:
      print "\nCurrent Status: Clear"
    else:
      print "\Current Status: Not Clear, conditions have been acceptable for ",
      print self.OKforsec, "seconds."


  def checkweather(self):
    "Monitor Cloud and Rain data, and take action if necessary"
    if self.weathererror:
      self.clear=0
      self.OKforsec=0
    else:
      if not self.clear:
        if (self.cloud <= self.sky + self.CloudOpenLevel) and (not self.rain):
          self.OKforsec=self.OKforsec+5
        else:
          self.OKforsec=0
        if self.OKforsec > self.WeatherOpenDelay:
          self.clear=1
      else:
        if (self.cloud >= self.sky + self.CloudCloseLevel) or self.rain:
          self.clear=0
          self.OKforsec=0

  def update(self):
    "Connect to the database to update fields"
    curs=_db.cursor()
    try:
      curs.execute('select unix_timestamp(now())-unix_timestamp(time) '+
          'as lastmod, cloud, rain from teljoy.weather order by time desc '+
          'limit 1')
                                       #Read the contents of the
                                       #'weather status' table to find
                                       #cloud voltage and rain status
      self.__dict__.update(curs.fetchallDict()[0])
    except:
      self.weathererror="Weather database not OK, can't get current values"
    if self.lastmod>200:
      self.weathererror="Weather database not updated for "+`self.lastmod`+" seconds."

    try:
      curs.execute('select cloud from weather where time > "' + self.starttime +
                    '" order by cloud limit 4' )
      res=curs.fetchallDict()     #Take the 4th lowest cloud value since we started monitoring
      self.sky=res[-1]['cloud']   #Unless there are less then 4, in which case take the lowest
    except:
      self.weathererror="Weather database not OK, can't get clear sky value"
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


def reset():
  curs=_db.cursor()
  if curs.execute('select from_unixtime(unix_timestamp(now())) as tnow'):
    starttime=curs.fetchallDict()[0]['tnow']
  




_db=MySQLdb.Connection(host='lear', user='honcho', passwd='',
                      db='teljoy', cursorclass=MySQLdb.DictCursor)
status=_Weather()
status.update()

