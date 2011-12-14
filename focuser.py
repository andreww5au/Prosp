
import pyfli
import time

STEPSIZE = 85e-9      #85nm step size
COTE = 13.0e-6        #Metres of expansion per metre of length, per degree C (steel=13.0e-6)
FLENGTH = 13.5*0.61   #Effective optical length of the tube

MARGIN = 5000         #Don't go within this many steps of the upper extent limit

# Create re-usable pointers to floats and longs for the C-library to return values
f1 = pyfli.floatp()
d1 = pyfli.doublep()
l1 = pyfli.longp()


class _Focusser:
  """FLI focuser class. Attributes contain status data, and methods allow
     focuser control.
  """
  def __init__(self):
    """Set initial attributes
    """
    self.initialized = False
    self.pos = 0
    self.remaining = 0
    self.filename = ''
    self.modelname = ''
    self.dev = -1
    self.retval = None
    self.extent = 0
    self.Tinternal = 0
    self.Texternal = 0
    self.datumT = None
    self.datumP = None
  def procret(self, val=0, fname="<not set>"):
    """Given a return value and function name, do something with them...
       Save return value in self.retval.
    """
    self.retval = val
    if val:
      print 'Error in function %s:-> %d' % (fname, val)
  def retok():
    """Returns true if the contents of self.retval
       indicate that the last function call was successful.
    """
    return self.retval == 0
  def update(self):
    """Connect to the FLI focuser to get the current position, steps remaining
       in a slew, and temperature data.
    """
    self.GetStepperPosition()
    self.GetStepsRemaining()
    self.ReadTemperature()
  def display(self):
    return "Focuser Position: %d - max extent is %d" % (self.pos, self.extent)
  def Initialise(self):
    """Set up the connection to the FLI focuser.
       Note that the device (/dev/fliusbN) must have the correct permissions.
    """
    self.procret(pyfli.FLISetDebugLevel('localhost',pyfli.FLIDEBUG_WARN), 'FLISetDebugLevel')
    self.procret(pyfli.FLICreateList(pyfli.FLIDOMAIN_USB | pyfli.FLIDEVICE_FOCUSER), 'FLICreateList')
    fn = ' '*100
    n = ' '*100
    self.procret(pyfli.FLIListFirst(l1,fn,99,n,99),'FLIListFirst')
    self.filename = fn.strip().strip('\x00')
    self.modelname = n.strip().strip('\x00')
    self.procret(pyfli.FLIOpen(l1,fn,pyfli.FLIDOMAIN_USB | pyfli.FLIDEVICE_FOCUSER),'FLIOpen')
    self.dev = l1.value()
    self.GetFocuserExtent()
    self.update()
  def GetFocuserExtent(self):
    """Get the maximum travel position for the focuser.
       Note that long slews finishing near this maximum value are truncated
       early, so we use a practical maximum about 5000 counts less than this
       for the Atlas focuser.
    """
    self.procret(pyfli.FLIGetFocuserExtent(self.dev,l1),'FLIGetFocuserExtent')
    if self.retok:
      self.extent = l1.value()-MARGIN
    else:
      pass
  def HomeFocuser(self):
    """Return the focuser to home position (0), the minimum thickness of
       the focuser. Note that this can take as long as 170 seconds.
    """
    self.procret(pyfli.FLIHomeFocuser(self.dev),'FLIHomeFocuser')
    if self.retok:
      self.pos = 0
    else:
      self.pos = -1
  def StepMotorAsync(self,n):
    """Start a slew moving the telescope by 'n' steps, where -4000<n<4000.
       Slews longer than 4095 steps are truncated due to a driver bug, so
       issue a warning if larger values are passed to the function.
    """
    if abs(n) > 4000:
      print "Warning - slews larger than 4000 steps are not supported"
    else:
      if self.GetStepsRemaining() <= 1:
        self.procret(pyfli.FLIStepMotorAsync(self.dev,n),'FLIStepMotorAsync')
      else:
        print "Focuser still in motion, aborting."
  def GetStepperPosition(self):
    """Get the current position of the focuser, store it in self.pos, and
       return the value as well. Note that you must also call self.GetStepsRemaining
       to determine whether the stepper is still in motion.
    """
    self.procret(pyfli.FLIGetStepperPosition(self.dev, l1),'FLIGetStepperPosition')
    if self.retok:
      self.pos = l1.value()
      return l1.value()
    else:
      self.pos = -1
      return -1
  def GetStepsRemaining(self):
    """Return the number of steps remaining in the current slew (call to 'StepMotorAsync').
    """
    self.procret(pyfli.FLIGetStepsRemaining(self.dev, l1), 'FLIGetStepsRemaining')
    if self.retok:
      self.remaining = l1.value()
      return l1.value()
    else:
      self.remaining = -1
      return -1
  def ReadTemperature(self):
    """Read the internal and external focuser temperatures, in degrees C, and store
       them in self.Tinternal and self.Texternal.
       Note that the internal and external temps have been swapped from the values
       identified by the driver, to correct for an (apparent) driver bug.
    """
    self.procret(pyfli.FLIReadTemperature(self.dev, pyfli.FLI_TEMPERATURE_INTERNAL, d1),'FLIReadTemperature')
    if self.retok:
      self.Texternal = d1.value()
    self.procret(pyfli.FLIReadTemperature(self.dev, pyfli.FLI_TEMPERATURE_EXTERNAL, d1),'FLIReadTemperature')
    if self.retok:
      self.Tinternal = d1.value()
    return self.Tinternal, self.Texternal
  def Goto(self,n):
    """Given a destination position, loop over enough slews to get there, calling
       StepMotorAsync repeatedly with 4000 step slews. Abort if a call to StepMotorAsync
       doesn't result in a change in the focuser position.
    """
    if n >= self.extent:
      print "Clipping to maximum position of %d." % (self.extent)
      n = self.extent
    if n < 0:
      print "Clipping to minimum position of 0."
      n = 0
    if n == 0:
      self.HomeFocuser()
    else:
      self.update()
      lastoffset = 0
      offset = n - self.pos
      while abs(offset) > 0:
        if abs(offset) > 4000:
          self.StepMotorAsync(4000*offset/abs(offset))        #Go + or - 4000 steps, depending on the sign of offset
        else:
          self.StepMotorAsync(offset)
        while self.GetStepsRemaining() > 1:
          time.sleep(0.2)
        self.update()
        lastoffset = offset
        offset = n - self.pos
        if abs(offset) > 0:
          time.sleep(0.2)
          print "Steps Remaining: %d" % (abs(offset))
        if offset == lastoffset:
          print "Focuser not converging on final position, aborting."
          break


