"""
Definition of Model-View-Presenter classes used in the TreeEditor package

The MVP structure
-----------------
We use a *lightly constrained* **MVP** architecture:

Model (M) 
    Models are used to represent data that can be edited. Models have no 
    special content, apart that they are `AbstractMVP` (see classes below)
   
Views (V)
    They represent content that are displayed. They can be a graphical 
    representation of a Model, or not.
    
Presenters (P)
    The Presenter can be used in two ways:
     - It can be a container of several Views and other sub-presenters. Its role
       is to be an intermediate node a the components tree of viewables.
     - It can be the presenter in a Model-View(s)-Presenter triplets. This is
       the MVP pattern where the presenter manages the communication with the 
       model, and with one or more views. In this pattern, model and views don't
       communicate with one-another directly.
    
Editor
    It is the top Presenter which also does the interaction with PLantGL 
    and QGL for graphical update and dispatching user controls.

classes
-------

AbstractMVP
    Base abstract class of all MVPs. It provides references to the parent 
    container (its `presenter`). This implements the upward communication in the
    MVP hierarchy. 
    It also manage the action registering.

Model
    Simply an AbstractMVP. Maybe it will later provide some standard interfaces 
    for model edition and updates.

AbstractViewable
    Abstract class parent of View and Presenter, which can both be displayed.
    It defines the interface of object for display: bounding box, draw, ...

View
    Implementation of AbstractViewable for managing a PlantGL Scene.

Presenter
    It manages a list AbstractViewable (View and sub-presenters) and all 
    downward communication (container-to-component). It should be used as base
    class to implement specific Model-View-Presenter block.
    Typical subclass is `treeeditor.tree.TreePresenter`

AbstractEditor
    Definition of a part of the Editor API. Mainly, it is a Presenter that keep
    a reference to a "currently edited" sub-presenter.


Theme
-----

All components of the TreeEditor hierarchy share a `theme` dictionary. A default
theme is defined at the TreeEditor root modules. It stores default parameter 
values that are used, and shared, by all components.

The theme dict used by a container object is always passed to sub-components.


Bounding box
------------
Views and Presenters implements the (AbstractViewable) bounding box API. The 
implementation is made to be *lazy*: it does the computation only when the a
value is requested. 
In practice this means that:
 - views call `update_boundingbox` when they have changed. This flags them and 
   all their containers (parent, grandparent, etc... iteratively). 
 - Then when requested by a call to `get_boundingbox`, `_compute_boundingbox`
   is called on all flagged components, only.

update_boundingbox
    flag an object, and its containers, as having an obsolete bounding box.
    
get_boundingbox
    Return the already computed boundingbox, and recompute it if it is flagged 
    as obsolete
    
_compute_boundingbox
    Private function to compute the bounding box. It is the method that should 
    be implemented according to the type of viewable: 
      - Views compute the bounding box of their PlantGL `scene`, and
      - Presenter compute the union of the viewable objects it contains.
    
    Note that this method can also be used to set the bounding box.


Actions
-------
Any components can define actions, using the `add_***_actions` methods. The list
of declared actions can be obatined using the `get_***_actions` methods. Leaves
components (views and models) will return their own actions, and presenters
return their as well as those of their components.

An action is represented by a dictionary. They are stored in lists that can be
seen as menus. Such list can also contain `None` which are meant to represent 
separation bars.

At minima, action dictionaries should have a 'description' and a 'function' 
items that states, what they do, and which function to call when triggered, 
respectively. Other items can be added, to provide additional functionality:
 - keys: 
     A list of shortcut keys, such as ['Ctrl+A','Shift+Space']
 - isenable: 
     If given, the action represent a check button, and its value indicates in
     which state their are initiated (True for checked or False otherwise)
 - dialog:
     For file action that required a user interface to select a file. The value
     can be 'open' or 'save. Then a (open of save) file selection user dialog is
     opened and it is the user selected file that is passed to the action 
     'function'
 - warning:
     For used with `dialog`: if given, first ask the

Possible improvements: 
 * use a centralized system (instead of hierarchical):
    - central system is initiated by editor
       > add_***_action goes through self.presenter()
    - components register actions
    - they can be updated, w.r.t to uid
    . still need presenter to list their own actions?
    . actions should still be stored hierarchically or by components
       > all actions of 1 component can be disabled, ...
 * add 'id' to action dict
 * add 'isenable' callback to action dict
"""

