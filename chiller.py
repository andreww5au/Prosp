
import serial
import urllib2
import os
import time
import sys
import threading

import globals
from BeautifulSoup import BeautifulSoup

headroom = 50.0    #Try and maintain chiller setpoint temp this far above CCD settemp
dewheadroom = 2.0  #Make sure to keep chiller setpoint this far above dewpoint

os.environ["http_proxy"]="http://proxy.calm.wa.gov.au:8080"

ser = serial.Serial('/dev/ttyS2', 9600, timeout=1)

logfile = open('/data/templog','a')

ReadSetpoint = [0x01,0x03,0x00,0x7F,0x00,0x01]
ReadTemp = [0x01,0x03,0x00,0x1C,0x00,0x01]

EnterProgram1 = [0x01,0x06,0x03,0x00,0x00,0x05]      #Flag next message as secured - reply should be this message
EnterProgram2 = [0x01,0x06,0x15,0x00,0x00,0x00]      #Enter programming mode - reply should be this message
WriteSetpoint = [0x01,0x06,0x00,0x7F,0x00,0x00]      #Last two bytes are setpoint*10, high then low
ExitProgram1 = [0x01,0x06,0x03,0x00,0x00,0x06]       #Flag next message as secured - reply should be this message
ExitProgram2 = [0x01,0x06,0x16,0x00,0x00,0x00]       #Exit programming mode - reply should be this message

threadlist = []      #A list of all thread objects from this module that are currently running


def updateDewpoint():
  """Download the current ambient temperature and dewpoint from the BOM website.
  """
  global airtemp, dewpoint, lastdewchecktime, goodBOM
  try:
    f=urllib2.urlopen('http://www.bom.gov.au/products/IDW60034.shtml')
    html=f.read()
    f.close()
    soup=BeautifulSoup()
    soup.feed(html)
    rl = soup.fetch('table', attrs={'border': '1'})
    if rl:
      rl = rl[0].fetch('tr')
  
    for r in rl:
      dl = r.fetch('td')
      if dl:
        if dl[0].first('a').renderContents() == 'BICKLEY':
          airtemp = float(dl[2].renderContents())
          dewpoint = float(dl[3].renderContents())  
          lastdewchecktime = time.time()
          goodBOM = 1
  except:
    airtemp = 20.0
    dewpoint = 20.0
    goodBOM = 0
    print 'Error grabbing temp,dewpoint'
    sys.excepthook(*sys.exc_info())


def _background():
  """Called every 6 seconds from Prosp. Use to check dewpoint every hour to make sure the chiller is
     maintaining a temp safely above the dewpoint.
  """
  global lastchillerchecktime, watertemp, setpoint

  for t in threadlist[:]:
    if not t.isAlive():
      threadlist.remove(t)      #Remove completed download threads from the threadlist, leaving only active ones

  #Download new temp/dewpoint every hour if there are no threads already, try again after 90 min if 1 blocked thread
  if ( (((time.time() - lastdewchecktime) > 3600) and (len(threadlist)==0)) or
       (((time.time() - lastdewchecktime) > 5400) and (len(threadlist)==1)) ):    
    t=threading.Thread(target=updateDewpoint,
                       name='BOM Bickley weather page download')
    t.setDaemon(1)
    t.start()
    threadlist.append(t)

  if (time.time() - lastchillerchecktime) > 300:         #Download new watertemp, setpoint every 5 min
    w,s = getTemp(), getSetpoint()
    if (w > -90.0) and (s > -90.0):
      lastchillerchecktime = time.time()
    else:
      globals.ewrite('Unable to get watertemp, settemp from chiller unit')
      lastchillerchecktime = time.time() - 120       #If there was an error, try again in 2 minutes
    logfile.write("%12.2f %4.1f %4.1f %4.1f %4.1f \n" % (time.time(), airtemp, watertemp, setpoint, dewpoint) )

    if goodBOM:
      try:
        desired = status.settemp + headroom      #Temperature to try and keep chiller setpoint near
        if desired > airtemp:
          desired = airtemp
        if desired < (dewpoint + dewheadroom):
          desired = dewpoint + dewheadroom

        if (abs(desired-setpoint) > 5.0) or (setpoint < (dewpoint + dewheadroom)):
          newSetpoint(desired)
          print "Changing chiller setpoint to ",round(desired,1)
      except:
        pass       #Not running inside Prosp, no CCD setpoint info


