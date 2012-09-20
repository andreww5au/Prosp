#
# TODO - investigate SetCoolerMode function that defines whether cooler is kept on after a ShutDown call, or turned off
#
#      - Bomb-proof the cooling so that ShutDown isn't called until the cooler is warmer than -20C, and the system
#        is ALWAYS called on exit
#
#      -Use functions like IsCoolerOn() to detect state on startup, and in an update() method to the status class
#
#      -Investigate GetMetaDataInfo (using funky time struct) to get timing info for an image, for more accurate 
#       time in headers
#      
import time
import cPickle

import pyandor
import fits
import improc
from globals import swrite, ewrite,filtname

FITS = improc.FITS

AndorPath = '/usr/local/etc/andor'

debug = True

DRV_ERRS = {20001:'DRV_ERROR_CODES',
            20002:'DRV_SUCCESS', 20003:'DRV_VXDNOTINSTALLED', 20004:'DRV_ERROR_SCAN', 20005:'DRV_ERROR_CHECK_SUM', 20006:'DRV_ERROR_FILELOAD', 
            20007:'DRV_UNKNOWN_FUNCTION', 20008:'DRV_ERROR_VXD_INIT', 20009:'DRV_ERROR_ADDRESS', 20010:'DRV_ERROR_PAGELOCK', 20011:'DRV_ERROR_PAGEUNLOCK', 
            20012:'DRV_ERROR_BOARDTEST', 20013:'DRV_ERROR_ACK', 20014:'DRV_ERROR_UP_FIFO', 20015:'DRV_ERROR_PATTERN', 

            20017:'DRV_ACQUISITION_ERRORS',
            20018:'DRV_ACQ_BUFFER', 20019:'DRV_ACQ_DOWNFIFO_FULL', 20020:'DRV_PROC_UNKONWN_INSTRUCTION', 20021:'DRV_ILLEGAL_OP_CODE', 
            20022:'DRV_KINETIC_TIME_NOT_MET', 20023:'DRV_ACCUM_TIME_NOT_MET', 20024:'DRV_NO_NEW_DATA', 20025:'KERN_MEM_ERROR', 20026:'DRV_SPOOLERROR', 
            20027:'DRV_SPOOLSETUPERROR', 20028:'DRV_FILESIZELIMITERROR', 20029:'DRV_ERROR_FILESAVE', 

            20033:'DRV_TEMP_CODES', 
            20034:'DRV_TEMP_OFF', 20035:'DRV_TEMP_NOT_STABILIZED', 20036:'DRV_TEMP_STABILIZED', 20037:'DRV_TEMP_NOT_REACHED', 
            20038:'DRV_TEMP_OUT_RANGE', 20039:'DRV_TEMP_NOT_SUPPORTED', 20040:'DRV_TEMP_DRIFT', 

            20049:'DRV_GENERAL_ERRORS', 
            20050:'DRV_INVALID_AUX', 20051:'DRV_COF_NOTLOADED', 20052:'DRV_FPGAPROG', 20053:'DRV_FLEXERROR', 20054:'DRV_GPIBERROR', 20055:'DRV_EEPROMVERSIONERROR', 

            20064:'DRV_DATATYPE', 
            20065:'DRV_DRIVER_ERRORS', 20066:'DRV_P1INVALID', 20067:'DRV_P2INVALID', 20068:'DRV_P3INVALID', 20069:'DRV_P4INVALID', 20070:'DRV_INIERROR', 
            20071:'DRV_COFERROR', 20072:'DRV_ACQUIRING', 20073:'DRV_IDLE', 20074:'DRV_TEMPCYCLE', 20075:'DRV_NOT_INITIALIZED', 20076:'DRV_P5INVALID', 
            20077:'DRV_P6INVALID', 20078:'DRV_INVALID_MODE', 20079:'DRV_INVALID_FILTER', 

            20080:'DRV_I2CERRORS',
            20081:'DRV_I2CDEVNOTFOUND', 20082:'DRV_I2CTIMEOUT', 20083:'DRV_P7INVALID', 20084:'DRV_P8INVALID', 20085:'DRV_P9INVALID', 20086:'DRV_P10INVALID', 

            20089:'DRV_USBERROR', 
            20090:'DRV_IOCERROR', 20091:'DRV_VRMVERSIONERROR', 20093:'DRV_USB_INTERRUPT_ENDPOINT_ERROR', 20094:'DRV_RANDOM_TRACK_ERROR', 
            20095:'DRV_INVALID_TRIGGER_MODE', 20096:'DRV_LOAD_FIRMWARE_ERROR', 20097:'DRV_DIVIDE_BY_ZERO_ERROR', 20098:'DRV_INVALID_RINGEXPOSURES', 
            20099:'DRV_BINNING_ERROR', 20100:'DRV_INVALID_AMPLIFIER', 

            20115:'DRV_ERROR_MAP', 20116:'DRV_ERROR_UNMAP', 20117:'DRV_ERROR_MDL', 20118:'DRV_ERROR_UNMDL', 20119:'DRV_ERROR_BUFFSIZE', 20121:'DRV_ERROR_NOHANDLE', 

            20130:'DRV_GATING_NOT_AVAILABLE', 20131:'DRV_FPGA_VOLTAGE_ERROR', 

            20150:'DRV_OW_CMD_FAIL', 20151:'DRV_OWMEMORY_BAD_ADDR', 20152:'DRV_OWCMD_NOT_AVAILABLE', 20153:'DRV_OW_NO_SLAVES', 
            20154:'DRV_OW_NOT_INITIALIZED', 20155:'DRV_OW_ERROR_SLAVE_NUM', 20156:'DRV_MSTIMINGS_ERROR', 

            20990:'DRV_ERROR_NOCAMERA', 20991:'DRV_NOT_SUPPORTED', 20992:'DRV_NOT_AVAILABLE'
           }

