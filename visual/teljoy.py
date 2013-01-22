
import MySQLdb
import convert
from convert import *

def yn(arg=0):
  if arg:
    return 'yes'
  else:
    return 'no'

class TJstatus:
  "Telescope position and object info"

  def empty(self):
    "called by __init__ or manually to clear status"
    self.name=''
    self.ObjRA=0
    self.ObjDec=0
    self.ObjEpoch=0
    self.RawRA=0
    self.RawDec=0
    self.RawHourAngle=0
    self.Alt=0
    self.Azi=0
    self.LST=0
    self.UTDec=0
    self.posviolate=0
    self.moving=0
    self.EastOfPier=0
    self.NonSidOn=0
    self.DomeInUse=0
    self.ShutterInUse=0
    self.DomeTracking=0
    self.Frozen=0
    self.RA_GuideAcc=0
    self.DEC_GuideAcc=0
    self.LastMod=''
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
    print 'posviolate=',yn(self.posviolate)
    print 'moving=',yn(self.moving)
    print 'EastOfPier=',yn(self.EastOfPier)
    print 'NonSidOn=',yn(self.NonSidOn)
    print 'DomeInUse=',yn(self.DomeInUse)
    print 'ShutterInUse=',yn(self.ShutterInUse)
    print 'DomeTracking=',yn(self.DomeTracking)
    print 'Frozen=',yn(self.Frozen)
    print 'RA_GuideAcc=',self.RA_GuideAcc
    print 'DEC_GuideAcc=',self.DEC_GuideAcc
    print 'LastMod=',self.LastMod

  def update(self):
    "Connect to the database to update fields"
    cursor.execute('select * from ncurrent')
    c=cursor.fetchall()[0]                                         
                                       
    self.name=c[0]
    self.ObjRA=c[1]
    self.ObjDec=c[2]
    self.ObjEpoch=c[3]
    self.RawRA=c[4]
    self.RawDec=c[5]
    self.RawHourAngle=c[6]
    self.Alt=c[7]
    self.Azi=c[8]
    self.LST=c[9]
    self.UTDec=c[10]
    self.posviolate=c[11]
    self.moving=c[12]
    self.EastOfPier=c[13]
    self.NonSidOn=c[14]
    self.DomeInUse=c[15]
    self.ShutterInUse=c[16]
    self.ShutterOpen=c[17]
    self.DomeTracking=c[18]
    self.Frozen=c[19]
    self.RA_GuideAcc=c[20]
    self.DEC_GuideAcc=c[21]
    self.lastmod=c[23]

    self.updated()   #Call the 'updated' function to indicate fresh contents

  def updated(self):
    "Empty stub, override if desired. Called when status contents change"

class TJobj:

  def empty(self):
    self.ObjID=''
    self.ObjRA=''
    self.ObjDec=''
    self.ObjEpoch=0
    self.filtname=''
    self.exptime=1
    self.XYpos_X=0
    self.XYpos_Y=0
    self.lastmod=-1

  def __init__(self,str=''):
    if str=='':
      self.empty
    else:
      cursor.execute("select * from objects where ObjID='"+str+"'")
      c=cursor.fetchall()[0]

      self.ObjID=c[0]
      self.ObjRA=c[1]
      self.ObjDec=c[2]
      self.ObjEpoch=float(c[3])
      self.filtname=c[4]
      self.exptime=float(c[5])
      self.XYpos=(int(c[6]),int(c[7]))
      self.lastmod=int(c[8])



def jumpid(id=''):
  if len(id)<9 and len(id)>0:
    cursor.execute("insert into tjbox (ObjID) values ('"+id+"') ")
  else:
    print "Invalid object ID for jump (must be 1 to 8 characters long)"

def jump(id='', ra='', dec='', epoch=0):
  "Jumps to a new RA and Dec"
  if (len(ra)<5 or len(ra)>12 or len(dec)<5 or len(dec)>12 or epoch<0 or 
        epoch>2100):
    print "Invalid RA, Dec, or Epoch provided to teljoy.jump"
  else:
    cursor.execute("insert into tjbox (ObjID,ObjRA,ObjDec,ObjEpoch) "+
         "values ('"+ra+"', '"+dec+"', "+`epoch`+") ")

def jumpoff(offra=0, offdec=0):
  "Moves the telescope by offra,offdec arcseconds"
  if abs(offra)>7200 or abs(offdec)>7200:
    print "Offsets must be less than 7200 arc seconds."
  else:
    cursor.execute("insert into tjbox (OffsetRA,OffsetDec) "+
         "values ("+`offra`+", "+`offdec`+") ")

def dome(azi=90):
  "Moves the dome to the given dome (NOT telescope) azimuth."
  if abs(azi)<0 or abs(azi)>359:
    print "Azimuth must be 0-359 degrees"
  else:
    cursor.execute("insert into tjbox (DomeAzi) values ("+`azi`+") ")




     

print 'connecting to database for teljoy status info'
db=MySQLdb.connect(db='teljoy',host='chef',user='honcho',passwd='')
cursor=db.cursor()
print 'connected'
status=TJstatus()

