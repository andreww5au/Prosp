
import serial
import urllib2
import os
import time
import sys

import globals
from BeautifulSoup import BeautifulSoup

os.environ["http_proxy"]="http://proxy.calm.wa.gov.au:8080"

ser = serial.Serial('/dev/ttyS2', 9600, timeout=1)

ReadSetpoint = [0x01,0x03,0x00,0x7F,0x00,0x01]
ReadTemp = [0x01,0x03,0x00,0x1C,0x00,0x01]

EnterProgram1 = [0x01,0x06,0x03,0x00,0x00,0x05]      #Flag next message as secured - reply should be this message
EnterProgram2 = [0x01,0x06,0x15,0x00,0x00,0x00]      #Enter programming mode - reply should be this message
WriteSetpoint = [0x01,0x06,0x00,0x7F,0x00,0x00]      #Last two bytes are setpoint*10, high then low
ExitProgram1 = [0x01,0x06,0x03,0x00,0x00,0x06]       #Flag next message as secured - reply should be this message
ExitProgram2 = [0x01,0x06,0x16,0x00,0x00,0x00]       #Exit programming mode - reply should be this message


def getDewpoint():
  """Download the current ambient temperature and dewpoint from the BOM website.
  """
  temp = 0.0
  dewpoint = 0.0
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
          temp = float(dl[2].renderContents())
          dewpoint = float(dl[3].renderContents())  
  except:
    print 'Error grabbing temp,dewpoint'
    sys.excepthook(*sys.exc_info())

  return temp,dewpoint


def _background():
  """Called every 6 seconds from Prosp. Use to check dewpoint every hour to make sure the chiller is
     maintaining a temp safely above the dewpoint.
  """
  global lastdewchecktime, lastchillerchecktime, airtemp, dewpoint, watertemp, setpoint

  if (time.time() - lastdewchecktime) > 3600:         #Download new temp/dewpoint every hour
    t,d = getDewpoint()
    if t or d:
      airtemp = t
      dewpoint = d
      lastdewchecktime = time.time()
    else:
      globals.ewrite('Unable to get temp,dewpoint from BOM website')
      lastdewchecktime = time.time() - 1800          #If there was an error, try again in 30 minutes

  if (time.time() - lastchillerchecktime) > 600:         #Download new watertemp, setpoint every hour
    w,s = getTemp(), getSetpoint()
    if (w > -90.0) and (s > -90.0):
      watertemp = w
      setpoint = s
      lastchillerchecktime = time.time()
    else:
      globals.ewrite('Unable to get watertemp, settemp from chiller unit')
      lastchillerchecktime = time.time() - 300       #If there was an error, try again in 5 minutes


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
  send(ReadTemp)
  reply = map(ord, ser.read(7))
  temp = -99.9
  if len(reply)>4:
    if crc(reply[:-2])[-2:] == reply[-2:]:
      temp = (reply[3]*256 + reply[4]) / 10.0
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
  send(ReadSetpoint)
  reply = map(ord, ser.read(7))
  temp = -99.9
  if len(reply)>4:
    if crc(reply[:-2])[-2:] == reply[-2:]:
      temp = (reply[3]*256 + reply[4]) / 10.0
  else:
    print "No data ",reply
  return temp


def newSetpoint(temp=20.0):
  """Changes the chiller's current setpoint temperature.
  """
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

  send(ExitProgram1)
  reply = map(ord, ser.read(8))
  if reply[:-2] <> ExitProgram1:
    print "Bad response to ExitProgram1 ",reply

  send(ExitProgram2)
  reply = map(ord, ser.read(8))
  if reply[:-2] <> ExitProgram2:
    print "Bad response to ExitProgram2 ",reply
  



airtemp = 99.9
dewpoint = 99.9
lastdewchecktime = 0
lastchillerchecktime = 0
watertemp = -99.9
setpoint = -99.9

#_background()        #This will block for ~10 seconds every time it downloads the BOM web page
