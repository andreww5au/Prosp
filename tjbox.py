
import MySQLdb
import threading
import datetime

import safecursor
from globals import *

DictCursor = safecursor.SafeCursor

ShutterAction = None
FreezeAction = None

Active = threading.Event()
Active.set()

status = None

def _yn(arg=0):
  if arg:
    return 'yes'
  else:
    return 'no'


class DomeStatus(object):
  def __init__(self):
    self.DomeInUse = False
    self.ShutterInUse = False
    self.DomeMoved = False
    self.ShutterOpen = False
    self.DomeThere = False
    self.AutoDome = False
    self.DomeTracking = False
    self.DomeLastTime = 0
    self.NewDomeAzi = -10
    self.NewShutter = ''


class TimeStatus(object):
  def __init__(self):
    self.UT = datetime.datetime.utcnow()    #Current date and time, in UTC
    self.JD = 0.0                           #Fractional Julian Day
    self.LST = 0.0                          #Local Sidereal Time, in hours


class CurrentStatus(object):
  def __init__(self):
    self.Ra = None
    self.Dec = None
    self.Epoch = None
    self.RaA = None
    self.DecA = None
    self.RaC = None
    self.DecC = None
    self.Alt = None
    self.Azi = None
    self.ObjID = None
    self.TraRA = None
    self.TraDEC = None
    self.posviolate = None
    self.Time = TimeStatus()
    self.DomePos = None


class MotorsStatus(object):
  def __init__(self):
    self.Jumping = False
    self.Paddling = False
    self.Moving = False
    self.PosDirty = False
    self.ticks = 0
    self.Frozen = False


class PrefsStatus(object):
  def __init__(self):
    self.EastOfPier = False


class TJstatus(object):
  """Telescope position and object info
  """
  def __init__(self):
    self.paused = False
    self.dome = DomeStatus()
    self.current = CurrentStatus()
    self.motors = MotorsStatus()
    self.prefs = PrefsStatus()
    self.info = ''
    self.lastmod = 0

  def display(self):
    "Tells the status object to display itself"
    print 'ObjID=', self.current.ObjID
    print 'ObjRA=', sexstring(self.current.Ra/15/3600)
    print 'ObjDec=', sexstring(self.current.Dec/3600)
    print 'ObjEpoch=', self.current.Epoch
    print 'RawRA=', sexstring(self.current.RaC/15/3600)
    print 'RawDec=', sexstring(self.current.DecC/3600)
    print 'RawHourAngle=', sexstring(self.current.RaC/15/3600-self.current.Time.LST)
    print 'Alt=', sexstring(self.current.Alt)
    print 'Azi=', sexstring(self.current.Azi)
    print 'LST=', sexstring(self.current.Time.LST)
    print 'UT=', self.current.Time.UT
    print 'posviolate=', _yn(self.current.posviolate)
    print 'moving=', _yn(self.motors.Moving)
    print 'EastOfPier=', _yn(self.prefs.EastOfPier)
    print 'DomeInUse=', _yn(self.dome.DomeInUse)
    print 'ShutterInUse=', _yn(self.dome.ShutterInUse)
    print 'ShutterOpen=', _yn(self.dome.ShutterOpen)
    print 'DomeTracking=', _yn(self.dome.DomeTracking)
    print 'Frozen=', _yn(self.motors.Frozen)
    print 'lastmod=', self.lastmod
    print 'paused=', self.paused

  def update(self, u_curs=None):
    "Connect to the database to update fields"

    if not u_curs:
      u_curs = db.cursor()
    u_curs.execute('select name,ObjRA,ObjDec,ObjEpoch,RawRA,RawDec,' +
                   'RawHourAngle,Alt,Azi,LST,UTDec,posviolate,moving,' +
                   'EastOfPier,NonSidOn,DomeInUse,ShutterInUse,ShutterOpen,' +
                   'DomeTracking,Frozen,AutoRunning,NumRead,CurNum,' +
                   'RA_GuideAcc,DEC_GuideAcc,LastError,' +
                   'unix_timestamp(now())-unix_timestamp(LastMod) as lastmod ' +
                   'from current')

    c = u_curs.fetchallDict()[0]

    self.current.ObjID = c['name']
    self.current.Ra = c['ObjRa']*15*3600
    self.current.Dec = c['ObjDec']*3600
    self.current.Epoch = c['ObjEpoch']
    self.current.RaC = c['RawRA']
    self.current.DecC = c['RawDec']
    self.current.Alt = c['Alt']
    self.current.Azi = c['Azi']
    self.current.Time.LST = c['LST']
    self.current.Time.UT = c['UTDec']
    self.current.posviolate = c['posviolate']
    self.dome.DomeInUse = c['DomeInUse']
    self.dome.ShutterInUse = c['ShutterInUse']
    self.dome.ShutterOpen = c['ShutterOpen']
    self.dome.DomeTracking = c['DomeTracking']
    self.motors.Moving = c['moving']
    self.motors.Frozen = c['Frozen']
    self.lastmod = c['lastmod']

    if self.lastmod > 300:
      tmp = self.lastmod
      self.__init__()   #Empty all values
      self.current.ObjID = "(no info)"
      self.lastmod = tmp


def existsTJbox(curs):
  """Returns true if the tjbox table has an entry. Takes one parameter, the
     database connection to use for the query.
  """
  curs.execute('select * from teljoy.tjbox')

  if curs.rowcount:
    return 1
  else:
    return 0


