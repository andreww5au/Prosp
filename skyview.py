import os
import string
import threading

base='http://skyview.gsfc.nasa.gov/cgi-bin/nnskcall.pl?'
params=['EQUINX=2000',
        'SURVEY="Digitized Sky Survey"',
        'PIXELX=512&PIXELY=512',
        'COLTAB="B-W LINEAR"', 
        'GRIDDD="Yes"',
        'SFACTR=0.08533', 
        'RESAMP="Interpolation"',
        'ISCALN="Log(10)"',
        'CATLOG="HST Guide Star Catalog, Version 1.2"']


def skyview(coords):
  URL=base+'VCOORD="'+coords+'"&'+string.join(params,'&')
  URL=string.replace(URL, ' ', '%20')
  t=threading.Thread(group=None,
                     target=os.system,
                     args=("netscape '"+URL+"'",) )
  t.setDaemon(1)
  t.start()
  return URL


