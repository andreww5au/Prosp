
import serial
import time

from globals import *

FILTERS = {1:195, 2:-205, 3:-605, 4:-1005, 5:-1405, 6:-1805, 7:-2205, 8:-2605}
MIRRORS = {'IN':2300, 'OUT':0}

LATENCY = 0.25   #seconds between optical coupler commands

START_FILTER = 6       # I
XGUIDER_CENTER = 1650
YGUIDER_CENTER = 1115
MIRROR_IN = 2300

def init():   #Initialise at runtime
  """Query optical coupler controller boards to see if they have already
     been initialised - if so, read current state. If they haven't, initialise
     the boards.

     Returns a tuple of (filter, x, y, mirror), where filter is 1-8, x and y
     are (0,0) for the centre of the field, and mirror is 'IN' or 'OUT'. If the
     boards couldn't be initialised, some of all of these will be None.
  """
  global ser, logfile  
  ser = serial.Serial('/dev/ttyS0', 9600, timeout=1.0, rtscts=1)
  filter = GetFilter()
  x,y = GetXYStage()
  mirror = GetMirror()
  if (filter is None) or (x is None) or (y is None) or (mirror is None):
    logger.info("Initialising optical coupler")
    error = InitializeBoards()
    if not error:
      HomeFilter()
      SelectFilter(START_FILTER)
      HomeXYStage()
      HomeMirror()
      MoveMirror(MIRRORS['IN'])
      filter = START_FILTER
      x,y = 0,0
      mirror = 'IN'
      logger.info("Optical coupler setup complete.")
    else:
      logger.error("Optical coupler serial interface not responding!")
  return filter, x, y, mirror


def SendCommand(s=''):
  """Send a command to the optical coupler.
  """
  ser.flushInput()
  ser.flushOutput()
  ser.write(s+'\r')
  logger.debug('[%s]' % s)


def GetResponse():
  """Reads from the serial port until either a '#' is received, or a timout occurs.
  """
  response = []
  tcount = 0
  rchar = ''

  while rchar <> '#' and tcount < 60:
    rchar = ser.read(1)
    if rchar:
      response.append(rchar)
    else:
      tcount += 1
#  print response, 'TIMER=%d' % tcount
  response = ''.join(response)
  logger.debug('-->{%s}=>(%s)' % (response,response.strip()) )
  return response.strip()


def ParseResponse(s):
  """Parse the response string.
  """
  if (not s) or ('ERROR' in s):
    logger.debug('Error or missing string: |%s|' % s)
    return True,-1
  elif s[0] == '#':
    logger.debug('Prompt but no return val: |%s|' %s)
    return None,None
  else:
    try:
      logger.debug("taking int('%s'[:-1])" % s)
      val = int(s[:-1])
    except ValueError:
      logger.debug('Exception taking int()')
      return 'ValueError',None
  return None,val


def Ask(s):
  """Send command in string 's' and wait for integer reply. Return reply value.
  """
  SendCommand(s)
  time.sleep(LATENCY)
  r = GetResponse()
  error,val = ParseResponse(r)
  if (not error) and (val is None):
    return 'EmptyResponse',None
  else:
    return error,val
    

def Tell(s):
  """Send command in string 's' to optical coupler, wait for new prompt, check for error return
  """
  SendCommand(s)
  time.sleep(LATENCY)
  r = GetResponse()
  error,v = ParseResponse(r)
  return error


