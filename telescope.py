

import time
import threading

from globals import *
import tjbox
from teljoy.extras import tjclient

Active = threading.Event()
Active.set()

USEPYRO = True

pausetime = 0

if USEPYRO:
  print tjclient.Init()
  status = tjclient.status
  jump = tjclient.jump
  jumpoff = tjclient.jumpoff
  offset = tjclient.jumpoff
  dome = tjclient.dome
  freeze = tjclient.freeze
  unfreeze = tjclient.unfreeze
else:
  tjbox.Init()
  status = tjbox.status
  jump = tjbox.jump
  jumpoff = tjbox.jumpoff
  offset = tjclient.jumpoff
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
    pausetime = time.time()     #Record when we've paused
    Active.clear()
    freeze(True)
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
    freeze(False)
    Active.set()


def _background():
  """Function to be run in the background, updates the status object.
  """
  try:
    sincepause = time.time() - pausetime
    if (not Active.isSet()) and (sincepause > 300) and (sincepause < 480):
      dome('CLOSE')             #If it's been 5-6 minutes since pausing,
      #close the shutter again to be safe

    if USEPYRO:
      tjclient._background()
    else:
      tjbox._background()
  except KeyboardInterrupt:
    print "a keyboard interrupt in telescope._background()"
