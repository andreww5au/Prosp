
import ArCommands     #Camera interface library
import time       #for the 'sleep' function
import os
import string
import getpass
from ArCommands import *   #Make camera functions usable without module name
                           #qualifier
import improc
from improc import reduce,dodark,doflat
import planet
from planet import *
from dobjects import Object
import teljoy
from xpa import display
from globals import *
import sendftp
import ephemint


def randd(fname, histeq=1):
  """Reduce and display a set of images.
     The 'histeq' parameter is passed to the 'display' function. See the
     documentation for this function for further information.
     eg: randd('/data/test005.fits')
  """
  outfile=reduce(fname)
  if outfile:
    display(outfile,histeq)
  return outfile


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


def getdarks(n=1, et=900):
  """Get n dark images of exposure time 'et', then process them to 'dark.fits'.
     Any existing 'dark.fits' is deleted first, so this command can be run more
     than once to add to any existing dark frames.

     Original file and object names are restored after the dark images are 
     gathered.

     If the reduction process does not complete, type 'dodarks' from the
     command line to process the dark field images manually.
     eg: getdarks(6,600)
         (take 6 dark images with a 600 second exposure time)
  """
  exptime(et)
  dark('dark')
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


def doall(yrs=['2K','01']):
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
  os.system('scp W*I.gz planet@mitchell.astro.rug.nl:NotPublic/Incoming01')
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
  

