

import MySQLdb
try:
  DictCursor=MySQLdb.DictCursor
except AttributeError:     #New version of MySQLdb puts cursors in a seperate module
  import MySQLdb.cursors
  DictCursor=MySQLdb.cursors.DictCursor


class SafeCursor(DictCursor):
  """New cursor class with a wrapper around the 'execute' method to catch
     any exceptions and retry a few times, in case it's a bogus 2013
     exception.
  """

  def execute(self, *args, **kws):
    "wrapper around the base class execute method"
    try:
      DictCursor.execute(self, *args, **kws)
    except MySQLdb.OperationalError:
     ewrite("One OperationalError exception in MySQL call")
     try:
       DictCursor.execute(self, *args, **kws)
     except MySQLdb.OperationalError:
       ewrite("Two OperationalError exceptions in MySQL call, giving up")
       raise
