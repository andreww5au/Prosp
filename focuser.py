
"""Focuser unit - used to talk to the Finger Lakes Instrumentation
   focuser unit. Code to take images and evaluate them using PyRAF
   functions sits at a higher level, this unit has no dependencies.
"""

import time
import commands

MinPos = 0
MaxPos = 1000    #Maximum focuser position

focmd = './focuser/focus 0 '    #Name and first arg of C program

class _FocusStatus:
  """Focuser status object.
  """
  def __init__(self):
    self.pos = 0
  def update(self):
    getPos()
  def display(self):
    return "Focuser Position: %d" % (self.pos, )


def getPos():
  "Returns the current focuser position"
  global status
  txt = commands.getoutput(focmd + 'position 0')
#  print txt
  status.pos = None
  for l in txt.split('\n'):
    llist = l.split(':')
    if llist[0].strip() == "focuser position":
      try:
        status.pos = int(llist[1].strip())
      except:
        print "Error parsing focuser low-level output."
  if status.pos is None:
    print "Error communicating with focuser."
  return status.pos


def Home():
  "Homes the focuser (returns to zero position)"
  commands.getoutput(focmd + 'home 0')
  print "Focuser moved to position 0"
  time.sleep(0.5)
  status.update()


def Goto(N=0):
  "Moves the focuser to ABSOLUTE position N"
  if (N <= MaxPos) and (N >= MinPos):
    status.update()
    if N is not None:
      dif = N - status.pos
      txt = commands.getoutput(focmd + 'offset ' + `dif`)
      print txt
      time.sleep(0.5)
      status.update()
      if status is not None:
        print "Focuser moved to position",status.pos
      else:
        print "Problem communicating with focuser after move."
    else:
      print "Problem communicating with focuser before move."
  else:
    print "Position must be between %d and %d." % (MaxPos,MinPos)



def init():
  global status
  status = _FocusStatus()
  Home()
"  Goto(500)"
"  status.update()"
