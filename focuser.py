
"""Focuser unit - used to talk to the Finger Lakes Instrumentation
   focuser unit. Code to take images and evaluate them using PyRAF
   functions sits at a higher level, this unit has no dependencies.
"""

import commands

MaxPos = 1000    #Maximum focuser distance (plus or minus) from home

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
  for l in txt.split('\n'):
    llist = l.split(':')
    if llist[0].strip() == "focuser position":
      try:
        status.pos = int(llist[1].strip())
      except:
        print "Error parsing focuser low-level output."
  return status.pos


def Home():
  "Homes the focuser (returns to zero position)"
  commands.getoutput(focmd + 'home 0')
  status.pos = 0


def Goto(N=0):
  "Moves the focuser to ABSOLUTE position N"
  if N <= MaxPos:
    status.update()
    dif = N - status.pos
    commands.getoutput(focmd + 'offset ' + `dif`)
    status.update()


status = _FocusStatus()
status.update()
