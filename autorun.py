
#(Partly untested) program to use the AP7 camera for the Perth Automated
#Supernova Search. Uses the Python interface to 'Ariel', and communicates with
#the telescope control software ('Teljoy') via an SQL database, as well as 
#the image processing software running inside Vista on a PC (via ftp to 
#a shared filesystem)
#
#Written by Andrew Williams, Perth Observatory, 1999

localstore=0    #Set to 0 to send 'store' object files to vista
librarymode=0    #Force store mode SN library imgs

ftphost='bigbang'
ftpuser='plat'
ftppass='sn1993k'
ftpimagedir='/t/533-Observatory/Astronomical/Images/New'
ftpmaildir='/t/533-Observatory/Astronomical/Plat/Mail'

import ArCommands
from ArCommands import *
import MySQLdb
from ftplib import FTP     #Import the FTP object class
import time                #Time handler functions
import improc
import planet
import utils
import xpa
from xpa import display


class CCDbox:
  "An object containing the current CCDbox action parameters"
  def __init__(self):
    curs.execute('select * from ccdbox') #Use data from 'ccdbox' table in SQL
                                       # database provided by telescope software
    if curs.rowcount: 
      c=curs.fetchallDict()[0]
      self.valid=1
      self.error=0
      self.seq=int(c['Seq'])
      self.name=string.strip(c['Name'])
      self.exptime=float(c['exptime'])
      self.filter=string.strip(string.upper(c['filtname']))
      self.objid=string.strip(c['ObjID'])
      self.objra=string.strip(c['ObjRA'])
      self.objdec=string.strip(c['ObjDec'])
      self.objepoch=float(c['Epoch'])
      self.ut=c['UT'][8:10]+" "+c['UT'][10:12]+" "+c['UT'][12:]
      self.ut_date=c['UT'][6:8]+" "+c['UT'][4:6]+" "+c['UT'][:4]
      self.julday=float(c['JulDay'])
      self.alt=float(c['Alt'])
      self.azi=float(c['Azi'])
      self.ratrk=float(c['RAtrack'])
      self.dectrk=float(c['DECtrack'])
      self.xypos=(int(c['XYpos_X']),int(c['XYpos_Y']))
      self.obstype=string.strip(string.upper(c['ObsType']))
      self.basename=self.objid
      self.filename=''
      if c['Comment']:
        self.comment='(AP7) '+c['Comment']
      else:
        self.comment='(AP7)'
    else:
      self.valid=0

  def write(self):
    "Write the mailbox file in the format that Vista expects"
    swrite('writing autorun mailbox file - seq='+`self.seq`)
    f=open('/tmp/vista.box','w')
    f.write('Seq:     '+`self.seq`+"\r\n")  # back quotes convert to string type
    f.write('Name:    '+self.name+"\r\n")
    f.write('ExpTime: '+`self.exptime`+"\r\n")
    f.write('Filter:  '+self.filter+"\r\n")
    f.write('ObjID:   '+self.objid+"\r\n")
    f.write('Top.RA:  '+self.objra+"\r\n")
    f.write('Top.Dec: '+self.objdec+"\r\n")
    f.write('Epoch:   '+`self.objepoch`+"\r\n")
    f.write('UT:      '+self.ut+"\r\n")
    f.write('UT_Date: '+self.ut_date+"\r\n")
    f.write('JulDay:  '+`self.julday`+"\r\n")
    f.write('Alt:     '+`self.alt`+"\r\n")
    f.write('Azi:     '+`self.azi`+"\r\n")
    f.write('RAtrk:   '+`self.ratrk`+"\r\n")
    f.write('DECtrk:  '+`self.dectrk`+"\r\n")
    f.write('XYpos:   '+`self.xypos[0]`+" "+`self.xypos[1]`+"\r\n")
    f.write('ObsType: '+self.obstype+"\r\n")
    f.write('FilName: '+_dosname(os.path.basename(self.filename))+"\r\n")
    f.write('Comment: '+self.comment+"\r\n")
    f.close()

  def take(self):
    "Take a CCD image based on action parameters from 'ccdbox' table"
    swrite('autorun - about to take an image of '+self.objid+':')
    if self.obstype=='PLANET':
      _modplanet(self)
    elif self.obstype=='IMAGE':
      _modsnsearch(self)
    elif self.obstype=='STORE':
      _modstore(self)
    elif self.obstype=='PHOTOM':
      _modstore(self)

    object(self.objid)
    exptime(self.exptime)
    filename(self.basename)
    filter(self.filter)
    guider(self.xypos[0],self.xypos[1])
    swrite(self.basename+': '+`self.exptime`+' sec '+self.filter+', type='+self.obstype)

    self.filename=improc.reduce(fpat=go())
    display(self.filename)

    #Add UT, UT_Date, JulDay updates here too sometime

    if self.obstype=='STORE' or librarymode:
      _poststore(self)
    elif self.obstype=='PLANET':
      _postplanet(self)
    elif self.obstype=='IMAGE':
      _postsnsearch(self)
    elif self.obstype=='PHOTOM':
      _poststore(self)

  def sendfiles(self):
    "Send image and mailbox files to vista via ftp, waiting if vista is busy"
    swrite('autorun - sending files via ftp')

    self.write()
    #Temporary testing setup - convert to appropriate host/directories
    ftp=FTP(ftphost,ftpuser,ftppass)  #open connection and create
                                                # ftp object
    ftp.cwd(ftpimagedir)
    swrite("autorun - ftp changed to "+ftpimagedir)

    #Send image file (using binary with 8kb blocksize
    f=open(self.filename,'r')
    ftp.storbinary('STOR '+_dosname(os.path.basename(self.filename)),f,8192)
    f.close()
    swrite("autorun - ftp transferred "+ftpimagedir+'/'+_dosname(os.path.basename(self.filename)))

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