#Gain in electrons per ADU, as a function of HSSpeed index, preamp gain index, and high capacity flag
#Eg, for 3.0Mhz (HSSpeed=1), and preamp gain of x4.0 (gain index=2) and high-cap mode on, GAIN[1][2][1]=4.3
GAIN = {0:{0:(8.0,18.2), 1:(4.5,12.3), 2:(2.3,6.5)},     #speed 0 (5 MHz), preamp 0,1,2 (1.0, 2.0, 4.0)
        1:{0:(3.8,14.5), 1:(2.0,7.8), 2:(1.1,4.3)},      #speed 1 (3 MHz), preamp 0,1,2 (1.0, 2.0, 4.0)
        2:{0:(3.7,14.8), 1:(1.9,7.1), 2:(1.0,3.8)},      #speed 2 (1 MHz), preamp 0,1,2 (1.0, 2.0, 4.0)
        3:{0:(3.7,14.8), 1:(1.9,7.1), 2:(1.1,3.6)}       #speed 3 (50kHz), preamp 0,1,2 (1.0, 2.0, 4.0)
       }

#Readout noise in electrons, as a function of HSSpeed index, preamp gain index, and high capacity flag
#Eg, for 50kHz (HSSpeed=3), and preamp gain of x1.0 (gain index=0) and high-cap mode off, NOISE[3][0][0]=4.2
NOISE = {0:{0:(50.4,105.3), 1:(42.4,86.0), 2:(33.3,71.5)},   #speed 0 (5 MHz), preamp 0,1,2 (1.0, 2.0, 4.0)
         1:{0:(20.7,76.3),  1:(13.6,46.7), 2:(10.9,38.4)},   #speed 1 (3 MHz), preamp 0,1,2 (1.0, 2.0, 4.0)
         2:{0:(11.4,44.7),  1:(8.2,24.2),  2:(7.1,21.7)},    #speed 2 (1 MHz), preamp 0,1,2 (1.0, 2.0, 4.0)
         3:{0:(4.2,15.5),   1:(3.6,10.2),  2:(3.4,8.5)}      #speed 3 (50kHz), preamp 0,1,2 (1.0, 2.0, 4.0)
       }


SATLEVEL = 74995    #saturation threshold, in electrons

def satadu(hsspeed=0, preamp=0, highcap=0):
  return SATLEVEL/GAIN[hsspeed][preamp][highcap]

def CurrentSaturation():
  return satadu(hsspeed=status.hsspeed, preamp=status.preamp, highcap=status.highcap)

def CurrentGain():
  return GAIN[status.hsspeed][status.preamp][status.highcap]

def CurrentNoise():
  return NOISE[status.hsspeed][status.preamp][status.highcap]

# Note - ideal usage for Perth 61cm telescope is probably:
#        HSSpeed = 3 (50kHz) for 84 sec 1x1 binned readout time, 21 sec 2x2 binned readout time
#        VSSpeed = 1 (76 us)
#        HighCapacity Off
#        PreAmpGain of 2 (= 4.0) for 1x1 binning, to give pixel saturation at around 69,000 ADU
#        PreAmpGain of 0 (= 1.0) for 2x2 binning, to give pixel saturation at around 82,000 ADU



XSIZE, YSIZE = 2048, 2048

SECPIX = 0.3375     #arcseconds per pixel, unbinned
SHUTTEROPEN = 50    #Shutter open time in milliseconds
SHUTTERCLOSE = 50   #Shutter close time in milliseconds

MAX_NOLOOPTIME = 5   #Max exposure time to handle with no temp averaging loop
LOOPTIME = 1         #Loop time in seconds to sample CCD temp during exposure

