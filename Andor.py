#!/usr/bin/python
#
# TODO - investigate SetCoolerMode function that defines whether cooler is kept on after a ShutDown call, or turned off
#
#      - Bomb-proof the cooling so that ShutDown isn't called until the cooler is warmer than -20C, and the system
#        is ALWAYS called on exit
#
#      -Use functions like IsCoolerOn() to detect state on startup, and in an update() method to the status class
#
#
import time
import sys
import Pyro4
#Pyro4.config.HMAC_KEY = "Froople, Froople, Twiggle and Mice"
import traceback
import threading
import signal
import atexit
import shlex
from subprocess import Popen
import logging

import pyandor
import fits
import improc
import globals
from globals import *


if __name__ == '__main__':
  globals.SERVER = True
  globals.CLIENT = False
  filef = logging.Formatter("%(asctime)s: %(name)s-%(levelname)s (%(threadName)-10s) %(message)s")
  conf = logging.Formatter("%(name)s-%(levelname)s (%(threadName)-10s) %(message)s")

  try:
    sfh = logging.FileHandler(LOGFILES['Server'])
  except IOError:    #Can't open a logfile for writing, probably the wrong user
    sfh = logging.NullHandler()

  sfh.setLevel(LOGLEVELS['Server']['File'])
  sfh.setFormatter(filef)

  # create console handler with a different log level, and without timestamps
  conh = logging.StreamHandler(sys.stdout)
  conh.setLevel(LOGLEVELS['Server']['Console'])
  conh.setFormatter(conf)

  # create global logger object
  logger = logging.getLogger("Andor")
  logger.setLevel(MLOGLEVEL)

  # add the handlers to the logger
  logger.addHandler(sfh)
  logger.addHandler(conh)

  #Make it the default logger for everything else in this process that imports 'globals'
  globals.logger = logger


FITS = improc.FITS

pyro_thread = None
ns_process = None

SIGNAL_HANDLERS = {}
CLEANUP_FUNCTION = None

exitnow = False   #Set to true to force program exit.

AndorPath = '/usr/local/etc/andor' + ('\x00'*100)

MODES = ['bin1slow', 'bin1fast', 'bin2slow', 'bin2fast', 'centre']


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
  """Return the saturation level, in ADU, for the given
     camera readout parameters.
  """
  return SATLEVEL/GAIN[hsspeed][preamp][highcap]


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


  'ulGetFunctions':32781,#AC_GETFUNCTION_TEMPERATURE 0x01, AC_GETFUNCTION_TEMPERATURERANGE 0x04, AC_GETFUNCTION_DETECTORSIZE 0x08
                         #AC_GETFUNCTION_BASELINECLAMP 0x8000
                         #  (not capable of getting target temperature or many other undocumented modes)

  'ulFeatures':6948781,  #AC_FEATURES_POLLING 1, AC_FEATURES_SPOOLING 4, AC_FEATURES_SHUTTER 8, AC_FEATURES_EXTERNAL_I2C 32
                         #AC_FEATURES_FANCONTROL 128, AC_FEATURES_MIDFANCONTROL 256, AC_FEATURES_TEMPERATUREDURINGACQUISITION 512
                         #AC_FEATURES_KEEPCLEANCONTROL 1024, AC_FEATURES_PHOTONCOUNTING 0x20000, AC_FEATURES_DUALMODE 0x80000
                         #AC_FEATURES_REALTIMESPURIOUSNOISEFILTER 0x200000, AC_FEATURES_POSTPROCESSSPURIOUSNOISEFILTER 0x400000
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
              'EXPTIME':"0.0",
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
              'SATADU':0,
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
                'EXPTIME':"'Exposure time in seconds'",
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
                 'SATADU':"'Estimated saturation level in ADU per (binned) pixel'",
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
f1.assign(0.0)
f2.assign(0.0)
f3.assign(0.0)

i1,i2,i3,i4,i5,i6 = pyandor.intp(), pyandor.intp(), pyandor.intp(), pyandor.intp(), pyandor.intp(), pyandor.intp()
i1.assign(0)
i2.assign(0)
i3.assign(0)
i4.assign(0)
i5.assign(0)
i6.assign(0)