def _dosname(uname):
  "Return shortened filename for DOS 8.3 restrictions"
  dname=uname[:-1]   #strip .fits to .fit
  dname=dname[:-7]+dname[-5:]  #strip leading digits from filectr
  return dname



def _modplanet(box):
  "Modify box parameters for PLANET object"
  p=planet.Pobject(box.objid)
  if p.valid:
    box.objid=p.root
    box.basename=planet.site+p.root+box.filter[0]
  else:
    ewrite("autorun - PLANET object type with invalid ObjID: "+box.objid)
    box.error=1


def _modsnsearch(box):
  "Modify box parameters for SN-Search object"
  box.basename=box.objid
  # if librarymode:
  #  box.exptime=box.exptime*3


def _modstore(box):
  "Modify box paramers for 'store' object"


def _postplanet(box):
  "Do post-processing for PLANET object"
  if box.filename:
    box.filename=planet.allocate(box.filename)
  if box.filename:
    p=planet.Pobject(box.objid)
    if p.valid:
      planet.process(p.root)
    else:
      ewrite("autorun - error in objID "+box.objid+", aborting auto mode.")
      box.error=1
  else:
    ewrite("autorun - Error processing "+box.objid+", aborting auto mode.")
    box.error=1


def _postsnsearch(box):
  "Do post-processing for SN-Search object"
  if box.filename:    #Data reduction completed OK
    box.sendfiles()
    curs.execute("update sn.targets set lastobs=NOW() where ObjID='"+box.objid+
       "' or altID='"+box.objid+"' ")
  else:
    ewrite("autorun - Error processing "+box.objid+", aborting auto mode.")
    box.error=1


def _poststore(box):
  "Do post-processing for 'store' object"
  box.obstype='STORE'   #Force store type in case we are in 'forcestore' mode
  if not localstore:
    if box.filename:    #Data reduction completed OK
      box.sendfiles()
    else:
      ewrite("autorun - Error preprocessing "+box.objid+", aborting auto mode.")
      box.error=1

 
 
def auto():
  """Go into automatic mode in the directory that the current 'path' is set to.
     A subdirectory below this will be created for reduced images.
     Exit by typing ^C.
     eg: auto()
  """
  global curs,wd
  swrite('Automatic mode in '+status.path+' - hit ^C to exit')
  global status
  status.ObsType=''
  try:
    swrite('connecting to database for mailbox info')
    db=MySQLdb.Connection(host='lear', user='honcho', passwd='',
                          db='teljoy', cursorclass=MySQLdb.DictCursor)
    curs=db.cursor()
    swrite('connected')
    wd=os.getcwd()
    os.chdir(status.path)
    while 1:                                #Loop forever
      print 'Waiting to take an image:'
      box=CCDbox()
      while (not box.valid) or status.TJ.paused: 
        time.sleep(5)
        box=CCDbox()
      if not box.error:
        box.take()                       #Take image
        curs.execute('delete from ccdbox')  #Delete ccdbox record to indicate
                                            # readiness for another image
      if box.error:
        break                         #Exit auto mode if there's a problem.

  except KeyboardInterrupt:
    swrite('Automatic mode aborted')
    os.chdir(wd)

