
#TODO - check for existing file with same name before saving FITS file!

import os
import sys
import cPickle
import math

import Andor
import opticalcoupler
import xpa
from globals import *


class GuideZero:
  def __init__(self,x=0,y=0):
    self.gxoff = x
    self.gyoff = y


class ExtendedCameraStatus(Andor.CameraStatus):
  """Add attributes needed for AnCommands code - filter, filename, etc.
  """
  def empty(self):
    Andor.CameraStatus.empty(self)
    #Exposure time and file name/path parameters
    self.imgtype = 'OBJECT'  #or 'BIAS', 'DARK', or 'FLAT'
    self.object = ''         #Object name
    self.path = '/data'
    self.filename = 'andor'
    self.nextfile = ''
    self.lastfile = ''
    self.filectr = 0
    self.observer = ''
    #Optical coupler setting parameters
    self.filter = -1
    self.filterid = 'X'
    self.guider = (9999,9999)
    self.mirror = 'IN'
    #Housekeeping parameters
    self.lastact = time.time()

  def __str__(self):
    """Tells the status object to display itself to the screen"""
    s = Andor.CameraStatus.__str__(self)
    s += 'Observer = %s\n' % self.observer
    s += 'imgtype = %s\n' % self.imgtype
    s += 'object = %s\n' % self.object
    s += 'filter = %d (%s)\n' % (self.filter, filtname(self.filter))
    s += 'guider = (%d,%d)\n'  % self.guider
    s += 'mirror = %s\n' % self.mirror
    s += 'last file = %s\n' % self.lastfile
    s += 'path, nextfile = %s, %s\n' % (self.path, self.nextfile)
    s += 'Errors: %s' % self.errors
    return s

  def update(self):
    """Called to grab fresh status data from the real status object (on the server), and
       save that data, plus all local attributes (filename, filter, teljoy and weather status,
       etc) to a pickled file for access by the CGI scripts.
    """
    if not connected:
      return
    Andor.CameraStatus.update(self)
    m = os.umask(0)   #Open file with r/w permission for all, so that multiple clients as different users will work
    f = open('/tmp/prospstatus','w')
    cPickle.dump(self,f)
    f.close()
    os.umask(m)       #restore original file creation permissions



def filter(n='I'):
  """Change filter - default to I if no argument
     Parameter can be either the filter number (1-8) or the filter name
     ('Red', 'I', 'Infrared', etc). Type 'filters' to see the current 
     filter list.
     eg: filter('R')
  """
  if n=='':
    n = 'I'
  if type(n) == str:
    fid = filtid(n)
    fnum = filtnum(fid)
    opticalcoupler.SelectFilter(fnum)
    camera.status.filterid = fid
    camera.status.filter = fnum
    logger.info('Moved to filter '+`n`)
  else:
    if (n>=1) and (n<=8):
      opticalcoupler.SelectFilter(n)
      logger.info('Moved to filter '+`n`)
    else:
      logger.error("Error in filter value: "+repr(n))


def guider(x=0,y=0):
  """Change guider position - default to 0,0 if no argument
     eg: guider(123,-456)
  """
  if x==0 and y==0 and (gzero.gxoff<>0 or gzero.gyoff<>0):
    opticalcoupler.HomeXYStage()
  opticalcoupler.MoveXYStage( x=(x+gzero.gxoff), y=(y+gzero.gyoff) )
  camera.status.guider = (x,y)


def zguider():
  """Make the current position 0,0 for all future guider movement
     eg: zguider()
  """
  gzero.gxoff = camera.status.xguider + gzero.gxoff
  gzero.gyoff = camera.status.yguider + gzero.gyoff
  guider(0,0)
  f = open('/data/guidezero','w')
  cPickle.dump(gzero,f)
  f.close()


def mirror(to='IN'):
  """Change mirror position - argument can be 'IN' or 'OUT' (case insensitive).
     'IN' means that the mirror hole is centred on the main beam for normal
     offset guiding use.
     eg: mirror('in')
         mirror('out')
  """
  to = to.strip().upper()
  if (to=="OUT"):
    opticalcoupler.MoveMirror(0)
    logger.info('Mirror: '+to)
    camera.status.mirror = 'OUT'
  elif (to=="IN"):
    opticalcoupler.MoveMirror(opticalcoupler.MIRROR_IN)
    logger.info('Mirror: '+to)
    camera.status.mirror = 'IN'
  else:
    logger.error("Usage: 'mirror IN' or 'mirror OUT'")


def exptime(et=0.02):
  """Change exposure time - default to 0.02 if no argument.
     eg: exptime(0.1)
  """
  if et < 0.02:
    et = 0.02
    logger.error('Exposure time less than 0.02 seconds specified, using 0.02.')
  print camera.exptime(et)
  camera.status.update()


def _ctrn(s=''):  #Used in 'filename' to find filectr's for matching files
  "Return the file counter number given a complete filename"
  bname = os.path.basename(s).split('.')[0]
  im = ''
  for i in range(len(bname)-1,0,-1):
    if bname[i].isdigit() and len(im)<5:
      im = bname[i] + im
    else:
      break
  try:
    return int(im)
  except:
    return 0.0