def InitializeBoards():
  """Set both boards so that they return a prompt at end of response
     also set separated mode on board 0, and define some procedures
     return -1 on error, 0 otherwise
  """

  SendCommand("@0") 	#don't wait for a reply from this
  error = Tell("singleline(1)")
  
  if not error:
    error,reply = Ask("separated(1)")
    if (reply <> 0):
      error = True
  
  # set stepper parameters for normal motion in both axes on board 0 
  if not error:
    error,reply = Ask("param(0,50,400,200)")
    if (reply <> 0):
      error = True

  if not error:
    error,reply = Ask("param(1,50,400,200)")
    if (reply <> 0):
      error = True

  # define a procedure for moving a single axis and waiting until move is completed 
  if not error:
    error = Tell("proc movewait() { move(%1,%2) while(moving(%1)) {} }")

  # define a procedure that runs until it senses home, and then stops 
  if not error:
    error = Tell("proc stophome() { while(moving(0) && (not in(0)) ) {} stop(0) } ")

  if not error:
    SendCommand("@1") 		# don't wait for a reply from this */
    error = Tell("singleline(1)")

  # set stepper parameters for normal motion in both axes on board 1 
  if not error:
    error,reply = Ask("param(0,25,200,100)")
    if (reply <> 0):
      error = True

  if not error:
    error,reply = Ask("param(1,25,200,100)")
    if (reply <> 0):
      error = True

  # define a procedure for moving a both axes and waiting until move is completed 
  if not error:
    error = Tell("proc move2wait() { move(%1,%2) while(moving()) {} }")

  return error




def HomeFilter():
  """home the filter wheel using the optosensor
     returns -1 on ERROR, 0 otherwise
  """

  # Talk to the board that controls the Filter Wheel
  error = Tell("@0")

  # set motor parameters for normal motion
  if not error:
    error,reply = Ask("param(0,50,400,200)")
    if (reply <> 0):
      error = True

  # turn on the diode
  if not error:
    error,reply = Ask("out(0)")
    if (reply <> 0):
      error = True

  # check if filter wheel is at home position
  if not error:
    error,reply = Ask("in(0)")
    if ((not error) and (reply == 1)):
      # zero on this position
      error,reply = Ask("datum(0)")
      if (reply <> 0):
        error = True

      # back off a bit and wait until move is finished
      if not error:
	error = Tell("movewait(0,-50)")

  # zero on this position 
  if not error:
    error,reply = Ask("datum(0)")
    if (reply <> 0):
      error = True

  # move the filter wheel far away from zero position 
  if not error:
    error,reply = Ask("move(0, 6400)")
    if (reply <> 0):
      error = True

  # run embedded procedure 
  if not error:
    error = Tell("stophome()")

  # overshoot...back up a bit again, and then try again more slowly 

  # zero on this position 
  if not error:
    error,reply = Ask("datum(0)")
    if (reply <> 0):
      error = True

  # back off a bit and wait until move is finished
  if not error:
    error = Tell("movewait(0,-50)")

  # set motor parameters for slower motion 
  if not error:
    error,reply = Ask("param(0,0,63,25)")
    if (reply <> 0):
      error = True

  # start motor heading towards the optosensor */
  if not error:
    error,reply = Ask("move(0,50)")
    if (reply <> 0):
      error = True

  # run embedded procedure again 
  if not error:
    error = Tell("stophome()")

  # zero on this position 
  if not error:
    error,reply = Ask("datum(0)")
    if (reply <> 0):
      error = True

  # turn off the diode 
  if not error:
    error,reply = Ask("out(255)")
    if (reply <> 0):
      error = True
  
  # set motor parameters for normal motion 
  if not error:
    error,reply = Ask("param(0,50,400,200)")
    if (reply <> 0):
      error = True

  return error



def SelectFilter(filter_number=1):
  """move the filter wheel to a given filter position
     returns -1 on error, 0 otherwise

     NOTE - filter numbers are 1-8, not 0-7
  """

  # Talk to the board that controls the filter position
  error = Tell("@0")

  # move to selected filter position  and wait until move is finished
  error = Tell("movewait(0,%d)" % FILTERS[filter_number])

  if not error:
    error,reply = Ask("where(0)")
    if error or (reply <> FILTERS[filter_number]):
      error = True

  return error


def GetFilter():
  """Return the current filter number, or None if the filter wheel isn't
     at one of the predefined filter positions.

     NOTE - filter numbers are 1-8, not 0-7
  """
  # Talk to the board that controls the filter position
  error = Tell("@0")
  if not error:
    error,reply = Ask("where(0)")

  if error:
    return None

  for n,v in FILTERS.items():
    if v == reply:
      return n
  return None