hardware = """
   Camera characteristics:

   GetPixelSize: 13.5um by 13.5um
   GetDetector: 2048 by 2048
   GetTemperatureRange: min=-120, max=-10

   FastestRecommendedVSSSpeed: index 0, 38.549999237060547us
   GetNumberADChannels: 1 (index=0 for all channel values)
   GetNumberAmp: 1 (index=0 for all output amp values)
   
   GetNumberPreAmpGains: 3   (index=0,1,2)
   GetPreAmpGain: gain[0]=1.0, gain[1]=2.0, gain[2]=4.0
   (ALSO - Can do SetHighCapacity(1) to turn on high pixel capacity mode in output amp. Seems to ~ halve output values)
   (note - all preamp gains available at all speeds)
   
   GetNumberVSAmplitudes: 3   (index=0,1,2)

   GetNumberFKVShiftSpeeds: 2  (index=0 or 1)
   GetNumberVSSpeeds: 2  (index=0 or 1)
   GetVSSpeed: VSS[0]=38.549999237060547us,  VSS[1]=76.949996948242188us

   GetNumberHSSpeeds: 4 (ADC=0, type=0)
   GetHSSpeed: HSS[0]=5.0 MHz, HSS[1]=3.0, HSS[2]=1.0, HSS[3]=0.05 MHz
   (unbinned readout time around 0.84 seconds at 5.0Mhz, 4.2 seconds at 1.0Mhz, and 84 seconds at 50kHz)
   (note - all preamp gains available at all speeds)
   -------------------------------
"""

PreAmpGains = {0:1.0, 1:2.0, 2:4.0}

HSSpeeds = {0:'5.0 MHz', 1:'3.0 MHz', 2:'1.0 MHz', 3:'50 kHz'}

VSSpeeds = {0:'38.55 us', 1:'76.95 us'}

#  Capability Flags:
CAPS = { 
  'ulAcqModes':47,   # AC_ACQMODE_SINGLE 1, AC_ACQMODE_VIDEO 2, AC_ACQMODE_ACCUMULATE 4, AC_ACQMODE_KINETIC 8, AC_ACQMODE_FASTKINETICS 32
                     #  (not capable of frame transfer or overlap acquisition)

  'ulReadModes':63,  #AC_READMODE_FULLIMAGE 1, AC_READMODE_SUBIMAGE 2, AC_READMODE_SINGLETRACK 4, AC_READMODE_FVB 8
                     #AC_READMODE_MULTITRACK 16, AC_READMODE_RANDOMTRACK 32
                     #  (not capable of Random Track read mode)

  'ulTriggerModes':19,   #AC_TRIGGERMODE_INTERNAL 1, AC_TRIGGERMODE_EXTERNAL 2, AC_TRIGGERMODE_EXTERNALSTART 16
                         #  (not capable of FVB_EM, continuous, bulb, external exposure, or inverted trigger)

  'ulCameraType':13,     # iKon

  'ulPixelMode':4,       #AC_PIXELMODE_16BIT 4
                         #  (16 bit acquisitions only)

  'ulSetFunctions':32487, #AC_SETFUNCTION_VREADOUT 0x01, AC_SETFUNCTION_HREADOUT 0x02, AC_SETFUNCTION_TEMPERATURE 0x04
                          #AC_SETFUNCTION_BASELINECLAMP 0x20, AC_SETFUNCTION_VSAMPLITUDE 0x40, AC_SETFUNCTION_HIGHCAPACITY 0x80
                          #AC_SETFUNCTION_PREAMPGAIN 0x0200, AC_SETFUNCTION_CROPMODE 0x0400, AC_SETFUNCTION_DMAPARAMETERS 0x0800
                          #AC_SETFUNCTION_HORIZONTALBIN 0x1000, AC_SETFUNCTION_MULTITRACKHRANGE 0x2000, AC_SETFUNCTION_RANDOMTRACKNOGAPS 0x4000
                          #  (not capable of MCPGAIN, EMCCDGAIN, BASELINEOFFSET
                          #   or undocumented modes EMADVANCED, GATEMODE, DDGTIMES, IOC, INTELLIGATE, INSERTION_DELAY, or GATESTEP)


  'ulGetFunctions':13,   #AC_GETFUNCTION_TEMPERATURE 0x01, AC_GETFUNCTION_TEMPERATURERANGE 0x04, AC_GETFUNCTION_DETECTORSIZE 0x08
                         #  (not capable of getting target temperature or many other undocumented modes)

  'ulFeatures':133037,   #AC_FEATURES_POLLING 1, AC_FEATURES_SPOOLING 4, AC_FEATURES_SHUTTER 8, AC_FEATURES_EXTERNAL_I2C 32
                         #AC_FEATURES_FANCONTROL 128, AC_FEATURES_MIDFANCONTROL 256, AC_FEATURES_TEMPERATUREDURINGACQUISITION 512
                         #AC_FEATURES_KEEPCLEANCONTROL 1024, AC_FEATURES_PHOTONCOUNTING 0x20000
                         #  (not capable of Windows events, SetShutterEx, Saturation event, DDGLite, Frame Transfer external,
                         #   DAC control, metadata, or TTL IO control)
  }


