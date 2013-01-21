"""Pyro4 RPC client library for Teljoy
"""
import Pyro4

status = None

XSIZE, YSIZE = 2048, 2048

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
    self.initialized = False
    self.errors = []         #List of (time,message) tuples containting all error messages, as they occurred.
    #Amplifier and readout parameters - unique to Andor camera
    self.highcap = None      #Is HighCapacity mode on?
    self.preamp = None       #PreAmp gain index
    self.hsspeed = None      #Horizontal shift speed index
    self.vsspeed = None      #Vertical shift speed index
    self.cycletime = None    #minimum time between successive exposures, allowing for exposure and readout
    self.readouttime = None  #Time taken to read out an image using the current readout settings
    self.mode = None         #Parameter mode set name (unbinned-slow, binned-fast, etc)
    #Temperature and regulation parameters
    self.cool = False        #Is Cooler on?
    self.tset = False        #Has temperature stabilised at setpoint?
    self.settemp = 999       #Regulated setpoint
    self.temp = 999          #Latest CCD temperature
    self.tempstatus = ''     #Latest CCD temperature regulation status - unique to Andor
    #Shutter and image type parameters
    self.imaging = False     #True if an image is being acquired, False otherwise.
    self.shuttermode = 0     #0 for auto, 1 for open, 2 for close - unique to Andor
    self.exptime = 0.0
    #Cropping boundaries - note boundaries are INDEPENDENT of binning, so 2048x2048 is always
    #  the full image, no matter what the binning factors are. However, these values must be
    #  exactly divisible by the binning factor for the given axis.
    self.xmin,self.xmax = 1,XSIZE   #Cropping boundaries for X
    self.ymin,self.ymax = 1,YSIZE   #Cropping boundaries for Y
    self.roi = (self.xmin,self.xmax,self.ymin,self.ymax)
    self.xbin = 1             #Horizontal (X) binning factor, 1-2048
    self.ybin = 1             #Vertical (Y) binning factor, 1-2048
    self.imgtype = ''  #or 'BIAS', 'DARK', or 'FLAT'
    self.object = ''         #Object name
    self.path = ''
    self.filename = ''
    self.nextfile = ''
    self.lastfile = ''
    self.filectr = 0
    self.observer = ''
    #Optical coupler setting parameters
    self.filter = -1
    self.filterid = 'X'
    self.guider = (9999, 9999)
    self.mirror = ''
    #Housekeeping parameters
    self.lastact = 0

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