def jump(id='', ra='', dec='', epoch=0):
  """Takes the ObjID, RA, Dec, and Epoch given, and sends a command to Teljoy
     to jump to that position. The Object ID is optional. It will silently
     fail if Teljoy isn't ready to be remote-controlled, or if there is
     something wrong with the position (below altitude cutoff, etc).
     eg: jump('frog','12:34:56','-32:00:00',1998.5)
         jump(id='plref', ra='17:47:28', dec='-27:49:49', epoch=1998.5)
  """
  if (len(ra) < 5 or len(ra) > 12 or len(dec) < 5 or len(dec) > 12 or epoch < 0 or
      epoch > 2100):
    logger.error("Invalid RA, Dec, or Epoch provided to teljoy.jump")
  else:
    curs = db.cursor()
    while existsTJbox(curs):
      print "Waiting for teljoy to become free"
      time.sleep(5)
    curs.execute("insert into tjbox (Action,ObjID,ObjRA,ObjDec,ObjEpoch) " +
                 "values ('jumpRD', '" + id + "', '" + ra + "', '" + dec + "', " + `epoch` + ") ")


def jumpoff(offra=0, offdec=0):
  """Moves the telescope by offra,offdec arcseconds.
     Silently fails if Teljoy isn't ready to be remote-controlled.
     eg: jumpoff(2.45,-12.13)
  """
  if abs(offra) > 7200 or abs(offdec) > 7200:
    logger.error("jumpoff - Offsets must be less than 7200 arc seconds.")
  else:
    while existsTJbox(curs):
      print "Waiting for teljoy to become free"
      time.sleep(5)
    curs.execute("insert into tjbox (Action,OffsetRA,OffsetDec) " +
                 "values ('offset', " + `offra` + ", " + `offdec` + ") ")


def dome(arg=90):
  """Moves the dome (given an azimuth), or opens/shuts it, given
     a string that looks like 'open' or 'close'.
     Silently fails if Teljoy isn't ready to be remote-controlled.
     eg: dome(90)
  """
  if type(arg)==int or type(arg)==float:
    _dmove(arg)
  elif type(arg)==str:
    if arg.upper() in ['O','OPEN']:
      _dshutter('OPEN')
    elif arg.upper() in ['C','CLOSE']:
      _dshutter('CLOSE')
    else:
      print "Unknown argument: specify an azimuth in degrees, or 'open', or 'close'"
  else:
    print "Unknown argument: specify an azimuth in degrees, or 'open', or 'close'"


def _dmove(azi):
  """Moves the dome to the given dome (NOT telescope) azimuth.
     Silently fails if Teljoy isn't ready to be remote-controlled.
     eg: dome(90)
  """
  if abs(azi) < 0 or abs(azi) > 359:
    logger.error("teljoy.dome - Azimuth must be 0-359 degrees")
  else:
    while existsTJbox(curs):
      print "Waiting for teljoy to become free"
      time.sleep(5)
    curs.execute("insert into tjbox (Action,DomeAzi) values ('dome', " + `azi` + ") ")


def freeze(action=True):
  """Freezes all telescope tracking if the argument is true, unfreezes
     if the argument is false. Silently fails if Teljoy isn't ready to be
     remote-controlled (waiting at a coordinate prompt or an older
     version of Teljoy). Check the 'Frozen' status flag to see if
     this command has worked.

     Usage: freeze(1)
            freeze(0)
  """
  global FreezeAction
  if action:
    FreezeAction = 1
  else:
    FreezeAction = 0


def unfreeze():
  """Unfreezes the telescope - utility function to match calls in new RPC protocol.
  """
  freeze(False)


def _dshutter(action='CLOSE'):
  """Open/close the shutter. Argument must be 'OPEN' or 'CLOSE'. All
     action takes place in the background, so the function returns
     immediately. If Teljoy is not in a state where it can be remote
     controlled, this function will do nothing.
  """
  global ShutterAction
  action = action.strip().upper()
  if action == "OPEN":
    ShutterAction = 1
  elif action == "CLOSE":
    ShutterAction = 0
  else:
    logger.error("teljoy.shutter: Argument must be 'OPEN' or 'CLOSE'")


def _background():
  """Function to be run in the background, updates the status object.
  """
  global ShutterAction, FreezeAction
  try:
    b_curs = b_db.cursor()
    status.update(b_curs)

    if ShutterAction <> None:
      if status.ShutterOpen <> ShutterAction:
        b_curs.execute("delete from tjbox")
        b_curs.execute("insert into tjbox (Action,shutter) values" +
                       " ('shutter', " + `ShutterAction` + ") ")
      else:
        ShutterAction = None
    elif FreezeAction <> None:
      if status.Frozen <> FreezeAction:
        b_curs.execute("delete from tjbox")
        b_curs.execute("insert into tjbox (Action,freeze) values" +
                       " ('freeze', " + `FreezeAction` + ") ")
      else:
        FreezeAction = None
    else:
      if not existsTJbox(b_curs):
        b_curs.execute("insert into tjbox (Action) values ('none')")

  except KeyboardInterrupt:
    print "a keyboard interrupt in tjbox._background()"


def Init():
  """Call externally to set up the database commes, etc
  """
  global db, b_db, curs, status
  db = MySQLdb.Connection(host='mysql', user='honcho', passwd='',
                          db='teljoy', cursorclass=DictCursor)
  b_db = MySQLdb.Connection(host='mysql', user='honcho', passwd='',
                            db='teljoy', cursorclass=DictCursor)

  curs = db.cursor()
  status = TJstatus()