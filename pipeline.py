
import string
import time
import sys

import objects
import teljoy

from globals import *
if CAMERA == 'Apogee':
  import ArCommands as CameraCommands
elif CAMERA == 'Andor':
  import AnCommands as CameraCommands
else:
  print "Invalid value for 'CAMERA' global: %s" % CAMERA

import xpa
import improc
from guidestar.starposc import getstars, best 


"""
Pipeline control module and classes:

Anything that inherits this module to define an observing pipeline should:
  -subclass dObject and override whatever functions are desired to implement the pipeline. An
   observation is initiated by external code calling the 'take' method on the object
  -Add a new item in the pipeline.Pipelines dictionary, mapping from the (upper case)
   observation type string to the pipeline class appropriate for that type of object
  -If abbreviated names are to be possible, write a function that takes an abbreviated name
   and returns the full name to be looked up in the database, and add that function to the
   pipeline.TryNames list.

"""

Pipelines = { }  #Dictionary, mapping from (upper case) observation types to classes derived from dObject

TryNames= [ ]  #List of functions that map from abbreviated names to full names, eg "eb2k05"->"EB2K005"



class dObject(objects.Object):
  "A new object class with dynamic methods, like 'jump'."

  def __repr__(self):
    return "Pipeline[" + self.ObjID + "]"

  def __str__(self):
    return 'P[%9s:%11s %11s (%6.1f)%8s%6.5g (%5d,%5d)%8s]\n' % (self.ObjID,
             self.ObjRA,
             self.ObjDec,
             self.ObjEpoch,
             self.filtname,
             self.exptime,
             self.XYpos[0],self.XYpos[1],
             self.type)

  def jump(self):
    "Move the telescope to the object coordinates"
    self.errors=""
    while teljoy.status.paused:
      print "Waiting for weather to clear"
      time.sleep(60)
    logger.info("Moving to object ... "+self.ObjID)
    teljoy.jump(id=self.ObjID, ra=self.ObjRA, dec=self.ObjDec,
                epoch=self.ObjEpoch)
    time.sleep(3)
    teljoy.status.update()
    while teljoy.status.moving or teljoy.status.DomeInUse:
      time.sleep(1)
      teljoy.status.update()
    logger.info("Teljoy has jumped to "+self.ObjID+": "+teljoy.status.name)
    if string.upper(teljoy.status.name)[:8] <> string.upper(self.ObjID)[:8]:   #Teljoy hasn't jumped to this object
      ewrite("Teljoy hasn't jumped to "+self.ObjID+" - possibly too low")
      self.errors=self.errors+"Teljoy hasn't jumped to "+self.ObjID+" - possibly too low\n"

  def fileprefix(self,prefix=""):
    "Set the filename prefix (minus the exposure number and the .fits extension)"
    if prefix:
      CameraCommands.filename(prefix)
    else:
      CameraCommands.filename(self.ObjID+filtid(self.filtname))

  def preset(self):
    "Carry out any parameter changes desired before the image (override with actual code)"
    pass

  def set(self):
    "Set the observing params for Ariel to this object's params."
    CameraCommands.object(self.ObjID)
#    print 'X=',self.XYpos[0], ' Y=',self.XYpos[1]
    if (self.XYpos[0] == 0) and (self.XYpos[1] == 0):
      try:
        slist = getstars(ra=self.ObjRA, dec=self.ObjDec, epoch=self.ObjEpoch)
      except:
        slist = []
        ewrite('Exception in guide star code')
        sys.excepthook(*sys.exc_info())
      bstar = None
      if slist:
        bstar = best(slist)      
      if bstar is not None:
        s = slist[bstar]
        print "Chosen guide star %d of %d: Mag=%5.2f, x=%d, y=%d" % (bstar,len(slist),s.mag,s.x,s.y)
        CameraCommands.guider(s.x, s.y)
      else:
        print "No guide star in database, no guide star found in GSC"
    else:
      CameraCommands.guider(self.XYpos[0],self.XYpos[1])
    CameraCommands.filter(self.filtname)
    CameraCommands.exptime(self.exptime)

  def get(self):
    "Take the actual image of this object, and do preprocessing."
    self.rawfilename = CameraCommands.go()
    self.filename=improc.reduce(self.rawfilename)
    xpa.display(self.filename)

  def reduce(self):
    "Carry out full reduction on the preprocessed image (override with actual code)"
    print "No reduction to do."

  def log(self):
    "Log the results of the current observation (override with actual code)"
    print "No result logging to do."

  def take(self):
    "Carry out a full observation and reduction for this object."
    self.errors=""
    self.set()
    self.jump()
    if not self.errors:
      for frame in range(self.subframes):
        self.subframe(frame)
        self.preset()
        self.fileprefix()
        self.set()
        self.updatetime()
        self.get()
        self.reduce()
        self.log()
    else:
      print "Errors: "+self.errors
      return self.errors


def allobjects():
  "Return a list of pipeline objects for everything in the Object database."
  plist=[]
  for o in objects.allobjects():
    if Pipelines.has_key(string.upper(o.type)):
      plist.append(Pipelines[string.upper(o.type)](o.ObjID))
    else:
      plist.append(dObject(o.ObjID))
  return plist


def getobject(str):
  "Return an appropriate pipeline object for the object with ObjID given in 'str'"
  o=objects.Object(str)
  if not o.ObjRA:             #Object not in database
    for nfunc in TryNames:
      o=objects.Object(nfunc(str))
      if o.ObjRA:
        if Pipelines.has_key(string.upper(o.type)):
          return Pipelines[string.upper(o.type)](str)
        else:
          return dObject(str)
    return None
  else:
    if Pipelines.has_key(string.upper(o.type)):
      return Pipelines[string.upper(o.type)](str)
    else:
      return dObject(str)
