
import Ariel
from Ariel import command

import sys   #system functions
import os    #operating system calls
import string  #string handlign functions
import glob    #Filename expansion
import time    #Time and date routines
import types   #Built in type identifiers
import cPickle
import globals
from globals import *

filters=globals.filters


def filtnum(fname):
  "Return filter slot number given name"
  id=string.upper(fname[0])
  num=2   #Default if not found
  for nm in filters:
    if id==nm[0]:
      num=filters.index(nm)+1
  return num


def update():
  "Attach to Ariel and grab current status information"

  tmpstr=status.lastfile   #save last filename becuase you can't read it back
  status.empty()
  command('status',0)
  command('istatus',0)
  command('tcstatus',0)
  command('config',0)
  status.lastfile=tmpstr  #restore last filename
  status.updated()


def filter(n='I'):
  """Change filter - default to I if no argument
     Parameter can be either the filter number (1-8) or the filter name
     ('Red', 'I', 'Infrared', etc). Type 'filters' to see the current 
     filter list.
     eg: filter('R')
  """
  if n=='':
    n='I'
  if type(n)==types.StringType:
    command('filter '+`filtnum(n)`,1)
  else:
    if (n>=1) and (n<=8):
      command('filter '+`n`,1)
      swrite('Moved to filter '+`n`)
    else:
      ewrite("Error in filter value: "+repr(n))


def guider(x=0,y=0):
  """Change guider position - default to 0,0 if no argument
     eg: guider(123,-456)
  """
  if x==0 and y==0 and (gzero.gxoff<>0 or gzero.gyoff<>0):
    command('guider 0 0',1)
  command('guider '+`x+gzero.gxoff`+' '+`y+gzero.gyoff`,1)


def zguider():
  """Make the current position 0,0 for all future guider movement
     eg: zguider()
  """
  gzero.gxoff=status.xguider+gzero.gxoff
  gzero.gyoff=status.yguider+gzero.gyoff
  guider(0,0)
  f=open('/tmp/guidezero','w')
  cPickle.dump(gzero,f)
  f.close()


def mirror(to='IN'):
  """Change mirror position - argument can be 'IN' or 'OUT' (case insensitive).
     'IN' means that the mirror hole is centred on the main beam for normal
     offset guiding use.
     eg: mirror('in')
         mirror('out')
  """
  to=string.strip(string.upper(to))
  if (to=="IN") or (to=="OUT"):
    command('mirror '+to,1)
    swrite('Mirror: '+to)
  else:
    ewrite("Usage: 'mirror IN' or 'mirror OUT'")


def exptime(et=0.02):
  """Change exposure time - default to 0.02 if no argument.
     eg: exptime(0.1)
  """
  command('exptime '+`et`,1)


def _ctrn(str=''):  #Used in 'filename' to find filectr's for matching files
  "Return the file counter number given a complete filename"
  bname=os.path.basename(str)
  if (len(bname)>7) and   \
     (bname[-8] in string.digits) and  \
     (bname[-7] in string.digits) and  \
     (bname[-6] in string.digits):
    return float(str[-8:-5])
  else:
    return 0


def filename(fname='apogee'):
  """Change file name - default to 'apogee' if no argument. When the image is
     taken, a three digit image counter and the ".fits" extension is appended.
     eg: filename('test')
     
  """
  fname=string.strip(fname)
  pc=max(map(_ctrn,glob.glob(status.path+fname+"*.fits"))+[0])
  cc=max(map(_ctrn,glob.glob("/data/counters/"+fname+"*.cntr"))+[0])
  fc=max([pc,cc])+1
   #Set the filectr to one higher than the highest existing file with 
   #the same basename in the current path or in /data/counters
  command('filename '+fname,1)
  filectr(fc)


def filectr(fc=1):
  """Change file counter - default to '1' if no argument.

     Note! Call 'filename' first to set the basename and choose a default
     file counter (1 more than the previous file counter for that
     basename). If you change the file name, a new file counter will be chosen.

     If you override the default counter value with the 'filectr' function,
     it does not check for name conflicts until ariel actually creates the
     file. If there is a file of the same name at the time of image creation,
     ariel chooses a random name (ap??????.fits) to avoid overwriting any
     existing file.
     eg: filectr(3)
  """
  command('filectr '+`fc`,1)
  swrite('Next file name: '+status.path+status.nextfile)


def path(str='/data'):
  """Change image save path - default to /data if no argument
     eg: path('/data/rd000922')
  """
  command('path '+string.strip(str),1)
  swrite('Next file name: '+status.path+status.nextfile)


def observer(oname='unknown'):
  """Change the name of the observer, stored in the FITS header.
     eg: observer("Andrew Williams")
  """
  command('observer '+string.strip(oname),1)
  swrite('Observer name: '+oname)


def xbin(n=1):
  """Change x bin factor - default to 1 if no argument.
     eg: xbin(2)
  """
  command('xbin '+`n`,1)

def ybin(n=1):
  """Change y bin factor - default to 1 if no argument.
     eg: ybin(2)
  """
  command('ybin '+`n`,1)

def roi(ri=(1,512,1,512)):
  """Change Region-of-interest - default to (1,512,1,512) if no argument.
     eg: roi((193,320,193,320))
     (This will read out a 128x128 pixel region in the center of the image.
      Note the _double_ parentheses.)
  """
  command('roi '+`ri[0]`+' '+`ri[1]`+' '+`ri[2]`+' '+`ri[3]`,1)


