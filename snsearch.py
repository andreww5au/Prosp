
import time
import os

import MySQLdb
import safecursor
DictCursor=safecursor.SafeCursor

#Uncomment one of these lines to choose whether to use mailbox files or the
#table teljoy.vistabox to communicate with Vista

# VistaMail = 'file'
VistaMail = 'SQL'


from ftplib import FTP     #Import the FTP object class

from globals import *
import pipeline
import teljoy
dObject=pipeline.dObject



ftphost='rover'
ftpuser='plat'
ftppass='sn1993k'
ftpimagedir='/t/533-Observatory/Astronomical/Images/New'
ftpmaildir='/t/533-Observatory/Astronomical/Plat/Mail'
nfsimagedir='/chef/Astronomical/Images/new'


def _dosname(uname):
  "Return shortened filename for DOS 8.3 restrictions"
  dname=uname[:-1]   #strip .fits to .fit
  dname=dname[:-7]+dname[-5:]  #strip leading digits from filectr
  return dname


def nextseq():
  try:
    seq=int(open('/data/counters/snsearch.seq').read())
  except (NameError,ValueError):
    seq=1000000
  seq=seq+1
  try:
    open('/data/counters/snsearch.seq','w').write(`seq`+"\n")
  except:
    ewrite('Error writing SNSearch sequence number file.')
  return seq


class SNObject(dObject):

  def writemailbox(self):
    "Write the mailbox file in the format that Vista expects"
    swrite('writing autorun mailbox file - seq='+`self.seq`)
    f=open('/tmp/vista.box','w')
    f.write('Seq:     '+`self.seq`+"\r\n")  # back quotes convert to string type
    f.write('Name:    '+self.name+"\r\n")
    f.write('ExpTime: '+`self.exptime`+"\r\n")
    f.write('Filter:  '+self.filtname+"\r\n")
    f.write('ObjID:   '+self.ObjID+"\r\n")
    f.write('Top.RA:  '+self.ObjRA+"\r\n")
    f.write('Top.Dec: '+self.ObjDec+"\r\n")
    f.write('Epoch:   '+`self.ObjEpoch`+"\r\n")
    f.write('UT:      '+time.strftime("%H %M %S",time.gmtime())+"\r\n")
    f.write('UT_Date: '+time.strftime("%d %m %Y",time.gmtime())+"\r\n")
    f.write('JulDay:  '+`julday()`+"\r\n")
    f.write('Alt:     '+`teljoy.status.Alt`+"\r\n")
    f.write('Azi:     '+`teljoy.status.Azi`+"\r\n")
    f.write('RAtrk:   0\r\n')
    f.write('DECtrk:  0\r\n')
    f.write('XYpos:   '+`self.XYpos[0]`+" "+`self.XYpos[1]`+"\r\n")
    f.write('ObsType: '+self.type+"\r\n")
    f.write('FilName: '+self.dosname+"\r\n")
    f.write('Comment: '+self.comment+"\r\n")
    f.close()

  def writesqlbox(self):
    "Write an entry in the table teljoy.vistabox on the SQL server"
    curs.execute("insert into teljoy.vistabox (Seq,Name,exptime,filtname," +
                 "ObjID,ObjRA,ObjDec,Epoch,UT,JulDay,Alt,Azi,RAtrack,DECtrack," +
                 "XYpos_X,XYpos_Y,ObsType,filename,Comment) values ("+
         `self.seq`+", "+
         "'"+self.name+"', "+
         `self.exptime`+", "+
         "'"+self.filtname+"', "+
         "'"+self.ObjID+"', "+
         "'"+self.ObjRA+"', "+
         "'"+self.ObjDec+"', "+
         `self.ObjEpoch`+", "+
         "'"+time.strftime("%Y-%m-%d %H:%M:%S",time.gmtime())+"', "+
         `julday()`+", "+
         `teljoy.status.Alt`+", "+
         `teljoy.status.Azi`+", "+
         "0, 0, "+
         `self.XYpos[0]`+", "+
         `self.XYpos[1]`+", "+
         "'"+self.type+"', "+
         "'"+self.filename[4:]+"', "+
         "'"+self.comment+"') ")
       #Need to strip the '/big' off the beginning of the filename to math NFS mount paths
    

  def sendfilesftp(self):
    "Send image and mailbox files to vista via ftp, waiting if vista is busy"
    swrite('snsearch - sending files via ftp')

    #Temporary testing setup - convert to appropriate host/directories
    ftp=FTP(ftphost,ftpuser,ftppass)  #open connection and create
                                                # ftp object
    ftp.cwd(ftpimagedir)
    swrite("snsearch - ftp changed to "+ftpimagedir)

    #Send image file (using binary with 8kb blocksize
    f=open(self.filename,'r')
    ftp.storbinary('STOR '+self.dosname,f,8192)
    f.close()
    swrite("snsearch - ftp transferred "+ftpimagedir+'/'+self.dosname)

    ftp.cwd(ftpmaildir)
    swrite("snsearch - ftp changed to "+ftpmaildir)

    self.writemailbox()
    #Send mailbox file, as 'VISTA.NEW', deleting any previous file of that name
    if 'VISTA.NEW' in ftp.nlst():
      ftp.delete('VISTA.NEW')
    f=open('/tmp/vista.box','r')
    ftp.storbinary('STOR VISTA.NEW',f,1024)
    f.close()
    swrite("snsearch - ftp transferred "+ftpmaildir+'/vista.new')

    #Wait for vista.box to be deleted, then rename vista.new to vista.box
    while ('VISTA.BOX' in ftp.nlst()):
      print 'waiting for Vista to finish:'
      time.sleep(5)
    ftp.rename('VISTA.NEW','VISTA.BOX')
    ftp.quit()
    swrite("snsearch - ftp renamed VISTA.NEW to VISTA.BOX")


  def sendfilessql(self):
    "Send mailbox file to vista via sql, waiting if vista is busy"
#    while curs.execute("select * from vistabox"):
#      print 'Waiting for Vista to finish:'
#      time.sleep(5)
    print "WARNING! Communication with Vista disables, uncomment"
    print "the three lines above this message in snsearch.py!"
    self.writesqlbox()
    swrite("snsearch - SQL mailbox written to Vista")


  def reduce(self):
    "Send image and mailbox to vista for post-processing for SN-Search object"
    self.dosname=_dosname(os.path.basename(self.filename))
    self.seq=nextseq()
    if (self.filename) and (not self.errors):    #Data reduction completed OK
      if VistaMail == 'file':
        self.sendfilesftp()
      else:
        self.sendfilessql()
      curs.execute("update sn.targets set lastobs=NOW() where ObjID='"+self.ObjID+
         "' or altID='"+self.ObjID+"' ")
    else:
      ewrite("snsearch - Error processing "+self.ObjID+", aborting processing.")
      self.errors="snsearch - Error processing "+self.ObjID+", aborting processing."



#Unit initialisation

pipeline.Pipelines['IMAGE']=SNObject

swrite('SNSearch module connecting to database')
db=MySQLdb.Connection(host='mysql', user='honcho', passwd='',
                      db='teljoy', cursorclass=DictCursor)
curs=db.cursor()
swrite('connected')