defheaders = {'CREATOR':"'Andor.py version xxxxx'",
              'OBSERVAT':"'Perth'",
              'LATITUDE':"'-32:00:29.1'",
              'LONGITUD':"'-116:08:06.07'",
              'INSTRUME':"'Andor iKon-L serial CCD-11417'",
              'DETECTOR':"'E2V CCD42-40 2048x2048 13.5um serial 09382-22-06'",
              'INSTID':"'Perth iKon-L'",
              'TIMESYS':"'UTC'",
              'SATLEVEL':`SATLEVEL`,
              'DATE-OBS':"'%d-%d-%d'",
              'TIME-OBS':"'%d:%d:%d'",
              'OBSERVER':"''",
              'NAXIS1':"2048",
              'NAXIS2':"2048",
              'CCDXBIN':"0",
              'CCDYBIN':"0",
              'CCDTEMP':"999.9",
              'SECPIX':"0",
              'SHUTTER':"''",
              'GAIN':"0",
              'PREGAIN':"0",
              'HSSPEED':"''",
              'VSSPEED':"''",
              'RONOISE':"0.0",
              'SUBFXMIN':"1",
              'SUBFXMAX':"2048",
              'SUBFYMIN':"1",
              'SUBFYMAX':"2048",
              'COOLER':"'Unknown'",
              'TEMPSTAT':"'Unknown",
              'FILTERID':"'Unknown'",
              'FILTER':"-1",
              'XYSTAGE':"'9999,9999'",
              'MIRROR':"'Unknown'",
              'RA_OBJ':"0.0",
              'RA':"'00:00:00'",
              'DEC_OBJ':"0.0",
              'DEC':"'00:00:00'",
              'EQUINOX':"0"
              }

defcomments = {'OBSERVAT':"'Observatory name'",
               'LATITUDE':"'Telescope latitude (south=negative)'",
               'LONGITUD':"'Telescope longitude (east=negative)'",
               'SATLEVEL':"'Sat threshold, in e-, not inc. bias offset'",
               'DATE-OBS':"'Date of start of exposure'",
               'TIME-OBS':"'Time of start of exposure'",
               'OBSERVER':"'Name of observer'",
                 'NAXIS1':"'Fastest changing axis'",
                 'NAXIS2':"'Next fastest changing axis'",
                'CCDXBIN':"'Horizontal binning factor'",
                'CCDYBIN':"'Vertical binning factor'",
                'CCDTEMP':"'CCD temperature in degrees C'",
                 'SECPIX':"'Arcsec/pixel with current binning factor'",
                'SHUTTER':"'Internal shutter mode during exposure'",
                   'GAIN':"'Total system gain in electrons per ADU'",
                'PREGAIN':"'PreAmp gain setting (x1.0, x2.0, or x4.0)'",
                'HSSPEED':"'Horizontal pixel readout frequency'",
                'VSSPEED':"'Vertical shift time, in microseconds'",
                'RONOISE':"'Estimated readout noise in electrons per pixel'",
               'SUBFXMIN':"'Subframe min X in unbinned raw coords, 1-2048'",
               'SUBFXMAX':"'Subframe max X in unbinned raw coords, 1-2048'",
               'SUBFYMIN':"'Subframe min Y in unbinned raw coords, 1-2048'",
               'SUBFYMAX':"'Subframe max Y in unbinned raw coords, 1-2048'",
                 'COOLER':"'Peltier cooler power'",
               'FILTERID':"'Filter name'",
                 'FILTER':"'Filter slot number (0-7)'",
                'XYSTAGE':"'Coordinates of offset guider stage'",
                 'MIRROR':"'Either IN (camera open to sky) or OUT (camera obscured)'",
                 'RA_OBJ':"'Right Ascension, in decimal degrees'",
                     'RA':"'Right Ascension, in hours:minutes:seconds'",
                'DEC_OBJ':"'Declination, in decimal degrees'",
                    'DEC':"'Declination, in degrees:minutes:seconds'",
                'EQUINOX':"'Equinox of coordinates'"
              }


# Create re-usable pointers to floats, ints, uints and longs for the C-library to return values
f1,f2,f3 = pyandor.floatp(), pyandor.floatp(), pyandor.floatp()
i1,i2,i3,i4,i5,i6 = pyandor.intp(), pyandor.intp(), pyandor.intp(), pyandor.intp(), pyandor.intp(), pyandor.intp()
u1,u2,u3,u4,u5,u6 = pyandor.uintp(), pyandor.uintp(), pyandor.uintp(), pyandor.uintp(), pyandor.uintp(), pyandor.uintp()
l1,l2,l3 = pyandor.longp(), pyandor.longp(), pyandor.longp()