u1,u2,u3,u4,u5,u6 = pyandor.uintp(), pyandor.uintp(), pyandor.uintp(), pyandor.uintp(), pyandor.uintp(), pyandor.uintp()
u1.assign(0)
u2.assign(0)
u3.assign(0)
u4.assign(0)
u5.assign(0)

l1,l2,l3 = pyandor.longp(), pyandor.longp(), pyandor.longp()
l1.assign(0)
l2.assign(0)
l3.assign(0)

retval = 0



def retok():
  """Returns true if the contents of global variable 'retval'
     indicate a succesful function call.
  """
  return retval == pyandor.DRV_SUCCESS     #20002



class CameraError(object):
  """Used to flag errors with the Andor camera.
  """
  def __init__(self,value):
    self.value=value
  def __str__(self):
    return `self.value`



class CameraStatus(object):
  """Andor camera status information
  """
  def empty(self):
    """Called by __init__ or manually to clear status"""
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

  def update(self):
    """Given a dict, update the attributes of this object with the
       values in the dict specified.
    """
    if type(camera) == Pyro4.core.Proxy:    #We are instantiated in a client proxy object
      self.__dict__.update(camera.getStatus())
    else:
      pass

  def __str__(self):
    """Tells the status object to display itself to the screen"""
    s = 'mode = %s\n' % self.mode
    s += 'temp = %4.1f\n' % self.temp
    s += 'settemp = %4.1f\n' % self.settemp
    s += 'imaging = %s\n' % {False:'No', True:'YES'}[self.imaging]
    s += 'exptime = %8.3f\n' % self.exptime
    s += 'xbin,ybin = (%d,%d)\n' % (self.xbin, self.ybin)
    s += 'roi = (%d,%d,%d,%d)\n' % self.roi
    s += 'Errors: %s\n' % self.errors
    return s

  def __repr__(self):
    return str(self)

  def __init__(self):
    """Called automatically when instance is created"""
    self.empty()




