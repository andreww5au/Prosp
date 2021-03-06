
import string
import math
import time
import datetime

from globals import *

import pipeline
import ephemint
import telescope

import MySQLdb
import safecursor
DictCursor=safecursor.SafeCursor

AltCutoff = 25


#types={'PLANET':1000.0, 'STORE':1.0, 'IMAGE':20.0} 
types={'PLANET':5.0, 'STORE':1.0, 'IMAGE':1.0} 
 

candidates={}
cantimestamp=MySQLdb.Timestamp(1970,1,1)
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
    moveangle=max( anglediff(telescope.status.current.Azi, o.AZ),
                   anglediff(telescope.status.current.RaC/3600, o.RA*15),
                   anglediff(telescope.status.current.DecC/3600, o.DEC) )
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
    moveangle=max( anglediff(telescope.status.current.Azi, o.AZ),
                   anglediff(telescope.status.current.RaC/3600, o.RA*15),
                   anglediff(telescope.status.current.DecC/3600, o.DEC) )
  except TypeError:
    moveangle = 0              #Teljoy appears inactive, ignore moveangle factor for testing
  movefactor = abs(math.cos(moveangle/540*math.pi))     #=1 for zero shift, 0.5 for 180 degrees

  timefactor = abs((float(MySQLdb.TimestampFromTicks(time.time())) - o.LastObs) / (o.period*86400))

  if o.ALT < AltCutoff:
    altfactor=0.0
  else:
    altfactor = 1.0

  ha=o.RA - telescope.status.Time.LST
  if abs(ha) > 5:
    hafactor = 0.0           #Don't allow any jumps outside -5 < HA < +5 hours 
  else:                      #No matter what the altitude
    if o.DEC == 90.0:
      ch = 999
    elif o.DEC == -90.0:
      ch = -999
    else:
      ch=( (math.sin(AltCutoff/180*math.pi)-math.sin(ephemint.obslat)*math.sin(o.DEC/180*math.pi)) / 
           (math.cos(ephemint.obslat)*math.cos(o.DEC/180*math.pi)) )

    #ch is the cos of the objects abs(hour angle) at rise/set (above altcutoff)
    #ch <= 1.0 implies always above horizon
    #ch == 0 implies object rises and sets when HA = +/-6 hours
    #ch == 0.25 implies object rises and sets when HA = +/-5 hours
    #ch >= 1.0 implies always below horizon

    if ch <= 0.25:
      hafactor = math.cos(ha/10*math.pi)    #if object always visible when -5<HA<5
    elif ch >= 1.0:
      hafactor = 0             #Always below horizon
    else:
      hafactor = 5.0/(12*math.acos(ch)/math.pi) * math.cos(ha/(24*math.acos(ch)/math.pi)*math.pi)

    if hafactor > 10.0:
      hafactor = 10.0
    
  return movefactor * timefactor * altfactor * hafactor


def Ptest3(o):
  """Flatter priority function, useful mostly for PLANET or other objects observed many
     times per night. Priority =0 for alt<AltCutoff and abs(HA)>5, and has cos factor for
     the max of dome or telescope azimuth difference
  """
  timefactor = abs( (time.time() - o.LastObs) / (o.period*86400) )

  if o.ALT < AltCutoff:
    altfactor=0.0
  else:
    altfactor = 1.0  

  try:
    ha=o.RA - telescope.status.Time.LST
  except TypeError:
    ha = None   #Teljoy appears inactive, ignore LST and HA for now

  if ha is None:
    hafactor = 0.0
  else:
    if ha > 12:
      ha = ha -24
    elif ha < -12:
      ha = ha + 24
    if abs(ha) > 5:
      hafactor = 0.0           #Don't allow any jumps outside -5 < HA < +5 hours 
    else:                      #No matter what the altitude
      hafactor = 1.0

  try:
    moveangle=min( anglediff(telescope.status.Azi, o.AZ),
                   anglediff(telescope.status.current.RaC/3600, o.RA*15))

  except TypeError:
    moveangle = 0       #Teljoy appears inactive, ignore moveangle factor for testing
  movefactor = abs(math.cos(moveangle/360*math.pi))      #Cos(moveangle/2) in degrees


  return timefactor * altfactor * hafactor * movefactor



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
#        print id, cantimestamp,o.LastObs
        o.RA=stringsex(o.ObjRA)
        o.DEC=stringsex(o.ObjDec)
        if (o.RA is None) or (o.DEC is None):
          print "Bad RA or dec in object: ", id
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
        if (o.RA is None) or (o.DEC is None):
          print "Bad RA or dec in object: ", id
        if _valid(o):
          candidates[id] = o

  for k in candidates.keys():       #remove any existing candidates that are now invalid
    if not _valid(candidates[k]):   #eg, due to a change in the scheduler.types global
      del candidates[k]

  cantimestamp=temptime
  best=None
  for o in candidates.values():
    o.ALT, o.AZ = ephemint.altaz(o.RA, o.DEC)
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
db=MySQLdb.Connection(host='mysql', user='honcho', passwd='',
                      db='teljoy', cursorclass=DictCursor)
curs=db.cursor()
#print 'connected'
