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

from treeeditor import tree       as _tree
from treeeditor import background as _background


_toVec = lambda v : _qgl.Vec(*v)##v.x,v.y,v.z)
##toV3  = lambda v : _pgl.Vector3(*v)##v.x,v.y,v.z)

# TreeEditor class
# ----------------
class TreeEditor(_QGLViewer):
    """
    Class that implements a QGLViewer interface for the edition of tree structures
    """
    Camera,View,Edition = range(3)
    _mode_name = {Camera:'Camera', View:'View', Edition:'Edition'}
    
    
    def __init__(self, parent=None, tree=None, background=None, theme=None, *presenters):
        """ create a TreeEditor for `tree`, `background`, and other optional Presenter """
        # super __init__
        if parent: _QGLViewer.__init__(self,parent=None)
        else:      _QGLViewer.__init__(self)
                                              
        # defaults
        if theme is None:
            from treeeditor import THEME
            theme = THEME.copy()
        self.theme = THEME
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
        
        self.presenters = []
        for p in presenters: self.add_presenter(p)
        

    # add/set content to display
    # --------------------------
    def set_tree(self, tree):
        """ set the TreePresenter object to be edited """
        if tree is None:
            tree = _tree.TreePresenter(theme=self.theme)
        else:
            tree.set_theme(self.theme)
        tree.register_editor(self)
        self.tree = tree
        
    def set_background(self, background):
        """ set the background view object """
        if background is None: 
            background = _background.BackgroundPresenter(theme=self.theme)
        else:
            background.set_theme(self.theme)
        background.register_editor(self)
        self.background = background 

    def add_presenter(self,presenter):
        """ add optional Presenter object """
        presenter.register_editor(self)
        self.presenters.append(presenter)
                     

    # clipping plane of displayed content
    # -----------------------------------
    def enabledClippingPlane(self, enabled):
        """ unable/disable clipping plane of opengl draw """
        self.clippingPlaneEnabled = enabled
        if enabled: self.showMessage('Enabled Clipping Plane')
        else:       self.showMessage('Disabled Clipping Plane')
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
        self.setMouseBindingDescription(QtCore.Qt.Key_Space,"Switch between edition and camera interaction mode")
        self.setMouseBindingDescription(QtCore.Qt.CTRL+QtCore.Qt.Key_Q,"Quit")
        ##self.setMouseBindingDescription(QtCore.Qt.LeftButton,"When double clicking on a line, create a new line",True)
        
        self.camera().setViewDirection(_qgl.Vec(0,-1,0))
        self.camera().setUpVector(_qgl.Vec(0,0,1))
        
        self.background.__gl_init__()
        
        self.register_key('Space',  'switch camera/edition mode', self.switch_mode)
        self.register_key('Ctrl+Q', 'close editor', self.close)
        self.register_key('Ctrl+R', 'look at whole tree', self.update_scene_bbox, ['tree'])

    def set_2d_camera(self):
        """ constraint camera to view at the 2D x-y plane """ 
        cam = self.camera()
        cam.setType(cam.ORTHOGRAPHIC)
        cam.setUpVector(_toVec([0,-1,0]))
        cam.setViewDirection(_toVec([0,0,1]))
        
        constraint = _qgl.WorldConstraint()
        constraint.setRotationConstraintType(_qgl.AxisPlaneConstraint.FORBIDDEN)
        cam.frame().setConstraint(constraint)
        
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
        #self.showMessage('Interaction mode:' + self._mode_name[self.mode])
            
    def setManipulatedFrame(self, obj):
        """ set `obj` as this Viewer manipulated frame, and set according mode """
        _QGLViewer.setManipulatedFrame(self,obj)
        if obj:
            self.set_mode(self.Edition)
        else:
            self.set_mode(bool(self.mode))
        self.updateGL()
            
    def switch_mode(self, key_seq=None):
        """ Switch editor mode (View,Edition)<>Camera """
        self.set_mode(not self.mode)
        self.updateGL()

    def update_scene_bbox(self, lookAt=None):
        """
        Update scene boundingbox
        
        `lookAt` (optional) Either:
            - a BoundingBox object to focus camera on
            - 'all', to look at the whole scene
            - 'tree', to look at the whole tree
                
        Return the update scene bounding box 
        """
        bbox_all = map(lambda p: p.get_bounding_box(), [self.background,self.tree]+self.presenters)
        bbox = filter(None, bbox_all)
        
        if len(bbox)==0:
            self.showMessage('Editor scene is empty')
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
        
        # draw Presenter objects
        self.background.draw(self.glrenderer)
        if self.mode==self.Camera:
            self.tree.fastDraw(self.glrenderer)
        else:
            self.tree.draw(self.glrenderer)
        for p in self.presenters:
            p.draw(self.glrenderer)

        
        ## to be done by Points in BackgroundPresenter
        ##if self.pointDisplay and self.points:
        ##    #self.pointMaterial.apply(self.glrenderer)
        ##    #self.points.apply(self.glrenderer)
        ##    self.pointsRep.apply(self.glrenderer)
        ##    
        ##if self.contractedpointDisplay and self.contractedpoints:
        ##     self.contractedpointsRep.apply(self.glrenderer)


        # draw temporary info
        ##_gl.glEnable(_gl.GL_LIGHTING)
        ##_gl.glEnable(_gl.GL_BLEND)
        ##_gl.glBlendFunc(_gl.GL_SRC_ALPHA,_gl.GL_ONE_MINUS_SRC_ALPHA)

        if 0:#self.temporaryinfo2D:
            self.startScreenCoordinatesSystem()
            self.temporaryinfo2D.apply(self.glrenderer)
            self.stopScreenCoordinatesSystem()
            
        if 0:#self.temporaryinfo:
            self.temporaryinfo.apply(self.glrenderer)
            
    def fastDraw(self):
        """ fast (re)paint in opengl """
        self.background.fastDraw(self.glrenderer)
        self.tree.fastDraw(self.glrenderer)
        for p in self.presenters:
            p.fastDraw(self.glrenderer)

    
    def showMessage(self,message,timeout = 0):
        """ display a message """
        self.displayMessage(message,timeout)
        print message
        self.updateGL()
        
    # manage mouse and keyboard events
    # --------------------------------
    def register_key(self, key_sequence, description, callback, cb_args=[]):
        """ register the `callback` to be triggered by `key_sequence` 
        
        :Inputs:
          - `key_sequence`
                Any valid input of `QtGui.QKeySequence`. For example, to bing a
                callback for the control 'p' key sequence, the following works:
                  -  "Ctrl+z"
                  -  "Ctrl+Z"
                  -  QtCore.Qt.CTRL + QtCore.Qt.Key_Z
                  -  or the equivalent QKeySequence object
           
          - `callback` 
                A callable object (i.e. function) with no argument
        """
        self.key_callback[QtGui.QKeySequence(key_sequence).toString()] =\
                                                [description, callback,cb_args]
        
    def bind_openfile_dialog(self,key_sequence,title,callback,warning=None):
        """ set to open an "open file" dialog for given `key_sequence`
        
        The dialog will have title `title` and, once selected, given `callback`
        is called with the filename as argument.
        if `warning` is given, a warning dialog is opened before the the open 
        file dialog with message given by `warning`.  
        """
        self.IO_callback.append((key_sequence, title, self.openfile_dialog, [title,callback,warning]))
        self.register_key(key_sequence, title, self.openfile_dialog, cb_args=[title,callback,warning])
        
    def bind_savefile_dialog(self,key_sequence,title,callback,warning=None):
        """ set to open a "save file" dialog for given `key_sequence`
        
        The dialog will have title `title` and, once selected, given `callback`
        is called with the filename as argument.
        if `warning` is given, a warning dialog is opened before the the save 
        file dialog with message given by `warning`.  
        """
        self.IO_callback.append((key_sequence, title, self.openfile_dialog, [title,callback,warning]))
        self.register_key(key_sequence, title, self.savefile_dialog, cb_args=[title,callback,warning])
        
    def _mouse_local_position(self,global_position=None):
        """ Return mouse position in the Viewer frame coordinates 
        
        if global_position is None, use QtGui.QCursor.pos()
        """
        viewer_frame = self.geometry().topLeft()
        p  = self.parent()
        while p:
            viewer_frame += p.geometry().topLeft()
            p  = p.parent()
            
        if global_position is None:
            global_position = QtGui.QCursor.pos()
        return global_position - viewer_frame
        
    def keyPressEvent(self, event):
        """ distribute key event to registered callback """
        modif_int = 0
        modif = event.modifiers()
        ## strange behaviors using directly modifiers with arrow keys... 
        if modif&QtCore.Qt.CTRL:  modif_int += QtCore.Qt.CTRL
        if modif&QtCore.Qt.ALT:   modif_int += QtCore.Qt.ALT
        if modif&QtCore.Qt.SHIFT: modif_int += QtCore.Qt.SHIFT
        if modif&QtCore.Qt.META:  modif_int += QtCore.Qt.META
        key_seq = QtGui.QKeySequence(modif_int|event.key()).toString()
        ##print key_seq, modif_int, event.key(), modif_int|event.key()
        
        desc, callback, args = self.key_callback.get(key_seq, ('',None,[]))
        if callback:                                           
            callback(*args)
        else:
            _QGLViewer.keyPressEvent(self, event)

    def _mouse_button_string(self,event):
        """ contruct "button" string (see mousePressEvent doc) """
        modifiers = event.modifiers()
        
        # if camera mode, switch 'alt' modifiers
        if self.mode==self.Camera:
            modifiers ^= QtCore.Qt.ALT
        
        button = QtGui.QKeySequence(modifiers|QtCore.Qt.Key_A).toString()[:-1]
        if   event.button()==QtCore.Qt.LeftButton:  button += 'Left'
        elif event.button()==QtCore.Qt.RightButton: button += 'Right'
        else:                                       button += 'Middle'
        return button
        
    def mousePressEvent(self,event):
        """ 
        Call TreePresenter mousePressEvent with arguments:
          - button: a string representing all pressed button, such as:
                    'Ctrl+Shift+Right'  (always in this order)
          - position: the mouse position
          - camera: this viewer camera
        """
        button = self._mouse_button_string(event)
        edit_mode = 'Alt' not in button and\
                    not self.background.is_empty() and\
                    not self.tree.is_empty()

        if not edit_mode and 'Right' in button:
            context_items = self.tree.contextEvent(event.pos(),self.camera())
            self.contextMenu(event.globalPos(), context_items)
            processed = True
            
        elif edit_mode:
            print 'mouse pressed:', button
            processed = self.tree.mousePressEvent(button,event.pos(),self.camera())
        else:
            processed = False
            
        if not processed:
            return _QGLViewer.mousePressEvent(self,event)
        
    def mouseDoubleClickEvent(self,event):
        button = self._mouse_button_string(event)
        processed = self.tree.mouseDoubleClickEvent(button,event.pos(),self.camera())
        if not processed:
            return _QGLViewer.mouseDoubleClickEvent(self,event)
        
    def mouseReleaseEvent(self,event):
        """ distribute relase event and  """
        button = self._mouse_button_string(event)
        processed = self.tree.mouseReleaseEvent(button,event.pos(),self.camera())
        if not processed:
            return _QGLViewer.mouseReleaseEvent(self,event)
        
    def setRevolveAroundPoint(self, position):
        """ 
        Set camera to revolve around given `position`
        if `position` is None, set the camera to revolve around scene center
        """
        if position:
            self.camera().setRevolveAroundPoint(_toVec(position))
        else:
            self.camera().setRevolveAroundPoint(self.sceneCenter())
    def contextMenu(self,position, items):
        """ create a context menu at `position` contening `items` 
        
        `items` is a list of either:
           - text(string):  display the text
           - [text,callback]: display the text, and call `callback` when clicked
           - None: to add a separator
        """
        menu = QtGui.QMenu(self)
        for item in items:
            if item is None:
                menu.addSeparator()
            elif isinstance(item, basestring):
                menu.addAction(item)
            else:
                menu.addAction(*item)
                
        # add registered file I/O
        if len(self.IO_callback):
            from functools import partial
            menu.addSeparator()
            for key,desc,cb,args in self.IO_callback:
                menu.addAction(desc+' ('+key+')', partial(cb, *args))
                
        menu.exec_(position)

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
        
        
    
## to move to PointCloudPresenter
#        self.pointMaterial = _pgl.Material(self.theme['Points'],1)
#        self.contractedpointMaterial = _pgl.Material(self.theme['ContractedPoints'],1)
#        
#        self.pointDisplay = True
#        self.contractedpointDisplay = True
#        
#        self.modelRep = None
#        
#        self.points = None if pointfile is None else _pgl.Scene(pointfile)[0].geometry
#        self.contractedpoints = None
#        
#        self.pointsRep = None
#        self.contractedpointsRep = None
#        
#        self.ctrlPoints = None
#        self.ctrlPointPrimitive = None
#        self.ctrlPointsRep = None               
#        
## not sure...
#        self.pointfilter = 0
#        self.pointWidth = 2
#
#        self.pointsKDTree = None
#        
#        # Debug Information
#        self.nodesinfo = None
#        self.nodesinfoRepIndex = {}
        
        

def main():
    """ simple test program """
    qapp = QtGui.QApplication([])
    viewer = TreeEditor()#background=imbg)
    viewer.setWindowTitle("TreeEditor")
    viewer.show()
    qapp.exec_()

if __name__ == '__main__':
    main()
