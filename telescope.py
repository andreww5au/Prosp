

import time
import tjbox
from teljoy.extras import tjclient

from globals import *

USEPYRO = False

pausetime = 0

if USEPYRO:
  pass
else:
  status = tjbox.status
  status.update()
  _background = tjbox._background   #Function to be called regularly, from Prosp
  Active = tjbox.Active
  jump = tjbox.jump
  jumpoff = tjbox.jumpoff
  dome = tjbox.dome
  freeze = tjbox.freeze
  unfreeze = tjbox.unfreeze


def pause():
  """Goes into "Pause" mode and closes dome, used during bad-weather
  """
  global pausetime
  if not Active.isSet():
    logger.error("Teljoy already paused, can't pause() again")
  else:
    logger.info("Teljoy Paused due to bad weather.")
    status.paused = 1
    pausetime = time.time()     #Record when we've paused
    Active.clear()
    freeze(1)
    dome('CLOSE')


def unpause():
  """Leaves "Pause" mode and opens dome, used when weather clears.
  """
  global pausetime
  if Active.isSet():
    logger.error("Teljoy not in Pause mode, can't unpause()")
  else:
    logger.info("Teljoy un-paused, weather OK now.")
    pausetime = 0          #Zap the pause time so the dome doesn't reclose
    dome('OPEN')
    freeze(0)
    Active.set()
    status.paused = 0


def _background():
  """Function to be run in the background, updates the status object.
  """
  try:
    sincepause = time.time() - pausetime
    if (sincepause > 300) and (sincepause < 480):
      dome('CLOSE')             #If it's been 5-6 minutes since pausing,
      #close the shutter again to be safe

    if USEPYRO:
      tjclient._background()
    else:
      tjbox._background()
  except KeyboardInterrupt:
    print "a keyboard interrupt in telescope._background()"