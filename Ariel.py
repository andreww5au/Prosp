
#Python interface library to 'Ariel', the control software for CCD cameras.
#Ariel was developed at Ohio State University (OSU), and this interface
#library was written by Andrew Williams at Perth Observatory.
#
#See the file 'prosp.py' for a minimal 'wrapper' using this library
#to provide a user interface similar to the OSU 'Prospero' program

import os    #operating system calls
import select  #non-blocking file-IO support
import string  #string handlign functions
import glob    #Filename expansion
import cPickle  #Object saves to file
import fcntl   #File locking functions
from globals import *

class GuideZero:
  def __init__(self,x=0,y=0):
    self.gxoff=x
    self.gyoff=y

gzero=GuideZero(0,0)

class ArielStatus:
  "Define a status object, plus methods to initialise and display it"
  def empty(self):
    "Called by __init__ or manually to clear status"
    self.temp=0
    self.settemp=0
    self.shutter=0
    self.exptime=0
    self.filter=0
    self.xguider=0
    self.yguider=0
    self.mirror='IN'
    self.xbin=0
    self.ybin=0
    self.roi=(0,0,0,0)  #Stored as a 'tuple' - 4 dimensional vector
    self.xover=0
    self.yover=0
    self.imgtype=''
    self.object=''
    self.nextfile=''
    self.lastfile=''
    self.path=''
    self.cool=0
    self.tset=0
    self.tmin=0
    self.tmax=0
    self.filectr=0
    self.inst=''
    self.ic=0
    self.tc=0
    self.ie=0
  def display(self):
    "Tells the status object to display itself to the screen"
    print 'temp=',self.temp
    print 'settemp=',self.settemp
    print 'shutter=',self.shutter
    print 'exptime=',self.exptime
    print 'filter=',self.filter,' = ',filtname(self.filter)
    print 'guider=',self.xguider,',',self.yguider
    print 'mirror=',self.mirror
    print 'xbin,ybin=',self.xbin,',',self.ybin
    print 'roi=',self.roi
    print 'xover,yover=',self.xover,',',self.yover
    print 'imgtype=','"'+self.imgtype+'"'
    print 'object=','"'+self.object+'"'
    print 'path, nextfile=','"'+self.path+'", "'+self.nextfile+'"'
    print 'last file=','"'+self.lastfile+'"'
    print 'cool, tset, tmin, tmax=',self.cool,',',self.tset,',',self.tmin,',',self.tmax
    print 'filectr=',self.filectr
    print 'instrument=','"'+self.inst+'"'
    print 'ic,tc,ie=',self.ic,',',self.tc,',',self.ie
  def __init__(self):
    "Called automatically when instance is created"
    self.empty()
  def __call__(self):
    "Called when status object is called like a function"
    self.updated()
    self.display()
  def updated(self):
    "Called when status object changes, override to do something with the data"
    #In an overriding function, this could output to SQL or web page
    if not connected:
      return 0
    f=open('/tmp/arstatus','w')
    cPickle.dump(self,f)
    f.close()


class CommandResult:
  "Results from an ariel command received down the pipe"
  def __init__(self):
    "called automatically when an instance is created"
    self.STATUS=0   #true if the word 'STATUS' was received in any result line
    self.DONE=0   #true if the word 'DONE' was received in any result line
    self.ERROR=0  #true if the word 'ERROR' was received in any result line
    self.StatusStr=''   #Sum of all 'STATUS' lines received
    self.DoneStr=''     #Sum of all 'DONE' lines received
    self.ErrorStr=''    #Sum of all 'ERROR' lines received
  def display(self):
    "Call to display command results"
    if self.DONE:
      swrite(self.DoneStr)
    if self.STATUS:
      swrite(self.StatusStr)
    if self.ERROR:
      ewrite(self.ErrorStr)
  

def send(comd):
  "Add header and send command down the pipe to Ariel"
  outstr='PR>AR '+comd
  os.write(inf,outstr)   #use os.write to avoid trailing LF or space


def receive(timeout=1.0):
  "Wait at most (timeout) seconds, default 1, return string from ariel"
  r,w,e=select.select([outf],[],[],timeout)  #wait until any data to read
  str=''
  while r:   #r is true (non-empty list) if the pipe is ready to be read
    str=str+os.read(outf,1)
    r,w,e=select.select([outf],[],[],0.1)  #loop until no more data left in pipe
  return str


def command(cmd,waitdone=0):
  "Send cmd to ariel, return after one line of response unless 'waitdone' true"
  res=CommandResult()   #Create an empty instance of a CommandResult object
  if not connected:
    ewrite("Ariel not connected")
    return res
  send(cmd)             #send command to Ariel
  if waitdone:
    while (not res.DONE) and (not res.ERROR):  #keep reading lines till DONE
      str=receive()    #Get some text back
      strlist=string.split(str,'AR>PR ')  #split response into logical lines
      for line in strlist:
        if line:
          ParseLine(line,res)  #parse each non-empty line
  else:
    str=receive()                   #get some text back
    strlist=string.split(str,'AR>PR ')  #split response into logical lines
    for line in strlist:
      if line:
        ParseLine(line,res)    #parse each non-empty line
  return res         #return the CommandResult object
 
 