def crc(message=[]):
  """Calculates the CRC bytes required for message (a list of bytes) and returns the message with CRC appended.
  """
  if not message:
    return 0,0
  crc = 0xFFFF
  
  for byte in message:
    crc = crc ^ byte
    for bit in range(8):
      b = crc & 0x0001
      crc = (crc >> 1) & 0x7FFF
      if b:
        crc = crc ^ 0xA001
  return message + [(crc & 0x00FF), ((crc >> 8) & 0x00FF) ]


def send(message):
  """Calculate the CRC and send it and the message (a list of bytes) to the chiller
  """
  message = crc(message)
  ser.write(''.join(map(chr, message)))


def getTemp():
  """Read the current water outlet temperature from the chiller unit.
  """
  global watertemp
  send(ReadTemp)
  reply = map(ord, ser.read(7))
  temp = -99.9
  if len(reply)>4:
    if crc(reply[:-2])[-2:] == reply[-2:]:
      temp = (reply[3]*256 + reply[4]) / 10.0
      watertemp = temp
  else:
    print "No data ",reply
  return temp
    

def tobytes(temp=20.0):
  """Convert a temperature from degrees C to a list of two bytes (high,low)
  """
  t = int(temp*10)
  return list(divmod(t,256))
  


def getSetpoint():
  """Read the current setpoint temperature from the chiller unit.
  """
  global setpoint
  send(ReadSetpoint)
  reply = map(ord, ser.read(7))
  temp = -99.9
  if len(reply)>4:
    if crc(reply[:-2])[-2:] == reply[-2:]:
      temp = (reply[3]*256 + reply[4]) / 10.0
      setpoint = temp
  else:
    print "No data ",reply
  return temp


def newSetpoint(temp=20.0):
  """Changes the chiller's current setpoint temperature.
  """
  global setpoint,lastchillerchecktime
  try:
    temp=float(temp)
  except:
    print "Aborting - Invalid value: ",temp
    return

  if temp <= (dewpoint + 2):
    print "Aborting - Too low a temperature, current dewpoint is ",round(dewpoint,2)
    return
  elif temp >= 30:
   print "Aborting - Too high a temperature, max of 30C"

  send(EnterProgram1)
  reply = map(ord, ser.read(8))
  if reply[:-2] <> EnterProgram1:
    print "Aborting - Bad response to EnterProgram1 ",reply
    return

  send(EnterProgram2)
  reply = map(ord, ser.read(8))
  if reply[:-2] <> EnterProgram2:
    print "Aborting - Bad response to EnterProgram2 ",reply
    return

  WriteSetpoint[4:] = tobytes(temp)      #Note this changes global defined at top of file
  send(WriteSetpoint)
  reply = map(ord, ser.read(8))
  if reply[:-2] <> WriteSetpoint:
    print "Bad response to WriteSetpoint ",reply
    print "Trying to exit program mode"
  else:
    setpoint = temp
    lastchillerchecktime = time.time()-240    #Schedule a chiller update 1 minute from now

  send(ExitProgram1)
  reply = map(ord, ser.read(8))
  if reply[:-2] <> ExitProgram1:
    print "Bad response to ExitProgram1 ",reply

  send(ExitProgram2)
  reply = map(ord, ser.read(8))
  if reply[:-2] <> ExitProgram2:
    print "Bad response to ExitProgram2 ",reply

  



airtemp = 20.0
dewpoint = 20.0
lastdewchecktime = time.time() - 3600
goodBOM = 0
lastchillerchecktime = 0
watertemp = 20.0
setpoint = 20.0

#_background()
