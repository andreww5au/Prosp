
import MySQLdb

from globals import *

weather = None

#These are the initial defaults, copied to the status object on module init.
_SkyOpenTemp = -26  #Open if skytemp < this for more than WeatherOpenDelay sec
_SkyCloseTemp = -25  #Close is skytemp > this or raining
_WeatherOpenDelay=1800  #Wait for 1800 sec of no-rain and cloud < CloudOpenLevel
_CloudCloseDelay=150    #Wait until at least two cloud readings (1/2min) are 'cloudy'


def _unyv(arg=0):
  if arg == 0:
    return "?"
  elif arg == 1:
    return "No"
  elif arg == 2:
    return "Yes"
  elif arg == 3:
    return "VERY!"
  else:
    return "error."

def _yn(arg=0):
  if arg:
    return "Yes"
  else:
    return "No"


def render(v,dig,dp):
  """If v is None, return 'NULL' as a string. Otherwise return
     the value in v formatted nicely as a number, with the given
     number of digits in total, and after the decimal point.
  """
  if v is None:
    return "NULL"
  else:
    return ('%'+`dig`+'.'+`dp`+'f') % v


class Weather:
  "Cloud and rain detector status"

  def empty(self):
    "called by __init__ or manually to clear status"
    self.lastmod = -1
    self.skytemp = 0.0
    self.cloudf, self.windf, self.rainf, self.dayf = 0,0,0,0
    self.rain = False
    self.temp = 0.0
    self.windspeed = 0.0
    self.humidity = 0.0
    self.dewpoint = 0.0
    self.skylight = 0.0
    self.rainhit,self.wethead = False,False
    self.senstemp = 0.0
    self.weathererror = ""
    self.SkyCloseTemp = _SkyCloseTemp
    self.SkyOpenTemp = _SkyOpenTemp
    self.WeatherOpenDelay = _WeatherOpenDelay
    self.CloudCloseDelay = _CloudCloseDelay    #No interface for setting this at runtime
    self.OKforsec = 86400   #Assume it's clear when we start up
    self.CloudyForSec = 0
    self.clear = True

  def __init__(self):
    self.empty()
    self.update()

  def GetState(self):
    d = {}
    for n in ['lastmod','skytemp','cloudf','windf','rainf','dayf','rain','temp','windspeed','humidity','dewpoint',
              'skylight','rainhit','wethead','senstemp','weathererror','SkyCloseTemp','SkyOpenTemp','WeatherOpenDelay',
              'CloudCloseDelay','OKforsec','CloudyForSec','clear']:
      d[n] = self.__dict__.get(n)
    return d

  def __str__(self):
    "Tells the status object to display itself"
    print "Sky Temp:  ", self.skytemp
    print "Cloudy:    ", _unyv(self.cloudf)
    print "Windy:     ", _unyv(self.windf)
    print "Raining:   ", _unyv(self.rainf)
    print "Daylight:  ", _unyv(self.dayf)
    print "Last weather entry: ", self.lastmod,"seconds ago."
    print "Air temp:  ", render(self.temp,4,1)
    print "Avg wind:  ", render(self.windspeed,3,0)
    print "Humidity:  ", render(self.humidity,2,0)
    print "Dew point: ", render(self.dewpoint,4,1)
    print "Raindrops: ", _yn(self.rainhit)
    print "Wet sensor:", _yn(self.wethead)
    print "Sens. Temp:", render(self.senstemp,4,1)
    print
    print "Becomes 'not clear' if skytemp warmer than:", self.SkyCloseTemp
    print "Becomes 'clear' if skytemp colder than", self.SkyOpenTemp, "for",
    print self.WeatherOpenDelay, "seconds or more."
    if self.weathererror:
      print "Error: ", self.weathererror
    if self.clear:
      print "\nCurrent Status: Clear"
    else:
      print "\nCurrent Status: Not Clear, conditions have been acceptable for ",
      print self.OKforsec, "seconds."

  def checkweather(self):
    "Monitor Cloud and Rain data, and take action if necessary"
    if self.rainf <> 1:  #0 is unknown, 1 is not raining, 2 is 'wet', 3 is raining.
      self.rain = True
    else:
      self.rain = False
    if self.weathererror:
      self.clear = False
      self.OKforsec = False
    else:
      if not self.clear:
        if (self.skytemp <= self.SkyOpenTemp) and (not self.rain):
          self.OKforsec = self.OKforsec + 5
        else:
          self.OKforsec = 0
        if self.OKforsec > self.WeatherOpenDelay:
          self.clear = True
      else:
        if (self.skytemp >= self.SkyCloseTemp):
          self.CloudyForSec = self.CloudyForSec + 5
        else:
          self.CloudyForSec = 0
        if (self.CloudyForSec > self.CloudCloseDelay) or self.rain:
          self.clear = False
          self.OKforsec = 0

  def update(self, u_curs=None):
    "Connect to the database to update fields"
    self.weathererror = ""

    if not u_curs:
      u_curs = db.cursor()
    try:
      u_curs.execute('select unix_timestamp(now())-unix_timestamp(time) as lastmod, ' +
          'skytemp, cloudf, windf, rainf, dayf, temp, windspeed, humidity, dewpoint, ' +
          'skylight, rainhit, wethead, senstemp from misc.weather order by time desc '+
          'limit 1')
                                       #Read the contents of the
                                       #'weather status' table to find
                                       #cloud voltage and rain status
      row = u_curs.fetchall()[0]
      self.lastmod = row[0]
      self.skytemp = row[1]
      self.cloudf = row[2]
      self.windf = row[3]
      self.rainf = row[4]
      self.dayf = row[5]
      self.temp = row[6]
      self.windspeed = row[7]
      self.humidity = row[8]
      self.dewpoint = row[9]
      self.skylight = row[10]
      self.rainhit = row[11]
      self.wethead = row[12]
      self.senstemp = row[13]
    except:
      self.weathererror = "Weather database not OK, can't get current values"
    if self.lastmod > 540:
      self.weathererror = "Weather database not updated for " + `self.lastmod` + " seconds."

    self.checkweather()



def _background():
  """Function to be run in the background, updates the status object.
  """
  b_curs=b_db.cursor()
  try:
    status.update(b_curs)
  except:
    print "a weather exception"


def Init():
  global db, b_db, status
  db = MySQLdb.Connection(host='mysql', user='honcho', passwd='', db='misc')
  b_db = MySQLdb.Connection(host='mysql', user='honcho', passwd='', db='misc')
  status = Weather()
  status.update()