class Camera(object):
  """Represents an instance of an Andor CCD camera.
     In the main 'Andor' executable, this handles all communication with the camera, and this
     object is shared via Pyro. In clients, a proxy to this object allows methods to be called
     remotely.
  """
  #####  Private methods, not available to the proxy client  #############
  def __init__(self):
    self.status = CameraStatus()
    self.lock = threading.RLock()

  def _procret(self, val=20001, fname="<not set>"):
    """Use this method to wrap all calls to the low-level Andor
       library (SWIG wrapper). The wrapper parses the driver return code,
       sets the 'retval' global to that returned value, and logs the
       response (converted to text). The 'fname' argument should contain the
        name of the function called, used to make the logged message more useful.
    """
    global retval
    retval = val
    mesg = 'Function %s:-> %d = %s' % (fname, val, DRV_ERRS[val])
    if val:
      if val <> pyandor.DRV_SUCCESS:       #20002
        logger.error(mesg)
        self.status.errors.append( (time.time(),mesg) )
        return mesg
      else:
        logger.debug(mesg)
        return ''

  def _GetAvailableCameras(self):
    """This function returns the total number of Andor cameras currently installed. It's possible
       to call this function before (the/a) camera has been initialised.
    """
    mesg = self._procret(pyandor.GetAvailableCameras(l1), 'GetAvailableCameras')
    num = int(l1.value())
    if mesg:
      logger.error(mesg)
    return num

  def _GetCameraHandle(self, i):
    """Return the 'handle' corresponding to the installed Andor camera with an index of
       '0' (0 means the first installed camera, 1 is the second, etc).

      Returns a 'long' object, to be passed directly to the 'SetCurrentCamera' function.
    """
    l1.assign(i)
    mesg = self._procret(pyandor.GetCameraHandle(l1.value(), l2), 'GetCameraHandle')
    if mesg:
      logger.error(mesg)
    return l2

  def _SetCurrentCamera(self, handle):
    mesg = self._procret(pyandor.SetCurrentCamera(handle.value()), 'SetCurrentCamera')
    if mesg:
      logger.error(mesg)
    return mesg

  def _GetCapabilities(self):
    """Grab the current camera capabilities, and compare them to the values stored in
       record above. If there's a difference, it means the Andor driver has been updated,
       and new capabilities are available. If so, inspect the .h file, read the new
       driver docs, and update the source code.
    """
    ac = pyandor.AndorCapabilities()
    ac.initsize()
    mesg = self._procret(pyandor.GetCapabilities(ac), 'GetCapabilities')
    for group,value in CAPS.items():
      if ac.__getattr__(group) <> value:
        mesg += "New Capability: group %s is now %d, not %d. Update Andor.py source.\n" % (group,ac.__getattr__(group),value)
    if mesg:
      logger.error(mesg)
    return mesg

  def _SetHSSpeed(self, n=2):
    if n in HSSpeeds.keys():
      mesg = self._procret(pyandor.SetHSSpeed(0,n), 'SetHSSpeed')
      if retok():
        self.status.hsspeed = n
        self._GetAcquisitionTimings()
        mesg = "Horizontal Shift Speed set to %d (%s)" % (n, HSSpeeds[n])
        logger.info(mesg)
    else:
      mesg = "Invalid HSSpeed index: %d" % n
      logger.error(mesg)
      self.status.errors.append( (time.time(),mesg) )
    return mesg

  def _SetVSSpeed(self, n=1):
    if n in VSSpeeds.keys():
      mesg = self._procret(pyandor.SetVSSpeed(n), 'SetVSSpeed')
      if retok():
        self.status.vsspeed = n
        self._GetAcquisitionTimings()
        mesg = "Vertical Shift Speed set to %d (%s)" % (n, VSSpeeds[n])
        logger.info(mesg)
    else:
      mesg = "Invalid VSSpeed index: %d" % n
      logger.error(mesg)
      self.status.errors.append( (time.time(),mesg) )
    return mesg

  def _SetPreAmpGain(self, n=0):
    if n in PreAmpGains.keys():
      mesg = self._procret(pyandor.SetPreAmpGain(n), 'SetPreAmpGain')
      if retok():
        self.status.preamp = n
        self._GetAcquisitionTimings()
        mesg = "PreAmp gain set to %d (%s)" % (n, PreAmpGains[n])
        logger.info(mesg)
    else:
      mesg = "Invalid PreAmp gain index: %d" % n
      logger.error(mesg)
      self.status.errors.append( (time.time(),mesg) )
    return mesg

  def _SetHighCapacity(self, mode=False):
    if (type(mode)==str) and (len(mode)>0):
      if ( (mode[0].upper() == 'Y') or
           (mode.upper() == 'ON') ):
        mode = True
      else:
        mode = False
    else:
      mode = bool(mode)
    mesg = self._procret(pyandor.SetHighCapacity(mode), 'SetHighCapacityMode')
    if retok():
      self.status.highcap = mode
      self._GetAcquisitionTimings()
      mesg = "High Capacity mode turned %s." % {True: 'ON', False: 'OFF'}[mode]
      logger.info(mesg)
    return mesg

  def _SetSubimage(self, xmin,xmax,ymin,ymax):
    mesg = self._procret(pyandor.SetImage(self.status.xbin,self.status.ybin,xmin,xmax,ymin,ymax), 'SetImage')
    if retok():
      self.status.xmin, self.status.xmax = xmin,xmax
      self.status.ymin, self.status.ymax = ymin,ymax
      self.status.roi = (xmin,xmax,ymin,ymax)
      self._GetAcquisitionTimings()
      mesg = "Subimage cropping set to %d-%d, %d-%d" % (xmin, xmax, ymin, ymax)
      logger.info(mesg)
    return mesg

  def _SetBinning(self, xbin,ybin):
    mesg = self._procret(pyandor.SetImage(xbin,ybin,self.status.xmin,self.status.xmax,self.status.ymin,self.status.ymax), 'SetImage')
    if retok():
      self.status.xbin = xbin
      self.status.ybin = ybin
      self._GetAcquisitionTimings()
      mesg = "Binning set to %d horizontal (x), %d vertical (y)" % (xbin, ybin)
      logger.info(mesg)
    return mesg

  def _GetAcquisitionTimings(self):
    mesg = self._procret(pyandor.GetAcquisitionTimings(f1,f2,f3),'GetAcquisitionTimings')
    if retok():
      self.status.exptime = round(f1.value(),3)
      self.status.cycletime = round(f2.value(),3)
      self.status.readouttime = round(f2.value()-f1.value(),3)
      mesg = "exptime=%8.3f, cycletime=%8.3f, readouttime=%5.3f" % (self.status.exptime, self.status.cycletime, self.status.readouttime)
    return mesg

  def _Initialize(self):
    mesg = self._procret(pyandor.Initialize(AndorPath), 'Initialize')
    if retok():
      self.status.initialized = True
      mesg = "Driver initialized OK"
      logger.info(mesg)
    return mesg

  def _Setup(self):
    with self.lock:
      mesg = self._procret(pyandor.SetReadMode(4), 'SetReadMode')    #Full image
      mesg += self._procret(pyandor.SetAcquisitionMode(1), 'SetAcquisitionMode')   #Single image
      mesg += self.SetShutter(0)
      mesg += self.SetMode('bin2slow')
      mesg += self.exptime(0.1)
      self.GetTemperature()
    return mesg

  def _ShutDown(self):
    mesg = self._procret(pyandor.ShutDown(),'ShutDown')
    if retok():
      self.status.initialized = False
      mesg = "Andor camera API shut down"
      self.status.errors.append( (time.time(), mesg) )
    return mesg

  def _servePyroRequests(self):
    """When called, start serving Pyro requests.
    """
    while True:
      logger.info("Starting AndorCamera Pyro4 server")
      try:
        ns = Pyro4.locateNS()
      except:
        logger.error("Can't locate Pyro nameserver - waiting 10 sec to retry")
        time.sleep(10)
        break

      try:
        existing = ns.lookup("AndorCamera")
        logger.info("AndorCamera still exists in Pyro nameserver with id: %s" % existing.object)
        logger.info("Previous Pyro daemon socket port: %d" % existing.port)
        # start the daemon on the previous port
        pyro_daemon = Pyro4.Daemon(host='animal', port=existing.port)
        # register the object in the daemon with the old objectId
        pyro_daemon.register(self, objectId=existing.object)
      except Pyro4.errors.NamingError:
        # just start a new daemon on a random port
        pyro_daemon = Pyro4.Daemon(host='animal')
        # register the object in the daemon and let it get a new objectId
        # also need to register in name server because it's not there yet.
        uri =  pyro_daemon.register(self)
        ns.register("AndorCamera", uri)
      try:
        pyro_daemon.requestLoop()
      except:
        logger.error("Exception in AndorCamera Pyro4 server. Restarting in 10 sec: %s" % (traceback.format_exc(),))
        time.sleep(10)

  #####  Public methods, available to the proxy client  #############

  def Exit(self, reason):
    """Flag an immediate exit - the main loop will detect this and exit
       cleanly, calling the cleanup function to Lock the camera, start the CCD warming, and
       wait for the temp to hit -20C before calling _ShutDown() and exiting.
    """
    global exitnow
    mesg = 'Exit() method called: %s' % reason
    logger.info(mesg)
    self.status.errors.append( (time.time(),mesg) )
    exitnow = True
    return mesg

  def getStatus(self):
    """Return the status object - needed for use by proxies, since attributes
       don't work.
    """
    return self.status.__dict__

  def Lock(self):
    self.lock.acquire()

  def Unlock(self):
    self.lock.release()

  def SetMode(self, mode='bin2slow'):
    """Set a bunch of camera parameters for a predefined mode
    """
    if (type(mode) != str) or (mode.lower() not in MODES):
      mesg = 'Invalid readout mode: %s not in %s' % (mode, MODES)
      logger.error(mesg)
      self.status.errors.append( (time.time(),mesg) )
      return mesg
    if mode.lower() == 'bin2slow':
      roi = (1,XSIZE,1,YSIZE)
      bin = (2,2)       #1k x 1k, 27um pixels
      hspeed = 3        #50kHz, ~20 sec readout at 2x2 binning
      vspeed = 1        #77ms
      gain = 0          #Gain of 1.0. Note, use PreAmpGain=2 (4.0) for 1x1 binning.
      hcap = False
    elif mode.lower() == 'bin2fast':
      roi = (1,XSIZE,1,YSIZE)
      bin = (2,2)       #1k x 1k, 27um pixels
      hspeed = 2        #1MHz, ~1 sec readout at 2x2 binning
      vspeed = 1        #77ms
      gain = 0          #Gain of 1.0. Note, use PreAmpGain=2 (4.0) for 1x1 binning.
      hcap = False
    elif mode.lower() == 'bin1slow':
      roi = (1,XSIZE,1,YSIZE)
      bin = (1,1)       #2k x 2k, 13.5um pixels
      hspeed = 3        #50kHz, ~20 sec readout at 2x2 binning
      vspeed = 1        #77ms
      gain = 2          #Gain of 4.0. Note, use PreAmpGain=0 (1.0) for 2x2 binning.
      hcap = False
    elif mode.lower() == 'bin1fast':
      roi = (1,XSIZE,1,YSIZE)
      bin = (1,1)       #2k x 2k, 13.5um pixels
      hspeed = 2        #1MHz, ~4 sec readout at 1x1 binning
      vspeed = 1        #77ms
      gain = 2          #Gain of 4.0. Note, use PreAmpGain=0 (1.0) for 2x2 binning.
      hcap = False
    elif mode.lower() == 'centre':
      roi = (897,1152,897,1152)
      bin = (2,2)       #1k x 1k, 27um pixels
      hspeed = 2        #1MHz, ~1 sec readout at 2x2 binning
      vspeed = 1        #77ms
      gain = 0          #Gain of 1.0. Note, use PreAmpGain=2 (4.0) for 1x1 binning.
      hcap = False
    else:
      mesg = "Invalid SetMode mode: %s" % mode
      logger.error(mesg)
      self.status.errors.append( (time.time(),mesg) )
      return mesg

    nerrors = len(self.status.errors)
    with self.lock:
      mesg = self._SetSubimage(*roi)   #256x256 unbinned or 128x128 binned
      mesg += self._SetBinning(*bin)      #1k x 1k, 27um pixels
      mesg += self._SetHSSpeed(hspeed)        #1MHz, ~1 sec readout at 2x2 binning
      mesg += self._SetVSSpeed(vspeed)        #77ms
      mesg += self._SetPreAmpGain(gain)     #Gain of 1.0. Note, use PreAmpGain=2 (4.0) for 1x1 binning.
      mesg += self._SetHighCapacity(hcap)

    if len(self.status.errors) == nerrors:
      self.status.mode = mode
      mesg = "Changed observing mode to %s" % mode
      logger.info(mesg)
    else:
      mesg += "Errors changing observing mode - INCONSISTENT STATE!"
      logger.error(mesg)
    return mesg

  def CurrentSaturation(self):
    pixsat = satadu(hsspeed=self.status.hsspeed, preamp=self.status.preamp, highcap=self.status.highcap)
    return pixsat * self.status.xbin * self.status.ybin   #Saturation per physical pixel, times the binning factors

  def CurrentGain(self):
    return GAIN[self.status.hsspeed][self.status.preamp][self.status.highcap]

  def CurrentNoise(self):
    return NOISE[self.status.hsspeed][self.status.preamp][self.status.highcap]

  def CoolerON(self):
    with self.lock:
      mesg = self._procret(pyandor.CoolerON(), 'CoolerON')
      if retok():
        self.status.cool = True
        mesg = "Peltier cooler turned ON"
        logger.info(mesg)
    return mesg

  def CoolerOFF(self):
    with self.lock:
      mesg = self._procret(pyandor.CoolerOFF(), 'CoolerOFF')
      if retok():
        self.status.cool = False
        mesg = "Peltier cooler turned OFF"
        logger.info(mesg)
    return mesg

  def SetTemperature(self, t=-10):
    with self.lock:
      mesg = self._procret(pyandor.SetTemperature(int(t)),'SetTemperature')
      if retok():
        self.status.settemp = int(t)
        mesg = "Cooler setpoint changed to %d" % int(t)
        logger.info(mesg)
    return mesg

  def GetTemperature(self):
    global retval
    with self.lock:
      rv = pyandor.GetTemperatureF(f1)
      self.status.temp = f1.value()

    retval = rv
    if rv == pyandor.DRV_NOT_INITIALIZED or rv == pyandor.DRV_ERROR_ACK:
      mesg = "Error getting temperature data"
      self.status.tempstatus = mesg
      logger.error(mesg)
      self.status.errors.append( (time.time(),mesg) )
      self.status.temp = 999.999
    else:
      if rv == pyandor.DRV_TEMP_OFF:
        self.status.tempstatus = 'Cooler OFF'
        self.status.cool = False
        self.status.tset = False
      elif rv == pyandor.DRV_TEMP_NOT_REACHED:
        self.status.tempstatus = 'Set Temp not yet reached'
        self.status.cool = True
        self.status.tset = False
      elif rv == pyandor.DRV_TEMP_NOT_STABILIZED:
        self.status.tempstatus = 'Set Temp reached, but not yet stabilized'
        self.status.cool = True
        self.status.tset = False
      elif rv == pyandor.DRV_TEMP_STABILIZED:
        self.status.tempstatus = 'Temp Stabilized'
        self.status.cool = True
        self.status.tset = True
      elif rv == pyandor.DRV_TEMP_DRIFT:
        self.status.tempstatus = 'Temp was Stabilized, but has since drifted'
        self.status.cool = True
        self.status.tset = False
      mesg = "Temp=%6.2f  status='%s'" % (f1.value(), self.status.tempstatus)
      logger.info(mesg)

    return self.status.temp

  def SetShutter(self, mode=0):
    """mode=0 for auto, 1 for open, 2 for close
    """
    with self.lock:
      mesg = self._procret(pyandor.SetShutter(0,mode,SHUTTERCLOSE,SHUTTEROPEN), 'SetShutter')
      if retok:
        self.status.shuttermode = mode
        mesg = "Shutter mode set to %d (%s)" % (mode, {0: 'Auto', 1: 'Always Open', 2: 'Always Closed'} )
        logger.info(mesg)
    return mesg

  def exptime(self, et):
    """Set camera exposure time, in seconds.
    """
    with self.lock:
      mesg = self._procret(pyandor.SetExposureTime(et), 'SetExposureTime')
      if retok():
        self._GetAcquisitionTimings()
        mesg = "Exposure time set to %6.3f seconds" % self.status.exptime
        logger.info(mesg)
    return mesg

  def GetFits(self):
    logger.info("Starting image acquisition, exposure time = %8.3f" % self.status.exptime)
    with self.lock:
      temps = []     #Individual CCD temp values during exposure
      self.status.imaging = True    #Indicate image acquisition in progress
      stime = time.gmtime()
      stemp = self.GetTemperature()
      self._procret(pyandor.StartAcquisition(), 'StartAcquisition')
      if not retok():
        logger.error("Failed to StartAcquisition")
        self.status.imaging = False    #Finished image acquisition
        return None
      if self.status.exptime < MAX_NOLOOPTIME:    #Don't loop
        self._procret(pyandor.WaitForAcquisition(), 'WaitForAcquisition')
        if not retok():
          logger.error("Failed to WaitAcquisition")
          self.status.imaging = False    #Finished image acquisition
          return None
      else:
        done = False
        while not done:
          rv1 = pyandor.WaitForAcquisitionTimeOut(LOOPTIME*1000)
          rv2 = pyandor.GetStatus(i1)
          temps.append(self.GetTemperature())
          if ( (i1.value() <> pyandor.DRV_ACQUIRING) or      #System is not acquiring an image
               (rv2 <> pyandor.DRV_SUCCESS) ):                 #Error getting status from camera
            done = True
        if rv2 <> pyandor.DRV_SUCCESS:
          self._procret(rv2)
          logger.error("Failed to GetStatus during acquisition wait loop")
          self.status.imaging = False    #Finished image acquisition
          return None
      self.status.imaging = False    #Finished image acquisition
      logger.info("Finished image acquisition")
      etemp = self.GetTemperature()
      if temps:
        temps.append(stemp)
        ccdtemp = reduce(lambda x, y: x+y, temps)/len(temps)
      else:
        ccdtemp = (etemp+stemp)/2.0

      f = FITS()
      f.headers.update(defheaders)
      f.comments.update(defcomments)
      rxsize = self.status.xmax - self.status.xmin+1
      rysize = self.status.ymax - self.status.ymin+1
      numpixels = (rxsize*rysize) / (self.status.xbin*self.status.ybin)
    #  f.data = fits.zeros(numpixels, dtype=fits.float32)
    #  self._procret(pyandor.GetAcquiredFloatData(f.data), 'GetAcquiredFloatData')
      data = fits.zeros(numpixels, dtype=fits.int32)   #Will only work with numpy
      self._procret(pyandor.GetMostRecentImage(data),'GetMostRecentImage')

    f.data = data.astype(fits.float32)
    if not retok():
      logger.error("Failed to acquire image from camera")
      return None
    xsize = rxsize/self.status.xbin
    ysize = rysize/self.status.ybin
    f.data.shape = (xsize,ysize)
    f.headers['NAXIS1'] = `xsize`
    f.headers['NAXIS2'] = `ysize`
    f.headers['DATE-OBS'] = "'%d-%02d-%02d'" % (stime.tm_year, stime.tm_mon, stime.tm_mday)
    f.headers['TIME-OBS'] = "'%02d:%02d:%02d'" % (stime.tm_hour, stime.tm_min, stime.tm_sec)
    f.headers['EXPTIME'] = "%8.2f" % self.status.exptime
    f.headers['COOLER'] = "'%s'" % {False:'OFF', True:'ON'}[self.status.cool]
    f.headers['TEMPSTAT'] = "'%s'" % self.status.tempstatus
    f.headers['CCDTEMP'] = "%6.2f" % ccdtemp
    f.headers['MODE'] = "'%s'" % self.status.mode
    f.headers['CCDXBIN'] = `self.status.xbin`
    f.headers['CCDYBIN'] = `self.status.ybin`
    if self.status.xbin == self.status.ybin:
      f.headers['SECPIX'] = "%6.4f" % (SECPIX*self.status.xbin)
    f.headers['SHUTTER'] = {0:"'OPEN'", 1:"'STAY OPEN'", 2:"'CLOSED'"}[self.status.shuttermode]
    f.headers['GAIN'] = "%6.3f" % self.CurrentGain()
    f.headers['RONOISE'] = "%6.3f" % self.CurrentNoise()
    f.headers['SATADU'] = "%d" % self.CurrentSaturation()
    f.headers['HSSPEED'] = "'%s'" % HSSpeeds[self.status.hsspeed]
    f.headers['VSSPEED'] = "'%s'" % VSSpeeds[self.status.vsspeed]
    f.headers['PREGAIN'] = "'%s'" % PreAmpGains[self.status.preamp]
    f.headers['ROMODE'] = "'%s'" % {False:'High Sensitivity Mode', True:'High Capacity Mode for high binning factors'}[self.status.highcap]
    f.headers['SUBFXMIN'] = `self.status.xmin`
    f.headers['SUBFXMAX'] = `self.status.xmax`
    f.headers['SUBFYMIN'] = `self.status.ymin`
    f.headers['SUBFYMAX'] = `self.status.ymax`

    return f