def filename(fname='andor'):
  """Change file name - default to 'apogee' if no argument. When the image is
     taken, a three digit image counter and the ".fits" extension is appended.
     eg: filename('test')
     
  """
  fname = fname.strip()
  pc = max(map(_ctrn,glob.glob(os.path.join(camera.status.path,fname+"*.fits")))+[0])
  cc = max(map(_ctrn,glob.glob("/data/counters/"+fname+"*.cntr"))+[0])
  fc = max([pc,cc])+1
   #Set the filectr to one higher than the highest existing file with 
   #the same basename in the current path or in /data/counters
  camera.status.filename = fname
  filectr(fc)


def filectr(fc=1):
  """Change file counter - default to '1' if no argument.

     Note! Call 'filename' first to set the basename and choose a default
     file counter (1 more than the previous file counter for that
     basename). If you change the file name, a new file counter will be chosen.

     If you override the default counter value with the 'filectr' function,
     it does not check for name conflicts until it tries to actually create the
     file. If there is a file of the same name at the time of image creation,
     it chooses a random name to avoid overwriting any
     existing file.
     eg: filectr(3)
  """
  camera.status.filectr = fc
  camera.status.nextfile = camera.status.filename + `camera.status.filectr` + '.fits'
  logger.info('Next file name: '+os.path.join(camera.status.path,camera.status.nextfile))


def path(pathstring='/data'):
  """Change image save path - default to /data if no argument
     eg: path('/data/rd000922')
  """
  camera.status.path = pathstring.strip()
  logger.info('Next file name: '+os.path.join(camera.status.path,camera.status.nextfile))


def observer(oname='unknown'):
  """Change the name of the observer, stored in the FITS header.
     eg: observer("Andrew Williams")
  """
  camera.status.observer = oname.strip()
  logger.info('Observer name: '+oname)


def dark(s='dark'):
  """Change mode to dark frames, set object name to arg, default='dark'.
     This doesn't take any images, it just means that subsequent exposures
     will not open the shutter, and will have a fits keyword indicating
     that the image is a dark frame.
     Use this command when taking dark images manually, instead of using
     'getdarks'.
     eg: dark('dark-12C')
  """
  s = s.strip()[:80]    #truncate to 80 char to fit in FITS header
  print camera.SetShutter(2)
  camera.status.imgtype = 'DARK'
  camera.status.object = s
  camera.status.update()


def bias(s='bias'):
  """Change mode to bias frames, set object name to arg, default='bias'.
     This doesn't take any images, it just means that subsequent exposures
     will not open the shutter, and will have a FITS keyword indicating
     that the image is a bias frame. (NOT necessary on this system).
     eg: bias('abias')
  """
  s = s.strip()[:80]    #truncate to 80 char to fit in FITS header
  exptime(0.0)
  print camera.SetShutter(2)
  camera.status.imgtype = 'BIAS'
  camera.status.object = s
  camera.status.update()


def flat(s='flat'):
  """Change mode to flat frames, set object name to arg, default='flat'.
     This doesn't take any images, it just means that subsequent exposures
     will have a fits keyword indicating that the image is a flatfield frame.
     Use this command when taking flatfield images manually, instead of using
     'getflats'.
     eg: flat('dark-12C')
  """
  s = s.strip()[:80]    #truncate to 80 char to fit in FITS header
  print camera.SetShutter(0)
  camera.status.imgtype = 'FLAT'
  camera.status.object = s
  camera.status.update()


def object(s='object'):
  """Change mode to object, set object name to arg, default='object'.
     This doesn't take any images, it just means that subsequent exposures
     will have a fits keyword indicating that the image is an object frame.
     This is the normal operating mode for taking images.
     eg: object('SN1993k')
  """
  s = s.strip()[:80]    #truncate to 80 char to fit in FITS header
  print camera.SetShutter(0)
  camera.status.imgtype = 'OBJECT'
  camera.status.object = s
  camera.status.update()


def mode(s='bin2slow'):
  """Change camera readout mode to the value specified. Valid modes are
     defined in Andor.MODES, and the code to parse the mode field and set
     the specific readout parameters is defined in Andor.Camera.SetMode().
  """
  ms = s.strip().lower()
  print camera.SetMode(ms)
  camera.status.update()


def settemp(t=-10):
  """Change regulation set point temperature, default to -10C.
     eg: settemp(-12)
  """
  print camera.SetTemperature(t)
  camera.status.update()


def cooldown():
  """Initiate CCD cooldown by turning on CCD cooler power. Cancels any previous
     "warmup" command.
  """
  print camera.CoolerON()
  camera.status.update()


def warmup():
  """Shut down CCD cooler power. Use 'cooldown' to turn the power back on again.
  """
  print camera.CoolerOFF()
  camera.status.update()


def ccdtemp(n=2):
  """Update and return CCD temperature.
  """
  temp = camera.GetTemperature()
  camera.status.update()
  return temp


