
import time
import os

import MySQLdb
try:
  DictCursor=MySQLdb.DictCursor
except AttributeError:     #New version of MySQLdb puts cursors in a seperate module
  import MySQLdb.cursors
  DictCursor=MySQLdb.cursors.DictCursor


from ftplib import FTP     #Import the FTP object class

from globals import *
import pipeline
import teljoy
from pipeline import dObject



ftphost='rover'
ftpuser='plat'
ftppass='sn1993k'
ftpimagedir='/t/533-Observatory/Astronomical/Images/New'
ftpmaildir='/t/533-Observatory/Astronomical/Plat/Mail'


def _dosname(uname):
  "Return shortened filename for DOS 8.3 restrictions"
  dname=uname[:-1]   #strip .fits to .fit
  dname=dname[:-7]+dname[-5:]  #strip leading digits from filectr
  return dname


def nextseq():
  try:
    seq=int(open('/data/counters/snsearch.seq').read())
  except NameError,ValueError:
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

  def sendfiles(self):
    "Send image and mailbox files to vista via ftp, waiting if vista is busy"
    swrite('autorun - sending files via ftp')

    self.writemailbox()
    #Temporary testing setup - convert to appropriate host/directories
    ftp=FTP(ftphost,ftpuser,ftppass)  #open connection and create
                                                # ftp object
    ftp.cwd(ftpimagedir)
    swrite("autorun - ftp changed to "+ftpimagedir)

    #Send image file (using binary with 8kb blocksize
    f=open(self.filename,'r')
    ftp.storbinary('STOR '+self.dosname,f,8192)
    f.close()
    swrite("autorun - ftp transferred "+ftpimagedir+'/'+self.dosname)

    ftp.cwd(ftpmaildir)
    swrite("autorun - ftp changed to "+ftpmaildir)
  
    #Send mailbox file, as 'VISTA.NEW', deleting any previous file of that name
    if 'VISTA.NEW' in ftp.nlst():
      ftp.delete('VISTA.NEW')
    f=open('/tmp/vista.box','r')
    ftp.storbinary('STOR VISTA.NEW',f,1024)
    f.close()
    swrite("autorun - ftp transferred "+ftpmaildir+'/vista.new')

    #Wait for vista.box to be deleted, then rename vista.new to vista.box
    while ('VISTA.BOX' in ftp.nlst()):
      print 'waiting for Vista to finish:'
      time.sleep(5)
    ftp.rename('VISTA.NEW','VISTA.BOX')
    ftp.quit()
    swrite("autorun - ftp renamed VISTA.NEW to VISTA.BOX")

  def reduce(self):
    "Send image and mailbox to vista for post-processing for SN-Search object"
    self.dosname=_dosname(os.path.basename(self.filename))
    self.seq=nextseq()
    if (self.filename) and (not self.errors):    #Data reduction completed OK
      self.sendfiles()
      curs.execute("update sn.targets set lastobs=NOW() where ObjID='"+self.ObjID+
         "' or altID='"+self.ObjID+"' ")
    else:
      ewrite("autorun - Error processing "+self.ObjID+", aborting auto mode.")
      self.errors="autorun - Error processing "+self.ObjID+", aborting auto mode."



#Unit initialisation

pipeline.Pipelines['IMAGE']=SNObject

swrite('SNSearch module connecting to database')
db=MySQLdb.Connection(host='lear', user='honcho', passwd='',
                      db='teljoy', cursorclass=DictCursor)
curs=db.cursor()
swrite('connected')

