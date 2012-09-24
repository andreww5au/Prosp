
#TODO - check for existing file with same name before saving FITS file!

import os
import sys
import cPickle

import Andor
from Andor import status
import opticalcoupler
import xpa
from globals import *


class GuideZero:
  def __init__(self,x=0,y=0):
    self.gxoff = x
    self.gyoff = y



def update():
  "Attach to Andor camera and grab current status information"

#  tmpstr=status.lastfile   #save last filename becuase you can't read it back
#  status.empty()
#  command('status',0)
#  command('istatus',0)
#  command('tcstatus',0)
#  command('config',0)
#  status.lastfile=tmpstr  #restore last filename
  status.updated()


def filter(n='I'):
  """Change filter - default to I if no argument
     Parameter can be either the filter number (1-8) or the filter name
     ('Red', 'I', 'Infrared', etc). Type 'filters' to see the current 
     filter list.
     eg: filter('R')
  """
  if n=='':
    n = 'I'
  if type(n) == types.StringType:
    fid = filtid(n)
    fnum = filtnum(fid)
    opticalcoupler.SelectFilter(`fnum`)
    status.filterid = fid
    status.filter = fnum
    swrite('Moved to filter '+`n`)
  else:
    if (n>=1) and (n<=8):
      opticalcoupler.SelectFilter(n)
      swrite('Moved to filter '+`n`)
    else:
      ewrite("Error in filter value: "+repr(n))


def guider(x=0,y=0):
  """Change guider position - default to 0,0 if no argument
     eg: guider(123,-456)
  """
  if x==0 and y==0 and (gzero.gxoff<>0 or gzero.gyoff<>0):
    opticalcoupler.HomeXYStage()
  opticalcoupler.MoveXYStage( x=(x+gzero.gxoff), y=(y+gzero.gyoff) )
  status.guider = (x,y)


def zguider():
  """Make the current position 0,0 for all future guider movement
     eg: zguider()
  """
  gzero.gxoff = status.xguider + gzero.gxoff
  gzero.gyoff = status.yguider + gzero.gyoff
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
    swrite('Mirror: '+to)
    status.mirror = 'OUT'
  elif (to=="IN"):
    opticalcoupler.MoveMirror(opticalcoupler.MIRROR_IN)
    swrite('Mirror: '+to)
    status.mirror = 'IN'
  else:
    ewrite("Usage: 'mirror IN' or 'mirror OUT'")


def exptime(et=0.02):
  """Change exposure time - default to 0.02 if no argument.
     eg: exptime(0.1)
  """
  if et < 0.02:
    et = 0.02
    ewrite('Exposure time less than 0.02 seconds specified, using 0.02.')
  Andor.exptime(et)


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
  pc = max(map(_ctrn,glob.glob(os.path.join(status.path,fname+"*.fits")))+[0])
  cc = max(map(_ctrn,glob.glob("/data/counters/"+fname+"*.cntr"))+[0])
  fc = max([pc,cc])+1
   #Set the filectr to one higher than the highest existing file with 
   #the same basename in the current path or in /data/counters
  status.filename = fname
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
  status.filectr = fc
  status.nextfile = status.filename + `status.filectr` + '.fits'
  swrite('Next file name: '+os.path.join(status.path,status.nextfile))


def path(pathstring='/data'):
  """Change image save path - default to /data if no argument
     eg: path('/data/rd000922')
  """
  status.path = pathstring.strip()
  swrite('Next file name: '+os.path.join(status.path,status.nextfile))


def observer(oname='unknown'):
  """Change the name of the observer, stored in the FITS header.
     eg: observer("Andrew Williams")
  """
  status.observer = oname.strip()
  swrite('Observer name: '+oname)


def xbin(n=1):
  """Change x bin factor - default to 1 if no argument.
     eg: xbin(2)
  """
  Andor.SetBinning(n, status.ybin)


def ybin(n=1):
  """Change y bin factor - default to 1 if no argument.
     eg: ybin(2)
  """
  Andor.SetBinning(status.xbin, n)


def roi(ri=(1,2048,1,2048)):
  """Change Region-of-interest - default to  if no argument.
     eg: roi((193,320,193,320))
         (This will read out a 128x128 pixel region of the image.
         Note the _double_ parentheses.)

     This readout region is _before_ binning, so (1,2048,1,2048) will
     always read the whole image, regardless of binning. However, the size
     of the readout region must be an exact multiple of the binning factors.
  """
  if (type(ri) == tuple) and (len(ri) == 4):
    Andor.SetSubImage(ri[0],ri[1],ri[2],ri[3])
  else:
    print "expected tuple(xmin,xmax,ymin,ymax)"


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
  Andor.SetShutter(2)
  status.imgtype = 'DARK'
  status.object = s


