"""
User interface for the edition of tree structures

  * Powered by PlantGL *
"""
# import
# ------
# QT, OpenGL and qglViewer
from openalea.vpltk.qt import QtGui, QtCore # (!) needs to called before any other qt import 

# plantgl, qglviewer, opengl
from OpenGL import GL       as _gl
import PyQGLViewer          as _qgl
import openalea.plantgl.all as _pgl
from PyQGLViewer import QGLViewer as _QGLViewer

# tree editor components
from treeeditor.mvp  import AbstractEditor as _AbstractEditor
from treeeditor.tree import TreePresenter  as _TreePresenter
from treeeditor.background import BackgroundPresenter as _BackgroundPresenter
                                                                                

_toVec = lambda v : _qgl.Vec(*v)
##toV3  = lambda v : _pgl.Vector3(*v)


## patch for pgl.BoundingBox.__add__ bug
def bb_add(b1,b2):
    llc = map(min,zip(list(b1.lowerLeftCorner),list(b2.lowerLeftCorner)))
    urc = map(max,zip(list(b1.upperRightCorner),list(b2.upperRightCorner)))
    return _pgl.BoundingBox(llc,urc)
_pgl.BoundingBox.__add__ = bb_add


# TreeEditor main class
# ---------------------
class TreeEditorWidget(_QGLViewer, _AbstractEditor):
    """
    Class that implements a QGLViewer interface for the edition of tree structures
    """
    Camera,Edition = range(2)
    _mode_name = {Camera:'Camera', Edition:'Edition'}
    
    def __init__(self, parent=None, tree='default', background='default', theme=None, **presenters):
        """ create a TreeEditor for `tree`, `background`, and other optional Presenter """
        # super __init__
        if parent: _QGLViewer.__init__(self,parent=None)
        else:      _QGLViewer.__init__(self)
                  
        if theme is None:
            from . import THEME as theme
        _AbstractEditor.__init__(self,theme=theme)
                  
        # defaults
        self.mode  = self.Edition
        
        # clipping plane
        self.clippingPlaneEnabled = False        
        self.frontVisibility = 0
        self.backVisibility = 1.0
        
        # temporary info 
        self.temporaryinfo2D = None
        self.temporaryinfo = None
        
        
        # plantgl rendering objects 
        self.discretizer  = _pgl.Discretizer()
        self.glrenderer   = _pgl.GLRenderer(self.discretizer)
        self.glrenderer.renderingMode = _pgl.GLRenderer.Dynamic
        try:
            self.glrenderer.setGLFrame(self)
        except:
            print 'no text on GL Display'

        # store functions to be called by key press event
        self.key_callback = {}
        self.IO_callback = []

        # attach content to display
        if background:
            self.set_background(background)
        if tree:
            self.set_tree(tree)
        for name,pres in presenters.iteritems():
            self.attach_viewable(name,pres)

        # register actions
        self._registered_action = {}
        self.open_file_callback = {}  # file open functions w.r.t file extension
        
        # events & actions
        self.setFocusPolicy(QtCore.Qt.StrongFocus) # keyboard & mouse focus
        self.setAcceptDrops(True)                  # accept drop event
        ##self.add_file_action('close editor',    self.close,          keys=['Ctrl+Q'])
        self.add_view_action('refresh', self.look_at, keys=['Space'], checked=False)


    # add/set tree and background
    # ---------------------------
    def set_tree(self, tree):
        """ set the TreePresenter object to be edited """
        if tree is None or tree=='default':
            tree = _TreePresenter(theme=self.theme)
        self.attach_viewable('tree',tree)
        self.set_edited_presenter('tree')
        if not tree.is_empty():
            self.look_at(tree.get_boundingbox())
        
    def set_background(self, background):
        """ set the background view object """
        if background is None or background=='default':
            background = _BackgroundPresenter()
        self.attach_viewable('background',background)

    # clipping plane of displayed content
    # -----------------------------------
    def enabledClippingPlane(self, enabled):
        """ unable/disable clipping plane of opengl draw """
        self.clippingPlaneEnabled = enabled
        if enabled: self.show_message('Enabled Clipping Plane')
        else:       self.show_message('Disabled Clipping Plane')
        if self.isVisible():
            self.updateGL()
        
    def setFrontVisibility(self, value):
        """ set front clipping plane (in percent) """
        self.frontVisibility = (value / 100.)
        if self.isVisible() : self.updateGL()
    
    def setBackVisibility(self, value):
        """ set back clipping plane (in percent) """
        self.backVisibility = value / 100.
        if self.isVisible() : self.updateGL()
    

    # opengl
    # ------
    def init(self):
        """ initialize opengl environement """
        ##_gl.glEnable(_gl.GL_LIGHTING)
        ##_gl.glEnable(_gl.GL_LIGHT0)
        ##_gl.glEnable(_gl.GL_DEPTH_TEST)
        ##_gl.glLightfv(_gl.GL_LIGHT0,_gl.GL_DIFFUSE,[1,3,2,1])
        ##_gl.glLightf(_gl.GL_LIGHT0,_gl.GL_CONSTANT_ATTENUATION,.0)
        ##_gl.glLightf(_gl.GL_LIGHT0,_gl.GL_LINEAR_ATTENUATION,.0)
        ##_gl.glLightf(_gl.GL_LIGHT0,_gl.GL_QUADRATIC_ATTENUATION,.0)
        _gl.glLightfv(_gl.GL_LIGHT0,_gl.GL_AMBIENT, [0.7,0.7,0.7,1])

        self.set_mode(self.Camera)
        self.set_camera('3D')
        
    def set_mode(self,mode):
        """ set editor mode and related QGLViewer states """
        # Note: the below QGLViewer configurations indicates how QGLViewer 
        # process events. However, these events are first intercepted by the 
        # relative event function (mousePressEvent, ...). 
        Qt  = QtCore.Qt
        QGL = _QGLViewer
        
        # if camera mode: mouse event redirected to camera motion, and ctrl+mouse to nothing
        # otherwise, it's this opposite
        cam_mode = mode==self.Camera
        self.setMouseBinding(Qt.LeftButton,         QGL.CAMERA, QGL.TRANSLATE if cam_mode else QGL.NO_MOUSE_ACTION)
        self.setMouseBinding(Qt.RightButton,        QGL.CAMERA, QGL.ROTATE    if cam_mode else QGL.NO_MOUSE_ACTION)
        self.setMouseBinding(Qt.MidButton,          QGL.CAMERA, QGL.ZOOM      if cam_mode else QGL.NO_MOUSE_ACTION)
                                        
        self.setMouseBinding(Qt.LeftButton +Qt.ALT, QGL.CAMERA, QGL.NO_MOUSE_ACTION if cam_mode else QGL.TRANSLATE)
        self.setMouseBinding(Qt.RightButton+Qt.ALT, QGL.CAMERA, QGL.NO_MOUSE_ACTION if cam_mode else QGL.ROTATE)
        self.setMouseBinding(Qt.MidButton  +Qt.ALT, QGL.CAMERA, QGL.NO_MOUSE_ACTION if cam_mode else QGL.ZOOM)
        
        self.setWheelBinding(Qt.NoModifier,  QGL.CAMERA, QGL.ZOOM)
        
        if mode == self.Edition:
            self.setMouseBinding(Qt.LeftButton, QGL.FRAME, QGL.TRANSLATE)
        
        self.mode = mode
            
    def switch_mode(self, key_seq=None):
        """ Switch editor mode (View,Edition)<>Camera """
        self.set_mode(not self.mode)
        self.updateGL()

    def set_camera(self, camera='3D'):
        """ set camera type
        
        Either:
         - '3D': an (unconstraint) perpective camera
         - '2D': an orthographic view contraint on the 2D x-y plane
        """
        cam = self.camera()
        if camera=='3D':
            cam.setType(cam.PERSPECTIVE)
            cam.setViewDirection(_qgl.Vec(0,-1,0))
            cam.setUpVector(_qgl.Vec(0,0,1))
            cam.frame().setConstraint(None)
        else:
            cam.setType(cam.ORTHOGRAPHIC)
            cam.setUpVector(_toVec([0,-1,0]))
            cam.setViewDirection(_toVec([0,0,1]))
            
            constraint = _qgl.WorldConstraint()
            constraint.setRotationConstraintType(_qgl.AxisPlaneConstraint.FORBIDDEN)
            cam.frame().setConstraint(constraint)
        
    def setManipulatedFrame(self, obj):
        """ set `obj` as this Viewer manipulated frame, and set according mode """
        _QGLViewer.setManipulatedFrame(self,obj)
        if obj: self.set_mode(self.Edition)
        else:   self.set_mode(self.Camera)
        self.updateGL()
                                                           
    def setRevolveAroundPoint(self, position):
        """ 
        Set camera to revolve around given `position`
        if `position` is None, set the camera to revolve around scene center
        """
        if position:
            self.camera().setRevolveAroundPoint(_toVec(position))
        else:
            self.camera().setRevolveAroundPoint(self.sceneCenter())
            
    # rendering and printing
    # ----------------------
    def draw(self):
        """ paint in opengl """
        if self.clippingPlaneEnabled:
            _gl.glPushMatrix()
            _gl.glLoadIdentity()
            zNear = self.camera().zNear()
            zFar = self.camera().zFar()
            zDelta = (zFar-zNear) / 2
            viewDir = self.camera().viewDirection()
            if self.frontVisibility > 0:
                eq = [0.,0.,-1., -(zNear+  zDelta * self.frontVisibility)]
                _gl.glClipPlane(_gl.GL_CLIP_PLANE0,eq)
                _gl.glEnable(_gl.GL_CLIP_PLANE0)
            if self.backVisibility < 1.0:
                eq2 = [0.,0.,1., (zNear+  zDelta * self.backVisibility)]
                _gl.glClipPlane(_gl.GL_CLIP_PLANE1,eq2)
                _gl.glEnable(_gl.GL_CLIP_PLANE1)
            
            _gl.glPopMatrix()
        else:
            _gl.glDisable(_gl.GL_CLIP_PLANE0)
            _gl.glDisable(_gl.GL_CLIP_PLANE1)
        
        _AbstractEditor.draw(self, self.glrenderer)
            
    def fastDraw(self):
        """ fast (re)paint in opengl """
        _AbstractEditor.fastDraw(self, self.glrenderer)
    
    def show_message(self,message,timeout = 5000):
        """ display a message """
        self.displayMessage(message,timeout)
        print message
        self.updateGL()
        
    # menus
    # -----
    def get_file_menu(self):
        """ generate the file menu """
        return self._create_menu('File', self.get_file_actions())

    def get_edit_menu(self):
        """ generate the edit menu """
        return self._create_menu('Edition', self.get_edit_actions())
        
    def get_view_menu(self):
        """ generate the view menu """
        return self._create_menu('View', self.get_view_actions())
        
    def get_plugin_actions(self):
        """ return TreeEditor actions for OAlab """
        actions = []
        
        def add_some_action(menu, action_dicts):
            action_dicts = filter(None, action_dicts)
            for action in action_dicts:
                action = self._get_action(**action)
                actions.append((menu,action,1)) #(-pane_name-), group_name, action, btn_type)
            
        add_some_action('file',self.get_file_actions())
        add_some_action('edit',self.get_edit_actions())
        add_some_action('view',self.get_view_actions())
        
        return actions
    
    def _create_menu(self, title, actions, filter_dict=None):
        """ create an QMenu for get_***_menu """
        menu = QtGui.QMenu(title, self)
        for action in actions:
            if action is None: menu.addSeparator()
            else:              menu.addAction(self._get_action(**action))
        menu.addSeparator()
        
        return menu
        
    def _get_action(self, description, function, keys=None, **kargs):
        """ get the registered QAction, and create if first registered """
        registered_key = (function,None if keys is None else tuple(keys))
        
        if registered_key in self._registered_action:
            return self._registered_action[registered_key]
            
        else:
            dialog   = kargs.get('dialog')
            warning  = kargs.get('warning')
            open_ext = kargs.get('opened_extension')
    
            if open_ext is not None:
                if isinstance(open_ext,basestring):
                    open_ext = [open_ext]
                for ext in open_ext:
                    self.open_file_callback[ext] = function
              
            if dialog=='save':
                from functools import partial
                function = partial(self.savefile_dialog, description, function, warning)
            elif dialog=='open':
                from functools import partial
                function = partial(self.openfile_dialog, description, function, warning)
                
            action = QtGui.QAction(description, self)
            action.triggered.connect(function)
            self.addAction(action)
            
            checked = kargs.get('checked',None)
            if checked is not None:
                action.setCheckable(True)
                action.setChecked(checked)
                
            if keys:
                action.setShortcuts([QtGui.QKeySequence(kseq).toString() for kseq in keys])
                action.setShortcutContext(QtCore.Qt.WidgetWithChildrenShortcut)

            self._registered_action[registered_key] = action
            return action
        
    # mouse and keyboard events
    # -------------------------
    def _mouse_string(self,event):                                  
        """ contruct key sequence string from mouse `event` """
        modifiers = event.modifiers()
        buttons =  QtGui.QKeySequence(modifiers).toString()
        if buttons is None:
            buttons = ''
        if hasattr(event,'button'):
            button = event.button()                        
            if   QtCore.Qt.LeftButton  == button: buttons += 'Left'
            elif QtCore.Qt.RightButton == button: buttons += 'Right'
            elif QtCore.Qt.MidButton   == button: buttons += 'Middle'
        
        return buttons
        
    def mousePressEvent(self,event):
        """ 
        Call TreePresenter mousePressEvent with arguments:
          - keys: a string representing all pressed keys, such as: 'Ctrl+Shift'
          - position: the mouse position
          - camera: this viewer camera
        """
        buttons = self._mouse_string(event)
        edited = self.get_edited_presenter()
        if 'Right' not in buttons and edited:
            processed = edited.mousePressEvent(buttons,event.pos(),self.camera())
            if processed:
                return
            
        return _QGLViewer.mousePressEvent(self,event)
        
    def mouseReleaseEvent(self,event):
        """ distribute relase event and  """
        buttons = self._mouse_string(event)
        edited = self.get_edited_presenter()
        if edited:
            processed = edited.mouseReleaseEvent(buttons,event.pos(),self.camera())
            if processed:
                return
        return _QGLViewer.mouseReleaseEvent(self,event)
        
    def contextMenuEvent(self, event):
        """ generate a context menu on click"""
        buttons = self._mouse_string(event)
        edited = self.get_edited_presenter()
        if edited:
            menu = edited.contextMenuEvent(buttons, event.pos(),self.camera())
            
            if menu:
                menu = self._create_menu('Context', menu)
                menu.exec_(event.globalPos())
                return
                
        return _QGLViewer.contextMenuEvent(self,event)

    
    # accept drop mtg to open
    # -----------------------
    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat("text/plain"):
            event.accept()
            return
            
        event.ignore()

    def dropEvent(self, event):
        mimeData = event.mimeData()
        if not mimeData.hasFormat("text/plain"):
            event.ignore()
            
        import os
        filename = str(mimeData.text())
        if filename.startswith("data/'"):
            # mimeData come from OpenAleaLab
            from openalea.oalab.session.session import Session
            path = Session().project.path
            filename = filename[6:].split("'")[0]
            filename = str(path / 'data' / filename)
            
        ext = os.path.splitext(filename)[-1]
        fct = self.open_file_callback.get(ext)
        if fct is None:
            raise TypeError('Cannot open file with extension: ' + ext)
        else:
            fct(filename)
        event.accept()


    # updating
    # --------
    def _compute_boundingbox(self):
        """
        Compute scene boundingbox center and radius
        
        `lookAt` (optional) Either:
            - a BoundingBox object to focus camera on
            - 'all', to look at the whole scene
            - 'tree', to look at the whole tree
                
        Return the update scene bounding box 
        """
        _AbstractEditor._compute_boundingbox(self)
        
        bbox = self.get_boundingbox()
        if not bbox:
            return
            
        cam = self.camera()
        cam.setSceneRadius(_pgl.norm(bbox.lowerLeftCorner-bbox.upperRightCorner))
        cam.setSceneCenter(_toVec(bbox.lowerLeftCorner+bbox.upperRightCorner)/2)

    def look_at(self, bbox='scene'):
        """ set camera to look at given `bbox` """
        scene_bbox = self.get_boundingbox()
        
        edited = self.get_edited_presenter()
        if bbox==False and edited:
            bbox = edited.get_boundingbox()
        elif bbox=='scene' or isinstance(bbox,bool):
            bbox = scene_bbox
            
        if bbox is None:
            self.show_message('*** look_at error: bounding box is empty ***')
        else:
            self.camera().fitBoundingBox(_toVec(bbox.lowerLeftCorner),_toVec(bbox.upperRightCorner))
            self.updateGL()
                                                    
    def updateGL(self):
        scene_bbox = self.get_boundingbox()  ## recompute if flaged
        _QGLViewer.updateGL(self)
        
    # dialog
    # ------
    def openfile_dialog(self, title, callback=None, warning=None):
        """ open an "open file" dialog with given `title`
        If `callback` is given, call it with user select filename as input
        If `warning` is given, open first a warning dialog with given message.
        """
        import os
        from openalea.oalab import session
        from treeeditor.io import get_shared_data
        
        # display warning message, if required
        if hasattr(warning,'__call__'):
            warning = warning()
        if warning:                
            msgBox = QtGui.QMessageBox()
            msgBox.setText(warning)
            msgBox.setStandardButtons(QtGui.QMessageBox.Cancel | QtGui.QMessageBox.Open)
            msgBox.setDefaultButton(QtGui.QMessageBox.Open)
            res = msgBox.exec_()
            if res==QtGui.QMessageBox.Cancel:
                return
        
        # select opened directory
        if hasattr(session,'session'): # test if oalab is started
            s = session.session.Session()
            data_dir = str(s.project.path / 'data')
        else:
            data_dir = get_shared_data()

        filename = QtGui.QFileDialog.getOpenFileName(None, title, data_dir,
                                                "All Files (*.*)")#,
                                                #QtGui.QFileDialog.DontUseNativeDialog)
        #d = QtGui.QFileDialog()
        #d.setAcceptMode(QtGui.QFileDialog.AcceptOpen)
        #filename = d.exec_()
        
        if not filename:
            return
        if callback:               
            callback(filename)
        return filename
        
    def savefile_dialog(self, title, callback=None, warning=None):
        """ open a "save file" dialog with given `title`
        If `callback` is given, call it with user select filename as input
        If `warning` is given, open first a warning dialog with given message.
        """
        import os
        from openalea.oalab import session
        from treeeditor.io import get_shared_data
        
        # print warning message, if required
        if hasattr(warning,'__call__'):
            warning = warning()
        if warning:
            msgBox = QtGui.QMessageBox()
            msgBox.setText(warning)
            msgBox.setStandardButtons(QtGui.QMessageBox.Cancel | QtGui.QMessageBox.Save)
            msgBox.setDefaultButton(QtGui.QMessageBox.Save)
            res = msgBox.exec_()
            if res==QtGui.QMessageBox.Cancel:
                return
                
        # select directory
        if hasattr(session,'session'): # test if oalab is started
            s = session.session.Session()
            data_dir = str(s.project.path / 'data')
        else:
            data_dir = get_shared_data()

        filename = QtGui.QFileDialog.getSaveFileName(self, title, data_dir,
                                                "All Files (*.*)")
                                                #QtGui.QFileDialog.DontUseNativeDialog)
        if not filename:
            return
        if callback:
            callback(filename)
        return filename        


        
