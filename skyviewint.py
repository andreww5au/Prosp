
"""Skyview interface:

   Defines 'skyview' function, to bring up a netscape browser window
   with a 'Skyview' image of the position specified, scaled to match the
   AP7 field of view and pixel size.

   Due to Netscape irregularities and a slow net connection, this might not
   work the first time it's called, and will take a while...

   The http proxy server is hardwired into this module near the top of the file.

   See http://skyview.gsfc.nasa.gov

"""

import os
import string
import webbrowser
import urllib
import threading
import os

os.environ['http_proxy']='http://192.168.25.72:3128'

base='http://skyview.gsfc.nasa.gov/cgi-bin/nnskcall.pl'
params={'SURVEY':'Digitized Sky Survey',
        'SCOORD':'Equatorial',
        'MAPROJ':'Gnomonic',
        'GRIDDD':'Yes',
        'PIXELX':512,
        'PIXELY':512,
        'COLTAB':'B-W LINEAR', 
        'SFACTR':0.0853333, 
        'RESAMP':'Interpolation',
        'CATLOG':'HST Guide Star Catalog, Version 1.2',
         }


def skyview(posn='', equinox=2000):
  """Take a position string and optional equinox, and start the connection
     in a background thread (it takes ages). The global form parameter 
     dictionary (params) is used - see the skyview advanced form web page
     HTML source for details of parameter names and values.
  """
  if posn:
    params['VCOORD']=posn
  else:
    print "Needs position or object name"
    return 0
  params['EQUINX']=equinox
  data=urllib.urlencode(params)     #Encode spaces as %20, etc
  t=threading.Thread(target=_getpage,
                     name='Skyview page download',
                     args=(base,data))
  t.setDaemon(1)
  t.start()


def _getpage(base,data):
  """This function runs in the background to actually download the page.
     It passes the base script URL along with all the form values as a 'POST' -
     passing them directly in the URL fails due to the CALM web proxy barfing
     on long URL's.
  """
  f=urllib.urlopen(base, data)
  out=open('/tmp/skyview.html','w')   #Copy the page to a local file
  page=f.read()
  f.close()

  #Insert a '<base>' tag to give the base URL, so netscape will display the 
  #local file, but still correctly load all the relative links to embedded
  #images.
  page=string.replace(page,'<HEAD>',
       '<HEAD>\n<base href="http://skyview.gsfc.nasa.gov/cgi-bin/nnskcall.pl">')
  out.write(page)
  out.close()

  #The webbrowser interface to netscape is a bit erratic, it doesn't handle
  #cases where netscape isn't already open very well.
  webbrowser.open('file:/tmp/skyview.html')
