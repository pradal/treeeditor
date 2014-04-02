"""
Definition of Model-View-Presenter classes used in the TreeEditor package
"""

class AbstractMVP(object):
    """ Abstract class common to Model, View and Presenter """
    def __init__(self, theme=None, presenter=None):
        """ set theme and parent presenter """
        self.set_theme(theme)
        self.set_presenter(presenter)
        
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
            
    def set_presenter(self, presenter):
        """ set the controling Presenter """
        self._presenter = presenter
        
    def updateGL(self):
        """ call parent updateGL """
        if self._presenter:
            self._presenter.updateGL()
        else:
            print type(self).__name__ + '.updateGL: parent is not set'
            
    def update_content(self, lookAt=True):
        """ call parent update_content """
        if self._presenter:
            if lookAt==True: lookAt=self.get_boundingbox()
            self._presenter.update_content(lookAt=lookAt)
        else:
            print 'Could not update: parent is not set'
   
class Model(AbstractMVP):
    """ unspecialized class """
    pass

class View(AbstractMVP):
    """ Simple View that render a PlantGL scene """
    def __init__(self, scene=None, theme=None, presenter=None):
        """ create the view to display given `scene` """
        AbstractMVP.__init__(self, theme=theme, presenter=presenter)
        
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
        
    # bounding box
    # ------------
    def update_boundingbox(self):
        """ (re)compute the view boundingbox """
        if self.scene:
            self.boundingbox = self.compute_boundingbox(self.scene)
        else:
            self.boundingbox = None
        return self.boundingbox
        
    def get_boundingbox(self):
        """ return the *already* computed boundingbox
        Use `update_boundingbox to recompute it 
        """
        return self.boundingbox
        
    @staticmethod
    def compute_boundingbox(scene):
        """ Compute the bounding box of PlantGL.Scene `scene` """
        import openalea.plantgl.all as _pgl
        # compute bounding box of `new_content`
        bbc = _pgl.BBoxComputer(_pgl.Discretizer())
        bbc.process(scene)
        
        return bbc.boundingbox
        
    # opengl & draw
    # -------------
    def __gl_init__(self):
        """ called for initialization of opengl environment - by default do nothing"""
        pass

    def show(self, display=True):
        """ show (or hide) view """
        self.display = display
        self.updateGL()
        
    def draw(self,glrenderer):
        """ draw the scene in given `glrenderer` """
        if self.display and self.scene:
            self.scene.apply(glrenderer)
        
    def fastDraw(self,glrenderer):
        """ implement fast drawing - by default call `draw` """
        self.draw(glrenderer)



class Presenter(AbstractMVP):
    """
    By default, a Presenter simply manage and display a set of View objects. 
    Subclasses can also manage Model object, at their convenience, as well as 
    the interactions between views and models.
    """
    def __init__(self, theme=None, editor=None, **views):
        """ Create a Presenter displaying given View objects """
        AbstractMVP.__init__(self, theme=theme, presenter=editor)
        self._view_names  = set()
        self._file_actions = []
        self._edit_actions = []
        self._view_actions = []
        
        for name,view in views.iteritems():
            self.attach_view(name,view)
        
    def set_editor(self, editor):
        self.set_presenter(editor)
        
    # actions
    # -------
    def get_file_actions(self):
        """ Return the list of actions provided by this presenter
            See also: `add_file_action`
        """
        return self._file_actions
        
    def get_edit_actions(self):
        """ Return the list of actions provided by this presenter
            See also: `add_edit_action`
        """
        return self._edit_actions
    
    def get_view_actions(self):
        """ Return a list of actions to enable/disable the View.display
        """
        return self._view_actions
        
    def add_file_action(self, description, function, dialog=None, keys=None, warning=None):
        """ register an action to be returned by `get_file_action`
        
        description: string to put in generated menu
        function: the function to call (with a filename as argument)
        dialog: dialog required. Either None, 'open' or 'save'
        keys (optional): a list of keyboard access. Ex: ['Ctrl+S']
        warning (optional): a function that return a warning message or None
        """
        action = dict(description=description, function=function, dialog=dialog, keys=keys, warning=warning)
        self._file_actions.append(action)
        
    def add_edit_action(self, description, function, keys=None, isenable=None):
        """ register an action to be returned by `get_edit_action`
        
        description: string to put in generated menu
        function: the function to call when action is triggered
        keys (optional): a list of keyboard access. Ex: ['Del','Ctrl+D']
        isenable (optional): a function that check if action is enable
        """
        action = dict(description=description, function=function, 
                                     keys=keys, isenable=isenable)
        self._edit_actions.append(action)
        
    def add_view_action(self, description, function, keys=None, isenable=None, checked=None):
        """ register an action to be returned by `get_view_action`
        
        description: string to put in generated menu
        function: the function to call when action is triggered
        keys (optional): a list of keyboard access. Ex: ['Del','Ctrl+D']
        isenable (optional): a function that check if action is enable
        checked: None:nothing, True/False: checkable action initialized as given
        """
        action = dict(description=description, function=function, 
                                     keys=keys, checked=checked, isenable=isenable)
        self._view_actions.append(action)
        
        
    # view list
    # ---------
    def attach_view(self, name, view):
        """ attach `view` to this Presenter as attribute `name` """
        self.__dict__[name] = view
        self._view_names.add(name)
        view.set_theme(self.theme)
        view.set_presenter(self)
        if hasattr(view,'show'):
            self.add_view_action(description='display '+name, function=view.show, checked=view.display)
        
    def get_views(self):
        """ return the views managed by the Presenter as a dictionary """
        return [(name,getattr(self,name)) for name in self._view_names]
    
    def is_empty(self):
        """ True if this Presenter has no attached view, and True otherwise """
        return len(self._view_names)==0
        
    # opengl & draw
    # -------------
    def __gl_init__(self):
        """ called by the editor at opengl init - by default do nothing"""
        for name,view in self.get_views():
            view.__gl_init__()

    def draw(self, glrenderer):
        """ Draw content to given `glrenderer` """
        for name,view in self.get_views():
            view.draw(glrenderer)
        
    def fastDraw(self,glrenderer):
        """ implement fast drawing - by default call `draw` """
        for name,view in self.get_views():
            view.fastDraw(glrenderer)

    # updating content
    # ----------------
    def get_boundingbox(self):
        """ return the bounding box of the all of the views """
        bbox = filter(None,map(lambda x: x[1].get_boundingbox(), self.get_views()))
        if len(bbox):
            return reduce(lambda x,y:x+y, bbox)
        else:
            return None

        
    
    # misc
    # ----
    def contextMenuEvent(self, buttons, position, camera):
        """ return list of items for context menu """
        return []
    def show_message(self, message):
        """ send a message to the parent presenter, or print it if it is unset """
        if self._presenter:
            self._presenter.show_message(message)
        else:
            print message


