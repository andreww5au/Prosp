
import MySQLdb
import threading
import time
import weather
from globals import *


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


def shutterwait(action='CLOSE'):
  """Closes the dome shutter. Will not return until the shutter is fully
     opened/closed. Note, if teljoy is not accepting remote control commands
     (eg old version of teljoy, or sitting at coordinate entry prompt), 
     this function WILL NOT EVER RETURN.

     Usage: shutterwait('OPEN')
            shutterwait('CLOSE')
  """
  curs=db.cursor()
  send=-1
  action=string.upper(string.strip(action))
  if action=='OPEN':
    send=1
    swrite("Opening Shutter.")
  elif action=='CLOSE':
    send=0
    swrite("Closing Shutter.")
  if send<0:
    ewrite("teljoy.shutterwait - Parameter must be 'OPEN' or 'CLOSE'")
  else:
    print "looping",send,status.ShutterInUse,status.ShutterOpen
    while status.ShutterInUse or (status.ShutterOpen <> send):
      if not existsTJbox(curs):
        curs.execute("insert into tjbox (Action,shutter) values"+
              " ('shutter', "+`send`+") ")
        print "resending tjbox",send,status.ShutterInUse,status.ShutterOpen
      print "waiting for shutter to finish",send,status.ShutterInUse,status.ShutterOpen
      time.sleep(5)
    print "finishing",send,status.ShutterInUse,status.ShutterOpen


def freeze(action=0):
  """Freezes all telescope tracking if the argument is true, unfreezes
     if the argument is false. Silently fails if Teljoy isn't ready to be
     remote-controlled (waiting at a coordinate prompt or an older
     version of Teljoy). Check the 'Frozen' status flag to see if
     this command has worked.

     Usage: freeze(1)
            freeze(0)
  """
  curs=db.cursor()
  curs.execute("insert into tjbox (Action,freeze) values ('freeze', "+`action`+") ")
  if action:
    swrite("Telescope frozen.")
  else:
    swrite("Telescope un-frozen.")


def pause():
  """Goes into "Pause" mode and closes dome, used during bad-weather
  """
  if not Active.isSet():
    ewrite("Teljoy already paused, can't pause() again")
  else:
    swrite("Teljoy Paused due to bad weather.")
    status.paused=1
    Active.clear()
    freeze(1)
    time.sleep(5)
    shutter('CLOSE')


def unpause():
  """Leaves "Pause" mode and opens dome, used when weather clears.
  """
  if Active.isSet():
    ewrite("Teljoy not in Pause mode, can't unpause()")
  else:
    swrite("Teljoy un-paused, weather OK now.")
    shutter('OPEN')
    time.sleep(5)
    freeze(0)
    time.sleep(5)
    Active.set()
    status.paused=0


def shutter(action='CLOSE'):
  """Open/close the shutter in a background thread so that the function returns
     immediately.
  """
  tmpthread=threading.Thread(target=shutterwait, args=(action,))
  tmpthread.run()


def _backgroundloop():
  """Run in the background, updating the status object.
  """
  if not weather.Background.isAlive():
    weather.Background.start()
  while 1:
    try:
      status.update()
      if weather.WeatherActive:
        if weather.Clear.isSet() and (not Active.isSet()):
          unpause()
        if (not weather.Clear.isSet()) and Active.isSet():
          pause()
      time.sleep(5)
    except:
      print "a teljoy exception"
      time.sleep(5)


Background=threading.Thread(name='TeljoyBackground', target=_backgroundloop)
Background.setDaemon(1)


db=MySQLdb.Connection(host='lear', user='honcho', passwd='',
                      db='teljoy', cursorclass=MySQLdb.DictCursor) 
curs=db.cursor()

status=TJstatus()
status.update()
