
"""Utility functions that use features from several modules (planet, teljoy,
   etc). 
   Used in Prosp and as stand-alone.
"""

import time       #for the 'sleep' function
import os
import string
import threading

domeflatHA =  -2.68    #-2.68, -2.79, 
domeflatDec = -20.9    #-20.9, -24.0, 
#flatlist=[ ('V',5,13.0), ('R',7,4.0), ('I',7,2.0) ]
flatlist = [ ('B',5,None), ('V',7,None), ('R',7,None), ('I',7,None) ]

status = None         #Overwritten with actual AnCommands.camera.status object by Prosp on startup

from globals import *
from AnCommands import *

import improc
from improc import reduce,dobias,dodark,doflat
import planet
from planet import *
from pipeline import dObject, getobject
import teljoy
from xpa import display
from globals import *
import ephemint
import skyviewint
import objects
import math
import scheduler
import focuser
import service 
import guidestar

global grbflag

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
      fres=display(reduce(fres))
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
  fn = status.nextfile[:-8]
  filename('bias')
  files = go(n)
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
  fn = status.nextfile[:-8]
  filename('dark')
  files = go(n)
  filename(fn)   #Restore filename to orig, stripping counter
  object(fn)  #Swap to object type, not dark type
  dodark(files)
  

def getflats(filt='R', n=1, et=None):
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
  oet = status.exptime
  oldfn = status.nextfile[:-8]
  if len(status.object)>2:
    oldob = status.object[1:-1]
  else:
    oldob = ''
  if not et:
    autoexp = True
    filter(filtnum(filt))
    exptime(0.1)
    filename('testflat'+filt)
    flat('flat'+filt)
    tim = improc.FITS(go(),'r')
    tim.bias()
    testlevel = tim.median()
    et = 20000*0.1/testlevel
    if et < 1.0:
      print "Too bright, desired exposure time only %3.1f seconds." % (et,)
      filename(oldfn) #Restore filename to orig, stripping counter
      object(oldob)  #Swap to object type, not dark type
      exptime(oet)  #restore original exposure time
      return 0
    elif et > 120.0:
      print "Too dark, clipping exposure time %3.1f seconds." % (et,)
      et = 120
  else:
    autoexp = False

  filename('flat'+filt)
  filter(filtnum(filt))
  files = []
  numf = 0
  while len(files) < n:
    exptime(et)
    newfile = go()
    tim = improc.FITS(newfile,'r')
    tim.bias()
    testlevel = tim.median()
    if autoexp:
      if testlevel < 10000:
        print "Not enough signal in flatfield image - discarding."
      elif testlevel>30000:
        print "Signal level too high in flatfield image - discarding."
      else:
        files.append(newfile)
      if testlevel > 2000:    #If the shutter didn't open at all, don't try and adjust exptime
        et = 20000*et/testlevel
        if et < 1.0:
          print "Too bright, desired exposure time only %3.1f seconds." % (et,)
          break
        elif et > 120.0:
          print "Too dark, clipping exposure time %3.1f seconds." % (et,)
          et = 120
    else:
      files.append(newfile)

  filename(oldfn) #Restore filename to orig, stripping counter
  object(oldob)  #Swap to object type, not dark type
  exptime(oet)  #restore original exposure time
  doflat(files)


def set(obj=''):
  """Look up object data for from objects.dat and set up AP7.
     Uses the object database to set filename, object name, exposure time,
     filter, and guider position for a given object name.

     If no object name is given, read the current object name from Teljoy.
     eg: set()
         set('sn99ee')
  """
  if not obj:
    obj = status.TJ.name
  res = pipeline.getobject(obj)
  res.set()


def take(objs=[], force=0):
  """Moves telescope to and takes an image for each object specified.
     Does everything required for an image of each of object, in the order
     given. The object names are looked up in the objects database, and the
     RA, Dec, filter, exposure time, and guider position are found. The
     telescope is moved to each object, the filter,exptime, etc are set,
     and after the telescope and dome stop moving, an image is taken and 
     fully reduced, then the next object is handled.

     Object names are looked up in the object database for observing parameters
     and the type of image (used to choose the reduction pipeline).

     The objects can be specified as either a list of strings, or as one string
     with a list of object names seperated by spaces.

     eg: take('plref ob2k038 eb2k005 sn99ee')
         take( ['sn93k','sn94ai'], wait=1)

     if more than 6 objects are specified, and weather/twilight monitoring is
     not switched on, it will abort with an error message. To force operation
     anyway, add the argument 'force=1'

     eg: take('plref ob2k038 ... eb2k05', force=1)
  """
  if type(objs) == str:
    objs = string.replace(objs, ',', ' ')
    objs = string.split(objs)

  if (not status.MonitorActive) and (not force) and len(objs)>6:
    logger.info("Monitoring mode is not switched on - aborting take command run.")
    print "Use monitor('on') to switch on monitoring, or override by"
    print "calling, for example, ('plref ob2k038 ... eb2k05', force=1)"
    return 0
  for ob in objs:
    p = pipeline.getobject(ob)
    if not p:
      logger.error("Object: "+ob+" not in database, or has unknown reduction pipeline type.")
    else:
      p.take()