def dark(str='dark'):
  """Change mode to dark frames, set object name to arg, default='dark'.
     This doesn't take any images, it just means that subsequent exposures
     will not open the shutter, and will have a fits keyword indicating
     that the image is a dark frame.
     Use this command when taking dark images manually, instead of using
     'getdarks'.
     eg: dark('dark-12C')
  """
  str=str[:80]    #truncate to 80 char to fit in FITS header
  command('dark '+string.strip(str),1)   #strip leading and trailing spaces


def bias(str='bias'):
  """Change mode to bias frames, set object name to arg, default='bias'.
     This doesn't take any images, it just means that subsequent exposures
     will not open the shutter, and will have a FITS keyword indicating
     that the image is a bias frame. (NOT necessary on this system).
     eg: bias('abias')
  """
  str=str[:80]    #truncate to 80 char to fit in FITS header
  command('bias '+string.strip(str),1)   #strip leading and trailing spaces


def zero(str='zero'):
  """Change mode to zero frames, set object name to arg, default='zero'
     This doesn't take any images, it just means that subsequent exposures
     will not open the shutter, and will have a FITS keyword indicating
     that the image is a zero frame. (NOT necessary on this system).
     eg: zero('azero')
  """
  str=str[:80]    #truncate to 80 char to fit in FITS header
  command('zero '+string.strip(str),1)   #strip leading and trailing spaces


def flat(str='flat'):
  """Change mode to flat frames, set object name to arg, default='flat'.
     This doesn't take any images, it just means that subsequent exposures
     will have a fits keyword indicating that the image is a flatfield frame.
     Use this command when taking flatfield images manually, instead of using
     'getflats'.
     eg: flat('dark-12C')
  """
  str=str[:80]    #truncate to 80 char to fit in FITS header
  command('flat '+string.strip(str),1)   #strip leading and trailing spaces


def object(str='object'):
  """Change mode to object, set object name to arg, default='object'.
     This doesn't take any images, it just means that subsequent exposures
     will have a fits keyword indicating that the image is an object frame.
     This is the normal operating mode for taking images.
     eg: object('SN1993k')
  """
  str=str[:80]    #truncate to 80 char to fit in FITS header
  command('object '+string.strip(str),1)   #strip leading and trailing spaces


def settemp(t=-10):
  """Change regulation set point temperature, default to -10C.
     eg: settemp(-12)
  """
  command('settemp '+`t`,1)


def cooldown():
  """Initiate CCD cooldown by turning on CCD cooler power. Cancels any previous
     "warmup" command.
  """
  command('cooldown',1)


def warmup():
  """Shut down CCD cooler power safely by initiating slow warm-up to ambient
     temperature. Use 'cooldown' to turn the power back on again.
  """
  command('warmup',1)


def ccdtemp(n=2):
  """Update displayed CCD temperature value using an average of 'n' seconds
     of temp measurements, default 2. The 'At Temp', etc flags are only updated
     when a CCD image is actually taken. This command is useful becuase the
     CCD temperature is normally only measured during exposures, and it can
     be less accurate for very short exposure times (<1 second).
     eg: ccdtemp(1)
  """
  command('ccdtemp '+`n`,1)
  return status.temp


def focus(n=-1):
  """Open shutter for 'exptime' seconds, and move CCD down N lines.
     If N<0 or not specified, readout CCD. Use this command multiple times with
     an argument of 10-100 pixels, changing the focus each time, then force a 
     readout with 'focus(-1)'. You will see many images of your focus star, N
     pixel lines apart. Select the sharpest image and move to that focus 
     focus position used for that exposure.
     Would only useful if the telescope has a focus encoder.
     eg: focus(32)
         focus(32)
         focus(32)
         focus(-1)
  """
  if n<0:
    command('focus readout',1)
  else:
    command('focus '+`n`,1)
  update()   #grab new status information after the image


def _setcounter():
  """Updates the counter file in /data/counters for the next image taken.
  """
  fname=os.path.basename(status.lastfile)
  if len(fname)>8:
    nname=fname[:-4]
    bname=fname[:-8]
    for file in glob.glob('/data/counters/'+bname+'[0-9][0-9][0-9].cntr'):
      os.remove(file)
    f=open('/data/counters/'+nname+'cntr','w')
    f.close
    

def _abort():
  """Send an abort command to Ariel to stop curent exposure and dump the image.
     If Ariel isn't in the middle of taking an exposure, this will generate
     a spurious error message, which is safe to ignore.
  """
  command('abort',1)


def _stop():
  """Send a stop command to Ariel to stop curent exposure and keep the image.
     If Ariel isn't in the middle of taking an exposure, this will generate
     a spurious error message, which is safe to ignore.
  """
  command('stop',1)


def go(n=1):
  """Take N images - default to 1 if no argument.
     eg: go(2)
  """
  timetot=(status.exptime+12)*n   #Allow 12 seconds readout time per image
  swrite('Start time '+`time.asctime(time.localtime(time.time()))`+
         ' -  End at '+`time.asctime(time.localtime(time.time()+timetot))`)
  aborted=0
  result=[]
  try:
    for i in range(n):
      command('go',1)   
      update()  #grab new status information after the image
      result.append(status.path+status.lastfile)
  except KeyboardInterrupt:
    swrite("Exposure aborted, keeping image.")
    _stop()
    aborted=1
  update()   #grab new status information after the image
  _setcounter()
  print '\7'
  if len(result)==1:
    return result[0]
  else:
    return result


#Module initialisation section

gzero=Ariel.GuideZero(0,0)
if os.path.exists('/tmp/guidezero'):
  f=open('/tmp/guidezero','r')
  gzero=cPickle.load(f)
  f.close()

Ariel.gzero=gzero