def Home():
  """Slews the focuser to home position (0), the minimum thickness.
     Note that the maximum slew travel time is around 170 seconds.
  """
  status.HomeFocuser()


def getPos():
  """Returns the current focuser position
  """
  return status.GetStepperPosition()


def Goto(n):
  """Slews the focuser to absolute position 'n'.
     Note that the maximum slew travel time is around 170 seconds.
  """
  status.Goto(n)


def Tzero():
  """Record the current external focuser temperature and motor position,
     defining those values as the 'datum point' for a good focus. Call this
     function immediately after focussing the telescope.

     Subsequent calls to 'Tcorrect()' will read the new focuser external
     temperature, and move the focuser to the optimum motor position for
     that temperature.
  """
  status.update()
  status.datumT = status.Texternal
  status.datumP = status.pos


def Tcorrect():
   """Read the new focuser external temperature, and move the focuser to
      the optimum motor position for that temperature. An initial reference
      temperature and position must have been previously defined by a call
      to Tzero(), immediately after focussing the telescope.
   """
   if status.datumT is None or status.datumP is None:
     print "Initial temperature/position datum not set"
   else:
     status.update()
     deltaT = status.datumT - status.Texternal
     deltaPos = int(FLENGTH*COTE*deltaT / STEPSIZE)
     newpos = status.datumP + deltaPos
     if newpos <> status.pos:
       print "Adjusting focus for %5.2fC temp drift since focus set: Moving %d steps to position %d." % (deltaT, newpos-status.pos, newpos)
       Goto(status.datumP + deltaPos)
     else:
       print "No temperature drift, focus not changed."


status = _Focusser()

def init():
  status.Initialise()

