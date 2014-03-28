"""
Definition of Model-View-Presenter used in the TreeEditor package
"""
import openalea.plantgl.all as _pgl

class Presenter(object):
    """
    This is a base class for Presenter which simply display a list of View 
    objects. It is however expected that subcalsses also control Model object, 
    as well as all insteractions between views and models.
    """
    def __init__(self, view_list=[]):
        """ Create a Presenter displaying given View objects """
        self.view_list = view_list
        self._editor = None
        
        for view in view_list:
            view.set_presenter(self)
        
    def get_view_list(self):
        """ return the list of views managed by the Presenter """
        return self.view_list
    def __gl_init__(self):
        """ called by the editor at opengl init - by default do nothing"""
        for view in self.get_view_list():
            view.__gl_init__()

    def draw(self, glrenderer):
        """ Draw content to given `glrenderer` """
        for view in self.get_view_list():
            view.draw(glrenderer)
        
    def fastDraw(self,glrenderer):
        """ implement fast drawing - by default call `draw` """
        for view in self.get_view_list():
            view.fastDraw(glrenderer)

    def get_bounding_box(self):
        """ return the bounding box of the all of the views """
        bbox = filter(None,map(lambda x: x.boundingbox, self.get_view_list()))
        if len(bbox):
            return reduce(lambda x,y:x+y, bbox)
        else:
            return None

    def register_editor(self, editor):
        """ Attach this view to the given `editor` """
        self._editor = editor
        
    def show_message(self, message):
        """ send a message to the editor for printing """
        if self._editor:
            self._editor.showMessage(message)
        else:
            print message

class AbstractVM(object):
    """ abstract class common to Model and View """
    def set_presenter(self, presenter):
        """ set the controling Presenter """
        self._presenter = presenter
        
class Model(AbstractVM):
    pass

class View(AbstractVM):
    """
    Simple View that render a PlantGL scene
    """
    def __init__(self, scene=None):
        """ create the view to display given `scene` """
        self.display = True
        self.scene = scene
        self.update_boundingbox()
        
    def update_boundingbox(self):
        """ (re)compute the view boundingbox """
        if self.scene:
            self.boundingbox = get_boundingbox(self.scene)
        else:
            self.boundingbox = None
        
    def draw(self,glrenderer):
        """ draw the scene in given `glrenderer` """
        if self.display and self.scene:
            self.scene.apply(glrenderer)
        
    def fastDraw(self,glrenderer):
        """ implement fast drawing - by default call `draw` """
        self.draw(glrenderer)


def get_boundingbox(scene):
    """
    Compute the bounding box of PlantGL.Scene `scene`
    """
    # compute bounding box of `new_content`
    bbc = _pgl.BBoxComputer(_pgl.Discretizer())
    bbc.process(scene)
    
    return bbc.boundingbox

