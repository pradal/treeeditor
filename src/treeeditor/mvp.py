"""
Definition of Model-View-Presenter used in the TreeEditor package
"""
import openalea.plantgl.all as _pgl

class AbstractVMP(object):
    """ Abstract class common to Model, View and Presenter """
    def __init__(self, theme=None):
        """ Create a Presenter displaying given View objects """
        self.set_theme(theme)
        
    def set_theme(self, theme=None):
        """ set given `theme` for the Presenter """
        # display parameters
        from treeeditor import THEME
        if theme is None:
            self.theme = THEME.copy()
        else:
            for k,v in THEME.iteritems():
                theme.setdefault(k,v)
            self.theme = theme
            
class Presenter(AbstractVMP):
    """
    This is a base class for Presenter which simply display a set of View 
    objects. It is expected that subcalsses also control Model object, 
    as well as all interactions between views and models.
    """
    def __init__(self, theme=None, **views):
        """ Create a Presenter displaying given View objects """
        AbstractVMP.__init__(self, theme=theme)
        self._view_names = set()
        self._editor = None
        
        for name,view in views.iteritems():
            self.attach_view(name,view)
        
    def set_theme(self, theme=None):
        """ set given `theme` for the Presenter """
        # display parameters
        from treeeditor import THEME
        if theme is None:
            self.theme = THEME.copy()
        else:
            for k,v in THEME.iteritems():
                theme.setdefault(k,v)
            self.theme = theme
        
    def attach_view(self, name, view):
        """ attach `view` to this Presenter as attribute `name` """
        self.__dict__[name] = view
        self._view_names.add(name)
        view.set_theme(self.theme)
        view.set_presenter(self)
        
    def get_view_list(self):
        """ return the list of views managed by the Presenter """
        return map(getattr,(self,)*len(self._view_names), self._view_names)
    
    def is_empty(self):
        """ True if this Presenter has not view attached, and True otherwise """
        return len(self._view_names)==0
        
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

    def contextEvent(self, position, camera):
        """ return list of items for context menu """
        return []
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

class AbstractVM(AbstractVMP):
    """ abstract class common to Model and View """
    def __init__(self, theme=None, presenter=None):
        """ Create a Presenter displaying given View objects """
        AbstractVMP.__init__(self,theme=theme)
        self.set_presenter(presenter)
        
    def set_presenter(self, presenter):
        """ set the controling Presenter """
        self._presenter = presenter
        
class Model(AbstractVM):
    pass

class View(AbstractVM):
    """ Simple View that render a PlantGL scene """
    def __init__(self, scene=None, theme=None):
        """ create the view to display given `scene` """
        self.display = True
        self.scene = scene
        self.update_boundingbox()
        
        # display parameters
        from treeeditor import THEME
        if theme is None:
            self.theme = THEME.copy()
        else:
            for k,v in THEME.iteritems():
                theme.setdefault(k,v)
            self.theme = theme
        
    def update_boundingbox(self):
        """ (re)compute the view boundingbox """
        if self.scene:
            self.boundingbox = self.get_boundingbox(self.scene)
        else:
            self.boundingbox = None
        return self.boundingbox
        
    @staticmethod
    def get_boundingbox(scene):
        """ Compute the bounding box of PlantGL.Scene `scene` """
        # compute bounding box of `new_content`
        bbc = _pgl.BBoxComputer(_pgl.Discretizer())
        bbc.process(scene)
        
        return bbc.boundingbox
        
    def draw(self,glrenderer):
        """ draw the scene in given `glrenderer` """
        if self.display and self.scene:
            self.scene.apply(glrenderer)
        
    def fastDraw(self,glrenderer):
        """ implement fast drawing - by default call `draw` """
        self.draw(glrenderer)



