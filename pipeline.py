
import string
import time

import objects
import teljoy
from globals import *
import ArCommands
import xpa
import improc


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

  def jump(self):
    "Move the telescope to the object coordinates"
    while teljoy.status.paused:
      print "Waiting for weather to clear"
      time.sleep(60)
    swrite("Moving to object "+self.ObjID)
    teljoy.jump(id=self.ObjID, ra=self.ObjRA, dec=self.ObjDec,
                epoch=self.ObjEpoch)
    time.sleep(3)
    teljoy.status.update()
    while teljoy.status.moving or teljoy.status.DomeInUse:
      time.sleep(1)
      teljoy.status.update()
    if string.upper(teljoy.status.name) <> string.upper(self.ObjID):   #Teljoy hasn't jumped to this object
      ewrite("Teljoy hasn't jumped to "+self.ObjID+" - possibly too low")
      self.errors=self.errors+"Teljoy hasn't jumped to "+self.ObjID+" - possibly too low\n"

  def fileprefix(self,prefix=""):
    "Set the filename prefix (minus the exposure number and the .fits extension)"
    if prefix:
      ArCommands.filename(prefix)
    else:
      ArCommands.filename(self.ObjID)

  def preset(self):
    "Carry out any parameter changes desired before the image (override with actual code)"
    pass

  def set(self):
    "Set the observing params for Ariel to this object's params."
    ArCommands.object(self.ObjID)
    ArCommands.guider(self.XYpos[0],self.XYpos[1])
    ArCommands.filter(self.filtname)
    ArCommands.exptime(self.exptime)

  def get(self):
    "Take the actual image of this object, and do preprocessing."
    self.rawfilename=ArCommands.go()
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
    self.jump()
    if not self.errors:
      self.preset()
      self.fileprefix()
      self.set()
      self.get()
      self.reduce()
      self.log()
    else:
      print "Errors: "+self.errors


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
