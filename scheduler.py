
import string
import math
import time

from globals import *
import objects
import pipeline
import ephemint
import teljoy

import MySQLdb
try:
  DictCursor=MySQLdb.DictCursor
except AttributeError:     #New version of MySQLdb puts cursors in a seperate module
  import MySQLdb.cursors
  DictCursor=MySQLdb.cursors.DictCursor


AltCutoff = 30


types=""
candidates={}
cantimestamp=MySQLdb.Timestamp(0)
best=None


def anglediff(a,b):
  """Returns the absolute separation in degrees between any two angles, allowing for
     'wraparound'
  """
  diff=max(a-b, b-a)
  if diff>180:
    diff=360.0-diff
  return diff


def Ptest1(o):
  """Initial priority function test. Takes an object record and returns a priority
     value (higher is better).
  """
  try:
    moveangle=max( anglediff(teljoy.status.Azi, o.AZ), 
                   anglediff(teljoy.status.RawRA*15, o.RA*15),
                   anglediff(teljoy.status.RawDec, o.DEC) )
  except TypeError:
    moveangle = 0              #Teljoy appears inactive, ignore moveangle factor for testing
  movefactor = abs(math.cos(moveangle/360*math.pi))            #Cos(moveangle/2) in degrees

  timefactor = abs((float(MySQLdb.TimestampFromTicks(time.time())) - o.LastObs) / (o.period*86400))

  if o.ALT < AltCutoff:
    altfactor=0.0
  else:
    altfactor = (o.ALT - AltCutoff) / (90 - AltCutoff)
  
  return timefactor * movefactor * altfactor
  

def Ptest2(o):
  """Initial priority function test. Takes an object record and returns a priority
     value (higher is better).
  """
  try:
    moveangle=max( anglediff(teljoy.status.Azi, o.AZ), 
                   anglediff(teljoy.status.RawRA*15, o.RA*15),
                   anglediff(teljoy.status.RawDec, o.DEC) )
  except TypeError:
    moveangle = 0              #Teljoy appears inactive, ignore moveangle factor for testing
  movefactor = abs(math.cos(moveangle/360*math.pi))            #Cos(moveangle/2) in degrees

  timefactor = abs((float(MySQLdb.TimestampFromTicks(time.time())) - o.LastObs) / (o.period*86400))

  if o.ALT < AltCutoff:
    altfactor=0.0
  else:
    altfactor = 1.0

  ha=o.RA - teljoy.status.LST
  if abs(ha) > 5:
    hafactor = 0.0           #Don't allow any jumps outside -5 < HA < +5 hours 
  else:                      #No matter what the altitude
    ch=( (math.sin(AltCutoff/180*math.pi)-math.sin(ephemint.obslat)*math.sin(o.DEC/180*math.pi)) / 
        (math.cos(ephemint.obslat)*math.cos(o.DEC/180*math.pi)) )
    if ch<1.0:
      hafactor=(6-ha)          #always above horizon
    elif ch>1.0:
      hafactor=0             #Always below horizon
    else:
      hafactor=(6-ha) * (0.5 * math.pi / math.acos(ch))
    
  
  return movefactor * timefactor * altfactor * hafactor



def UpdateCandidates():
  """Connect to the objects database and re-get all objects whose 'lastmod'
     timestamp is more recent than 'cantimestamp', the last update time.
     After getting any changed objects, calculate a new alt and azimuth for each
     object, then calculate the priority function for each object.
  """
  global types,candidates,cantimestamp,Pfunction,best
  temptime=MySQLdb.TimestampFromTicks(time.time())

  if types:
    if type(types)==type(""):
      types=[types]
    types=map(string.upper, types)
    for ty in types:
      curs.execute("select ObjID from objects where lastmod > '"+
                    str(cantimestamp)+"' and "+
                    "upper(type) = '"+ty+"'")
      c=curs.fetchallDict()
      for row in c:
        id=row['ObjID']
        o=pipeline.getobject(id)
        o.RA=stringsex(o.ObjRA)
        o.DEC=stringsex(o.ObjDec)
        if _valid(o):
          candidates[id] = o
  else:
      curs.execute("select ObjID from objects where lastobs > '"+
                    str(cantimestamp)+"'")
      c=curs.fetchallDict()
      for row in c:
        id=row['ObjID']
        o=pipeline.getobject(id)
        o.RA=stringsex(o.ObjRA)
        o.DEC=stringsex(o.ObjDec)
        if _valid(o):
          candidates[id] = o

  cantimestamp=temptime
  best=None
  for o in candidates.values():
    al,az=ephemint.altaz(o.RA/12*math.pi, o.DEC/180*math.pi)
    o.ALT, o.AZ = al/math.pi*180,  az/math.pi*180
    o.PRIORITY = Pfunction(o)
    try:
      if o.PRIORITY > best.PRIORITY:
        best=o
    except AttributeError:
      best=o



def _valid(o):
  """Return true if the object is to be considered by the scheduler - currently
     just tests for the existence of a valid observing period (desired interval
     between observations, in days)
  """
  try:
    return (o.period <> 0)
  except:
    return 0



Pfunction=Ptest2


#print 'connecting to database for objects database access'
db=MySQLdb.Connection(host='lear', user='honcho', passwd='',
                      db='teljoy', cursorclass=DictCursor)
curs=db.cursor()
#print 'connected'
