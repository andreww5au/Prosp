
"""Utility functions that use features from several modules (planet, teljoy,
   etc). 
   Used in Prosp and as stand-alone.
"""

import ArCommands     #Camera interface library
import time       #for the 'sleep' function
import os
import string
import getpass
from ArCommands import *   #Make camera functions usable without module name
                           #qualifier
import improc
from improc import reduce,dobias,dodark,doflat
import planet
from planet import *
from dobjects import Object
import teljoy
from xpa import display
from globals import *
import ephemint
import skyviewint
import threading


def gord(n=1):
  """Take 'n' images, reducing and displaying each image.
     A subdirectory under the image path is created and the reduced images
     are stored there, with the same filenames.
     eg: gord()
         gord(2)
  """
  resfiles=[]
  for i in range(n):
    fres=go()
    if fres:
      fres=randd(fres)
    if n==1:
      resfiles=fres
    else:
      resfiles.append(fres)
  return resfiles


def getbiases(n=1, name='bias'):
  """Get n bias images of exposure time 'et', then process them to 'bias.fits'.
     Any existing 'bias.fits' is deleted first, so this command can be run more
     than once to add to any existing dark frames.

     Original file and object names are restored after the bias images are
     gathered.

     eg: getbiases(20)
         (take 20 bias images)
  """
  exptime(0.02)
  bias(name)
  fn=status.nextfile[:-8]
  filename('bias')
  files=go(n)
  filename(fn)   #Restore filename to orig, stripping counter
  object(fn)  #Swap to object type, not dark type
  dobias(files)


def getdarks(n=1, et=900, name='dark'):
  """Get n dark images of exposure time 'et', then process them to 'dark.fits'.
     Any existing 'dark.fits' is deleted first, so this command can be run more
     than once to add to any existing dark frames.

     Original file and object names are restored after the dark images are 
     gathered.
     eg: getdarks(6,600)
         (take 6 dark images with a 600 second exposure time)
  """
  exptime(et)
  dark(name)
  fn=status.nextfile[:-8]
  filename('dark')
  files=go(n)
  filename(fn)   #Restore filename to orig, stripping counter
  object(fn)  #Swap to object type, not dark type
  dodark(files)
  

def getflats(filt='R', n=1, et=1):
  """Take and process n images in filter 'filt', exptime 'et' and create flat.
     The flatfield created will be 'flatX.fits' where 'X' is the filter name.

     Any existing 'flatX.fits' is deleted first, so this command can be run
     more than once to add to any existing flat field images, if you need to
     change exposure times, for example. NOTE - A valid 'dark.fits' file MUST
     be present before using this command, or the final output flatfield will 
     not be created. Use 'doflats I', for example, from the command line, to
     process the flats after creating a dark frame.
     
     Original file and object names are restored after the flatfield images are
     gathered.
     eg: getflats('R',5,0.7)
         getflats(filt='I', n=5, et=3)
  """
  exptime(et)
  flat('flat'+filt)
  fn=status.nextfile[:-8]
  filename('flat'+filt)
  filter(filtnum(filt))
  files=go(n)
  filename(fn) #Restore filename to orig, stripping counter
  object(fn)  #Swap to object type, not dark type
  doflat(files)



def offset(x,y):
  """Moves telescope to center whatever is now at pixel coordinates X,Y
     eg: offset(259,312)
  """
  scale=0.60    #0.58 for 23micron pixels, AP7 is 24micron
  dx=x-256
  dy=y-256
  oh=-dx*scale
  od=dy*scale
  swrite("Offset - Del RA =  "+`oh`+"arcsec\nDel Dec = "+`od`+"arcsec")
  print "Moving telescope - remember to do a reset position after this."
  teljoy.jumpoff(oh,od)


def set(obj=''):
  """Look up object data for from objects.dat and set up AP7.
     Uses the object database to set filename, object name, exposure time,
     filter, and guider position for a given object name.

     If no object name is given, read the current object name from Teljoy.
     eg: set()
         set('sn99ee')
  """
  if obj=='':
    obj=status.TJ.name
  res=Object(obj)
  res.set()


def pgo():
  """Take one image, then preprocess it and do a PLANET DoPhot reduction.
     eg: pgo()
  """
  preduced(go())
  p=Pobject(status.TJ.name)
  process(p.root)
  archive(p.root)


def take(objs=[],wait=0):
  """Moves telescope to and takes an image for each object specified.
     Does everything required for an image of each of object, in the order
     given. The object names are looked up in the objects database, and the
     RA, Dec, filter, exposure time, and guider position are found. The
     telescope is moved to each object, the filter,exptime, etc are set,
     and after the telescope and dome stop moving, there is a delay to wait
     for the automatic tracker system to lock in. If the 'wait' parameter is
     true, it waits for a keypress, otherwise it delays for 10 seconds.
     An image is then taken and reduced (including PLANET processing for
     PLANET type object names) and then the next object is handled.

     The objects can be specified as either a list of strings, or as one string
     with a list of object names seperated by spaces.

     eg: take('plref ob2k038 eb2k005 sn99ee')
         take( ['sn93k','sn94ai'], wait=1)
  """
  if type(objs)==type(''):
    objs=string.replace(objs, ',', ' ')
    objs=string.split(objs)
  for ob in objs:
    p=Pobject(ob)
    if p.valid:
      o=Object(p.root)
    else:
      o=Object(ob)
    if o.ObjRA<>'':
      swrite("take - Moving to object "+o.ObjID)
      o.jump()
      print "Waiting for telescope and optical coupler."
      o.set()
      status.TJ.update()
      while status.TJ.moving or status.TJ.DomeInUse:
        time.sleep(1)
        status.TJ.update()
      while status.TJ.paused:
        print "Waiting for weather to clear"
        sleep(60)
      if wait:
        raw_input("Press enter when tracker camera is tracking")
      else:
        print "Waiting for tracker camera to start tracking."
        time.sleep(10)
      if p.valid:
        pgo()
      else:
        gord()