retval = 0


class CameraStatus:
  """Andor camera status information
  """
  def empty(self):
    "Called by __init__ or manually to clear status"
    self.initialized = False
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
    self.shuttermode = 0     #0 for auto, 1 for open, 2 for close - unique to Andor
    self.imgtype = 'OBJECT'  #or 'BIAS', 'DARK', or 'FLAT'
    self.object = ''         #Object name
    #Cropping boundaries - note boundaries are INDEPENDENT of binning, so 2048x2048 is always
    #  the full image, no matter what the binning factors are. However, these values must be
    #  exactly divisible by the binning factor for the given axis.
    self.xmin,self.xmax = 1,2048   #Cropping boundaries for X
    self.ymin,self.ymax = 1,2048   #Cropping boundaries for Y
    self.roi = (self.xmin,self.xmax,self.ymin,self.ymax)
    self.xbin = 2             #Horizontal (X) binning factor, 1-2048
    self.ybin = 2             #Vertical (Y) binning factor, 1-2048
    #Exposure time and file name/path parameters
    self.exptime = 0.0
    self.path = '/data'
    self.filename = 'andor'
    self.nextfile = ''
    self.lastfile = ''
    self.filectr = 0
    self.observer = ''
    #Optical coupler setting parameters
    self.filter = -1
    self.guider = (9999,9999)
    self.mirror = 'IN'
    #Parameters unique to Apogee camera
    self.shutter = 0  #Is shutter open?
    self.xover = 0    #Overscan columns in X
    self.yover = 0    #Overscan rows in Y
    self.tmin = 0     #Temp at minimum reachable
    self.tmax=0       #Temp at maximum reachable
    self.inst=''
    self.ic=0
    self.tc=0
    self.ie=0

  def display(self):
    "Tells the status object to display itself to the screen"
    print 'mode=', self.mode
    print 'temp=', self.temp
    print 'settemp=', self.settemp
    print 'shutter=', self.shutter
    print 'exptime=', self.exptime
    print 'filter=', self.filter,' = ', filtname(self.filter)
    print 'guider=' ,self.guider
    print 'mirror=', self.mirror
    print 'xbin,ybin=', self.xbin, ',', self.ybin
    print 'roi=', self.roi
    print 'xover,yover=', self.xover, ',', self.yover
    print 'imgtype=', '"' + self.imgtype + '"'
    print 'object=', '"' + self.object + '"'
    print 'path, nextfile=', '"' + self.path + '", "' + self.nextfile + '"'
    print 'Observer=','"' + self.observer + '"'
    print 'last file=', '"' + self.lastfile + '"'
    print 'cool, tset, tmin, tmax=', self.cool, ',', self.tset, ',', self.tmin, ',', self.tmax
    print 'filectr=', self.filectr
    print 'instrument=', '"' + self.inst + '"'
    print 'ic,tc,ie=', self.ic, ',', self.tc, ',', self.ie

  def __init__(self):
    "Called automatically when instance is created"
    self.empty()

  def updated(self):
    "Called when status object changes, override to do something with the data"
    #In an overriding function, this could output to SQL or web page
    if not connected:
      return 0
    f = open('/tmp/camerastatus','w')
    cPickle.dump(self,f)
    f.close()


class CameraError:
  def __init__(self,value):
    self.value=value
  def __str__(self):
    return `self.value`


def init():     #Call this after creating a global status object
  "Initialise Andor connection"
  global connected
  swrite("Python Andor interface initialising:")
  try:
    Initialize()
    Setup()
  except:
    raise CameraError("Andor in use or not reachable")
    connected = 0
  else:
    if status.initialized:
      connected = 1
    else:
      raise CameraError('Andor initialization failed.')
  status.display()


def procret(val=20001, fname="<not set>"):
  """Given a return value and function name, do something with them...
  """
  global retval
  retval = val
  if val: 
    if debug or (val <> pyandor.DRV_SUCCESS):       #20002
      print 'Function %s:-> %d = %s' % (fname, val, DRV_ERRS[val])


def retok():
  """Returns true if the contents of global variable 'retval'
     indicate a succesful function call.
  """
  return retval == pyandor.DRV_SUCCESS     #20002


def GetCapabilities():
  ac = pyandor.AndorCapabilities()
  ac.initsize()
  procret(pyandor.GetCapabilities(ac),'GetCapabilities')
  for group,value in CAPS.items():
    if ac.__getattr__(group) <> value:
      print "New Capability: group %s is now %d, not %d. Update Andor.py source." % (group,ac.__getattr__(group),value)
  return ac


def Initialize(verbose=True):
  procret(pyandor.Initialize(AndorPath), 'Initialize')
  if retok():
    status.initialized = True
    if verbose:
      print "Driver initialized OK"