def foclines(n=-1):
  """Open shutter for 'exptime' seconds, and move CCD down N lines.
     If N<0 or not specified, readout CCD. Use this command multiple times with
     an argument of 10-100 pixels, changing the focus each time, then force a 
     readout with 'foclines(-1)'. You will see many images of your focus star, N
     pixel lines apart. Select the sharpest image and move to the 
     focus position used for that exposure.
     Would only be useful if the telescope had a focus encoder.
     eg: foclines(32)
         foclines(32)
         foclines(32)
         foclines(-1)

    *UNSUPPORTED ON ANDOR CAMERA!*
  """
#  if n<0:
#    command('focus readout',1)
#  else:
#    command('focus '+`n`,1)
#  update()   #grab new status information after the image
#  return status.path+status.lastfile
  logger.error("'foclines' unsupported on Andor camera!")


def _setcounter():
  """Updates the counter file in /data/counters for the next image taken.
  """
  fname = os.path.basename(camera.status.lastfile)
  tname = fname.split('.')[0]
  i = len(tname)-1
  if i > -1:
    while tname[i].isdigit() and i>-1:
      i = i - 1
    nname = fname[:-4]
    bname = tname[:i+1]
    for file in glob.glob('/data/counters/'+bname+'[0-9][0-9][0-9].cntr'):
      os.remove(file)
    for file in glob.glob('/data/counters/'+bname+'[0-9][0-9][0-9][0-9].cntr'):
      os.remove(file)
    f = open('/data/counters/'+nname+'cntr','w')
    f.close()
    

def setheaders(f):
  """Given a FITS image object returned from the camera, set the telescope 
     position and optical coupler related FITS header cards in the image
     based on current data.
  """
  f.headers['OBSERVER'] = "'%s'" % camera.status.observer
  f.headers['FILTERID'] = "'%s'" % filtname(camera.status.filter)
  f.headers['FILTER'] = "%1d" % camera.status.filter
  f.headers['XYSTAGE'] = "'%d,%d'" % camera.status.guider
  f.headers['MIRROR'] = "'%s'" % camera.status.mirror
  if camera.status.imgtype == 'BIAS':
    f.headers['BIAS'] = camera.status.object
  elif camera.status.imgtype == 'DARK':
    f.headers['DARK'] = camera.status.object
  else:
    f.headers['OBJECT'] = camera.status.object
  try:
    if camera.status.TJ.ObjRA:    #Position calibrated to epoch
      ra = camera.status.TJ.ObjRA
      dec = camera.status.TJ.ObjDec
      epoch = camera.status.TJ.ObjEpoch
      alt = camera.status.TJ.Alt
      GotTJ = True
    elif camera.status.TJ.RawRA:
      ra = camera.status.TJ.RawRA
      dec = camera.status.TJ.RawDec
      alt = camera.status.TJ.Alt
      t = time.gmtime()
      epoch = t.tm_year + (t.tm_yday/366.0)
      GotTJ = True
    else:
      GotTJ = False
  except AttributeError:
    GotTJ = False      
  if GotTJ:
    f.headers['RA_OBJ'] = "%12.9f" % ra
    f.headers['RA'] = "'%s'" % sexstring(ra)
    f.headers['DEC_OBJ'] = "%13.9f" % dec
    f.headers['DEC'] = "'%s'" % sexstring(dec)
    f.headers['EQUINOX'] = "%6.1f" % epoch
    f.headers['SECZ'] = "%6.3f" % (1/math.cos((90-alt)*math.pi/180))
  

def go(n=1):
  """Take N images - default to 1 if no argument.
     eg: go(2)
  """
  timetot = (camera.status.exptime+25)*n   #Allow 25 seconds readout time per image
  logger.info('Start time '+`time.asctime(time.localtime(time.time()))`+
         ' -  End at '+`time.asctime(time.localtime(time.time()+timetot))`)
  result = []
  try:
    for i in range(n):
      f = camera.GetFits()
      camera.status.update()
      setheaders(f)
      f.save(os.path.join(camera.status.path,camera.status.nextfile))
      result.append(os.path.join(camera.status.path,camera.status.nextfile))
      camera.status.lastfile = camera.status.nextfile
      _setcounter()
      filectr(camera.status.filectr + 1)
      camera.status.lastact = time.time()   #Record the time that the last image was taken
      xpa.display(f.filename)
  except KeyboardInterrupt:
    logger.error("Exposure aborted, dumping image.")
  print '\7'
  if len(result) == 1:
    return result[0]
  else:
    return result


def init():
  global camera, connected, gzero
  connected = Andor.InitClient()
  camera = Andor.camera
  camera.status = ExtendedCameraStatus()
  camera.status.imgtype = 'OBJECT'
  filename('junk')
  camera.status.update()

  gzero = GuideZero(0,0)
  if os.path.exists('/data/guidezero'):
    f = open('/data/guidezero','r')
    gzero = cPickle.load(f)
    f.close()

  if OPTICALCOUPLER:
    opticalcoupler.init()
    filter('I')
    guider(0,0)
    camera.status.mirror = 'IN'

#Module initialisation section

if __name__ == '__main__':
  init()