def grbRequest(flag='false',tile='true'):
  global grbflag
  global tileside
  if flag=='true':
      grbflag=1
  else:
      grbflag=0
  if tile=='true':
      tileside=3
  else:
      tileside=1


def sched(objs=[],force=0,mode=0):
  """This function is similar to the take function, however, it monitors for the arrival
     of a GRB email. Scheduled observations are interrupted while the observations
     requested by the email are made. Sched starts a background thread that monitors
     an email account for the arrival of GRB emails. If the email request is for an object
     that is below the the eastern horizon (30 degrees), then normal observations continue
     until the GRB has 'risen' above 30 degrees.

     Scheduled objects can be specified as either a list of strings, or as one
     string with a list of object names seperated by spaces.

     eg: sched('plref ob2k038 eb2k005 sn99ee',mode=1)
         sched( ['sn93k','sn94ai'], force=1)

     if more than 6 objects are specified, and weather/twilight monitoring is
     not switched on, it will abort with an error message. To force operation
     anyway, add the argument 'force=1'

     eg: sched('plref ob2k038 ... eb2k05', force=1)


# written by Ralph Martin
#            April 2003
#  grbflag=0
  global grbflag
  global tileside
  tileside=3
  grbflag=0
  time.sleep(10)
  if type(objs)==type(''):
    objs=string.replace(objs, ',', ' ')
    objs=string.split(objs)
  if (not status.MonitorActive) and (not force) and len(objs)>6:
    logger.info("Monitoring mode is not switched on - aborting take command run.")
    print "Use monitor('on') to switch on monitoring, or override by"
    print "calling, for example, ('plref ob2k038 ... eb2k05', force=1)"
    return 0
  monEmail=0
  for ob in objs:
    if grbflag < 1 and monEmail < 1: #no email request not monitoring old request
      take(ob)
    else:  #Email request received.
      alt,az=ephemint.altaz(grb.self.RA,grb.self.Dec)           #get the alt az of the object
      if alt > 30: #Object is above telescope horizon (30 degrees)
#       take it's picture
        take(grb.self.obj)
        grbRequest(flag='false') #reset the override flag
        monEmail=0     #don't monitor
      elif az < 0.0:   #object has transited and is now setting
        grbRequest(flag='false') #reset the override flag
        monEmail=0     #don't monitor
      else: #Object is below the telescope horizon - continue to monitor.
        grbRequest(flag='false') #reset the override flag
        monEmail=1     #waiting for object to rise
#     take the observing list exposure.
      take(ob)
  else: #finished the observing request continue to monitor for email request.
    monEmail=0
    print "running schedule and monitor GRB email: %s" %(monEmail)
    while 1:
#     run the automatic scheduler
      runsched(n=0, force=1, planetmode=mode)
#     scheduler.UpdateCandidates()
#     scheduler.best.take()
#     check the GRB email
      if grbflag < 1 and monEmail < 1:  #no email request and not monitoring
        time.sleep(1) #Sleep for 10 seconds
      else:  #Email request received.
        alt,az=ephemint.altaz(grb.self.RA,grb.self.Dec)           #get the alt az of the object
        if alt > 30: #Object is above telescope horizon (30 degrees)
          tile(grb.self.obj, side=3)           #take picture
          grbRequest(flag='false')             #reset the override flag
          monEmail=0                           #don't monitor
        elif az < 0.0:                         #object has transited and is now setting
          grbRequest(flag='false')             #reset the override flag
          monEmail=0                           #don't monitor
        else: #Object is below the telescope horizon - continue to monitor.
          grbRequest(flag='false')             #reset the override flag
          monEmail=1                           #waiting for object to rise
        time.sleep(2)                          #sleep for 10 seconds
"""

