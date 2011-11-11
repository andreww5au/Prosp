
import time
import datetime

from globals import *

import pipeline
import ephemint

import MySQLdb
import safecursor
DictCursor = safecursor.SafeCursor

LastFocusTime = 0
FocusInterval = 3600*2    #3 hours in ephem tics


def check():
  """Check time to see if a service observations is required.
  """
  global LastFocusTime
  hn = ephemint.herenow()         #get ephem time
  if (time.time()-LastFocusTime) > FocusInterval:     #It's been too long since the last focus image
    bestake = GetBestFocusStar(float(hn.date))   #Get current best focus star
    errors = bestake.take() 
    if errors:
      ewrite("Error executing 'take' command for focus observation")
    LastFocusTime = time.time()


def GetBestFocusStar(attime=0):
  """Connect to the objects database and re-get all objects whose 'lastmod'
     timestamp is more recent than 'cantimestamp', the last update time.
     After getting any changed objects, calculate a new alt and azimuth for each
     object, then calculate the priority function for each object.
  """
  candidates = {}
  curs.execute("select ObjID from objects where type='FOCUS'")
  c = curs.fetchallDict()
  for row in c:
    id = row['ObjID']
    o = pipeline.getobject(id)
    o.RA = stringsex(o.ObjRA)
    o.DEC = stringsex(o.ObjDec)
    if (o.RA is None) or (o.DEC is None):
      print "Bad RA or dec in object: ", id
    else:
      candidates[id] = o

  best = None
  bestALT = 0.0
  for o in candidates.values():
    o.ALT, o.AZ = ephemint.altazat(ra=o.RA, dec=o.DEC, att=attime)
    if (o.ALT >= bestALT):
      bestALT = o.ALT
      best = o
  return best



#print 'connecting to database for objects database access'
db = MySQLdb.Connection(host='mysql', user='honcho', passwd='',
                      db='teljoy', cursorclass=DictCursor)
curs = db.cursor()
#print 'connected'