def bias(s='bias'):
  """Change mode to bias frames, set object name to arg, default='bias'.
     This doesn't take any images, it just means that subsequent exposures
     will not open the shutter, and will have a FITS keyword indicating
     that the image is a bias frame. (NOT necessary on this system).
     eg: bias('abias')
  """
  s = s.strip()[:80]    #truncate to 80 char to fit in FITS header
  exptime(0.0)
  Andor.SetShutter(2)
  status.imgtype = 'BIAS'
  status.object = s


def flat(s='flat'):
  """Change mode to flat frames, set object name to arg, default='flat'.
     This doesn't take any images, it just means that subsequent exposures
     will have a fits keyword indicating that the image is a flatfield frame.
     Use this command when taking flatfield images manually, instead of using
     'getflats'.
     eg: flat('dark-12C')
  """
  s = s.strip()[:80]    #truncate to 80 char to fit in FITS header
  Andor.SetShutter(0)
  status.imgtype = 'FLAT'
  status.object = s


def object(s='object'):
  """Change mode to object, set object name to arg, default='object'.
     This doesn't take any images, it just means that subsequent exposures
     will have a fits keyword indicating that the image is an object frame.
     This is the normal operating mode for taking images.
     eg: object('SN1993k')
  """
  s = s.strip()[:80]    #truncate to 80 char to fit in FITS header
  Andor.SetShutter(0)
  status.imgtype = 'OBJECT'
  status.object = s


def settemp(t=-10):
  """Change regulation set point temperature, default to -10C.
     eg: settemp(-12)
  """
  Andor.SetTemperature(t)


def cooldown():
  """Initiate CCD cooldown by turning on CCD cooler power. Cancels any previous
     "warmup" command.
  """
  Andor.CoolerON()


def warmup():
  """Shut down CCD cooler power. Use 'cooldown' to turn the power back on again.
  """
  Andor.CoolerOFF()


def ccdtemp(n=2):
  """Update and return CCD temperature.
  """
  Andor.GetTemperature()
  return status.temp


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
  print "Unsupported on Andor camera!"


def _setcounter():
  """Updates the counter file in /data/counters for the next image taken.
  """
  fname = os.path.basename(status.lastfile)
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
  f.headers['FILTERID'] = "'%s'" % filtname(status.filter)
  f.headers['FILTER'] = "%1d" % status.filter
  f.headers['XYSTAGE'] = "'%d,%d'" % status.guider
  f.headers['MIRROR'] = "'%s'" % status.mirror
  try:
    if status.TJ.ObjRA:    #Position calibrated to epoch
      ra = status.TJ.ObjRA
      dec = status.TJ.ObjDec
      epoch = status.TJ.ObjEpoch
      GotTJ = True
    elif status.TJ.RawRA:
      ra = status.TJ.RawRA
      dec = status.TJ.RawDec
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
  

def go(n=1):
  """Take N images - default to 1 if no argument.
     eg: go(2)
  """
  timetot = (status.exptime+25)*n   #Allow 25 seconds readout time per image
  swrite('Start time '+`time.asctime(time.localtime(time.time()))`+
         ' -  End at '+`time.asctime(time.localtime(time.time()+timetot))`)
  aborted = 0
  result = []
  try:
    for i in range(n):
      f = Andor.GetFits()   
      f.save(os.path.join(status.path,status.nextfile))
      result.append(os.path.join(status.path,status.nextfile))
      status.lastfile = status.nextfile
      _setcounter()
      filectr(status.filectr + 1)
      status.lastact = time.time()   #Record the time that the last image was taken
      setheaders(f)
      xpa.display(f)
  except KeyboardInterrupt:
    swrite("Exposure aborted, dumping image.")
    aborted = 1
  print '\7'
  if len(result) == 1:
    return result[0]
  else:
    return result


def shutdown():
  """Shut down the Andor camera interface and exit the main program.
  """
  Andor.ShutDown()
  sys.exit()

#Module initialisation section

gzero = GuideZero(0,0)
if os.path.exists('/data/guidezero'):
  f = open('/data/guidezero','r')
  gzero = cPickle.load(f)
  f.close()