def InitClient():
  """Connect to the server process and create a proxy object to the
     real camera object.
  """
  global camera
  connected = False
  try:
    camera = Pyro4.Proxy('PYRONAME:AndorCamera')
    connected = True
  except Pyro4.errors.PyroError:
    logger.error("Can't connect to camera server - run Andor.py to start the server")
  camera.status = CameraStatus()
  try:
    camera.status.update()
  except Pyro4.errors.PyroError:
    pass
  return connected and camera.status.initialized   #True if we have a valid proxy, and the camera on the other end
                                                   #  has been initialized.


def InitServer():
  global camera, pyro_thread, ns_process
  camera = Camera()

  logger.info("Getting camera details:")
  n = camera._GetAvailableCameras()
  logger.info("%d Andor camera/s installed" % n)
  if n <> 1:
    logger.error("Can't cope with anything other than 1 camera, exiting.")
    return False

  logger.info("Getting handle for camera #0:")
  handle = camera._GetCameraHandle(0)
  logger.info("Handle = %s" % handle.value())

  logger.info("Setting current camera:")
  camera._SetCurrentCamera(handle)

  logger.info("Python Andor interface initialising")
  try:
    camera._Initialize()
    camera._Setup()
  except:
    camera.status.initialized = False
    logger.exception("Andor in use or not reachable")
    return False

  logger.info(camera.status)

  ns_process = Popen(shlex.split("python -Wignore -m Pyro4.naming --host=0.0.0.0"))
  logger.info("Started Pyro4 nameserver daemon")

  #Start the Pyro4 daemon thread listening for status requests and receiver 'putState's:
  pyro_thread = threading.Thread(target=camera._servePyroRequests, name='PyroDaemon')
  pyro_thread.daemon = True
  pyro_thread.start()
  logger.info("Started Pyro4 communication process to serve camera connections")
  #The daemon threads will continue to spin for eternity....

  return True