def CoolerON(verbose=True):
  procret(pyandor.CoolerON(), 'CoolerON')
  if retok():
    status.cool = True
    if verbose:
      print "Peltier cooler turned ON"


def CoolerOFF(verbose=True):
  procret(pyandor.CoolerOFF(), 'CoolerOFF')
  if retok():
    status.cool = False
    if verbose:
      print "Peltier cooler turned OFF"


def SetHSSpeed(n, verbose=True):
  if n in HSSpeeds.keys():
    procret(pyandor.SetHSSpeed(0,n), 'SetHSSpeed')
    if retok():
      status.hsspeed = n
      GetAcquisitionTimings(verbose=verbose)
      if verbose:
        print "Horizontal Shift Speed set to %d (%s)" % (n, HSSpeeds[n])
  else:
    print "Invalid HSSpeed index: %d" % n
      

def SetVSSpeed(n, verbose=True):
  if n in VSSpeeds.keys():
    procret(pyandor.SetVSSpeed(n),'SetVSSpeed')
    if retok():
      status.vsspeed = n
      GetAcquisitionTimings(verbose=verbose)
      if verbose:
        print "Vertical Shift Speed set to %d (%s)" % (n, VSSpeeds[n])
  else:
    print "Invalid VSSpeed index: %d" % n


def SetPreAmpGain(n, verbose=True):
  if n in PreAmpGains.keys():
    procret(pyandor.SetPreAmpGain(n),'SetPreAmpGain')
    if retok():
      status.preamp = n
      GetAcquisitionTimings(verbose=verbose)
      if verbose:
        print "PreAmp gain set to %d (%s)" % (n, PreAmpGains[n])
  else:
    print "Invalid PreAmp gain index: %d" % n


def SetHighCapacity(mode, verbose=True):
  if (type(mode)==str) and (len(mode)>0):
    if ( (mode[0].upper() == 'Y') or
         (mode.upper() == 'ON') ):
      mode = True
    else:
      mode = False
  else:
    mode = bool(mode)
  procret(pyandor.SetHighCapacity(mode),'SetHighCapacityMode')
  if retok():
    status.highcap = mode
    GetAcquisitionTimings(verbose=verbose)
    if verbose:
      print "High Capacity mode turned %s." % {True:'ON', False:'OFF'}[mode]


def SetTemperature(t, verbose=True):
  procret(pyandor.SetTemperature(int(t)),'SetTemperature')
  if retok():
    status.settemp = int(t)
    if verbose:
      print "Cooler setpoint changed to %d" % int(t)
      

def GetTemperature(verbose=True):
  global retval
  rv = pyandor.GetTemperatureF(f1)
  retval = rv
  if rv == pyandor.DRV_NOT_INITIALIZED or rv == pyandor.DRV_ERROR_ACK:
    f1.assign(999.9)
    status.tempstatus = 'Error getting temperature'
    if verbose:
      print "Error getting temperature data"
  else:
    status.temp = f1.value()
    if rv == pyandor.DRV_TEMP_OFF:
      status.tempstatus = 'Temperature OFF'
      status.cool = False
      status.tset = False
    elif rv == pyandor.DRV_TEMP_NOT_REACHED:
      status.tempstatus = 'Set Temp not yet reached'
      status.cool = True
      status.tset = False
    elif rv == pyandor.DRV_TEMP_NOT_STABILIZED:
      status.tempstatus = 'Set Temp reached, but not yet stabilized'
      status.cool = True
      status.tset = False
    elif rv == pyandor.DRV_TEMP_STABILIZED:
      status.tempstatus = 'Temp Stabilized'
      status.cool = True
      status.tset = True
    elif rv == pyandor.DRV_TEMP_DRIFT:
      status.tempstatus = 'Temp was Stabilized, but has since drifted'
      status.cool = True
      status.tset = False

    if verbose:
      print "Temp=%6.2f  status='%s'" % (f1.value(),status.tempstatus)
  return f1.value()


def SetSubimage(xmin,xmax,ymin,ymax, verbose=True):
  procret(pyandor.SetImage(status.xbin,status.ybin,xmin,xmax,ymin,ymax), 'SetImage')
  if retok():
    status.xmin, status.xmax = xmin,xmax
    status.ymin, status.ymax = ymin,ymax
    status.roi = (xmin,xmax,ymin,ymax)
    GetAcquisitionTimings(verbose=verbose)
    if verbose:
      print "Subimage cropping set to %d-%d, %d-%d" % (xmin,xmax,ymin,ymax)


def SetBinning(xbin,ybin, verbose=True):
  procret(pyandor.SetImage(xbin,ybin,status.xmin,status.xmax,status.ymin,status.ymax), 'SetImage')
  if retok():
    status.xbin = xbin
    status.ybin = ybin
    GetAcquisitionTimings(verbose=verbose)
    if verbose:
      print "Binning set to %d horizontal (x), %d vertical (y)" % (xbin, ybin)


