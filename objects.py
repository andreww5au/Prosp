
import MySQLdb
import string

def _gets(prompt='', df=''):
  "Ask the user for a string, return the value given in def as a default"
  str=raw_input(prompt+' ('+df+'): ')
  if str=='':
    return df
  else:
    return str

def _getn(prompt='', df=0.0):
  "Ask the user for a number, return the value given in def as a default"
  str=raw_input(prompt+' ('+`df`+'): ')
  if str=='':
    return df
  else:
    return float(str)

def _gett(prompt='', df=(0,0)):
  "Ask the user for a tuple, return the value given in def as a default"
  str=raw_input(prompt+' ('+`df`+'): ')
  if str=='':
    return df
  else:
    return eval(str)


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
    self.XYpos=(0,0)
    self.type=''
    self.comment=''
    self.errors=''

  def __init__(self,str=''):
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
      self.filtname=c['filtname']
      self.exptime=float(c['exptime'])
      self.XYpos=(int(c['XYpos_X']),int(c['XYpos_Y']))
      self.type=c['type']
      self.comment=c['comment']
      if not self.ObjRA:
        self.ObjRA=''
      if not self.ObjDec:
        self.ObjDec=''
      if not self.filtname:
        self.filtname=''
      if not self.type:
        self.type=''
      if not self.comment:
        self.comment=''
      self.errors=''

  def edit(self):
    self.ObjID=_gets('ObjID',self.ObjID)
    self.name=_gets('Name',self.name)
    self.ObjRA=_gets('RA',self.ObjRA)
    self.ObjDec=_gets('Dec',self.ObjDec)
    self.ObjEpoch=_getn('Epoch',self.ObjEpoch)
    self.filtname=_gets('Filter',self.filtname)
    self.exptime=_getn('ExpTime',self.exptime)
    self.XYpos=_gett('XY pos',self.XYpos)
    self.type=_gets('Type',self.type)
    self.comment=_gets('Comment',self.comment)

  def display(self):
    print '%9s:%11s %11s (%6.1f)%8s%6.5g (%5d,%5d)%8s' % (self.ObjID,
             self.ObjRA,
             self.ObjDec,
             self.ObjEpoch,
             self.filtname,
             self.exptime,
             self.XYpos[0],self.XYpos[1],
             self.type)

  def save(self,ask=1,force=0):
    if self.ObjID=='':
      print "Empty ObjID, can't save object."
      return 0
    if not curs.execute("select * from objects where ObjID='"+self.ObjID+"'"):
      curs.execute("insert into objects (ObjID,name,ObjRA,ObjDec,ObjEpoch,filtname,"+
         "exptime,"+
         "XYpos_X,XYpos_Y,type,comment) values ("+
         "'"+self.ObjID+"', "+
         "'"+self.name+"', "+
         "'"+self.ObjRA+"', "+
         "'"+self.ObjDec+"', "+
         `self.ObjEpoch`+", "+
         "'"+self.filtname+"', "+
         `self.exptime`+", "+
         `self.XYpos[0]`+", "+
         `self.XYpos[1]`+", "+
         "'"+self.type+"', "+
         "'"+self.comment+"' ) ")
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
         "filtname='"+self.filtname+"', "+
         "exptime="+`self.exptime`+", "+
         "XYpos_X="+`self.XYpos[0]`+", "+
         "XYpos_Y="+`self.XYpos[1]`+", "+
         "type='"+self.type+"', "+
         "comment='"+self.comment+"' "+
         "where ObjID='"+self.ObjID+"'")

    print "Object "+self.ObjID+" saved."
    return 1

  def delete(self,ask=1):
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



def allobjects():
  "Return a list of all objects in the Object database."
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
                      db='teljoy', cursorclass=MySQLdb.DictCursor)
curs=db.cursor()
#print 'connected'