def foc():
  "Takes a focus image - 10 successive exposures on the same frame, offset."
  for i in range(9):
    focus(25)
  focus(-1)


def viewer(vw=''):
  """Change the display program used - arguments are 'ds9' or 'SAOtng'.
     eg: viewer('ds9')
         viewer('SAOtng')
  """
  if vw=='':
    return xpa.viewer
  if vw<>'ds9' and vw<>'SAOtng':
    ewrite("Valid viewers - SAOtng, ds9.")
    return 0
  xpa.viewer=vw


def doall(yrs=['99','2K','01','02']):
  """Processes and archives all waiting images for all objects in the season.
     This does not run in the background, do it last thing before you go home
     in the morning and leave it running. Can take quite a long time...
     eg: doall()
  """
  if type(yrs)==type('frog'):
    yrs=[yrs]
  for yr in yrs:
    counts=planet.countimgs(status.path)
    processall(yr)
    archiveall(yr)
  for f in dircache.listdir(planet.PipeHome+'/outgoing/'):
    os.remove(planet.PipeHome+'/outgoing/'+f)
  for o in counts.keys():
    swrite("Object "+o+": "+`counts[o]`+" images.")
    ob=planet.Pobject(o)
    if ob.good:
      os.system('cp '+ob.archivedir+'/'+planet.site+ob.root+'I '+ 
           planet.PipeHome+'/outgoing/'+planet.site+ob.root+'I ;'+
           ' gzip '+planet.PipeHome+'/outgoing/'+planet.site+ob.root+'I')
  wd=os.getcwd()
  os.chdir(planet.PipeHome+'/outgoing')
  os.system('scp W*.gz planet@thales.astro.rug.nl:NotPublic/Incoming01')
  os.chdir(wd)


def ephemjump(ob=None):
  """Takes an ephemeris object (created with the 'elements()' function) and 
     jumps the telescope to the current position. Use 'ephempos()' if you
     just want the current coordinates displayed.
  """
  try:
    id,ra,dec=ephemint.ephempos(ob)
    teljoy.jump(id=id, ra=ra, dec=dec, epoch=2000)
  except:
    print "Problem with the object - use 'elements' to create an object."
  

def skyview(posn='', equinox=2000):
  """Open a Netscape window showing a 'Skyview' image of the area specified.
     You can either specify a position string (RA and Dec, seperated by a comma,
     with no colons in the value), an object name (resolved by Skyview), or 
     if no argument is specified, the current telescope position will be used.

     The pixel scale and field of view match the AP7 - the orientation will be
     correct for reduced images, or FITS image files loaded manually, but
     will be upside-down compared to 'raw' images displayed directly by Ariel
     as the image is taken. The numbered stars in the image are HST guide stars,
     and there is a key in the text below the image.

     The interface to Netscape is a little dodgy, this command might not work
     the first time you call it if Netscape isn't already running. It also 
     takes up to a minute to produce the output - the work is done in a
     background thread, so the command returns immediately.

     See http://skyview.gsfc.nasa.gov
  """

  if posn:
    skyviewint.skyview(posn, equinox)
  else:
    if status.TJ.ObjRA:
      posn=sexstring(status.TJ.ObjRA,' ')+', '+sexstring(status.TJ.ObjDec,' ')
      equinox=status.TJ.ObjEpoch
    elif status.TJ.RawRA:
      posn=sexstring(status.TJ.RawRA,' ')+', '+sexstring(status.TJ.RawDec,' ')
      t=time.localtime(time.time())
      equinox=t[0]+t[7]/365.246      #Raw coords are epoch-of-date
    else:
      print "No position specified, and Teljoy is not running."
      return
    skyviewint.skyview(posn, equinox)


def threads():
  """Lists all active threads.
     This is a test.
  """
  return threading.enumerate()


def newdir():
  """Create a new working directory based on the current date, and copy in
     bias and dark frames appropriate for the current CCD temperature.
  """
  t=time.localtime(time.time())
  if t[3]<12:
    t=time.localtime(time.time() - (t[3]+1)*3600 )
  dirname='/data/rd'+time.strftime('%y%m%d',t)
  print "Making directory: "+dirname
  os.system('mkdir '+dirname)
  os.chdir(dirname)
  path(dirname)
  darks=glob.glob('/data/dark-??Cmaster.fits')
  temps=[]
  for n in darks:
    mpos=string.find(n,'-')
    temps.append(int(n[mpos:mpos+3]))
  tempnow=ccdtemp(5)
  print "Current temperature: "+`tempnow`
  besttemp=100
  for t in temps:
    if abs(tempnow-t) < abs(tempnow-besttemp):
      besttemp=t
  print "Using bias+dark images for "+`besttemp`+"C."
  os.system("cp /data/bias"+`besttemp`+"Cmaster.fits "+dirname+"/bias.fits")
  os.system("cp /data/dark"+`besttemp`+"Cmaster.fits "+dirname+"/dark.fits")


