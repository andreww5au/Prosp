
import objects
import teljoy
import planet
import string
import ArCommands

class Object(objects.Object):
  "A new object class with dynamic methods, like 'jump'."

  def jump(self):
    "Move the telescope to the object coordinates"
    teljoy.jump(id=self.ObjID, ra=self.ObjRA, dec=self.ObjDec,
                epoch=self.ObjEpoch)

  def set(self):
    "Set the observing params for Ariel to this object's params."
    p=planet.Pobject(self.ObjID)
    if p.valid:
      ArCommands.filename(planet.site+p.root+p.filt)
    else:
      ArCommands.filename(self.ObjID)
    ArCommands.object(self.ObjID)
    ArCommands.guider(self.XYpos[0],self.XYpos[1])
    ArCommands.filter(self.filtname)
    ArCommands.exptime(self.exptime)

