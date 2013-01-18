"""Handle RPC comms with other components of the observing system, using Pyro4
"""

import Pyro4
import threading
import time
import traceback
import socket

from globals import *
import weather
import chiller
import focuser

status = None     #Override with actual status object from Prosp, when this is imported.

#hmac = "ShiverMeTimbers"
#Pyro4.config.HMAC_KEY = hmac or Pyro4.config.HMAC_KEY

class Prosp(object):
  """Class representing RPC access to the internals of an active telescope control object.
  """
  def __init__(self):
    self.lock = threading.RLock()

  def _servePyroRequests(self):
    """When called, start serving Pyro requests.
    """
    while True:
      logger.info("Starting Prosp Pyro4 server")
      try:
        ns = Pyro4.locateNS()
      except:
        logger.error("Can't locate Pyro nameserver - waiting 10 sec to retry")
        time.sleep(10)
        break

      try:
        existing = ns.lookup("Prosp")
        logger.info("Prosp still exists in Pyro nameserver with id: %s" % existing.object)
        logger.info("Previous Pyro daemon socket port: %d" % existing.port)
        # start the daemon on the previous port
        pyro_daemon = Pyro4.Daemon(host=Pyro4.socketutil.getInterfaceAddress('chef'), port=existing.port)
        # register the object in the daemon with the old objectId
        pyro_daemon.register(self, objectId=existing.object)
      except (Pyro4.errors.PyroError, socket.error):
        try:
          # just start a new daemon on a random port
          pyro_daemon = Pyro4.Daemon(host=Pyro4.socketutil.getInterfaceAddress('chef'))
          # register the object in the daemon and let it get a new objectId
          # also need to register in name server because it's not there yet.
          uri = pyro_daemon.register(self)
          ns.register("Prosp", uri)
        except:
          logger.error("Exception in Prosp Pyro4 startup. Retrying in 10 sec: %s" % (traceback.format_exc(),))
          time.sleep(10)
      try:
        pyro_daemon.requestLoop()
      except:
        logger.error("Exception in Prosp Pyro4 server. Restarting in 10 sec: %s" % (traceback.format_exc(),))
        time.sleep(10)

  def Ping(self):
    return

  def Lock(self):
    self.lock.acquire()

  def Unlock(self):
    self.lock.release()

  def GetStatus(self):
    return status.GetState()

  def GetChiller(self):
    return chiller.status.GetState()

  def GetFocuser(self):
    return focuser.status.GetState()

  def GetWeather(self):
    return weather.status.GetState()




def InitServer():
  global prosp, pyro_thread
  prosp = Prosp()

  #Start the Pyro4 daemon thread listening for status requests and receiver 'putState's:
  pyro_thread = threading.Thread(target=prosp._servePyroRequests, name='PyroDaemon')
  pyro_thread.daemon = True
  pyro_thread.start()
  logger.info("Started Pyro4 communication process to serve Prosp connections")
  #The daemon threads will continue to spin for eternity....

  return True