class TreeEditor(QtGui.QMainWindow):
    """ stand alone application """
    def __init__(self, editor=None):
        QtGui.QMainWindow.__init__(self)
                                                                                                 
        # tree editor
        if not editor:
            editor = TreeEditorWidget()
        self.editor = editor
        self.setCentralWidget(self.editor)
        self.editor.show()
        
        self.update_menu()
        self.show()
        
    def sizeHint(self):
        return QtCore.QSize(800,600)
        
    def update_menu(self):
        """ (re)create menus """
        menu = self.menuBar()
        for submenu in menu.actions():
            menu.removeAction(submenu)
        
        file_menu = self.editor.get_file_menu()
        file_menu.addSeparator()  ## does not work...?
        quit_action = QtGui.QAction("Quit editor", self)
        quit_action.triggered.connect(self.close)
        quit_action.setShortcuts(["Ctrl+Q"])
        file_menu.addAction(quit_action)
        menu.addMenu(file_menu)
        
        menu.addMenu(self.editor.get_edit_menu())
        menu.addMenu(self.editor.get_view_menu())
        
        
def start_editor(model=None, inline=False):
    qapp = QtGui.QApplication([])
    viewer = TreeEditor()
    viewer.setWindowTitle("TreeEditor")
    
    if model and model.lower()=='pas':
        from treeeditor.tree.model import PASModel
        viewer.editor.tree.set_model(PASModel())
    
    if inline: return viewer, qapp
    else:      qapp.exec_()
    
def main():
    """ editor as an executable program """
    from optparse import OptionParser
    
    parser = OptionParser()
    parser.add_option("-m","--model", dest='model',help="tree model to use (default or 'PAS')")
    options, args = parser.parse_args()
    start_editor(model=options.model)

if __name__=='__main__':
    main()
