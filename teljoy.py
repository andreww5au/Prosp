
import MySQLdb
import threading
import time
import weather
from globals import *

ShutterAction=None
FreezeAction=None

pausetime=0

Active=threading.Event()
Active.set()

def _yn(arg=0):
  if arg:
    return 'yes'
  else:
    return 'no'


class TJstatus:
  "Telescope position and object info"

  def empty(self):
    "called by __init__ or manually to clear status"
    self.name=''
    self.ObjRA=None
    self.ObjDec=None
    self.ObjEpoch=None
    self.RawRA=None
    self.RawDec=None
    self.RawHourAngle=None
    self.Alt=None
    self.Azi=None
    self.LST=None
    self.UTDec=None
    self.posviolate=1
    self.moving=0
    self.EastOfPier=0
    self.NonSidOn=0
    self.DomeInUse=0
    self.ShutterInUse=0
    self.ShutterOpen=0
    self.DomeTracking=0
    self.Frozen=1
    self.AutoRunning=0
    self.NumRead=0
    self.CurNum=0
    self.RA_GuideAcc=0
    self.DEC_GuideAcc=0
    self.LastError=''
    self.lastmod=0
    self.paused=0
  def __init__(self):
    self.empty()
  def display(self):
    "Tells the status object to display itself"
    print 'Name=',self.name
    print 'ObjRA=',sexstring(self.ObjRA)
    print 'ObjDec=',sexstring(self.ObjDec)
    print 'ObjEpoch=',self.ObjEpoch
    print 'RawRA=',sexstring(self.RawRA)
    print 'RawDec=',sexstring(self.RawDec)
    print 'RawHourAngle=', self.RawHourAngle
    print 'Alt=',sexstring(self.Alt)
    print 'Azi=',sexstring(self.Azi)
    print 'LST=',sexstring(self.LST)
    print 'UTDec=',sexstring(self.UTDec)
    print 'posviolate=',_yn(self.posviolate)
    print 'moving=',_yn(self.moving)
    print 'EastOfPier=',_yn(self.EastOfPier)
    print 'NonSidOn=',_yn(self.NonSidOn)
    print 'DomeInUse=',_yn(self.DomeInUse)
    print 'ShutterInUse=',_yn(self.ShutterInUse)
    print 'ShutterOpen=',_yn(self.ShutterOpen)
    print 'DomeTracking=',_yn(self.DomeTracking)
    print 'Frozen=',_yn(self.Frozen)
    print 'AutoRunning=',_yn(self.AutoRunning)
    print 'NumRead=',self.NumRead
    print 'CurNum=',self.CurNum
    print 'RA_GuideAcc=',self.RA_GuideAcc
    print 'DEC_GuideAcc=',self.DEC_GuideAcc
    print 'LastError=',self.LastError
    print 'lastmod=',self.lastmod
    print 'paused=',self.paused

  def update(self):
    "Connect to the database to update fields"

    curs=db.cursor()
    curs.execute('select name,ObjRA,ObjDec,ObjEpoch,RawRA,RawDec,'+
         'RawHourAngle,Alt,Azi,LST,UTDec,posviolate,moving,'+
         'EastOfPier,NonSidOn,DomeInUse,ShutterInUse,ShutterOpen,'+
         'DomeTracking,Frozen,AutoRunning,NumRead,CurNum,'+
         'RA_GuideAcc,DEC_GuideAcc,LastError,'+
         'unix_timestamp(now())-unix_timestamp(LastMod) as lastmod '+
         'from current');

    c=curs.fetchallDict()[0]

    self.__dict__.update(c)   #Create self.name, self.ObjRA, etc from
                              #the data returned from the query

    if self.lastmod>300:
      tmp=self.lastmod
      self.empty()
      self.name="(no info)"
      self.lastmod=tmp

    self.updated()   #Call the 'updated' function to indicate fresh contents

  def updated(self):
    "Empty stub, override if desired. Called when status contents change"

  def __getstate__(self):   #Pickle module can't save external functions
    "Return all attributes of the instance except for 'updated'"
    d=self.__dict__.copy()
    del d['updated']
    return d


def existsTJbox(curs):
  """Returns true if the tjbox table has an entry. Takes one parameter, the
     database connection to use for the query.
  """
  curs.execute('select * from teljoy.tjbox')
  
  if curs.rowcount:
    return 1
  else:
    return 0


def jumpid(id=''):
  """Takes an Object ID and sends a command to Teljoy to jump to that object.
     It will silently fail if the object is not recognised by Teljoy, or
     if Teljoy is not ready to move under remote control.
     eg: jumpid('plref')
  """
  if len(id)<9 and len(id)>0:
    while existsTJbox(curs):
      print "Waiting for teljoy to become free"
      time.sleep(5)
    curs.execute("insert into tjbox (Action,ObjID) values ('jumpID', '"+id+"') ")
  else:
    ewrite("Invalid ID '"+id+"' for jumpid (must be 1 to 8 chars)")


