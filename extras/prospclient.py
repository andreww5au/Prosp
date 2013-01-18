"""Pyro4 RPC client library for Teljoy
"""

import Pyro4

status = None

class StatusObj(object):
  def __repr__(self):
    return str(self.__dict__)

class ChillerStatus(StatusObj):
  def __init__(self):
    self.connected = False
    self.lastchillerchecktime = 0
    self.watertemp = 0.0
    self.setpoint = 20.0

class WeatherStatus(StatusObj):
  def __init__(self):
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
    self.SkyCloseTemp = 0
    self.SkyOpenTemp = 0
    self.WeatherOpenDelay = 0
    self.CloudCloseDelay = 0
    self.OKforsec = 86400   #Assume it's clear when we start up
    self.CloudyForSec = 0
    self.clear = True

class FocuserStatus(StatusObj):
  def __init__(self):
    self.connected = False
    self.pos = 0
    self.remaining = 0
    self.modelname = ''
    self.retval = None
    self.extent = 0
    self.Tinternal = 0
    self.Texternal = 0
    self.datumT = None
    self.datumP = None


class ProspClient(StatusObj):
  """Client object, using a Pyro4 proxy of the remote telescope
     object to get status and send commands.
  """
  def __init__(self):
    """Set up the client object on creation
    """
    self.connected = False
    self.proxy = None
    self.chiller = ChillerStatus()
    self.weather = WeatherStatus()
    self.focuser = FocuserStatus()

  def update(self):
    if status.connected:
      self.__dict__.update(self.proxy.GetStatus())
      self.chiller.__dict__.update(self.proxy.GetChiller())
      self.weather.__dict__.update(self.proxy.GetWeather())
      self.focuser.__dict__.update(self.proxy.GetFocuser())


def _background():
  """Function to be run in the background, updates the status object.
  """
  if status.connected:
    try:
      status.update()
    except KeyboardInterrupt:
      print "a keyboard interrupt in tjclient._background()"
    except Pyro4.errors.PyroError:
      Connect(status)


def Connect(s):
  s.connected = False
  try:
    s.proxy = Pyro4.Proxy('PYRONAME:Prosp')
    s.connected = True
  except Pyro4.errors.PyroError:
    print "Can't connect to Prosp server - run Prosp to start the server"
  try:
    s.update()
  except Pyro4.errors.PyroError:
    s.connected = False


def Init():
  """Connect to the Teljoy server process and create a proxy object to the
     real telescope object.
  """
  global status
  status = ProspClient()
  Connect(status)
  return status.connected   #True if we have a valid, working proxy