def SetShutter(mode=0, verbose=True):
  """mode=0 for auto, 1 for open, 2 for close
  """
  procret(pyandor.SetShutter(0,mode,SHUTTERCLOSE,SHUTTEROPEN), 'SetShutter')
  if retok: 
    status.shuttermode = mode
    if verbose:
      print "Shutter mode set to %d (%s)" % (mode, {0:'Auto', 1:'Always Open', 2:'Always Closed'} )


def GetAcquisitionTimings(verbose=True):
  procret(pyandor.GetAcquisitionTimings(f1,f2,f3),'GetAcquisitionTimings')
  if retok():
    status.exptime = round(f1.value(),3)
    status.cycletime = round(f2.value(),3)
    status.readouttime = round(f2.value()-f1.value(),3)


def exptime(et, verbose=True):
  """Set camera exposure time, in seconds.
  """
  procret(pyandor.SetExposureTime(et), 'SetExposureTime')
  if retok():
    GetAcquisitionTimings(verbose=verbose)
    if verbose:
      print "Exposure time set to %6.3f seconds" % status.exptime


def ShutDown():
  procret(pyandor.ShutDown(),'ShutDown')


def SetMode(mode='bin2slow'):
  """Set a bunch of camera parameters for a predefined mode
  """
  if mode == 'bin2slow':
    SetSubimage(1,XSIZE,1,YSIZE)
    SetBinning(2,2)      #1k x 1k, 27um pixels
    SetHSSpeed(3)        #50kHz, ~20 sec readout at 2x2 binning
    SetVSSpeed(1)        #77ms
    SetPreAmpGain(0)     #Gain of 1.0. Note, use PreAmpGain=2 (4.0) for 1x1 binning.
    SetHighCapacity(False)
  if mode == 'bin2fast':
    SetSubimage(1,XSIZE,1,YSIZE)
    SetBinning(2,2)      #1k x 1k, 27um pixels
    SetHSSpeed(2)        #1MHz, ~1 sec readout at 2x2 binning
    SetVSSpeed(1)        #77ms
    SetPreAmpGain(0)     #Gain of 1.0. Note, use PreAmpGain=2 (4.0) for 1x1 binning.
    SetHighCapacity(False)
  elif mode == 'unbinslow':
    SetSubimage(1,XSIZE,1,YSIZE)
    SetBinning(1,1)      #2k x 2k, 13.5um pixels
    SetHSSpeed(3)        #50kHz, ~84 sec readout at 1x1 binning
    SetVSSpeed(1)        #77ms
    SetPreAmpGain(2)     #Gain of 4.0. Note, use PreAmpGain=0 (1.0) for 2x2 binning.
    SetHighCapacity(False)
  elif mode == 'unbinfast':
    SetSubimage(1,XSIZE,1,YSIZE)
    SetBinning(1,1)      #2k x 2k, 13.5um pixels
    SetHSSpeed(2)        #1MHz, ~4 sec readout at 1x1 binning
    SetVSSpeed(1)        #77ms
    SetPreAmpGain(2)     #Gain of 4.0. Note, use PreAmpGain=0 (1.0) for 2x2 binning.
    SetHighCapacity(False)
  elif mode == 'centre':
    SetSubimage(897,1152,897,1152)   #256x256 unbinned or 128x128 binned
    SetBinning(2,2)      #1k x 1k, 27um pixels
    SetHSSpeed(2)        #1MHz, ~1 sec readout at 2x2 binning
    SetVSSpeed(1)        #77ms
    SetPreAmpGain(0)     #Gain of 1.0. Note, use PreAmpGain=2 (4.0) for 1x1 binning.
    SetHighCapacity(False)
  else:
    print "Invalid SetParams mode: %s" % mode
    return
  status.mode = mode



def Setup():
  procret(pyandor.SetReadMode(4), 'SetReadMode')    #Full image
  procret(pyandor.SetAcquisitionMode(1), 'SetAcquisitionMode')   #Single image
  status.imgtype = 'OBJECT'
  SetShutter(0)
  SetMode('bin2slow')
# CoolerOn()
# SetTemperature(-50)
  GetTemperature()


