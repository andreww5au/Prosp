#!/usr/bin/python

#Written by Andrew Williams, Perth Observatory, 1999

#List of files that we've tried to transfer - append to them if we try again.
appendlist=[]

#Define two custom exceptions - time out during transfer, and permission error
#when we try to send the file (the ftp server has refused the operation)
TimeOut="TimeOut"
PermError="PermissionError"


import ftplib              #FTP library
FTP=ftplib.FTP     #Import the FTP object class
import time                #Time handler functions
import __builtin__         #So we can override the built-in file type
import signal              #Signal handling
import os                  #Operating system support
import os.path             #Pathname and directory handling functions
import getpass             #Non-echoing password input

def open(filename, mode="rb"):
  "Override the built in open command to return my file object"
  return mfile(filename,mode)

class mfile:
  "Copy of the standard file object class with hooks in read and write methods"

  myfileobj = None

  def __init__(self, filename=None, mode=None, fileobj=None):
    if fileobj is None:
      fileobj = self.myfileobj = __builtin__.open(filename, mode or 'rb')
    if filename is None:
      if hasattr(fileobj, 'name'): filename = fileobj.name
      else: filename = ''
    if mode is None:
      if hasattr(fileobj, 'mode'): mode = fileobj.mode
      else: mode = 'rb'

    self.filename = filename
    self.fileobj = fileobj

  def write(self,data):
    if self.fileobj is None:
      raise ValueError, "write() on closed mfile object"
    self.fileobj.write(data)
    self.writecalled()    #Call write hook function when write method called

  def read(self, size=None):
    if self.fileobj is None:
      raise ValueError, "read() on closed mfile object"
    buf = self.fileobj.read(size)
    self.readcalled()     #Call read hook function when read method called
    return buf

  def close(self):
    self.fileobj=None
    if self.myfileobj:
      self.myfileobj.close()
      self.myfileobj=None

  def flush(self):
    self.fileobj.flush()

  def seek(self,offset,whence=0):
    self.fileobj.seek(offset,whence)

  def tell(self):
    return self.fileobj.tell()

  def isatty(self):
    return 0

  def readline(self):
    raise IOError, 'Only binary access, no readline...'

  def readlines(self):
    raise IOError, 'Only binary access, no readlines...'

  def writelines(self):
    raise IOError, 'Only binary access, no writelines...'

  def writecalled(self):
    "Called when a block is written to the file"
    signal.alarm(300)     #Set up an alarm signal in 300 seconds 
                          #Any pending signal is postponed.

  def readcalled(self):
    "Called when a block is read from the file"
    signal.alarm(300)     #Set up an alarm signal in 300 seconds
                          #Any pending signal is postponed

def sendfile(filename,host,username,password,directory):
  "Send a file to the remote site"
  global appendlist
  print 'sending file '+filename+' via ftp'

  signal.alarm(120)   #allow two minutes to open connection
  print "opening connection"
  sftp=FTP(host,username,password)  #open connection and create
                                    #ftp object
  signal.alarm(60)   #Allow one minute for the CWD
  print "changing directory"
  sftp.cwd(directory)

  #Try to delete the existing remote file. If there is an ftp permission
  #error, ignore it, because it probably means the rmeote file doesn't exist
  try:
    sftp.delete(filename)
  except ftplib.error_perm:
    pass

  #We are transferring this file, add it to the append list so that we can
  #resume the transfer after any interruption
  if filename not in appendlist:
    appendlist=appendlist+[filename,]

  #Send image file in binary with 8kb blocksize
  #If the transfer 'locks up', the alarm signal will break out when the timer
  #runs out - ie after 60 seconds from the start, or more than 300 seconds 
  #between the 8kb file read calls
  signal.alarm(60)   #Allow another minute for handshaking
  print "starting file transfer"
  f=open(filename,'r')
  sftp.storbinary('STOR '+filename,f,8192)
  f.close()    #Close the input file

  signal.alarm(120)   #Allow two minutes to close the connection
  print "closing connection"
  sftp.quit()
  signal.alarm(0)     #Cancel all alarms

  appendlist.remove(filename)  #We have successfully transferred this file, 
                               #so don't append to it if the local copy changes
 


def appendfile(filename,host,username,password,directory):
  "Continue to send a file to the remote site"
  print 'appending file '+filename+' via ftp'

  signal.alarm(120)   #allow two minutes to open connection
  print "opening connection"
  sftp=FTP(host,username,password)  #open connection and create
                                    #ftp object
  signal.alarm(120)   #Allow two minutes for the CWD and size check
  print "changing directory"
  sftp.cwd(directory)

  sftp.voidcmd("type I")   #Set the type to I to get the raw file size

  #Try getting the size of the remote file. If we get an ftp permission error
  #error, ignore it and set the remote size to zero because the file doesn't 
  #exist
  try:
    rsize=sftp.size(file)
  except ftplib.error_perm:
    rsize=0
  print "Remote file size is:",rsize

  #Send file in binary with 8kb blocksize
  #If the alarm timer expires, it will break out to the signal handler
  signal.alarm(60)   #Allow another minute for handshaking
  print "starting file transfer"
  f=open(filename,'r')
  f.seek(rsize)
  sftp.storbinary('APPE '+filename,f,8192)
  f.close()    #Close the input file

  signal.alarm(120)   #Allow two minutes to close the connection
  print "closing connection"
  sftp.quit()
  signal.alarm(0)     #Cancel all alarms

 
def alarmhandler(signum,frame):
  "Called when an alarm signal has been recieved"
  #If we get here, an alarm timer has run out, so something has 'locked up'
  print "Timeout while transferring file"
  raise TimeOut,"Timeout during file transfer"   #Raise a timeout exception




#Main Program:

def sendall(host='', username='',
            password='', directory=''):
  signal.signal(signal.SIGALRM, alarmhandler)  #Define the alarm signal handler

  if (not host):
    host=raw_input('Enter hostname: ')

  if (not username):
    username=raw_input('Enter username: ')

  if (not password):
    password=getpass.getpass('Password for '+username+'@'+host+': ')

  if (not directory):
    directory=raw_input('Enter dest. directory: ')

  while 1:   #Continue forever...
    try:
      print "Beginning Sync loop"
      signal.alarm(120)  #two minutes for main login and CWD
      ftp=FTP(host,username,password)  #open connection and create ftp object
      ftp.cwd(directory)

      #For each local file, check the size of the corresponding remote file
      for file in os.listdir(os.curdir):
        signal.alarm(60)   #one minute for each size check
        ftp.voidcmd("type I")
        try:
          rsize=ftp.size(file)
        except ftplib.error_perm:  #ftp error means remote file doesn't exist
          rsize=0

        try:
          if os.path.getsize(file) != rsize:   #If the file sizes don't match:
            if (file in appendlist) and (rsize > 0):
              appendfile(file,host,username,password,directory) 
            else:
              sendfile(file,host,username,password,directory) 
        except ftplib.error_perm:  #This time an ftp error means a real problem
          raise PermError,directory+"/"+file  #So raise a permission error

      print "Closing..."
      ftp.quit()
      return 

    except (TimeOut,)+ftplib.all_errors, EXarg:  #Handle timeouts and all ftp
                                               #protocol errors to catch
                                               #timouts and dropped connections
      signal.alarm(0)   #Cancel timeout
      print "Exception - arg=", EXarg
      print "waiting for 5 minutes"
      ftp.close()
      time.sleep(300)    #Wait for 5 minutes and start the loop again
 

if __name__ == '__main__':
  sendall()
