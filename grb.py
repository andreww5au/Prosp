#""" Gamma ray burst - monitor for GRB email"""

#!/usr/bin/python -i
backgrounds=[]
try:
  import readline
except ImportError:
  ewrite("Module readline not available.")
else:
  import rlcompleter
  readline.parse_and_bind("tab: complete")

import sys
import time       #for the 'sleep' function
import types
import threading
import improc
from improc import reduce
import planet
from planet import *
import teljoy
from teljoy import *
from snlists import *
import weather
import pipeline
import snsearch
import scheduler
#import grb
import chiller
import focuser
import focus

import utils
import poplib,getpass
import threading
import objects
import MySQLdb
import safecursor

DictCursor=safecursor.SafeCursor

#Create a new database connection to use in the background email-monitoring thread
b_db=MySQLdb.Connection(host='mysql', user='honcho', passwd='',
                        db='teljoy', cursorclass=DictCursor)
grb_curs=b_db.cursor()


# Process incoming GRB emails and place the results into the MySQLdb
# Written by Ralph Martin
def self():
  flag=0
  DT=''
  obj=''
  RA=''
  Dec=''
  name=''
  error=0
  errorbox=''

def emailstart():
# Check to see in the email thread is already running
  checkthreads=threading.enumerate()
  if string.find (`checkthreads`,'monitoring email') >-1: # email thread is already running
    print 'Email thread is already running.'
  else:
#   Start monitoring for a grb email
    emailThread=threading.Thread(target=email, name='monitoring email')
    emailThread.setDaemon(1)
    emailThread.start()

def email():
# Monitor for a GRB email.
# Once called will loop forever.
# This program Should run in the background.
  while 1:     #log in loop
#   connect to the email server
    try:
#      M=poplib.POP3("galaxy.calm.wa.gov.au")
       M=poplib.POP3("webmail.calm.wa.gov.au")
#      M=poplib.POP3("mail.iinet.net.au")
    except:
       print "Error establishing a link to the email server"
       time.sleep(7)
       continue
    try:
       M.user("perthobs")
#      M.user("ralphm")
#      M.pass_(getpass.getpass("Password for CALM email server:"))
       M.pass_("6asteroid")
#      M.pass_("password1")
#      M.pass_("stargaze")
    except poplib.error_proto, detail:
       print "Error logging into the CALM email server", detail
       try:
         M.quit()
       except:
         pass
       continue
         
#   Read email loop
    try:
       checkgrb(self, M)
       time.sleep(8)
       M.quit()
    except:
       print 'Error reading mail'
       try:
         M.quit() #log out
       except:
         pass

def checkgrb(self, M):
  fsize=360.0 #field of view
  settile='true'
  stat=M.stat()
  try:
    for n in range(stat[0]):
       msgnum=n+1
#      print msgnum
       try:
         response, lineslist, bytes = M.top(msgnum,0)
       except poplib.error_proto, detail:
          print 'exception reading message'
          M.quit() #This line causes an exception
     
       lines=`lineslist`
       lines=string.upper(lines)   # convert string to upper case
       if string.find(lines,'GCN') >-1 or string.find(lines,'RALPHM') >-1:
#        print 'found possible grb email'
#        Read this email            
         response,messagelist,byte=M.retr(msgnum)
         message=`messagelist`
         message=string.upper(message)

         if string.find (message,'NOTICE_DATE:') >-1:
#           format  NOTICE_DATE:  Sun 28 Apr 96 13:12:38 UT
            lowpos = string.find (message,'NOTICE_DATE:')
            startpos = string.find(message,':',lowpos)
            endpos=string.find(message,'UT',startpos)
            self.DT = message[startpos+1:endpos+2]
            print self.DT
         else:
            continue # not GRB email

         if string.find (message,'SWIFT-BAT GRB POSITION') > -1 or string.find(message,'SWIFT-BAT GRB NACK-POSITION') >-1
#           format  NOTICE_TYPE:   Swift-BAT GRB Postion
            print 'Found Swift position notice'
         else:
            continue # not GRB email

         if string.find (message,'TRIGGER_NUM:')  >-1:
#           format  TRIGGER_NUM:   5450
            print 'Found trigger number'
            lowpos=string.find(message,'TRIGGER_NUM:')
            endpos=string.find(message,",",lowpos)
            self.name = message [lowpos+12:endpos-1]
            self.name = string.strip (self.name)
            self.obj = self.name   # object = name
            print self.obj
         else:
            continue # not GRB email

#        Search for an RA
         if string.find (message,'GRB_RA:') >-1:
            lowpos = string.find (message,'GRB_RA:')
            extRA(self,message,lowpos)
         else:
            continue # not GRB email