def GetFits():
  global retval
  temps = []     #Individual CCD temp values during exposure
  stime = time.gmtime()
  stemp = GetTemperature()
  procret(pyandor.StartAcquisition(), 'StartAcquisition')
  if not retok():
    return "Failed to StartAcquisition"
  if status.exptime < MAX_NOLOOPTIME:    #Don't loop 
    procret(pyandor.WaitForAcquisition(), 'WaitForAcquisition')
    if not retok():
      return "Failed to WaitAcquisition"
  else:
    done = False
    while not done:
      rv1 = pyandor.WaitForAcquisitionTimeOut(LOOPTIME*1000)
      rv2 = pyandor.GetStatus(i1)
      temps.append(GetTemperature(verbose=False))
      if ( (i1.value() <> pyandor.DRV_ACQUIRING) or      #System is not acquiring an image
           (rv2 <> pyandor.DRV_SUCCESS) ):                 #Error getting status from camera
        done = True
    if rv2 <> pyandor.DRV_SUCCESS:
      procret(rv2)
      return "Failed to GetStatus during acquisition wait loop"
  etime = time.gmtime()
  etemp = GetTemperature()
  if temps:
    temps.append(stemp)
    ccdtemp = reduce(lambda x, y: x+y, temps)/len(temps)
  else:
    ccdtemp = (etemp+stemp)/2.0

  f = FITS()
  f.headers.update(defheaders)
  f.comments.update(defcomments)
  rxsize = status.xmax-status.xmin+1
  rysize = status.ymax-status.ymin+1
  numpixels = (rxsize*rysize)/(status.xbin*status.ybin)
#  f.data = fits.zeros(numpixels, dtype=fits.float32)
#  procret(pyandor.GetAcquiredFloatData(f.data), 'GetAcquiredFloatData')
  data = fits.zeros(numpixels, dtype=fits.int32)   #Will only work with numpy
  procret(pyandor.GetMostRecentImage(data),'GetMostRecentImage')
  f.data = data.astype(fits.float32)
  if not retok():
    return
  xsize = rxsize/status.xbin
  ysize = rysize/status.ybin
  f.data.shape = (xsize,ysize)
  f.headers['NAXIS1'] = `xsize`
  f.headers['NAXIS2'] = `ysize`
  f.headers['OBSERVER'] = "'%s'" % status.observer
  f.headers['DATE-OBS'] = "'%d-%02d-%02d'" % (stime.tm_year, stime.tm_mon, stime.tm_mday)
  f.headers['TIME-OBS'] = "'%02d:%02d:%02d'" % (stime.tm_hour, stime.tm_min, stime.tm_sec)
  f.headers['COOLER'] = "'%s'" % {False:'OFF', True:'ON'}[status.cool]
  f.headers['TEMPSTAT'] = "'%s'" % status.tempstatus
  f.headers['CCDTEMP'] = "%6.2f" % ccdtemp
  f.headers['MODE'] = "'%s'" % status.mode
  f.headers['CCDXBIN'] = `status.xbin`
  f.headers['CCDYBIN'] = `status.ybin`
  if status.xbin == status.ybin:
    f.headers['SECPIX'] = "%6.4f" % (SECPIX*status.xbin)
  f.headers['SHUTTER'] = {0:"'OPEN'", 1:"'STAY OPEN'", 2:"'CLOSED'"}[status.shuttermode]
  f.headers['GAIN'] = "%6.3f" % CurrentGain()
  f.headers['RONOISE'] = "%6.3f" % CurrentNoise()
  f.headers['SATADU'] = "%d" % CurrentSaturation()
  f.headers['HSSPEED'] = "'%s'" % HSSpeeds[status.hsspeed]
  f.headers['VSSPEED'] = "'%s'" % VSSpeeds[status.vsspeed]
  f.headers['PREGAIN'] = "'%s'" % PreAmpGains[status.preamp]
  f.headers['ROMODE'] = "'%s'" % {False:'High Sensitivity Mode', True:'High Capacity Mode for high binning factors'}[status.highcap]
  f.headers['SUBFXMIN'] = `status.xmin`
  f.headers['SUBFXMAX'] = `status.xmax`
  f.headers['SUBFYMIN'] = `status.ymin`
  f.headers['SUBFYMAX'] = `status.ymax`
  if status.imgtype == 'BIAS':
    f.headers['BIAS'] = status.object
  elif status.imgtype == 'DARK':
    f.headers['DARK'] = status.object
  else:
    f.headers['OBJECT'] = status.object

  return f



def OldGetFits(fname='/tmp/out.fits', bitpix=16):
  """args: fname is the filename
           bitpix is the output format (16, 32, or -32)
  """
  pyandor.StartAcquisition()
  pyandor.WaitForAcquisition()
  pyandor.SaveAsRaw('/tmp/andor.raw',2)
  f = FITS()
  fraw = open('/tmp/andor.raw','r').read()
  f.data = fits.fromstring(fraw,fits.Int32)
  f.data.shape = (HSIZE/hbin,VSIZE/vbin)
  f.headers['NAXIS1'] = HSIZE/hbin
  f.headers['NAXIS2'] = VSIZE/vbin
  f.save(fname, bitpix=bitpix)



connected=0
if __name__ == '__main__':
  status = AndorStatus()