def tile(ob, side=1, offsetRA=340, offsetDec=340 ):
#  side = take exposures to cover an area of side x side -- default 1x1
#  exp = exposure time -- default 1 second
#  ob = object
#  offsetRA = RA offset in arc seconds -- a little less than chip size
#  offset Dec = Dec offset in arc seconds
#  Object names at this stage are standard so that all images
#  have the same root object name i.e. the string ob.
   nme=['a','b','c','d','e','f','g','h','i','j','k','l','m', \
        'n','o','p','q','r','s','t','u','v','w','x','y','z']
   offsetRA=offsetRA/3600.0
   offsetDec=offsetDec/3600.0
   if side == 1:
     take(ob)
   else:
     centreob=objects.Object(ob)              # get details of the object from the data base
     if not centreob.ObjRA:
       print "Object not in data base."
     centreRA = stringsex(centreob.ObjRA)     # Ra and Dec in radians
     centreDec = stringsex(centreob.ObjDec)
     oldRA = centreRA
     oldDec = centreDec
#    read in the data base entry for this object
     fracpart,intpart=math.modf(side/2)
     subby=int(side-intpart)
     redo=1
     while redo==1:
       for i in range(1,side+1):
         for j in range(1,side+1):
           redo=0
#          After every exposure check the centre it may have been updates
#          since we started tiling.
#          If the centre has changed another email has arrived -- restart tiling.
           centreob=objects.Object(ob)              # get details of the object from the data base
           if not centreob.ObjRA:
             print "Object not in data base."
           centreRA = stringsex(centreob.ObjRA)     # Ra and Dec in radians
           centreDec = stringsex(centreob.ObjDec)
           if centreRA != oldRA or centreDec != oldDec:
             print 'new position restart tiling.'
             oldRA = centreRA
             oldDec = centreDec
             redo=1
             break
           oldRA = centreRA
           oldDec = centreDec
           ii=i-subby
           jj=j-subby
#          generate a file name based on ob.
           obtile=ob+nme[ii+12]+nme[jj+12]
#          update data base over write any pre-existing entry
           centreob.ObjID = obtile
           centreob.ObjRA  = sexstring(centreRA + ii*offsetRA)
           centreob.ObjDec = sexstring(centreDec + jj*offsetDec)
           centreob.save(ask=0,force=1) # save the observation
           take(obtile)
         if redo==1:
           break
       continue


def foc():
  "Takes a focus image - 10 successive exposures on the same frame, offset."
  saveob = status.object
  if focuser.status.pos is not None:
    object('Foc: %d' % (focuser.status.pos,) )
  else:
    object('Foc: 0')
  for i in range(9):
    foclines(25)
  foclines(-1)
  object(saveob)


def ephemjump(ob=None):
  """Takes an ephemeris object (created with the 'elements()' function) and 
     jumps the telescope to the current position. Use 'ephempos()' if you
     just want the current coordinates displayed.
  """
  try:
    id,ra,dec = ephemint.ephempos(ob)
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
      posn = sexstring(status.TJ.ObjRA,' ') + ', ' + sexstring(status.TJ.ObjDec,' ')
      equinox = status.TJ.ObjEpoch
    elif status.TJ.RawRA:
      posn = sexstring(status.TJ.RawRA,' ') + ', ' + sexstring(status.TJ.RawDec,' ')
      t = time.localtime(time.time())
      equinox = t[0] + t[7]/365.246      #Raw coords are epoch-of-date
    else:
      print "No position specified, and Teljoy is not running."
      return
    skyviewint.skyview(posn, equinox)


def threads():
  """Lists all active threads.
  """
  return threading.enumerate()


def newdir():
  """Create a new working directory based on the current date, and copy in
     bias and dark frames appropriate for the current CCD temperature.
  """
  obsname = raw_input("Enter Observers Name: ")
  observer(obsname)          #Set tonights observer name in FITS headers
  t = time.localtime(time.time())
  if t[3] < 12:
    t = time.localtime(time.time() - (t[3]+1)*3600 )
  dirname = '/data/rd' + time.strftime('%y%m%d',t)
  print "Making directory: " + dirname
  os.system('mkdir '+dirname)
  os.chdir(dirname)
  path(dirname)
  biases = glob.glob('/data/bias-bin2slow-??C.fits')
  temps = []
  for n in biases:
    mpos = n.find('.')
    temps.append(int(n[mpos-3:mpos-1]))
  tempnow = ccdtemp(5)
  print "Current temperature: " + `tempnow`
  besttemp = 100
  for t in temps:
    if abs(tempnow-t) < abs(tempnow-besttemp):
      besttemp = t
  print "Using bias+dark images for " + `besttemp` + "C."
  for mode in Andor.MODES:
    os.system(("cp /data/bias-%s-"+`besttemp`+"C.fits "+dirname+"/bias-%s.fits") % (mode,mode))
    os.system(("cp /data/dark-%s-"+`besttemp`+"C.fits "+dirname+"/dark-%s.fits") % (mode,mode))