def SignalHandler(signum=None,frame=None):
  """Called when a signal is received that would result in the programme exit, if the
     RegisterCleanup() function has been previously called to set the signal handlers and
     define an exit function using the 'atexit' module.

     Note that exit functions registered by atexit are NOT called when the programme exits due
     to a received signal, so we must trap signals where possible. The cleanup function will NOT
     be called when signal 9 (SIGKILL) is received, as this signal cannot be trapped.
  """
  logger.error("Signal %d received." % signum)
  sys.exit(-signum)    #Called by signal handler, so exit with a return code indicating the signal received


def RegisterCleanup(func):
  """Traps a number of signals that would result in the program exit, to make sure that the
     function 'func' is called before exit. The calling process must define its own cleanup
     function - typically this would shut down anything that needs to be stopped cleanly.

     We don't need to trap signal 2 (SIGINT), because this is internally handled by the python
     interpreter, generating a KeyboardInterrupt exception - if this causes the process to exit,
     the function registered by atexit.register() will be called automatically.
  """
  global SIGNAL_HANDLERS, CLEANUP_FUNCTION
  CLEANUP_FUNCTION = func
  for sig in [3,15]:
    SIGNAL_HANDLERS[sig] = signal.signal(sig,SignalHandler)   #Register a signal handler
  SIGNAL_HANDLERS[1] = signal.signal(1,signal.SIG_IGN)
  atexit.register(CLEANUP_FUNCTION)       #Register the passed CLEANUP_FUNCTION to be called on
                                          #  normal programme exit, with no arguments.


def cleanup():
  """Registers to be called just before exit by the exit handler.
     Warms up the camera, and waits for the temperature to hit -20C before
     exiting, then calls camera.ShutDown()
  """
  logger.info("Exiting Andor.py program - here's why: %s" % traceback.print_exc())
  try:
    ns_process.poll()
    if ns_process.returncode is None:
      ns_process.terminate()
      logger.info("Pyro4 name server shut down")
    if camera.status.initialized:
      logger.info("Acquiring lock on camera to prepare for shutdown")
      camera.Lock()   #Make sure clients don't use the camera while we are shutting down.
      logger.info("Turning off camera cooler")
      camera.CoolerOFF()
      temp = camera.GetTemperature()
      while temp < -20:
        logger.info("Waiting for camera to warm up to -20C - currently %6.1f" % temp)
        time.sleep(5)
  finally:
    if camera.status.initialized:
      camera._ShutDown()    #Shut down the camera API cleanly
      logger.info("Andor camera API ShutDown.")


if __name__ == '__main__':
  globals.SERVER = True
  globals.CLIENT = False
  RegisterCleanup(cleanup)
  InitServer()
  while not exitnow:    #Exit the daemon if we are told to
    time.sleep(1)