class AbstractMVP(object):
    """ Abstract class common to Model, View and Presenter """
    def __init__(self, theme=None, presenter=None):
        """ set theme and parent presenter """
        self.set_theme(theme)
        self.set_presenter(presenter)
        self._file_actions = []
        self._edit_actions = []
        self._view_actions = []
        
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
        
    def get_presenter(self):
        """ return this object parent """
        return self._presenter
        
    def get_editor(self):
        parent = self.get_presenter()
        if parent: return parent.get_editor()
        else:      return None
        
    def show_message(self, message):
        """ send a message to the parent presenter, or print it if it is unset """
        if self._presenter:
            self._presenter.show_message(message)
        else:
            print message
            
    def updateGL(self):
        """ call parent updateGL """
        if self._presenter:
            self._presenter.updateGL()
        else:
            print type(self).__name__ + '.updateGL: parent is not set'

    def look_at(self, bbox='me'):
        """ call editor to focus camera on given `bbox` """
        editor = self.get_editor()
        if editor:
            if bbox=='me':
                bbox = self.get_boundingbox()
            editor.look_at(bbox)

   
    # actions
    # -------
    def get_file_actions(self):
        """ Return the list of actions related to the file menu
            See also: `add_file_action`
        """
        return self._file_actions
        
    def get_edit_actions(self):
        """ Return the list of actions related to the edit menu
            See also: `add_edit_action`
        """
        return self._edit_actions
    
    def get_view_actions(self):
        """ Return the list of actions related to the view menu
            See also: `add_view_action`
        """
        return self._view_actions
        
    def add_file_action(self, description, function, dialog=None, keys=None, warning=None, **kargs):
        """ register an action to be returned by `get_file_action`
        
        description: string to put in generated menu
        function: the function to call (with a filename as argument)
        dialog: dialog required. Either None, 'open' or 'save'
        keys (optional): a list of keyboard access. Ex: ['Ctrl+S']
        warning (optional): a function that return a warning message or None
        """
        action = dict(description=description, function=function, dialog=dialog, keys=keys, warning=warning, **kargs)
        self._file_actions.append(action)
        
    def add_edit_action(self, description, function, keys=None, isenable=None, **kargs):
        """ register an action to be returned by `get_edit_action`
        
        description: string to put in generated menu
        function: the function to call when action is triggered
        keys (optional): a list of keyboard access. Ex: ['Del','Ctrl+D']
        isenable (optional): a function that check if action is enable
        """
        action = dict(description=description, function=function, 
                                     keys=keys, isenable=isenable, **kargs)
        self._edit_actions.append(action)
        
    def add_view_action(self, description, function, keys=None, isenable=None, checked=None, **kargs):
        """ register an action to be returned by `get_view_action`
        
        description: string to put in generated menu
        function: the function to call when action is triggered
        keys (optional): a list of keyboard access. Ex: ['Del','Ctrl+D']
        isenable (optional): a function that check if action is enable
        checked: None:nothing, True/False: checkable action initialized as given
        """
        action = dict(description=description, function=function, 
                                     keys=keys, checked=checked, isenable=isenable, **kargs)
        self._view_actions.append(action)
        
        
   
class Model(AbstractMVP):
    """ unspecialized class """
    pass

class AbstractViewable(AbstractMVP):
    """ Abstract class for viewable objects: View and Presenter objects 
    
    At minima, subclasses should implement:
      - _compute_boundingbox
      - draw
    """
    def __init__(self, theme=None, presenter=None):
        """ create the view to display given `scene` """
        AbstractMVP.__init__(self, theme=theme, presenter=presenter)
        self.display = True
        
    # bounding box
    # ------------
    def update_boundingbox(self, bbox=None):
        """ flag this object and its parent for bounding box recomputation """
        self._bbox_update_flag = True
        if self._presenter:
            self._presenter.update_boundingbox()
        
    def _compute_boundingbox(self, bbox):
        """ This abstract method set the boundingbox to given `bbox`
        Subclasses should call it after computing it them-selves.
        """
        self.boundingbox = bbox
        self._bbox_update_flag = False
        
    def get_boundingbox(self):
        """ return the boundingbox - and recompute if necessary
        Use `update_boundingbox to flag that recomputation is required 
        """
        if self._bbox_update_flag:
            self._compute_boundingbox()
        return self.boundingbox
        
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
        """ Abstract method to draw the object in given `glrenderer` """
        raise NotImplementedError("abstract draw: should be implemented by subclasses")
        
    def fastDraw(self,glrenderer):
        """ implement fast drawing - by default call `draw` """
        self.draw(glrenderer)


class View(AbstractViewable):
    """ Simple Viewable that store and render a PlantGL.Scene """
    def __init__(self, scene=None, theme=None, presenter=None):
        """ create the view to display given `scene` """
        AbstractViewable.__init__(self, theme=theme, presenter=presenter)
        self.scene = scene
        self.update_boundingbox()
    
    def _compute_boundingbox(self, bbox=None):
        """ (re)compute the view boundingbox
        if bbox is given, use it. Otherwise compute the scene bbox
        """
        if not bbox and self.scene:
            bbox = compute_scene_boundingbox(self.scene)
        AbstractViewable._compute_boundingbox(self,bbox)
        
    def draw(self,glrenderer):
        """ draw the scene in given `glrenderer` """
        if self.display and self.scene:
            self.scene.apply(glrenderer)
        

    def clear(self):
        """ clear View content - set scene to None """
        self.scene = None
        self.update_boundingbox()

