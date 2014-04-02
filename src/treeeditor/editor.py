"""
User interface for the edition of tree structures

  * Powered by PlantGL *
"""
# import
# ------
##import os
##import math

# QT, OpenGL and qglViewer
from openalea.vpltk.qt import QtGui, QtCore # (!) needs to called before any other qt import 

from OpenGL import GL       as _gl
import PyQGLViewer          as _qgl
import openalea.plantgl.all as _pgl

from PyQGLViewer import QGLViewer as _QGLViewer

from treeeditor.mvp  import Presenter     as _Presenter
from treeeditor.tree import TreePresenter as _TreePresenter
from treeeditor.background import BackgroundPresenter as _BackgroundPresenter
                                                                                

_toVec = lambda v : _qgl.Vec(*v)##v.x,v.y,v.z)
##toV3  = lambda v : _pgl.Vector3(*v)##v.x,v.y,v.z)

# TreeEditor main class
# ---------------------
class TreeEditorWidget(_QGLViewer, _Presenter):
    """
    Class that implements a QGLViewer interface for the edition of tree structures
    """
    Camera,Edition = range(2)
    _mode_name = {Camera:'Camera', Edition:'Edition'}
    
    
    def __init__(self, parent=None, tree=None, background=None, theme=None, **presenters):
        """ create a TreeEditor for `tree`, `background`, and other optional Presenter """
        # super __init__
        if parent: _QGLViewer.__init__(self,parent=None)
        else:      _QGLViewer.__init__(self)
                  
        _Presenter.__init__(self,theme=theme)
                  
        # defaults
        self.mode  = self.Edition
        ## global translation of the scene  ## removed as not used anymore (?)
        #self.translation = None
        
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
        self.set_background(background)
        self.set_tree(tree)
        for name,pres in presenters.iteritems():
            self.attach_presentation(name,pres)

        # actions
        ##self.add_file_action('close editor',    self.close,          keys=['Ctrl+Q'])
        self.add_view_action('refresh display', self.update_content, keys=['Space'])


    # add/set tree and background
    # ---------------------------
    def set_tree(self, tree):
        """ set the TreePresenter object to be edited """
        if tree is None:
            tree = _TreePresenter()
            
        self.attach_presentation('tree',tree)
        
    def set_background(self, background):
        """ set the background view object """
        if background is None: 
            background = _BackgroundPresenter()
                                                 
        self.attach_presentation('background',background)

    def attach_presentation(self, name, presentation):
        """ attach `presentation` to this Editor as attribute `name` """
        self.attach_view(name=name, view=presentation)
                     

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
        self.set_mode(self.Camera)
        
        self.camera().setViewDirection(_qgl.Vec(0,-1,0))
        self.camera().setUpVector(_qgl.Vec(0,0,1))
        
        self.background.__gl_init__()
        
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
        self.setMouseBinding(Qt.LeftButton,          QGL.CAMERA, QGL.TRANSLATE if cam_mode else QGL.NO_MOUSE_ACTION)
        self.setMouseBinding(Qt.RightButton,         QGL.CAMERA, QGL.ROTATE    if cam_mode else QGL.NO_MOUSE_ACTION)
        self.setMouseBinding(Qt.MidButton,           QGL.CAMERA, QGL.ZOOM      if cam_mode else QGL.NO_MOUSE_ACTION)
                                        
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

    def set_2d_camera(self):
        """ constraint camera to view at the 2D x-y plane """ 
        cam = self.camera()
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
            
    def update_scene_bbox(self, lookAt=None):
        """
        Update scene boundingbox
        
        `lookAt` (optional) Either:
            - a BoundingBox object to focus camera on
            - 'all', to look at the whole scene
            - 'tree', to look at the whole tree
                
        Return the update scene bounding box 
        """
        views = filter(None, [getattr(self,'background',None),getattr(self,'tree',None)]+
                              getattr(self,'presenters',[]))
        bbox_all = map(lambda p: p.get_boundingbox(), views)
        bbox = filter(None, bbox_all)
        
        if len(bbox)==0:
            self.show_message('Editor scene is empty')
            return
            
        bbox = reduce(lambda x,y: x+y, bbox)
        cam = self.camera()
        cam.setSceneRadius(_pgl.norm(bbox.lowerLeftCorner-bbox.upperRightCorner))
        cam.setSceneCenter(_toVec(bbox.lowerLeftCorner+bbox.upperRightCorner)/2)
        
        if lookAt:
            if lookAt=='all':
                lookAt = bbox
            elif lookAt=='tree':
                if bbox_all[1]:
                    lookAt = bbox_all[1]
                else:
                    lookAt = bbox
            cam.fitBoundingBox(_toVec(lookAt.lowerLeftCorner),_toVec(lookAt.upperRightCorner))
            
        self.updateGL()
                                                    
        
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
        
        _Presenter.draw(self, self.glrenderer)
            
    def fastDraw(self):
        """ fast (re)paint in opengl """
        _Presenter.fastDraw(self, self.glrenderer)

    
    def show_message(self,message,timeout = 0):
        """ display a message """
        self.displayMessage(message,timeout)
        print message
        self.updateGL()
        
    # actions and menus
    # -----------------
    def get_file_actions(self):
        """ Return the list of file actions provided by all presenters """
        actions = []
        for name,presenter in self.get_views():
            actions.extend(presenter.get_file_actions())
            actions.append(None)
            
        actions.append(None)
        actions.extend(_Presenter.get_file_actions(self))
                
        return actions
        
    def get_edit_actions(self):
        """ Return the list of edit actions provided by all presenters """
        actions = []
        for name,presenter in self.get_views():
            actions.extend(presenter.get_edit_actions())
                
        return actions
    
        
    def get_view_actions(self):
        """ Return the list of view actions provided by all presenters """
        actions = []
        for name,presenter in self.get_views():
            actions.extend(presenter.get_view_actions())
        actions.append(None)
        actions.extend(_Presenter.get_view_actions(self))
                
        return actions
        
    def get_file_menu(self):
        """ generate the file menu """
        def io_dialog(action):
            """ if required, insert open/save_dialog callback """
            action = dict(**action)
            dialog      = action.get('dialog')
            description = action['description']
            function    = action['function']
            warning     = action.get('warning')
            if dialog=='save':
                from functools import partial
                action['function'] = partial(self.savefile_dialog, description, function, warning)
            elif dialog=='open':
                from functools import partial
                action['function'] = partial(self.openfile_dialog, description, function, warning)
            return action
            
        return self._create_menu('File', self.get_file_actions(), io_dialog)

    def get_edit_menu(self):
        """ generate the edit menu """
        return self._create_menu('Edition', self.get_edit_actions())
        
    def get_view_menu(self):
        """ generate the view menu """
        return self._create_menu('View', self.get_view_actions())
        
    def _create_menu(self, title, actions, filter_dict=None):
        """ create an QMenu for get_***_menu """
        menu = QtGui.QMenu(title, self)
        
        for action in actions:
            if action is None: 
                menu.addSeparator()
            else:
                if filter_dict: action = filter_dict(action)
                menu.addAction(self._create_action(**action))
        
        return menu
        
    def _create_action(self, description, function, keys=None, **kargs):
        """ create an QAction for _creat_menu """
        action = QtGui.QAction(description, self)
        action.triggered.connect(function)
        
        checked = kargs.get('checked',None)
        if checked is not None:
            action.setCheckable(True)
            action.setChecked(checked)
            
        if keys:
            action.setShortcuts([QtGui.QKeySequence(kseq).toString() for kseq in keys])
        return action
        
    # manage mouse and keyboard events
    # --------------------------------
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
        if 'Right' not in buttons:
            processed = self.tree.mousePressEvent(buttons,event.pos(),self.camera())
        else:
            processed = False
            
        if not processed:
            return _QGLViewer.mousePressEvent(self,event)
        
    def mouseReleaseEvent(self,event):
        """ distribute relase event and  """
        buttons = self._mouse_string(event)
        processed = self.tree.mouseReleaseEvent(buttons,event.pos(),self.camera())
        if not processed:
            return _QGLViewer.mouseReleaseEvent(self,event)
        
    def contextMenuEvent(self, event):
        """ generate a context menu on click"""
        buttons = self._mouse_string(event)
        menu = self.tree.contextMenuEvent(buttons, event.pos(),self.camera())
        if menu:
            menu = self._create_menu('Context', menu)
            menu.exec_(event.globalPos())
            return
            
        return _QGLViewer.contextMenuEvent(self,event)


    # updating
    # --------
    def update_content(self, lookAt='all'):
        self.update_scene_bbox(lookAt=lookAt)
        parent = self.parent()
        if parent:
            parent.update_menu()
    def updateGL(self):
        _QGLViewer.updateGL(self)
        
    # dialog
    # ------
    def openfile_dialog(self, title, callback=None, warning=None):
        """ open an "open file" dialog with given `title`
        If `callback` is given, call it with user select filename as input
        If `warning` is given, open first a warning dialog with given message.
        """
        import os
        from treeeditor.io import get_shared_data
        
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
                
        filename = QtGui.QFileDialog.getOpenFileName(self, title,
                                                get_shared_data('data'),
                                                "All Files (*.*)",
                                                QtGui.QFileDialog.DontUseNativeDialog)
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
        from treeeditor.io import get_shared_data
        
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
                
        filename = QtGui.QFileDialog.getSaveFileName(self, title,
                                                get_shared_data('data'),
                                                "All Files (*.*)",
                                                QtGui.QFileDialog.DontUseNativeDialog)
        if not filename:
            return
        if callback:
            callback(filename)
        return filename        


        
class TreeEditor(QtGui.QMainWindow):
    def __init__(self):
        QtGui.QMainWindow.__init__(self)
                                                                                                 
        # tree editor
        self.editor = TreeEditorWidget()
        self.setCentralWidget(self.editor)
        self.editor.show()
        
        self.update_menu()
        self.show()
        
    def update_menu(self):
        """ (re)create menus """
        menu = self.menuBar()
        for submenu in menu.actions():
            menu.removeAction(submenu)
        menu.addMenu(self.editor.get_file_menu())
        menu.addMenu(self.editor.get_edit_menu())
        menu.addMenu(self.editor.get_view_menu())
        
def main():
    """ simple test program """
    qapp = QtGui.QApplication([])
    viewer = TreeEditor()
    viewer.setWindowTitle("TreeEditor")
    qapp.exec_()

if __name__ == '__main__':
    main()
