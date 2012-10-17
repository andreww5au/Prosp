
import xyglobs
from xyglobs import *

Sscale = 0.24    # multiply stepper values by this to get pixels
Cscale = X_Steps*Sscale   # multiply meters in focal plane by this to get pixels

import Image, ImageDraw    #from PIL

xmax,ymax = 800, 600

backcol = (255,255,255)


def rscale(mag=10.0):
  """Given a guidestar magnitude, return a dot radius in pixels.
  """
  if mag > 11.5:
    return 0.5
  elif mag > 11.0:
    return 1.0
  elif mag > 10.5:
    return 1.5
  elif mag > 10.0:
    return 1.5
  elif mag > 9.5:
    return 2.0
  elif mag > 9.0:
    return 2.5
  elif mag > 8.5:
    return 3.0
  else:
    return 3.5

def drawstars(slist=[], best=None, outfile='/tmp/stars.jpg'):
  """Given a list of Guidestar objects (with .x .y and .mag attributes) draw
     a mirror bounding box, with drill hole.
  """
  img = Image.new('RGB', (xmax,ymax), backcol)    #blank 8-bit color image
  draw = ImageDraw.Draw(img)

  x,y,radius = 400, 300, hole_radius*Cscale
  draw.rectangle( (400+Xmin*Cscale, 300-Ymin*Cscale, 400+Xmax*Cscale, 300-Ymax*Cscale), outline=(0,128,0), fill=None)
  draw.chord( (int(x-radius+0.5),int(y-radius+0.5),int(x+radius+0.5),int(y+radius+0.5)),
                  0, 360, outline=(0,128,0), fill=None)

  for i in range(len(slist)):
    x,y,radius = 400+slist[i].x*Sscale, 300-slist[i].y*Sscale, rscale(slist[i].mag)
    draw.chord( (int(x-radius+0.5),int(y-radius+0.5),int(x+radius+0.5),int(y+radius+0.5)),
                 0, 360, outline=(0,0,0), fill=(0,0,0))
    draw.text( (400+slist[i].x*Sscale+3, 300-slist[i].y*Sscale+3), `i`, fill=(0,0,0) )

  i = best    #Redraw the 'best' star in red
  try:
    x,y,radius = 400+slist[i].x*Sscale, 300-slist[i].y*Sscale, rscale(slist[i].mag)
    draw.chord( (int(x-radius+0.5),int(y-radius+0.5),int(x+radius+0.5),int(y+radius+0.5)),
                 0, 360, outline=(192,0,0), fill=(192,0,0))
    draw.text( (400+slist[i].x*Sscale+3, 300-slist[i].y*Sscale+3), `i`, fill=(192,0,0) )
  except TypeError,IndexError:
    pass  #There is no 'best' star

  img.save(outfile, quality=90)