class Presenter(AbstractViewable):
    """
    By default, a Presenter simply manage (i.e. display) a set of View objects. 
    Subclasses can also manage a Model object, at their convenience, as well as 
    the interactions between the model and related views.
    """
    def __init__(self, theme=None, editor=None, **viewables):
        """ Create a Presenter displaying given View objects """
        AbstractViewable.__init__(self, theme=theme, presenter=editor)
        self._view_names  = set()
        for name,viewable in viewables.iteritems():
            self.attach_viewable(name,viewable)
        
    def set_editor(self, editor):
        self.set_presenter(editor)
        
    # actions
    # -------
    def get_file_actions(self):
        """ Return the list of (file) actions of this object and its views """
        actions = []
        for name,view in self.get_viewables():
            actions.extend(view.get_file_actions())
            actions.append(None)
        actions.extend(AbstractViewable.get_file_actions(self))
        
        return actions
        
    def get_edit_actions(self):
        """ Return the list of (edit) actions of this object and its views """
        actions = []
        for name,view in self.get_viewables():
            actions.extend(view.get_edit_actions())
        actions.extend(AbstractViewable.get_edit_actions(self))
        
        return actions
    
    def get_view_actions(self):
        """ Return the list of (view) actions of this object and its views """
        actions = []
        for name,view in self.get_viewables():
            actions.extend(view.get_view_actions())
        actions.extend(AbstractViewable.get_view_actions(self))
        
        return actions
        
    # view list
    # ---------
    def attach_viewable(self, name, viewable):
        """ attach `view` to this Presenter as attribute `name` """
        self.__dict__[name] = viewable
        self._view_names.add(name)
        viewable.set_theme(self.theme)
        viewable.set_presenter(self)
        viewable.update_boundingbox()
        
    def get_viewables(self):
        """ return the views managed by the Presenter as a dictionary """
        return [(name,getattr(self,name)) for name in self._view_names]
    
    def is_empty(self):
        """ True if this Presenter has no attached view, and True otherwise """
        return len(self._view_names)==0
        
    # opengl & draw
    # -------------
    def __gl_init__(self):
        """ called by the editor at opengl init - by default do nothing"""
        for name,view in self.get_viewables():
            view.__gl_init__()

    def draw(self, glrenderer):
        """ Draw content to given `glrenderer` """
        for name,view in self.get_viewables():
            view.draw(glrenderer)
        
    def fastDraw(self,glrenderer):
        """ implement fast drawing - by default call `draw` """
        for name,view in self.get_viewables():
            view.fastDraw(glrenderer)

    # bounding box
    # ------------
    def _compute_boundingbox(self, bbox=None):
        """ compute the bounding box of the all of the views
        if bbox is given, use it. Otherwise compute the sum of views bbox
        """
        if not bbox:
            bbox = filter(None,map(lambda x: x[1].get_boundingbox(), self.get_viewables()))
            if len(bbox): bbox = reduce(lambda x,y:x+y, bbox)
            else:         bbox = None
        AbstractViewable._compute_boundingbox(self,bbox)
    
    # Events
    # ------
    def contextMenuEvent(self, buttons, position, camera):
        """ return list of items for context menu """
        return []


class AbstractEditor(Presenter):
    """ Abstract class for TreeEditor 
    
    An editor can be seen a the top presenter. 
    It should implements the OpenGL API, in particular:
      - draw/fastDraw which call children viewable with glrenderer
      - updateGL
      - look_at(bbox) that update the camera view
    """
    def __init__(self, theme=None, **viewables):
        Presenter.__init__(self, theme=theme, **viewables)
        self.set_edited_presenter(None)
        
    def get_editor(self):
        return self
        
    def updateGL(self):
        """ Should be implemented by editor classes """
        raise NotImplementedError("Editor.updateGL")
    def look_at(self):
        """ Should be implemented by editor classes """
        raise NotImplementedError("Editor.look_at")
        
        
    def set_edited_presenter(self, name):
        """ set the presenter that is being edited """
        if name:
            self._edited = getattr(self,name)
        else:
            self._edited = None
    
    def get_edited_presenter(self):
        """ return the currently edited presenter """
        return self._edited


def compute_scene_boundingbox(scene):
    """ Compute the bounding box of given PlantGL.Scene `scene` """
    import openalea.plantgl.all as _pgl
    # compute bounding box of `new_content`
    bbc = _pgl.BBoxComputer(_pgl.Discretizer())
    bbc.process(scene)
    
    return bbc.boundingbox
        

