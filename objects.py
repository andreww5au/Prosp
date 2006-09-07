
import MySQLdb
import safecursor
DictCursor=safecursor.SafeCursor

import string


class Object:

  def empty(self):
    self.ObjID=''
    self.name=''
    self.origid=''
    self.ObjRA=''
    self.ObjDec=''
    self.ObjEpoch=0
    self.filtname=''
    self.exptime=1
    self.subframes=1
    self.sublist=[('',0.0)]
    self.XYpos=(0,0)
    self.type=''
    self.period=0.0
    self.comment=''
    self.LastObs=0.0
    self.errors=''

  def __init__(self, str='', curs=None):
    if not curs:
      curs=db.cursor()
    if str=='':
      self.empty()
    else:
      curs.execute("select * from objects where ObjID='"+str+"'")
      
      if not curs.rowcount:
        self.empty()
        self.ObjID=str
        return
      else:
        c=curs.fetchallDict()[0]
      self.ObjID=c['ObjID']
      self.name=c['name']
      self.origid=self.ObjID
      self.ObjRA=c['ObjRA']
      self.ObjDec=c['ObjDec']
      self.ObjEpoch=float(c['ObjEpoch'])
      filtnames = c['filtnames']
      exptimes = c['exptimes']
      self.subframes,self.sublist = psl(filtnames,exptimes)
      self.XYpos=(int(c['XYpos_X']),int(c['XYpos_Y']))
      self.type=c['type']
      try:
        self.period=float(c['period'])
      except TypeError:
        self.period=0.0
      self.comment=c['comment']
      try:
        self.LastObs=float(c['LastObs'])
      except TypeError:
        self.LastObs=0
      if not self.ObjRA:
        self.ObjRA=''
      if not self.ObjDec:
        self.ObjDec=''
      if not self.type:
        self.type=''
      if not self.comment:
        self.comment=''
      self.errors=''
      self.subframe(0)

  def subframe(self, n=0):
    """Change the exposure time and filter to the n'th pair in the subframes list
    """
    if (n > self.subframes) or (n > len(subframes)-1):
      print "Invalid subframe number ",n," in object ",self.ObjID
    else:
      self.filtname, self.exptime = self.sublist[n]

  def updatetime(self, curs=None):
    if not curs:
      curs=db.cursor()
    curs.execute("update objects set lastobs=NOW() where ObjID='"+self.ObjID+"'")

  def display(self):
    print '%9s:%11s %11s (%6.1f)%8s%6.5g (%5d,%5d)%8s * %d' % (self.ObjID,
             self.ObjRA,
             self.ObjDec,
             self.ObjEpoch,
             self.filtname,
             self.exptime,
             self.XYpos[0],self.XYpos[1],
             self.type,
             self.subframes)

  def __repr__(self):
    return "Object[" + self.ObjID + "]"

  def __str__(self):
    return 'O[%9s:%11s %11s (%6.1f)%8s%6.5g (%5d,%5d)%8s * %d]' % (self.ObjID,
             self.ObjRA,
             self.ObjDec,
             self.ObjEpoch,
             self.filtname,
             self.exptime,
             self.XYpos[0],self.XYpos[1],
             self.type,
             self.subframes)
 

  def save(self,ask=1,force=0, curs=None):
    if not curs:
      curs=db.cursor()
    if self.ObjID=='':
      print "Empty ObjID, can't save object."
      return 0
    filtnames,exptimes = pls(self.sublist)
    if not curs.execute("select * from objects where ObjID='"+self.ObjID+"'"):
      curs.execute("insert into objects (ObjID,name,ObjRA,ObjDec,ObjEpoch,filtnames,"+
         "exptimes,"+
         "XYpos_X,XYpos_Y,type,period,comment) values ("+
         "'"+self.ObjID+"', "+
         "'"+self.name+"', "+
         "'"+self.ObjRA+"', "+
         "'"+self.ObjDec+"', "+
         `self.ObjEpoch`+", "+
         "'"+filtnames+"', "+
         "'"+exptimes+"', "+
         `self.XYpos[0]`+", "+
         `self.XYpos[1]`+", "+
         "'"+self.type+"', "+
         `self.period`+", "+
         "'"+self.comment+"') ")
      if string.upper(self.origid)<>string.upper(self.ObjID):
        if self.origid<>'':
          curs.execute("delete from objects where ObjID='"+self.origid+"'")
    else:
      if ask:
        print "Entry "+self.ObjID+" already exists, do you want to replace it?"
        ans=string.strip(string.lower(raw_input("y/n (default n): ")))[:1]
        if ans<>'y':
          print "Object "+self.ObjID+" not overwritten."
          return 0
      else:
        if not force:
          print "Object "+self.ObjID+" not overwritten."
          return 0
      curs.execute("update objects set "+
         "ObjID='"+self.ObjID+"', "+
         "name='"+self.name+"', "+
         "ObjRA='"+self.ObjRA+"', "+
         "ObjDec='"+self.ObjDec+"', "+
         "ObjEpoch="+`self.ObjEpoch`+", "+
         "filtnames='"+filtnames+"', "+
         "exptimes='"+exptimes+"', "+
         "XYpos_X="+`self.XYpos[0]`+", "+
         "XYpos_Y="+`self.XYpos[1]`+", "+
         "type='"+self.type+"', "+
         "period="+`self.period`+", "+
         "comment='"+self.comment+"' "+
         "where ObjID='"+self.ObjID+"'")

    print "Object "+self.ObjID+" saved."
    return 1


  def delete(self, ask=1, curs=None):
    if not curs:
      curs=db.cursor()
    if self.ObjID=='':
      print "Empty ObjID, can't delete object."
      return 0
    curs.execute("select * from objects where ObjID='"+self.ObjID+"'")
    if not curs.rowcount:
      print "Object not found in database."
      return 0
    if ask:
      print "Entry "+self.ObjID+" already exists, do you want to replace it?"
      ans=string.strip(string.lower(raw_input("y/n (default n): ")))[:1]
      if ans<>'y':
        print "Object "+self.ObjID+" not deleted."
        return 0
    curs.execute("delete from objects where ObjID='"+self.ObjID+"'")
    print "Object "+self.ObjID+" deleted from database."
    return 1


