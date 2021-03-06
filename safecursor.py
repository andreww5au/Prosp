
from globals import logger

import MySQLdb
from MySQLdb.cursors import DictCursor


class SafeCursor(DictCursor):
  """New cursor class with a wrapper around the 'execute' method to catch
     any exceptions and retry a few times, in case it's a bogus 2013
     exception.
  """

  def execute(self, query, args=None):
    "wrapper around the base class execute method"
    try:
      return DictCursor.execute(self, query, args)
    except MySQLdb.OperationalError:
      logger.exception("One OperationalError exception in MySQL call")
    try:
      return DictCursor.execute(self, query, args)
    except MySQLdb.OperationalError:
      logger.exception("Two OperationalError exceptions in MySQL call, giving up")
      raise

  def __del__(self):
    DictCursor.__del__(self)

  def close(self):
    DictCursor.close(self)
