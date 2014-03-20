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


toVec = lambda v : _qgl.Vec(v.x,v.y,v.z)
toV3  = lambda v : _pgl.Vector3(v.x,v.y,v.z)

# defaults TreeEditor theme:
# --------------------------
# define shape and material to be used for object display
THEME_GREY = { 'BackGround': (20,20,20), 
               'Points' : (180,180,180),
               'ContractedPoints' : (255,0,0),
               'CtrlPoints' : (30,250,30),
               'NewCtrlPoints' : (30,250,250),
               'SelectedCtrlPoints' : (30,250,30),
               'EdgeInf' : (255,255,255),
               'EdgePlus' : (255,255,0),
               '3DModel' : (128,64,0)}
                    
THEME_WHITE = {'BackGround': (255,255,255), 
               'Points' : (180,180,180),
               'ContractedPoints' : (255,0,0),
               'CtrlPoints' : (250,30,30),
               'NewCtrlPoints' : (30,250,250),
               'SelectedCtrlPoints' : (30,250,30),
               'EdgeInf' : (0,0,0),
               'EdgePlus' : (200,200,0),
               '3DModel' : (128,64,0)}

# TreeEditor class
# ----------------
class TreeEditor(_QGLViewer):
    """
    Class that implements a QGLViewer interface for the edition of tree structures
    """
    Camera,View,Edition = range(3)
    _mode_name = {Camera:'Camera', View:'View', Edition:'Edition'}
    
    
    def __init__(self,parent=None, tree=None, background=None, *view_controlers):
        """ create a TreeEditor for `tree`, `background`, and other optional ViewControler """   
        # super __init__
        if parent: _QGLViewer.__init__(self,parent=None)
        else:      _QGLViewer.__init__(self)
                                              
        # defaults
        self.mode  = self.Edition
        self.theme = THEME_GREY#THEME_WHITE
        
        # global translation of the scene  ## to remove or clarify (hack)?
        self.translation = None
        
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

        # attach content to display
        self.set_tree(tree)
        self.set_background(background)
        
        self.vcs = []
        for vc in view_controlers: self.add_viewcontroler(vc)
        

    # add/set content to display
    # --------------------------
    def set_tree(self, tree):
        """ set the TreeVC object to be edited """
        if tree is None:
            tree = _tree.TreeVC()
        tree.register_editor(self)
        self.tree = tree
        
    def set_background(self, background):
        """ set the background view object """
        if background is None: 
            background = _background.UniformBackgroundVC(self.theme['BackGround'])
        background.register_editor(self)
        self.background = background 

    def add_viewcontroler(self,vc):
        """ add optional ViewControler object """
        vc.register_editor(self)
        self.vcs.append(vc)
                     

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
        ##self.setMouseBinding(QtCore.Qt.LeftButton,_QGLViewer.FRAME,_QGLViewer.TRANSLATE)
        self.set_mode(self.Camera)
        ##self.setMouseBindingDescription(QtCore.Qt.ShiftModifier+QtCore.Qt.LeftButton,"Rectangular selection")
        ##self.setMouseBindingDescription(QtCore.Qt.LeftButton,"Camera/Control Points manipulation")
        ##self.setMouseBindingDescription(QtCore.Qt.LeftButton,"When double clicking on a line, create a new line",True)
        
        self.camera().setViewDirection(_qgl.Vec(0,-1,0))
        self.camera().setUpVector(_qgl.Vec(0,0,1))
        
        self.background.__init_gl__()
        
        self.register_key('Space',  self.switch_mode)
        self.register_key('Ctrl+Q', self.close)


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
        self.setMouseBinding(Qt.LeftButton,  QGL.CAMERA, QGL.TRANSLATE if cam_mode else QGL.NO_MOUSE_ACTION)
        self.setMouseBinding(Qt.RightButton, QGL.CAMERA, QGL.ROTATE    if cam_mode else QGL.NO_MOUSE_ACTION)
        self.setMouseBinding(Qt.MidButton,   QGL.CAMERA, QGL.ZOOM      if cam_mode else QGL.NO_MOUSE_ACTION)
        
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
        

    def update_scene_bbox(self, new_content, lookAt=True):
        """
        Update scene boundingbox to contain `new_content`
        
        :Inputs:
          - `new_content`:
                The added content, as a PlantGL Scene or Shape object
          - `lookAt`:
                If is True, move camera to focus on `new_content`
                
        :Output:
            The bounding box of `new_content` 
        """
        # compute bounding box of `new_content`
        bbc = _pgl.BBoxComputer(_pgl.Discretizer())
        bbc.process(new_content)
        
        # update scene bbox and camera center/radius
        if not hasattr(self,'scene_bbox'):
            self.scene_bbox = bbc.boundingbox
        else:
            self.scene_bbox += bbc.boundingbox
        bbx = self.scene_bbox
        cam = self.camera()
        cam.setSceneRadius(_pgl.norm(bbx.lowerLeftCorner-bbx.upperRightCorner))
        cam.setSceneCenter(toVec(bbx.lowerLeftCorner+bbx.upperRightCorner)/2)
        
        if lookAt:
            bb = bbc.boundingbox
            cam.fitBoundingBox(toVec(bb.lowerLeftCorner),toVec(bb.upperRightCorner))
            
        
    ##def look_at(self,obj):#center,radius):
    ##    """ """
    ##    bbc = _pgl.BBoxComputer(_pgl.Discretizer())
    ##    bbc.process(obj)
    ##    bbx = bbc.boundingbox                               
    ##    #self.setSceneCenter(toVec(center))
    ##    #self.setSceneRadius(radius)
        
                                                    
    # rendering
    # ---------
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
        
        # draw ViewControlers
        self.background.draw(self.glrenderer)
        self.tree.draw(self.glrenderer)
        for vc in self.vcs:
            vc.draw(self.glrenderer)
        
        ## to be done by PointsBackgroundVC
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
        for vc in self.vcs:
            vc.fastDraw(self.glrenderer)

    
    # manage mouse and keyboard events
    # --------------------------------
    def register_key(self, key_sequence, callback):
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
                A funtion callable with arguments:
                  - key:    the QtCore.Qt.Key_* value
                  - mouse:  the position of the mouse in the image - as a QtCore.QPoint
                  - camera: the active PyQGLViewer.Camera
        """
        self.key_callback[QtGui.QKeySequence(key_sequence).toString()] = callback
        
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
        key_seq = QtGui.QKeySequence(event.modifiers()|event.key()).toString()
        
        callback = self.key_callback.get(key_seq, None)
        if callback:                                           
            callback(key_seq)#, self._mouse_local_position(), self.camera())
        else:
            _QGLViewer.keyPressEvent(self, event)

    def _mouse_button_string(self,event):
        """ contruct "button" string (see mousePressEvent doc) """
        # remove control from 
        modifiers = event.modifiers()
        
        # if camera mode, switch 'alt' modifiers
        if self.mode==self.Camera:
            modifiers ^= QtCore.Qt.ALT
            
        button = QtGui.QKeySequence(modifiers|QtCore.Qt.Key_A).toString()[:-1]
        button.strip('+')
        if   event.button()==QtCore.Qt.LeftButton:  button += 'Left'
        elif event.button()==QtCore.Qt.RightButton: button += 'Right'
        else:                                       button += 'Middle'
        return button
        
    def mousePressEvent(self,event):
        """ 
        Call TreeVC mousePressEvent with arguments:
          - button: a string representing all pressed button, such as:
                    'Meta+Ctrl+Shift+j'  (always in this order)
          - position: the mouse position
          - camera: this viewer camera
        """
        button = self._mouse_button_string(event)
        print 'mouse pressed:', button
        if 'Alt' in button: # camera
            processed = False
        else:               # view or edition mode
            processed = self.tree.mousePressEvent(button,event.pos(),self.camera())
            
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
        
    ##def revolveAroundScene(self): ## connected ?
    ##    """ set camera RevolveAroundPoint to the scene center """
    ##    self.camera().setRevolveAroundPoint(self.sceneCenter())
    ##    self.showMessage("Revolve around scene center")
        

    # display
    # -------
    def showMessage(self,message,timeout = 0):
        """ display a message """
        self.displayMessage(message,timeout)
        print message
        

    
## to move to TreeVC
#        
## to move to PointCloudVC
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
    import numpy as np
    w,h,d = 64,128,3
    image = np.arange(w*h*3).reshape(w,h,3).astype('uint8')
    imbg = _background.ImageBackgroundVC(image)
    viewer = TreeEditor(background=imbg)
    viewer.setWindowTitle("TreeEditor")
    viewer.show()
    qapp.exec_()

if __name__ == '__main__':
    main()