#        Search for a Dec
         if string.find (message,'GRB_DEC:') >-1:
            lowpos = string.find (message,'GRB_DEC:')
            extDec(self,message,lowpos)
         else:
            continue # not GRB email

    
         if string.find (message,'GRB_ERROR:') >-1:
            print 'Found error_box (1)'
            lowpos=string.find (message,'GRB_ERROR:')
            endpos=string.find(message,'[',lowpos)
            ebString = message[lowpos+10:endpos]
            ebString = string.strip (ebString)
            errorbox=string.atof(ebString)
            print ebstring
         elif (string.find (message,'WXM_MAX_SIZE:') >-1 or 
               string.find (message,'SXC_MAX_SIZE:') >-1):
            print 'Found error box (2)'
            lowpos=string.find (message,'_MAX_SIZE:')
            endpos=string.find(message,'[',lowpos)
            ebString = message[lowpos+10:endpos]
            ebString = string.strip (ebString)
            errorbox=string.atof(ebString)
         elif string.find (message,'GRB_RXTE_SIZE:') >-1: 
            print 'Found error box (3)'
            lowpos=string.find (message,'XTE_ERROR:')
            endpos=string.find(message,'[',lowpos)
            ebString = message[lowpos+10:endpos]
            ebString = string.strip (ebString)
            errorbox=string.atof(ebString)
         elif string.find (message,'TRANS_ERROR:') >-1: 
            print 'Found error box (4)'
            lowpos=string.find (message,'ANS_ERROR:')
            endpos=string.find(message,'[',lowpos)
            ebString = message[lowpos+10:endpos]
            ebString = string.strip (ebString)
            errorbox=string.atof(ebString)
         elif string.find (message,'HUNT_ERR:') >-1: 
            print 'Found error box (5)'
            lowpos=string.find (message,'HUNT_ERR:')
            endpos=string.find(message,'[',lowpos)
            ebString = message[lowpos+9:endpos]
            ebString = string.strip (ebString)
            errorbox=string.atof(ebString)
         else:
            continue # not GRB email
         self.errorbox=ebString
#        calculate errorbox size in arcminutes
         if string.find (message,'DEG',endpos,endpos+20) >-1:  # errorbox is in degrees
            errorbox=errorbox*60.0
         elif string.find (message,'ARCMIN',endpos,endpos+20): # errorbox is in arcmin
            print 'arcmin'
            errorbox=errorbox
         elif string.find (message,'ARCSEC',endpos,endpos+20): # errorbox is in arcsec
            errorbox=errorbox/60.0
         else:
            print 'couldnt read units'
            errorbox=fsize*3.0                      # set size to turn on tiling
         if string.find (message,'RADIUS',endpos,endpos+30):
            errorbox=errorbox*2.0
         if errorbox >= fsize*1.2:
            settile='true'
            print 'Tiling is on.'
         else:
            settile='false'
            print 'Tiling is off.'

#        This is a valid email update the data base
         try:
            print 'saving to data base'
            grbDB(self)
            print 'signal observing interupt'
            utils.grbRequest(flag='true', tile=settile)
            f=open('grblog','a') # append the information to log
            print 'Writing log file'
            f.write ('\n')
            f.write (self.DT+'\n')
            f.write (self.obj+'\n')
            f.write (self.RA+'\n')
            f.write (self.Dec+'\n')
            f.write (self.errorbox+'\n')
            f.close()
            M.dele(msgnum)
            print 'found email'
#           Information has been archived so delete the message
         except: #couldn't archive the information
            M.quit()

  except:
    M.quit() #This line causes an exception that is trapped in email().
     
def grbDB(self):
#  Put this information into the data base.
   try:
     print self.obj
     newob=objects.Object(self.obj, curs=grb_curs)
     print self.errorbox
#    if newob.ObjRA:
#      print "GRB already in data base - updating."
#    else:
     newob.ObjID=self.obj
     newob.name = self.name
     newob.ObjRA = self.RA
     newob.ObjDec = self.Dec
     newob.ObjEpoch=2000.0
     newob.filtname='I'
     newob.filtnames='I'
     newob.exptime=90
     newob.exptimes=90
     newob.sublist=[('I',90.0)]
     newob.XYpos=(0,0)
     newob.type='STORE'
     newob.period=0.0001
     newob.comment=''
     newob.LastObs=0.0
     newob.errors=''

#  force the database to accept this object
#  as more accurate information vcomes in the data base is updated
     try:
       newob.save(ask=0,force=1, curs=grb_curs)
     except:
       print "object not saved in data base."
       sys.excepthook(*sys.exc_info())
       M.quit()
   except:
       M.quit()
   return ()

def extRA(self, message='', lowpos=0):
#  format  GRB_RA:        303.96d {+20h 15m 51s}  (J2000),
   startpos=string.find(message,'{',lowpos)
   endpos=string.find(message,'}',startpos)
   self.RA = message [startpos+1:endpos]
   self.RA=string.replace(self.RA,'H ',':')
   self.RA=string.replace(self.RA,'M ',':')
   self.RA=string.replace(self.RA,'S','  ') #wants double space
   self.RA = string.strip (self.RA)
   print self.RA

def extDec(self, message='', lowpos=0):
#  format  GRB_DEC:       +36.96d {+36d 57' 39"}  (J2000),
   startpos=string.find(message,'{',lowpos)
   endpos=string.find(message,'}',startpos)
   self.Dec = message[startpos+1:endpos]
   self.Dec=string.replace(self.Dec,'D ',':')
   self.Dec=string.replace(self.Dec,"\\' ",":")
   self.Dec=string.replace(self.Dec,'"','  ')
   self.Dec=string.strip (self.Dec)
   print self.Dec