def runsched(n=0, force=0, planetmode=1):
  """Run the scheduler repeatedly taking the best object each time. If 'n' is given, and non
     zero, exit after that many objects. If 'force' is given, and non-zero, skip the reminder
     about turning on monitoring for more than 6 objects.
     If 'planetmode' is given, and non-zero, run planet.UpdatePriorities() regularly to keep up
     homebase changes.
  """
  if n == 0:
    n = 9999
  if (not status.MonitorActive) and (not force) and (n>6):
    logger.info("Monitoring mode is not switched on - aborting take command run.")
    print "Use monitor('on') to switch on monitoring, or override by"
    print "calling, for example, runsched(force=1)"
    return 0

  for i in range(n):
    try:
      service.check()  # service.check if its time to focus the telescope
    except:
      print 'Exception while trying to focus telescope.'
    errors = ""
    if planetmode:
      planet.UpdatePriorities()
    scheduler.UpdateCandidates()
    if scheduler.best:
      errors = scheduler.best.take()
      if errors:
        logger.warning("Errors in moving to object, sleeping for 300 seconds")
        time.sleep(300)
    else:    #No object above horizon
      logger.warning("No object above horizon, sleeping for 300 seconds")
      time.sleep(300)
  print "runsched sequence of %d scheduler objects completed." % n


def domeflats():
  """Move the telescope and dome to the correct position for dome flats, and take
     V,R, and I images with appropriate exposure times, then reduce them.
  """
  teljoy.jump(id='flats', ra=sexstring(teljoy.status.LST+domeflatHA), dec=sexstring(domeflatDec) )
  exptime(0.1)
  filename('junk')
  while (teljoy.status.moving or teljoy.status.DomeInUse):
    print "Waiting for telescope slew..."
    time.sleep(5)
  teljoy.freeze(1)
  try:
    teljoy.dome(90)
    while (teljoy.status.DomeInUse):
      print "Waiting for Dome slew..."
      time.sleep(5)
    for filt,n,expt in flatlist:
      getflats(filt,n,expt)
  finally:
    teljoy.freeze(0)


def gpos(ra=None, dec=None):
  """For the current telescope position, request a guide star position in RA and Dec, 
     then return the X/Y guider coordinates for that position.
  """
  if (teljoy.status.RawRA is None) or (teljoy.status.RawDec is None):
    print "Current telescope coordinates undefined - enter centre position:"
    cra,cdec = stringsex(raw_input("RA:  ")), stringsex(raw_input("Dec: "))
    cen = guidestar.xyglobs.Coord(cdec,cra)
  else:
    cen = guidestar.xyglobs.Coord(teljoy.status.RawDec,teljoy.status.RawRA)

  if (ra is None) or (dec is None):
    print "Enter guide star coordinates:"
    ra,dec = stringsex(raw_input("RA:  ")), stringsex(raw_input("Dec: "))
  else:
    if type(ra) == string:
      ra = stringsex(ra)
    if type(dec) == string:
      dec = stringsex(dec)

  star = guidestar.xyglobs.Coord(dec,ra)
  p = guidestar.starposc.Eq2XY(star,cen)
  print "X=%d, Y=%d" % (p.x*guidestar.xyglobs.X_Steps, p.y*guidestar.xyglobs.Y_Steps)
  tst1 = ( (p.x<guidestar.xyglobs.Xmax) and (p.x>guidestar.xyglobs.Xmin) and 
           (p.y<guidestar.xyglobs.Ymax) and (p.y>guidestar.xyglobs.Ymin) )
  tst2 = ( (p.x**2 + p.y**2) > guidestar.xyglobs.hole_radius**2)
  if not tst1:
    print "Target star outside maximum travel limits for XY stage!"
  if not tst2:
    print "Target star too close to centre, inside hole in offset mirror!"
  return (int(p.x*guidestar.xyglobs.X_Steps), int(p.y*guidestar.xyglobs.Y_Steps), tst1 and tst2)


def offset(x,y):
  """Moves telescope to center whatever is now at pixel coordinates X,Y
     eg: offset(259,312)
  """
  xscale = Andor.SECPIX * status.xbin    #arcseconds per pixel
  yscale = Andor.SECPIX * status.ybin    #arcseconds per pixel
  dx = x - (Andor.XSIZE/status.xbin)/2
  dy = y - (Andor.YSIZE/status.ybin)/2
  od = dx * xscale
  oh = -dy * yscale
  logger.info("Offset - Del RA =  "+`oh`+"arcsec\nDel Dec = "+`od`+"arcsec")
  print "Moving telescope - remember to do a reset position after this."
  teljoy.jumpoff(oh,od)


def gof(n=1):
  """Same as 'go' command, only send the image/s to DS9 in the old 8-bit format,
    so IRAF can do an 'imexam' for focussing.
  """
  go(n=n, iraf=True)