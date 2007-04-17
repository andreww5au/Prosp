
"""Utility functions that use features from several modules (planet, teljoy,
   etc). 
   Used in Prosp and as stand-alone.
"""

import time       #for the 'sleep' function
import os
import string
import threading


from ArCommands import *   #Make camera functions usable without module name qualifier
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
import grb
import objects
import math
import scheduler
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
  oet=status.exptime
  exptime(et)
  flat('flat'+filt)
  fn=status.nextfile[:-8]
  filename('flat'+filt)
  filter(filtnum(filt))
  files=go(n)
  filename(fn) #Restore filename to orig, stripping counter
  object(fn)  #Swap to object type, not dark type
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
  if obj=='':
    obj=status.TJ.name
  res=pipeline.getobject(obj)
  res.set()


def pgo():
  """Take one image, then preprocess it and do a PLANET DoPhot reduction.
     eg: pgo()
  """
  preduced(go())
  p=Pevent(status.TJ.name)
  if p.good:
    process(p.root)
    archive(p.root)


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
  if type(objs)==type(''):
    objs=string.replace(objs, ',', ' ')
    objs=string.split(objs)


  if (not status.MonitorActive) and (not force) and len(objs)>6:
    swrite("Monitoring mode is not switched on - aborting take command run.")
    print "Use monitor('on') to switch on monitoring, or override by"
    print "calling, for example, ('plref ob2k038 ... eb2k05', force=1)"
    return 0
  for ob in objs:
    p=pipeline.getobject(ob)
    if not p:
      ewrite("Object: "+ob+" not in database, or has unknown reduction pipeline type.")
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
  """
# written by Ralph Martin
#            April 2003
#  grbflag=0
  global grbflag
  global tileside
  tileside=3
  grbflag=0
  #grb.emailstart()
  time.sleep(10)
  if type(objs)==type(''):
    objs=string.replace(objs, ',', ' ')
    objs=string.split(objs)
  if (not status.MonitorActive) and (not force) and len(objs)>6:
    swrite("Monitoring mode is not switched on - aborting take command run.")
    print "Use monitor('on') to switch on monitoring, or override by"
    print "calling, for example, ('plref ob2k038 ... eb2k05', force=1)"
    return 0
  monEmail=0
  for ob in objs:
    if grbflag < 1 and monEmail < 1: #no email request not monitoring old request
      observeThis(ob)
    else:  #Email request received.
      alt,az=ephemint.altaz(grb.self.RA,grb.self.Dec)           #get the alt az of the object
      if alt > 30: #Object is above telescope horizon (30 degrees)
#       take it's picture
        observeThis(grb.self.obj)
        grbRequest(flag='false') #reset the override flag
        monEmail=0     #don't monitor
      elif az < 0.0:   #object has transited and is now setting
        grbRequest(flag='false') #reset the override flag
#       grb.self.flag=0 #email acknowledged
        monEmail=0     #don't monitor
      else: #Object is below the telescope horizon - continue to monitor.
        grbRequest(flag='false') #reset the override flag
#       grb.self.flag=0 #email acknowledged
        monEmail=1     #waiting for object to rise
#     take the observing list exposure.
      observeThis(ob)
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
#         grb.self.flag=0                      #reset the override flag
          monEmail=0                           #don't monitor
        elif az < 0.0:                         #object has transited and is now setting
          grbRequest(flag='false')             #reset the override flag
#         grb.self.flag=0                      #email acknowledged
          monEmail=0                           #don't monitor
        else: #Object is below the telescope horizon - continue to monitor.
          grbRequest(flag='false')             #reset the override flag
#         grb.self.flag=0                      #email acknowledged
          monEmail=1                           #waiting for object to rise
        time.sleep(2)                          #sleep for 10 seconds

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
     observeThis(ob)
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
           observeThis(obtile)
         if redo==1:
           break
       continue

def observeThis(takeobj):
  p=pipeline.getobject(takeobj)
  if not p:
    ewrite("Object: "+takeobj+" not in database, or has unknown reduction pipeline type.")
  else:
    p.take()

def foc():
  "Takes a focus image - 10 successive exposures on the same frame, offset."
  for i in range(9):
    foclines(25)
  foclines(-1)


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
#  for f in dircache.listdir(planet.PipeHome+'/outgoing/'):
#    os.remove(planet.PipeHome+'/outgoing/'+f)
  for o in counts.keys():
    swrite("Object "+o+": "+`counts[o]`+" images.")
#    ob=planet.Pevent(o)
#    if ob.good:
#      os.system('cp '+ob.archivedir+'/'+planet.site+ob.root+'I '+ 
#           planet.PipeHome+'/outgoing/'+planet.site+ob.root+'I ;'+
#           ' gzip '+planet.PipeHome+'/outgoing/'+planet.site+ob.root+'I')
  wd=os.getcwd()
  os.chdir('/home/observer/PLANET-archives')
  os.system('./SyncArchives')
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
  """
  return threading.enumerate()


def newdir():
  """Create a new working directory based on the current date, and copy in
     bias and dark frames appropriate for the current CCD temperature.
  """
  obsname=raw_input("Enter Observers Name: ")
  observer(obsname)          #Set tonights observer name in FITS headers
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


def readlist(fname=''):
  """Read a list of object names from the file specified. If no path is given,
     the file is assumed to be in /tmp. The file format is flexible, simply 
     requiring the object names to be seperated by whitespace (spaces, tabs,
     or newlines in any combination), any number of objects per line. 

     Returns the list as a string (space seperated, 6 objects per line),
     which can be assigned to a variable if needed: 

     EG:

     mylist=readlist('/tmp/test.lis')
     take(mylist + eo2to8r)

     or

     take( readlist('test.lis') + eo2to8r)
  """
  if not os.path.dirname(fname):
    fname=os.path.join('/tmp',fname)
  try:
    tmplist=open(fname,'r').read().split()
  except IOError:
    ewrite('File: '+fname+' not found')
    return None

  out=''
  i=0
  for o in tmplist:
    out=out+o.ljust(10)
    i=i+1
    if (i/6.0)==(i/6):
      out=out+'\n'
  return out


def runsched(n=0, force=0, planetmode=1):
  """Run the scheduler repeatedly taking the best object each time. If 'n' is given, and non
     zero, exit after that many objects. If 'force' is given, and non-zero, skip the reminder
     about turning on monitoring for more than 6 objects.
     If 'planetmode' is given, and non-zero, run planet.UpdatePriorities() regularly to keep up
     homebase changes.
  """
  if n==0:
    n=9999
  if (not status.MonitorActive) and (not force) and (n>6):
    swrite("Monitoring mode is not switched on - aborting take command run.")
    print "Use monitor('on') to switch on monitoring, or override by"
    print "calling, for example, ('plref ob2k038 ... eb2k05', force=1)"
    return 0

  for i in range(n):
    errors=""
    if planetmode:
      planet.UpdatePriorities()
    scheduler.UpdateCandidates()
    if scheduler.best:
      errors=scheduler.best.take()
      if errors:
        ewrite("Errors in moving to object, sleeping for 300 seconds")
        time.sleep(300)
    else:    #No object above horizon
      ewrite("No object above horizon, sleeping for 300 seconds")
      time.sleep(300)
  print "runsched sequence of ",n," scheduler objects completed."
