
import string
import math
import time

from globals import *

import pipeline
import ephemint
import teljoy

import MySQLdb
import safecursor
DictCursor=safecursor.SafeCursor

AltCutoff = 30


types={'PLANET':1.0, 'IMAGE':0.000001}    #By default, SN searching is a last resort choice
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
  movefactor = abs(math.cos(moveangle/540*math.pi))     #=1 for zero shift, 0.5 for 180 degrees

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

    #ch is the cos of the objects abs(hour angle) at rise/set (above altcutoff)

#    if ch<-1.0:
#      hafactor=(6-ha)/6.0    #always above horizon -> =1 overhead, 0.17 at 5 hours
#    elif ch>1.0:
#      hafactor=0             #Always below horizon
#    else:
#      hafactor=(6-ha) / (12 * math.acos(ch) / math.pi)

    hafactor=1.0     #Disable HA weighting temporarily
  
  return movefactor * timefactor * altfactor * hafactor


def Ptest3(o):
  """Flat priority function, useful mostly for PLANET or other objects observed many
     times per night. No dependence on position apart from being =0 for alt<AltCutoff and abs(HA)>5
  """
  timefactor = abs((float(MySQLdb.TimestampFromTicks(time.time())) - o.LastObs) / (o.period*86400))

  if o.ALT < AltCutoff:
    altfactor=0.0
  else:
    altfactor = 1.0  

  ha=o.RA - teljoy.status.LST
  if abs(ha) > 5:
    hafactor = 0.0           #Don't allow any jumps outside -5 < HA < +5 hours 
  else:                      #No matter what the altitude
    hafactor = 1.0

  return timefactor * altfactor * hafactor



def UpdateCandidates():
  """Connect to the objects database and re-get all objects whose 'lastmod'
     timestamp is more recent than 'cantimestamp', the last update time.
     After getting any changed objects, calculate a new alt and azimuth for each
     object, then calculate the priority function for each object.
  """
  global types,candidates,cantimestamp,Pfunction,best
  temptime=MySQLdb.TimestampFromTicks(time.time())

  if types:
    if type(types)==type(""):      #simple string
      _types=[string.upper(types)]
      _weights=None
    elif type(types)==type({}):    #Dictionary, with priority weights
      _types=map(string.upper, types.keys())
      _weights={}
      for t in types.keys():
        _weights[string.upper(t)]=float(types[t])
    elif type(types)==type([]):
      _types=map(string.upper, types)
      _weights=None
    for ty in _types:
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
      _weights=None
      curs.execute("select ObjID from objects where lastmod > '"+
                    str(cantimestamp)+"'")
      c=curs.fetchallDict()
      for row in c:
        id=row['ObjID']
        o=pipeline.getobject(id)
        o.RA=stringsex(o.ObjRA)
        o.DEC=stringsex(o.ObjDec)
        if _valid(o):
          candidates[id] = o

  for k in candidates.keys():       #remove any existing candidates that are now invalid
    if not _valid(candidates[k]):   #eg, due to a change in the scheduler.types global
      del candidates[k]

  cantimestamp=temptime
  best=None
  for o in candidates.values():
    al,az=ephemint.altaz(o.RA/12*math.pi, o.DEC/180*math.pi)
    o.ALT, o.AZ = al/math.pi*180,  az/math.pi*180
    if _weights:
      o.PRIORITY = Pfunction(o) * _weights[string.upper(o.type)]
    else:
      o.PRIORITY = Pfunction(o)
    try:
      if o.PRIORITY > best.PRIORITY:
        best=o
    except AttributeError:
      best=o
  if best.PRIORITY <= 0:
    best=None



def _valid(o):
  """Return true if the object is to be considered by the scheduler - currently
     just tests for the existence of a valid observing period (desired interval
     between observations, in days)
  """
  try:
    return (o.period <> 0)
  except:
    return 0



Pfunction=Ptest3


#print 'connecting to database for objects database access'
db=MySQLdb.Connection(host='lear', user='honcho', passwd='',
                      db='teljoy', cursorclass=DictCursor)
curs=db.cursor()
#print 'connected'