def jump(id='', ra='', dec='', epoch=0):
  """Takes the ObjID, RA, Dec, and Epoch given, and sends a command to Teljoy
     to jump to that position. The Object ID is optional. It will silently
     fail if Teljoy isn't ready to be remote-controlled, or if there is
     something wrong with the position (below altitude cutoff, etc).
     eg: jump('frog','12:34:56','-32:00:00',1998.5)
         jump(id='plref', ra='17:47:28', dec='-27:49:49', epoch=1998.5)
  """
  if (len(ra)<5 or len(ra)>12 or len(dec)<5 or len(dec)>12 or epoch<0 or
        epoch>2100):
    ewrite("Invalid RA, Dec, or Epoch provided to teljoy.jump")
  else:
    while existsTJbox(curs):
      print "Waiting for teljoy to become free"
      time.sleep(5)
    curs.execute("insert into tjbox (Action,ObjID,ObjRA,ObjDec,ObjEpoch) "+
         "values ('jumpRD', '"+id+"', '"+ra+"', '"+dec+"', "+`epoch`+") ")


def jumpoff(offra=0, offdec=0):
  """Moves the telescope by offra,offdec arcseconds.
     Silently fails if Teljoy isn't ready to be remote-controlled.
     eg: jumpoff(2.45,-12.13)
  """
  if abs(offra)>7200 or abs(offdec)>7200:
    ewrite("jumpoff - Offsets must be less than 7200 arc seconds.")
  else:
    while existsTJbox(curs):
      print "Waiting for teljoy to become free"
      time.sleep(5)
    curs.execute("insert into tjbox (Action,OffsetRA,OffsetDec) "+
         "values ('offset', "+`offra`+", "+`offdec`+") ")


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
  jumpoff(oh,od)


def dome(azi=90):
  """Moves the dome to the given dome (NOT telescope) azimuth.
     Silently fails if Teljoy isn't ready to be remote-controlled.
     eg: dome(90)
  """
  if abs(azi)<0 or abs(azi)>359:
    ewrite("teljoy.dome - Azimuth must be 0-359 degrees")
  else:
    while existsTJbox(curs):
      print "Waiting for teljoy to become free"
      time.sleep(5)
    curs.execute("insert into tjbox (Action,DomeAzi) values ('dome', "+`azi`+") ")


def freeze(action=0):
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
    FreezeAction=1
  else:
    FreezeAction=0


def pause():
  """Goes into "Pause" mode and closes dome, used during bad-weather
  """
  global pausetime
  if not Active.isSet():
    ewrite("Teljoy already paused, can't pause() again")
  else:
    swrite("Teljoy Paused due to bad weather.")
    status.paused=1
    pausetime=time.time()     #Record when we've paused
    Active.clear()
    freeze(1)
    shutter('CLOSE')


def unpause():
  """Leaves "Pause" mode and opens dome, used when weather clears.
  """
  global pausetime
  if Active.isSet():
    ewrite("Teljoy not in Pause mode, can't unpause()")
  else:
    swrite("Teljoy un-paused, weather OK now.")
    pausetime=0          #Zap the pause time so the dome doesn't reclose
    shutter('OPEN')
    freeze(0)
    Active.set()
    status.paused=0


def shutter(action='CLOSE'):
  """Open/close the shutter. Argument must be 'OPEN' or 'CLOSE'. All
     action takes place in the background, so the function returns 
     immediately. If Teljoy is not in a state where it can be remote
     controlled, this function will do nothing.
  """
  global ShutterAction
  action=string.upper(string.strip(action))
  if action=="OPEN":
    ShutterAction=1
  elif action=="CLOSE":
    ShutterAction=0
  else:
    print "teljoy.shutter: Argument must be 'OPEN' or 'CLOSE'"


def _background():
  """Function to be run in the background, updates the status object.
  """
  global ShutterAction,FreezeAction
  try:
    sincepause=time.time()-pausetime
    if (sincepause>300) and (sincepause<480):
      shutter('CLOSE')             #If it's been 5-6 minutes since pausing,
                                   #close the shutter again to be safe
    curs=db.cursor()
    status.update()

    if ShutterAction <> None:
      if status.ShutterOpen <> ShutterAction:
        curs.execute("delete from tjbox")
        curs.execute("insert into tjbox (Action,shutter) values"+
                     " ('shutter', "+`ShutterAction`+") ")
      else:
        ShutterAction=None
    elif FreezeAction <> None:
      if status.Frozen <> FreezeAction:
        curs.execute("delete from tjbox")
        curs.execute("insert into tjbox (Action,freeze) values"+
                     " ('freeze', "+`FreezeAction`+") ")
      else:
        FreezeAction=None
  except KeyboardInterrupt:
    print "a teljoy exception"


db=MySQLdb.Connection(host='lear', user='honcho', passwd='',
                      db='teljoy', cursorclass=MySQLdb.DictCursor) 
curs=db.cursor()

status=TJstatus()
status.update()
