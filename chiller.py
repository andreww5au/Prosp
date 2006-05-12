
import serial
#import os
import time
#import sys

import globals
import weather

headroom = 43.0    #Try and maintain chiller setpoint temp this far above CCD settemp
dewheadroom = 5.0  #Make sure to keep chiller setpoint this far above dewpoint
errortemp = 12.0   #If we lose data from the weather station, use this as setpoint

ReadSetpoint = [0x01,0x03,0x00,0x7F,0x00,0x01]
ReadTemp = [0x01,0x03,0x00,0x1C,0x00,0x01]

EnterProgram1 = [0x01,0x06,0x03,0x00,0x00,0x05]      #Flag next message as secured - reply should be this message
EnterProgram2 = [0x01,0x06,0x15,0x00,0x00,0x00]      #Enter programming mode - reply should be this message
WriteSetpoint = [0x01,0x06,0x00,0x7F,0x00,0x00]      #Last two bytes are setpoint*10, high then low
ExitProgram1 = [0x01,0x06,0x03,0x00,0x00,0x06]       #Flag next message as secured - reply should be this message
ExitProgram2 = [0x01,0x06,0x16,0x00,0x00,0x00]       #Exit programming mode - reply should be this message



def _background():
  """Called every 6 seconds from Prosp. Use to check dewpoint every hour to make sure the chiller is
     maintaining a temp safely above the dewpoint.
  """

  if (time.time() - status.lastchillerchecktime) > 300:         #Download new watertemp, setpoint every 5 min
    w,s = getTemp(), getSetpoint()
    if (w > -90.0) and (s > -90.0):
      status.lastchillerchecktime = time.time()
    else:
      globals.ewrite('Unable to get watertemp, settemp from chiller unit')
      status.lastchillerchecktime = time.time() - 240       #If there was an error, try again in 1 minutes
    logfile.write("%s\t%4.1f\t%4.1f\t%4.1f\t%4.1f \n" % (time.asctime(), weather.status.temp, status.watertemp,
                                                     status.setpoint, weather.status.dewpoint) )
    logfile.flush()

    if (not weather.status.weathererror) and (weather.status.dewpoint is not None):
      try:
        desired = weather.status.dewpoint + dewheadroom      #Temperature to try and keep chiller setpoint near
        if desired < 2.0:
          desired = 2.0

        if (abs(desired-status.setpoint) >= 1.0):
          newSetpoint(desired)
          print "Changing chiller setpoint to ",round(desired,1)
      except:
        newSetpoint(errortemp)
        print "No dewpoint or air temp available, defaulting to %4.1f for chiller" % (errortemp,)


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
      status.watertemp = temp
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
      status.setpoint = temp
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

  if temp < (weather.status.dewpoint + dewheadroom):
    print "Aborting - %4.1f is too low a setpoint, current dewpoint is %4.1f" %(temp,weather.status.dewpoint)
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
    status.setpoint = temp
    status.lastchillerchecktime = time.time()-240    #Schedule a chiller update 1 minute from now

  send(ExitProgram1)
  reply = map(ord, ser.read(8))
  if reply[:-2] <> ExitProgram1:
    print "Bad response to ExitProgram1 ",reply

  send(ExitProgram2)
  reply = map(ord, ser.read(8))
  if reply[:-2] <> ExitProgram2:
    print "Bad response to ExitProgram2 ",reply


class _Chiller:
  """Chiller status object.
  """
  def __init__(self):
    self.setpoint = 25.0
    self.lastchillerchecktime = time.time() - 290
    self.watertemp = 20.0
    self.setpoint = 20.0
  def update(self):
    getTemp()
    getSetpoint()
  def display(self):
    return "Air:%4.1f  Water:%4.1f  Setpoint:%4.1f  Dewpoint:%4.1f" % (weather.status.temp, self.watertemp,
                                                                       self.setpoint, weather.status.dewpoint) 

def init():   #Initialise at runtime, including connection to chiller and downloading initial BOM data
  global status, ser, logfile  
  ser = serial.Serial('/dev/ttyS2', 9600, timeout=1)
  logfile = open('/data/templog','a')
  logfile.write("%s\t%s\t%s\t%s\t%s \n" % (time.asctime(),"Air","Water","Set","Dew") )

  status = _Chiller()
  _background()