def ParseLine(line,res):
  "Parse a line from Ariel - split into components, update status and result"

  np=string.find(line,'\0')   #Are there any null characters in the string?
  if (np > -1):
    line=line[:np]     #Truncate string to eliminate trailing nulls
  linelist=string.split(line)  #split string into a list of words

  #for example: linelist=["STATUS:","exposure","started","SHUTTER=1"]

  #Join together all words at the start of the string
  #until we come to a 'name=value' pair
  while (len(linelist) > 1) and (string.find(linelist[1],'=') == -1):
    linelist[0]=linelist[0]+' '+linelist[1]
    del linelist[1]

  #for example: linelist=["STATUS: exposure started","SHUTTER=1"]

  #test the start of the string for 'STATUS' and add to command result
  if string.find(linelist[0],'STATUS') > -1:
    res.STATUS=1
    if len(linelist[0]) > 8:
      swrite(linelist[0])     #Only print the status string if it's not empty
    res.StatusStr=res.StatusStr+linelist[0]+'\n'

  #test the start of the string for 'DONE' and add to command result
  if string.find(linelist[0],'DONE') > -1:
    res.DONE=1
    if len(linelist[0]) > 6:
      swrite(linelist[0])    #Only print the 'DONE' string it it's not empty
    res.DoneStr=res.DoneStr+linelist[0]+'\n'

  #test the start of the string for 'ERROR' and add to command result
  if string.find(linelist[0],'ERROR') > -1:
    res.ERROR=1
    if len(linelist[0]) > 7:
      ewrite(linelist[0])    #Only print the error string it it's not empty
    res.ErrorStr=res.ErrorStr+linelist[0]+'\n'

  #Test cool and tset results here as they aren't in the form 'name=value'
  if linelist.count('+cool'):
    status.cool=1
  if linelist.count('-cool'):
    status.cool=0
  if linelist.count('+tset'):
    status.tset=1
  if linelist.count('-tset'):
    status.tset=0
  if linelist.count('+tmin'):
    status.tmin=1
  if linelist.count('-tmin'):
    status.tmin=0
  if linelist.count('+tmax'):
    status.tmax=1
  if linelist.count('-tmax'):
    status.tmax=0

  #Join together pairs where there is a leading '(' until we find a 
  #trailing ')', or the end of the string. Used because the 'object' keyword
  #has a value that can contain spaces, eg 'object=(this is an object)'
  i=0
  while i < len(linelist)-1:
    i=i+1
    while (string.find(linelist[i],'(') > -1) and \
          (string.find(linelist[i],')')==-1) and  \
          i < len(linelist)-1:
      linelist[i]=linelist[i]+' '+linelist[i+1]
      del linelist[i+1]   #each del removes item i+1 so the next time around
                          #linelist[i+1] refers to a new item

  for pair in linelist:        #Loop over items in linelist
    pos=string.find(pair,'=')
    if pos>-1:                 #if there's an '=' char, split into id and value
      id=pair[:pos]
      val=pair[pos+1:]
      ParsePair(id,val)        #Parse id=value pairs one by one

  status.updated()    #Tell status object that it's been altered


def ParsePair(id,val):
  "Parse id=value pairs in ariel output, updating status object for each"

  if id=='temp':
    status.temp=eval(val)     #'eval' is a flexible number->string converter
  if id=='settemp':
    status.settemp=eval(val)
  elif id=='SHUTTER' or id=='shut':
    status.shutter=eval(val)
  elif id=='EXPTIME' or id=='exp':
    status.exptime=eval(val)
  elif id=='filter' or id=='FILTER':
    status.filter=eval(val)
  elif id=='xguider':
    status.xguider=eval(val)-gzero.gxoff
  elif id=='mirror':
    status.mirror=val
  elif id=='yguider':
    status.yguider=eval(val)-gzero.gyoff
  elif id=='xbin':
    status.xbin=eval(val)
  elif id=='ybin':
    status.ybin=eval(val)
  elif id=='roi':
    status.roi=eval(val)   #Store as a 4-dimensional vector - a 'tuple'
  elif id=='xover':
    status.xover=eval(val)
  elif id=='yover':
    status.yover=eval(val)
  elif id=='imtype' or id=='IMGTYPE':
    status.imgtype=val
  elif id=='OBJECT' or id=='obj':
    status.object=val
  elif id=='file' or id=='filename' or id=='nextfile':
    status.nextfile=val
  elif id=='LASTFILE':
    status.lastfile=val
  elif id=='path':
    status.path=val
  elif id=='filectr':
    status.filectr=eval(val)
  elif id=='inst':
    status.inst=val
  elif id=='ic':
    status.ic=(val=='ENABLED')
  elif id=='tc':
    status.tc=(val=='ENABLED')
  elif id=='ie':
    status.ie=(val=='ENABLED')


def update():
  "Attach to Ariel and grab current status information"

  tmpstr=status.lastfile   #save last filename becuase you can't read it back
  status.empty()
  command('status',0)
  command('istatus',0)
  command('tcstatus',0)
  command('config',0)
  status.lastfile=tmpstr  #restore last filename
  status.updated()


def init():     #Call this after creating a global status object
  "Initialise Ariel connection"
  global inf,outf,connected
  swrite("Python Ariel interface initialising:")

  #Open input and output pipes
  
  try:
    outf=os.open('/tmp/ariel.out',os.O_RDONLY | os.O_NONBLOCK)
    fcntl.flock(outf,fcntl.LOCK_EX+fcntl.LOCK_NB)  #Try a non-blocking lock
  except:
    try:
      os.close(outf)
    except:
      pass
    outf=os.open('/dev/null',os.O_RDONLY | os.O_NONBLOCK)
    inf=os.open('/dev/null',os.O_WRONLY | os.O_APPEND | os.O_SYNC)
    raise ArielError("Ariel in use or not reachable")
    connected=0
  else:
    inf=os.open('/tmp/ariel.in',os.O_WRONLY | os.O_APPEND | os.O_SYNC)
    connected=1

  update()
  status.display()


class ArielError:
  def __init__(self,value):
    self.value=value
  def __str__(self):
    return `self.value`

connected=0