def ZapPeriods(period=0, type='', curs=None):
  """Take an object type and set the desired observing interval for all objects of that
     type to the specified period, in days.
  """
  if not curs:
    curs=db.cursor()
  if type:
    curs.execute("update teljoy.objects set period="+`period`+" where type='"+type+"' and ObjID not like 'P%'")
   


def psl(filtnames='I',exptimes='1.0'):
  """Given filtnames and exptimes, return subframes and sublist.
  """
  filtlist = filtnames.split()
  exptlist = exptimes.split()
  if not filtlist:
    filtlist = ['I']
  if not exptlist:
    exptlist = [10.0]
  sublist = []
  if len(exptlist) == 1:
    subframes = len(filtlist)
    for fn in filtlist:
      sublist.append( (fn,float(exptlist[0])) )
  else:
    if len(filtlist) == 1:
      subframes = len(exptlist)
      for et in exptlist:
        sublist.append( (filtlist[0],float(et)) )
    else:
      if len(filtlist) == len(exptlist):
        subframes = len(exptlist)
        for i in range(len(filtlist)):
          sublist.append( (filtlist[i],float(exptlist[i])) )
      else:
        print "No match between number of filts and number of exptimes in object: "+self.ObjID
        subframes = 1
        sublist.append( (filtlist[0],float(exptlist[0])) )
  return subframes,sublist


def pls(sublist):
  """Given a subframe list of (filter,exptime) pairs, return
     filtnames and exptimes strings for putting in the database.
  """
  filtnames = ''
  exptimes = ''
  for p in sublist:
    filtnames += p[0]+' '
    exptimes += `p[1]`+' '
  return filtnames.strip(), exptimes.strip()




def allobjects(curs=None):
  "Return a list of all objects in the Object database."
  if not curs:
    curs=db.cursor()
  curs.execute("select ObjID from objects")
  c=curs.fetchallDict()
  olist=[]
  for row in c:
    olist.append(Object(row['ObjID']))
  return olist

def sortid(o,p):
  return cmp(o.ObjID,p.ObjID)

def sortra(o,p):
  return cmp(o.ObjRA,p.ObjRA)

def sortdec(o,p):
  return cmp(o.ObjDec,p.ObjDec)

def sorttype(o,p):
  return cmp(o.type,p.type)



#print 'connecting to database for objects database access'
db=MySQLdb.Connection(host='lear', user='honcho', passwd='',
                      db='teljoy', cursorclass=DictCursor)
#print 'connected'