def HomeXYStage(xcen=None,ycen=None):
  """Bring the xy stage to its limits, then home to a known point and mark as center
     the move command on this board is not separated --> move(x,y) not move(axis, position)
     returns -1 on error, 0 otherwise
  """
  if (xcen is None) or (ycen is None):
    xcen = XGUIDER_CENTER
    ycen = YGUIDER_CENTER

  # Talk to the board that controls the XY Stage
  error = Tell("@1")

  # move both axes to their limits and wait for move to finish
  if not error:
    error = Tell("move2wait(-4000,-4000)")

  # check that both axes are at their limit
  if not error:
    error,reply = Ask("limit(0)")
    if (reply <> -1):
      error = True

  if not error:
    error,reply = Ask("limit(1)")
    if (reply <> -1):
      error = True
  
  # zero on this position
  if not error:
    error,reply = Ask("datum()")
    if (reply <> 0):
      error = True

  # move to the xy center position
  if not error:
    error = Tell("move2wait(%d,%d)" % (xcen,ycen))

  # now zero on this position
  if not error:
    error,reply = Ask("datum()")
    if (reply <> 0):
      error = True

  return error


def MoveXYStage(x,y):
  """move the xy stage to position (x,y) as measured from the center
     return -1 on error, 0 otherwise
  """

  # Talk to the board that controls the XY Stage 
  error = Tell("@1")

  # move to (x,y) position 
  if not error:
    error = Tell("move2wait(%d,%d)" % (x,y))

  # check that the positions are correct 
  if not error:
    error,reply = Ask("where(0)")
    if (reply <> x):
      error = True

  if not error:
    error,reply = Ask("where(1)")
    if (reply <> y):
      error = True

  return error


def GetXYStage():
  """Return the current XY stage position as an x,y tuple.
     If there are any errors, return None,None
  """
  # Talk to the board that controls the XY Stage
  error = Tell("@1")
  x,y = None,None
  if not error:
    error,x = Ask("where(0)")
  if not error:
    error,y = Ask("where(1)")
  return x,y


def HomeMirror():
  """Bring the mirror to its limits, then home to a known point and mark as center
     returns -1 on error, 0 otherwise
  """

  # Talk to the board that controls the mirror position 
  error = Tell("@0")

  # move mirror to its limits and wait for move to finish 
  if not error:
    error = Tell("movewait(1,-2760)")

  # check that it is at its limit 
  if not error:
    error,reply = Ask("limit(1)")
    if (reply <> -1):
      error = True
  
  # zero on this position 
  if not error:
    error,reply = Ask("datum(1)")
    if (reply <> 0):
      error = True

  # move mirror forward a bit past the limit and wait for move to finish 
  if not error:
    error = Tell("movewait(1,10)")

  # home on this position 
  if not error:
    error,reply = Ask("datum(1)")
    if (reply <> 0):
      error = True

  return error


def MoveMirror(mpos):
  """Move the mirror to  the specified number of steps in from the home position (zero
     is fully 'out'). You can also supply 'IN' or 'OUT', specified in the global MIRRORS
     dictionary.

     return -1 on error, 0 otherwise
  """
  if type(mpos) == str and mpos.strip().upper() in MIRRORS.keys():
    mpos = MIRRORS[mpos.strip().upper()]

  # Talk to the board that controls the mirror position 
  error = Tell("@0");

  # move to position 
  if not error:
    error = Tell("movewait(1,%d)" % mpos);

  # check that the position is correct 
  if not error:
    error,reply = Ask("where(1)")
    if (reply <> mpos):
      error = True

  return error


def GetMirror():
  """Return the current mirror position as a string, 'IN' or 'OUT' (defined in MIRRORS
     global.

     If there are any errors, or if the position is not one of the standard
     locations, return None.
  """

  # Talk to the board that controls the XY Stage
  error = Tell("@0")
  pos = None
  if not error:
    error,pos = Ask("where(1)")

  if error:
    return None
  for n,v in MIRRORS.items():
    if pos == v:
      return n
  return None

