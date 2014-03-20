import os
from math import pi

from openalea.vpltk import qt
from PyQGLViewer import QGLViewer

import PyQGLViewer  as qgl
import openalea.plantgl.all as pgl

toVec = lambda v : qgl.Vec(v.x,v.y,v.z)
toV3  = lambda v : pgl.Vector3(v.x,v.y,v.z)



from PyQt4.QtGui import *
from PyQt4.Qt import *
from PyQGLViewer import *
from OpenGL.GL import *
from openalea.plantgl.all import *

if PGL_VERSION > 0x20e00:
  from openalea.plantgl.gui.editablectrlpoint import *
else:
  from editablectrlpoint import *

from vplants.pointreconstruction.util import *
from vplants.pointreconstruction.shareddata import get_shared_data
from vplants.pointreconstruction._pointreconstruction import *

import openalea.mtg.algo as mtgalgo


## to manage .ui files (from pointreconstruction.gui)
##import compile_ui as cui
##ldir    = os.path.dirname(__file__)
##cui.check_ui_generation(os.path.join(ldir, 'contraction.ui'))
##cui.check_ui_generation(os.path.join(ldir, 'reconstruction.ui'))
##cui.check_ui_generation(os.path.join(ldir, 'radius.ui'))

class Pos3Setter:
    def __init__(self,ctrlpointset,index):
        self.ctrlpointset = ctrlpointset
        self.index = index
    def __call__(self,pos):
        self.ctrlpointset[self.index] = toV3(pos)

def createMTGRepresentation(mtg,segment_inf_material,segment_plus_material,translation = None,positionproperty= 'position'):
    scene = Scene()
    shindex = {}
    positions = mtg.property(positionproperty)
    i = 0
    r = list(mtg.component_roots_at_scale(mtg.root,scale=mtg.max_scale()))
    def choose_mat(mtg,nid,segment_inf_material,segment_plus_material):
        if mtg.edge_type(nid) == '<': return segment_inf_material
        else : return segment_plus_material
    l = [createEdgeRepresentation(mtg.parent(nodeID),nodeID,positions,choose_mat(mtg,nodeID,segment_inf_material,segment_plus_material),translation) for nodeID in mtg.vertices(scale=mtg.max_scale()) if not nodeID in r]
    scene = Scene(l)
    shindex = dict((sh.id,i) for i,sh in enumerate(l))
    # for nodeID in mtg.vertices(scale=2):
        # for son in mtg.children(nodeID):
            # shindex[son] = i
            # scene += createEdgeRepresentation(nodeID,son,positions,segment_material,translation)
            # i+=1
            
    return scene, shindex

def createEdgeRepresentation(begnode,endnode,positions,material, translation = None):
    if begnode is None or endnode is None: 
        print 'Pb with node ', begnode, endnode
        return None
    res = Polyline([positions[begnode], positions[endnode]],width=1)
    #res = Group([res,Translated((positions[begnode]+positions[endnode])/2,Text(str(endnode)))])
    if translation:
        res = Translated(translation, res)
    return Shape(res,material,endnode)
    

def createCtrlPoints(mtg,color,positionproperty = 'position',callback = None):
    ctrlPoints = dict( (nodeID , createCtrlPoint(mtg,nodeID,color,positionproperty,callback)) for nodeID in mtg.vertices(scale=mtg.max_scale()) )
    return ctrlPoints

def createCtrlPoint(mtg,nodeID,color,positionproperty = 'position',callback = None):
    ccp = CtrlPoint(mtg.property(positionproperty)[nodeID], Pos3Setter(mtg.property(positionproperty),nodeID),color=color,id=nodeID)
    if callback: ccp.setCallBack(callback)
    return ccp

def createAttractorsRepresentation(attractors, width, material):
    pointset = PointSet(attractors)
    pointset.width = width
    return Scene([Shape(pointset, material)])


def getConeDirections(u, angle):
    return ConePerception().getConeAxis(u, angle)

def createCone(p1, p2, angle, resolution=20):
    from math import tan
    o = Vector3(p2)
    nz = Vector3(p1) - Vector3(p2)
    h = nz.normalize()
    ny = cross(nz,Vector3.OX)
    if  norm(ny) < 1e-3:
        ny = cross(nz,Vector3.OY)
    ny.normalize()
    nx = cross(ny,nz)
    nx.normalize()
    radius = tan(angle/2)*h
    return Translated(o,Oriented(nx,ny,Cone(radius,h,slices=resolution)))

def createConeRepresentation(p1, axises, height, angle, material):
    p2list = [ p1 + (height*u) for u in axises]
    
    res = Scene()
    for p2 in p2list:
        c = createCone(p1, p2, angle)
        res += Scene([Shape(c, material)])
    
    return res



class GLMTGEditor(QGLViewer):

    Edit,Rotate,Selection = range(3)

    def __init__(self,parent=None,pointfile = None, mtgfile = None):
        if parent:
            QGLViewer.__init__(self,parent=None)
        else:
            QGLViewer.__init__(self)

        self.setStateFileName('.mtgeditor.xml') 
        
        self.mode = self.Edit
        
        # shape and material to display the object
        self.greytheme = {'BackGround': (0,0,0), 
                          'Points' : (180,180,180),
                          'ContractedPoints' : (255,0,0),
                          'CtrlPoints' : (30,250,30),
                          'NewCtrlPoints' : (30,250,250),
                          'SelectedCtrlPoints' : (30,250,30),
                          'EdgeInf' : (255,255,255),
                          'EdgePlus' : (255,255,0),
                          '3DModel' : (128,64,0),
                          'LocalAttractors' :(255, 255, 0),
                          'Cone' :(255,255,0)}
                            
        self.whitetheme = {'BackGround': (255,255,255), 
                          'Points' : (180,180,180),
                          'ContractedPoints' : (255,0,0),
                          'CtrlPoints' : (250,30,30),
                          'NewCtrlPoints' : (30,250,250),
                          'SelectedCtrlPoints' : (30,250,30),
                          'EdgeInf' : (0,0,0),
                          'EdgePlus' : (200,200,0),
                          '3DModel' : (128,64,0),
                          'LocalAttractors' :(255, 255, 0),
                          'Cone' :(255,255,0)}
                            
        self.theme = self.whitetheme
        
        self.pointMaterial = Material(self.theme['Points'],1)
        self.contractedpointMaterial = Material(self.theme['ContractedPoints'],1)
        self.ctrlPointColor = self.theme['CtrlPoints']
        self.newCtrlPointColor = self.theme['NewCtrlPoints']
        self.edgeInfMaterial = Material(self.theme['EdgeInf'],1)
        self.edgePlusMaterial = Material(self.theme['EdgePlus'],1)
        self.selectedPointColor = Material(self.theme['SelectedCtrlPoints'],1)
        self.modelMaterial =  Material(self.theme['3DModel'],1)
        self.pointDisplay = True
        self.contractedpointDisplay = True
        self.mtgDisplay = True
        self.ctrlPointDisplay = True
        self.modelDisplay = True
        self.pointfilter = 0
        self.pointWidth = 2
        
        # plantgl basic object 
        self.discretizer = Discretizer()
        self.glrenderer = GLRenderer(self.discretizer)
        self.glrenderer.renderingMode = GLRenderer.Dynamic
        self.ctrlrenderer=GLCtrlPointRenderer(self.discretizer)
        try:
            self.glrenderer.setGLFrame(self)
        except:
            print 'no text on GL Display'
        
        self.modelRep = None
        
        self.points = None if pointfile is None else Scene(pointfile)[0].geometry
        self.contractedpoints = None
        self.mtgfile = mtgfile
        self.propertyposition = 'position'        
        
        self.pointsRep = None
        self.contractedpointsRep = None
        
        self.pointsKDTree = None
        
        self.mtg  = None        
        self.mtgrep = None
        self.mtgrepindex = None
        
        self.ctrlPoints = None
        self.ctrlPointPrimitive = None
        self.ctrlPointsRep = None
        
        if self.mtgfile : self.readMTG(mtgfile)
        
        self.focus = None
        self.selection = None
        self.selectionTrigger = None
        
        # Debug Information
        self.nodesinfo = None
        self.nodesinfoRepIndex = {}
        
        
        self.attractorsMaterial = Material(self.theme['LocalAttractors'],1)
        self.attractorsDisplay = True
        self.attractors = None
        self.attractorsRep = Scene() 
        
        self.coneMaterial = Material(ambient=self.theme['Cone'], diffuse=1, transparency=0.5)
        self.conesDisplay = True
        self.cones = None
        self.conesRep = Scene()
        
        self.translation = None
        
        self.clippigPlaneEnabled = False        
        self.frontVisibility = 0
        self.backVisibility = 1.0

        self.backupmtg = []
        self.maxbackup = 4
        
        self.temporaryinfo2D = None
        self.temporaryinfo = None
        
    def createBackup(self):
        from copy import deepcopy
        if len(self.backupmtg) == self.maxbackup:
            del self.backupmtg[0]
        self.backupmtg.append(deepcopy(self.mtg))
        self.emit(SIGNAL('undoAvailable(bool)'),True)
        self.discardTempInfoDisplay()
        
    def undo(self):
        if len(self.backupmtg) > 0:
            self.mtg = self.backupmtg.pop()
            self.showMessage("Undo to "+repr(self.mtg))
            self.mtgrep, self.mtgrepindex  = createMTGRepresentation(self.mtg,self.edgeInfMaterial,self.edgePlusMaterial)        
            self.ctrlPoints = createCtrlPoints(self.mtg,self.ctrlPointColor,self.propertyposition,self.__update_value__)
            self.createCtrlPointRepresentation()
            self.updateGL()
            if len(self.backupmtg) > 0:
                self.emit(SIGNAL('undoAvailable(bool)'),False)
        else:
            self.showMessage("No backup available.")
            self.emit(SIGNAL('undoAvailable(bool)'),False)
        
    def enabledClippingPlane(self, enabled):
        self.clippigPlaneEnabled = enabled
        if (enabled) : self.showMessage('Enabled Clipping Plane')
        else: self.showMessage( 'Disabled Clipping Plane')
        if self.isVisible() : self.updateGL()
        
    def setFrontVisibility(self, value):
        self.frontVisibility = (value / 100.)
        if self.isVisible() : self.updateGL()
    
    def setBackVisibility(self, value):
        self.backVisibility = value / 100.
        if self.isVisible() : self.updateGL()
    
    def applySelectionTrigger(self,node):
        if self.selectionTrigger:
            self.selectionTrigger(node)
        self.selectionTrigger = None
    def setSelectionTrigger(self,func):
        self.selectionTrigger = func
        
    def init(self):
        self.setHandlerKeyboardModifiers(QGLViewer.CAMERA, Qt.AltModifier)
        self.setHandlerKeyboardModifiers(QGLViewer.FRAME,  Qt.NoModifier)
        self.setHandlerKeyboardModifiers(QGLViewer.CAMERA, Qt.ControlModifier)
        self.setMouseBinding(Qt.LeftButton,QGLViewer.FRAME,QGLViewer.TRANSLATE)
        self.setMouseBindingDescription(Qt.ShiftModifier+Qt.LeftButton,"Rectangular selection")
        self.setMouseBindingDescription(Qt.LeftButton,"Camera/Control Points manipulation")
        self.setMouseBindingDescription(Qt.LeftButton,"When double clicking on a line, create a new line",True)
        self.setMode(self.Rotate)
        self.camera().setViewDirection(Vec(0,-1,0))
        self.camera().setUpVector(Vec(0,0,1))
        self.setBackgroundColor(QColor(255,255,255))
    
    def setFocus(self,point):
        """ Set focus to given control point """
        if self.focus:
            self.focus.hasFocus = False
            self.__update_ctrlpoint__(self.focus.id)
        self.focus = point
        if self.focus:
            point.hasFocus = True
            self.__update_ctrlpoint__(self.focus.id)
        
    def setSelection(self,point):
        """ Set focus to given control point """
        if self.selection:
            self.selection.selected = False
            self.__update_ctrlpoint__(self.selection.id)
        self.selection = point
        if self.selection:
            point.selected = True
            self.__update_ctrlpoint__(point.id)
            self.camera().setRevolveAroundPoint(toVec(point.position()))

    def fastDraw(self):
        """ paint in opengl """
        glDisable(GL_LIGHTING)
        if self.attractorsDisplay and self.attractors:
            self.attractorsRep.apply(self.glrenderer)
        
        if self.pointDisplay and self.points:
            #self.pointMaterial.apply(self.glrenderer)
            #self.points.apply(self.glrenderer)
            self.pointsRep.apply(self.glrenderer)
            
        if self.contractedpointDisplay and self.contractedpoints:
             self.contractedpointsRep.apply(self.glrenderer)
            
        if self.mtgDisplay and self.mtgrep:
            self.mtgrep.apply(self.glrenderer)

        if self.ctrlPointDisplay and self.focus :
            scid = self.ctrlPointsRepIndex[self.focus.id]
            self.ctrlPointsRep[scid].apply(self.glrenderer)
            
             
    def draw(self):
        """ paint in opengl """
        if self.clippigPlaneEnabled:
            glPushMatrix()
            glLoadIdentity()
            zNear = self.camera().zNear()
            zFar = self.camera().zFar()
            zDelta = (zFar-zNear) / 2
            viewDir = self.camera().viewDirection()
            if self.frontVisibility > 0:
                eq = [0.,0.,-1., -(zNear+  zDelta * self.frontVisibility)]
                glClipPlane(GL_CLIP_PLANE0,eq)
                glEnable(GL_CLIP_PLANE0)
            if self.backVisibility < 1.0:
                eq2 = [0.,0.,1., (zNear+  zDelta * self.backVisibility)]
                glClipPlane(GL_CLIP_PLANE1,eq2)
                glEnable(GL_CLIP_PLANE1)
            
            glPopMatrix()           
        else:
            glDisable(GL_CLIP_PLANE0)
            glDisable(GL_CLIP_PLANE1)
        glDisable(GL_LIGHTING)
        if self.attractorsDisplay and self.attractors:
            self.attractorsRep.apply(self.glrenderer)
         
        if self.pointDisplay and self.points:
            #self.pointMaterial.apply(self.glrenderer)
            #self.points.apply(self.glrenderer)
            self.pointsRep.apply(self.glrenderer)
            
        if self.contractedpointDisplay and self.contractedpoints:
             self.contractedpointsRep.apply(self.glrenderer)
            
        if self.mtgDisplay and self.mtgrep:
            self.mtgrep.apply(self.glrenderer)
        
        if self.ctrlPointDisplay and self.ctrlPointsRep:
            if self.focus is None:
                self.ctrlPointsRep.apply(self.glrenderer)
            else:
                scid = self.ctrlPointsRepIndex[self.focus.id]
                self.ctrlPointsRep[scid].apply(self.glrenderer)
            
        glEnable(GL_LIGHTING)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA,GL_ONE_MINUS_SRC_ALPHA)
        if self.modelDisplay and self.modelRep:
            self.modelRep.apply(self.glrenderer)
            

        if self.conesDisplay and self.cones:
            self.conesRep.apply(self.glrenderer)
        glDisable(GL_BLEND)
        glDisable(GL_LIGHTING)
         
        if self.temporaryinfo2D:
            self.startScreenCoordinatesSystem()
            self.temporaryinfo2D.apply(self.glrenderer)
            self.stopScreenCoordinatesSystem()
            
        if self.temporaryinfo:
            self.temporaryinfo.apply(self.glrenderer)
    
    def setTempInfoDisplay2D(self, sc):
        self.temporaryinfo2D = sc
    
    def setTempInfoDisplay(self, sc):
        self.temporaryinfo = sc
    
    def discardTempInfoDisplay(self):
        self.temporaryinfo2D = None
        self.temporaryinfo = None
        
    
    def setclassicdata(self,dataedit, dataoriginal, pointname = None):
        from os.path import join,exists
        firstname = join(get_shared_data('mtgdata'),'edition', dataedit+'.bmtg')
        if exists(firstname): mtgname = firstname
        else : mtgname = join(get_shared_data('mtgdata'),dataoriginal+'.bmtg')
        self.readMTG(str(mtgname))
        self.mtgfile = firstname
        
        if pointname is None: pointname = dataedit
        pointfname = str(join(get_shared_data('pointset'), pointname+'.bgeom'))
        print pointfname
        self.readPoints(pointfname)

    def puu1(self):
        self.setclassicdata('puu1','puu1_originalref')
        
    def puu3(self):
        self.setclassicdata('puu3','puu3_originalref')
        self.reorient()
        
    def cherry(self):
        self.setclassicdata('cherry','cherry_originalref','cherry_200k')
        
        
    def openMTG(self):
        initialname = os.path.dirname(self.mtgfile) if self.mtgfile else get_shared_data('mtgdata')
        fname = QFileDialog.getOpenFileName(self, "Open MTG file",
                                                initialname,
                                                "MTG Files (*.mtg;*.bmtg);;All Files (*.*)")
        if not fname: return
        fname = str(fname)
        self.readMTG(fname)
        
    def readMTG(self,fname):
        import os.path
        
        self.showMessage("Reading "+repr(fname))
        if os.path.splitext(fname)[1] == '.bmtg':
           mtg = readfile(fname)
        else: # .mtg
            # readable mtg format from openalea.mtg module
            stdmtg = read_mtg_file(fname)
            mtg = convertToMyMTG(stdmtg)
            
        self.setMTG(mtg,fname)
        self.showEntireScene()
        
    def setMTG(self,mtg,fname):
        self.selection = None
        self.focus = None
        self.mtg = mtg
        self.mtgfile = fname
        self.mtgrep, self.mtgrepindex  = createMTGRepresentation(self.mtg,self.edgeInfMaterial,self.edgePlusMaterial)        
        self.adjustTo(self.mtgrep)
        pointsize = self.getCtrlPointSize()
        self.ctrlPointPrimitive = Sphere(pointsize)
        self.ctrlPoints = createCtrlPoints(self.mtg,self.ctrlPointColor,self.propertyposition,self.__update_value__)
        self.createCtrlPointRepresentation()
        print self.mtg.nb_vertices()

    def updateMTGView(self):
        pt = self.camera().revolveAroundPoint()
        self.setMTG(self.mtg,self.mtgfile)
        self.camera().setRevolveAroundPoint(pt)
       
    def getCtrlPointSize(self):
        scradius = self.sceneRadius()
        return  scradius/800.
        
    def createCtrlPointRepresentation(self):
        self.ctrlPointsRep = Scene([ ctrlPoint.representation(self.ctrlPointPrimitive) for ctrlPoint in self.ctrlPoints.itervalues() ])
        self.ctrlPointsRepIndex = dict([( sh.id , i) for i,sh in enumerate(self.ctrlPointsRep) ])
        # self.ctrlPointsRepIndex = {2:0, 3:1, ..., 4362: 4360}

    def save(self):
        if self.mtgfile :
            self.writeMTG(self.mtgfile)
        else:
            self.saveMTG()
        
    def saveMTG(self):
        initialname = os.path.dirname(self.mtgfile) if self.mtgfile else get_shared_data('mtgdata')
        fname = QFileDialog.getSaveFileName(self, "Save MTG file",
                                                initialname,
                                                "MTG Files (*.mtg;*.bmtg);;All Files (*.*)")
        if not fname: return
        fname = str(fname)
        self.writeMTG(fname)
        
    def writeMTG(self,fname):
        fname = str(fname)
        import os.path,shutil
        if os.path.exists(fname):
            shutil.copy(fname,fname+'~')
        if os.path.splitext(fname)[1] == '.bmtg':
           writefile(fname,self.mtg)
        else: # .mtg
            # readable mtg format from openalea.mtg module
            stdmtg = convertToStdMTG(self.mtg)
            writeMTGfile(fname, stdmtg)
        self.mtgfile = fname
        self.showMessage("Write MTG in "+repr(fname))
        self.updateGL()
    
    def filter_points(self, pointset):
        print 'filter points'
        if self.pointfilter > 0 and self.mtg:
            print self.pointfilter
            nodeids = list(self.mtg.vertices(scale=self.mtg.max_scale()))
            pos = self.mtg.property('position')
            nodes = [pos[i] for i in nodeids]
            nonone = lambda x, y : y if x is None else x
            nodeiddict = dict([(vid,i) for i,vid in enumerate(nodeids)])
            parents = [nodeiddict[nonone(self.mtg.parent(i),i)] for i in nodeids]
            distantpoints = points_at_distance_from_skeleton(pointset.pointList,nodes, parents, -self.pointfilter,1)
            print len(distantpoints)
            if pointset.colorList:
                return pointset.pointList.subset(distantpoints), pointset.colorList.subset(distantpoints)
            else:
                return pointset.pointList.subset(distantpoints), pointset.colorList
        else :
            return pointset.pointList, pointset.colorList
            
    
    def createPointsRepresentation(self):
        pointList, colorList = self.filter_points(self.points)
        self.pointsRep = Scene([Shape(PointSet(pointList,colorList, width = self.pointWidth), self.pointMaterial)])
    
    def reorient(self):
        if self.points:
            self.points.pointList.swapCoordinates(1,2)
            if self.pointsRep[0].geometry.pointList.getPglId() != self.points.pointList.getPglId():
               self.pointsRep[0].geometry.pointList.swapCoordinates(1,2)
    
    def setPointFilter(self, value):
        self.pointfilter = self.sceneRadius() * value / 10000.
        self.showMessage("Remove points at a distance "+str(self.pointfilter)+" of the skeleton")
        print self.pointfilter, self.sceneRadius(), value
        if self.points : self.createPointsRepresentation()
        if self.contractedpoints : self.createContractedPointsRepresentation()
        if self.isVisible(): self.updateGL()
        
    def setPointWidth(self, value):
        self.pointWidth = value
        if self.pointsRep:
            self.pointsRep[0].geometry.width = value
        if self.contractedpointsRep:
            self.contractedpointsRep[0].geometry.width = value
        self.showMessage('Set Point Width to '+str(value))
        self.updateGL()
    
    def createContractedPointsRepresentation(self):
        pointList, colorList = self.filter_points(PointSet(self.contractedpoints.pointList))
        self.contractedpointsRep = Scene([Shape(PointSet(pointList, width = self.pointWidth), self.contractedpointMaterial)])

    def create3DModelRepresentation(self, translation=None):
        scene = Scene()
        from vplants.pointreconstruction.mtgdata import MTGData
        mtgdata = MTGData()
        mtgdata.initMTG(self.mtg)
        section= Polyline2D.Circle(1,30)
        if translation:
            for axe in mtgdata.treeAxes():
                points = [self.mtg.property('position').get(nodeID) for nodeID in axe]
                radius = [(self.mtg.property('radius').get(nodeID), self.mtg.property('radius').get(nodeID)) for nodeID in axe]
                scene += Shape(Translated(translation,Extrusion(Polyline(points), section, radius)), self.modelMaterial)
            self.modelRep =  scene
            
        else:
            for axe in mtgdata.treeAxes():
                points = [self.mtg.property('position').get(nodeID) for nodeID in axe]
                radius = [(self.mtg.property('radius').get(nodeID), self.mtg.property('radius').get(nodeID)) for nodeID in axe]
                scene += Shape(Extrusion(Polyline(points), section, radius), self.modelMaterial)
                
            self.modelRep = scene
        
    
    def importPoints(self):
        initialname = get_shared_data('pointset')
        fname = QFileDialog.getOpenFileName(self, "Open Points file",
                                                initialname,
                                                "Points Files (*.asc;*.xyz;*.pwn;*.pts;*.bgeom);;All Files (*.*)")
        if not fname: return
        fname = str(fname)
        self.readPoints(fname)
        
        
    def readPoints(self,fname):
        sc = Scene(fname)
        print
        try:
            points = sc[0].geometry.geometry
            self.translation =  sc[0].geometry.translation
            points.pointList.translate(self.translation)
        except AttributeError:
            points = sc[0].geometry
            self.translation =  Vector3(0,0,0)
        self.setPoints(points)
        
    def setPoints(self,points):
        self.points = points
        if self.points.colorList is None: 
            bbx = BoundingBox(self.points)
            print 'generate color'
            colorList = [(100+int(100*((i.x-bbx.getXMin())/bbx.getXRange())),
                          100+int(100*((i.y-bbx.getYMin())/bbx.getYRange())),
                          100+int(100*((i.z-bbx.getZMin())/bbx.getZRange())),0) for i in self.points.pointList]
            self.points.colorList = colorList
        self.adjustTo(points)
        self.createPointsRepresentation()
        self.showEntireScene()
        
    def importContractedPoints(self):
        initialname = get_shared_data('contractdata')
        fname = QFileDialog.getOpenFileName(self, "Open Points file",
                                                initialname,
                                                "Points Files (*.asc;*.xyz;*.pwn;*.pts;*.bgeom);;All Files (*.*)")
        if not fname: return
        fname = str(fname)
        self.readContractedPoints(fname)
        
        
    def readContractedPoints(self,fname):
        points = Scene(fname)[0].geometry.geometry
        self.setContractedPoints(points)
        
    def setContractedPoints(self,points):
        self.contractedpoints = points
        self.adjustTo(points)
        self.createContractedPointsRepresentation()
        self.showEntireScene()
        
    def exportContractedPoints(self):
        if self.contractedpointsRep is None:
            QMessageBox.warning(self,'data error','No contracted points to save')
        initialname = get_shared_data('contractdata')
        fname = QFileDialog.getSaveFileName(self, "Save Points file",
                                                initialname,
                                                "Points Files (*.asc;*.xyz;*.pwn;*.pts;*.bgeom);;All Files (*.*)")
        if not fname: return
        fname = str(fname)
        self.saveContractedPoints(fname)

    def set3DModel(self):
        self.create3DModelRepresentation()
        self.showEntireScene()
    
    def saveContractedPoints(self,fname):
        self.contractedpointsRep.save(fname)
    
    def exportAsGeom(self):
        initialname = 'out.bgeom'
        fname = QFileDialog.getSaveFileName(self, "Save Geom file",
                                                initialname,
                                                "GEOM Files (*.bgeom;*.geom);;All Files (*.*)")
        if not fname: return
        fname = str(fname)
        self.saveAsGeom(fname)
        
    def saveAsGeom(self,fname):
        sc = Scene()
        if self.attractorsDisplay and self.attractors:
            #sc += self.attractorsRep
            pointset = PointSet(self.attractors)
            pointset.width = self.pointWidth
            sc += Shape(Translated(self.translation,PointSet(pointset)), self.attractorsMaterial)
        
        if self.pointDisplay and self.points:
            #sc += self.pointsRep
            sc += Shape(Translated(self.translation,PointSet(self.points.pointList)), self.pointMaterial)
            
        if self.contractedpointDisplay and self.contractedpoints:
            #sc += self.contractedpointsRep
            sc += Shape(Translated(self.translation,PointSet(self.contractedpoints.pointList)), self.contractedpointMaterial)
            
        if self.mtgDisplay and self.mtgrep:
            #sc +=  self.mtgrep
            mtgrep, mtgrepindex  = createMTGRepresentation(self.mtg,self.edgeInfMaterial,self.edgePlusMaterial, translation=self.translation)
            sc += mtgrep
        
        #if self.conesDisplay and self.cones:
        #    sc += self.conesRep
         
        if self.ctrlPointDisplay and self.ctrlPointsRep: pass
            #sc += self.ctrlPointsRep
            #sc += Scene([ ctrlPoint.representation(self.ctrlPointPrimitive) for ctrlPoint in self.ctrlPoints.itervalues() ])
            
        if self.modelDisplay and self.modelRep:
            sc += self.create3DModelRepresentation(self.translation)
            
        sc.save(fname)
         
    def exportNodeList(self):
        initialname = os.path.dirname(self.mtgfile)+'/'+os.path.basename(self.mtgfile)+'.txt' if self.mtgfile else get_shared_data('mtgdata')
        fname = QFileDialog.getSaveFileName(self, "Save Geom file",
                                                initialname,
                                                "Txt Files (*.txt);;All Files (*.*)")
        if not fname: return
        fname = str(fname)
        self.saveNodeList(fname)
        self.showMessage("Export done ...")
        
    def saveNodeList(self,fname):
        from vplants.pointreconstruction.mtgdata import export_mtg_in_txt
        stream = file(fname,'w')
        export_mtg_in_txt(self.mtg, stream)
        stream.close()
        
    def adjustTo(self,obj):
        d = Discretizer()
        bbc = BBoxComputer(d)
        obj.apply(bbc)
        bbx = bbc.boundingbox
        print type(bbx)
        #print bbx.getSize(), norm(bbx.getSize())
        self.setSceneBoundingBox(toVec(bbx.lowerLeftCorner),toVec(bbx.upperRightCorner))
        print self.sceneRadius()

    def __update_ctrlpoint__(self,pid):
        scid = self.ctrlPointsRepIndex[pid]
        self.ctrlPointsRep[scid] = self.ctrlPoints[pid].representation(self.ctrlPointPrimitive)
        
    def __update_edges__(self,pid):
        eid = self.mtgrepindex.get(pid)
        positions = self.mtg.property(self.propertyposition)
        mat = self.edgeInfMaterial if self.mtg.edge_type(pid) == '<' else self.edgePlusMaterial
        if eid:
            self.mtgrep[eid] = createEdgeRepresentation(self.mtg.parent(pid),pid,positions,mat)
        for son in self.mtg.children(pid):
            mat = self.edgeInfMaterial if self.mtg.edge_type(son) == '<' else self.edgePlusMaterial
            self.mtgrep[self.mtgrepindex[son]] = createEdgeRepresentation(pid,son,positions,mat)
    
    def __update_value__(self,pid):
        """ update rep of mtg """
        self.__update_ctrlpoint__(pid)
        self.__update_edges__(pid)
        
        
    def enablePointDisplay(self,enabled) : 
        if self.pointDisplay != enabled:
            self.pointDisplay = enabled
            self.updateGL()
    def enableContractedPointDisplay(self,enabled) : 
        if self.contractedpointDisplay != enabled:
            self.contractedpointDisplay = enabled
            self.updateGL()
    def enableMTGDisplay(self,enabled) : 
        if self.mtgDisplay != enabled:
            self.mtgDisplay = enabled
            self.updateGL()
    def enableControlPointsDisplay(self,enabled) : 
        if self.ctrlPointDisplay != enabled:
            self.ctrlPointDisplay = enabled
            self.updateGL()
    def enable3DModelDisplay(self,enabled): 
        if self.modelDisplay != enabled:
            self.modelDisplay = enabled
            self.updateGL()
    def isPointDisplayEnabled(self) : return self.pointDisplay
    def isContractedPointDisplayEnabled(self) : return self.contractedpointDisplay
    def isMTGDisplayEnabled(self) : return self.mtgDisplay
    def isControlPointsDisplayEnabled(self) : return self.ctrlPointDisplay
    def is3DModelDisplayEnabled(self): return self.modelDisplay
    
    def adjustView(self):
        self.showEntireScene()
        
    def refreshView(self):
        self.setMTG(self.mtg,self.mtgfile)
   
    def getSelection(self,pos):
        possibles = []
        if self.ctrlPoints and self.ctrlPointDisplay:
            for cCtrlPoint in self.ctrlPoints.itervalues():
                cCtrlPoint.checkIfGrabsMouse(pos.x(), pos.y(), self.camera())
                if cCtrlPoint.grabsMouse():
                    pz = self.camera().viewDirection() * (cCtrlPoint.position()-self.camera().position()) 
                    z =  (pz - self.camera().zNear()) /(self.camera().zFar()-self.camera().zNear())
                    if z > 0 and not self.clippigPlaneEnabled or self.frontVisibility <= z*2 <= self.backVisibility:
                        possibles.append((z,cCtrlPoint))
        if len(possibles) > 0:
            possibles.sort(lambda x,y : cmp(x[0],y[0]))
            return possibles[0][1]
        return None
        
    def keyPressEvent(self, event):
        globalpos = self.geometry().topLeft()
        p  = self.parent()
        while p:
            globalpos += p.geometry().topLeft()
            p  = p.parent()
            
        mousepos = QCursor.pos() - globalpos
        if event.key() == Qt.Key_T:            
            cCtrlPoint = self.getSelection(mousepos)
            if cCtrlPoint:
                self.setSelection(cCtrlPoint)
                self.stickToPoints()
        elif event.key() == Qt.Key_G:            
            cCtrlPoint = self.getSelection(mousepos)
            if cCtrlPoint:
                self.setSelection(cCtrlPoint)
                self.stickSubtree()
        elif event.key() == Qt.Key_R:            
            cCtrlPoint = self.getSelection(mousepos)
            if cCtrlPoint:
                self.setSelection(cCtrlPoint)
                self.revolveAroundSelection()
        elif event.key() == Qt.Key_N:            
            cCtrlPoint = self.getSelection(mousepos)
            if cCtrlPoint:
                self.setSelection(cCtrlPoint)
                self.newChild()
        elif event.key() == Qt.Key_M:            
            cCtrlPoint = self.getSelection(mousepos)
            if cCtrlPoint:
                self.setSelection(cCtrlPoint)
                self.setAxialPoint()
        elif event.key() == Qt.Key_P:            
            cCtrlPoint = self.getSelection(mousepos)
            if cCtrlPoint:
                self.setSelection(cCtrlPoint)
                self.beginReparentSelection()
        elif event.key() == Qt.Key_E:            
            cCtrlPoint = self.getSelection(mousepos)
            if cCtrlPoint:
                self.setSelection(cCtrlPoint)
                self.splitEdge()
        elif event.key() == Qt.Key_Delete:            
            cCtrlPoint = self.getSelection(mousepos)
            if cCtrlPoint:
                self.setSelection(cCtrlPoint)
                self.removeSelection()
        else: QGLViewer.keyPressEvent(self, event)

    def mousePressEvent(self,event):
        """ Check for eventual operations the user asks: 
            shift start rectangular selection
            else check for which point is selected
        """
        nompe = False
        if self.mode == self.Selection:
            # Selection of a second point to finish a previous action
            cCtrlPoint = self.getSelection(event.pos())
            if cCtrlPoint:
                self.applySelectionTrigger(cCtrlPoint)
            else:
                QMessageBox.warning(self,'Selection','Cannot find a node to select')
        elif event.modifiers() & Qt.ControlModifier :
            # only rotation
            self.setSelection(None)
            self.setMode(self.Edit)
        elif event.button() == Qt.RightButton:
            # context menu asked
            self.setSelection(None)
            cCtrlPoint = self.getSelection(event.pos())
            if cCtrlPoint:
                self.setSelection(cCtrlPoint)
                self.updateGL()
                self.contextMenu(event.globalPos())
                nompe = True
            else:
                self.setMode(self.Rotate)
        else:
            # move selection or rotate
            self.setSelection(None)
            cCtrlPoint = self.getSelection(event.pos())
            if cCtrlPoint:
                self.setFocus(cCtrlPoint)
                self.createBackup()
                self.camera().setRevolveAroundPoint(toVec(cCtrlPoint.position()))
                self.setManipulatedFrame(cCtrlPoint)
                self.showMessage("Move point "+str(cCtrlPoint.id))
                # move manipulated frame
                self.setMode(self.Edit)
                self.updateGL()
            else: # if no point is selected, then move camera
                self.setMode(self.Rotate)
        if not nompe :
            QGLViewer.mousePressEvent(self,event)
        
    def mouseDoubleClickEvent(self,event):
        cCtrlPoint = self.getSelection(event.pos())
        if cCtrlPoint:
            print 'Select point ',cCtrlPoint.id
            if self.mode == self.Selection:
                self.applySelectionTrigger(cCtrlPoint)
            else:                
                self.camera().setRevolveAroundPoint(toVec(cCtrlPoint.position()))

    def mouseMoveEvent(self,event):
        """On mouse release, we release every grabbed objects"""
        QGLViewer.mouseMoveEvent(self,event)
        
    def mouseReleaseEvent(self,event):
        """On mouse release, we release every grabbed objects"""
        QGLViewer.mouseReleaseEvent(self,event)
        # clear manipulated object
        self.setManipulatedFrame(None)
        self.setFocus(None)
        self.setMode(self.Rotate)
        self.updateGL()
    
    def contextMenu(self,pos):
        menu = QMenu(self)
        action = menu.addAction("Node "+str(self.selection.id))
        f = QFont()
        f.setBold(True)
        action.setFont(f)
        menu.addSeparator()
        menu.addAction("Remove node (DEL)",self.removeSelection)
        if len(list(self.mtg.children(self.selection.id))) > 0:
            menu.addAction("Remove subtree",self.removeSubtree)
        menu.addSeparator()
        menu.addAction("New child (N)",self.newChild)
        menu.addAction("Reparent (P)",self.beginReparentSelection)
        menu.addAction("Split Edge (E)",self.splitEdge)
        menu.addSeparator()
        menu.addAction("Set Branching Points",self.setBranchingPoint)
        menu.addAction("Set Axial Points (M)",self.setAxialPoint)        
        if self.points:
            menu.addSeparator()
            menu.addAction("S&tick to points (T)",self.stickToPoints)
            menu.addAction("Stick subtree (G)",self.stickSubtree)
        menu.addSeparator()
        menu.addAction("Revolve Around (R)",self.revolveAroundSelection)
        menu.addSeparator()
        menu.addAction("Properties",self.printNodeProperties)
        if not self.nodesinfo is None:
            menu.addSeparator()
            submenu = menu.addMenu('SCA')
            submenu.addAction("Show Attractors",self.showAttractors)
            submenu.addAction("Show Cone of Creation", self.showConeofCreation)
            submenu.addAction("Show Conical Perception",self.showConePerception)
            submenu.addAction("Clean", self.cleanNodeInfo)
        menu.exec_(pos)
        
    def setMode(self,mode):
        if self.mode != mode:
            if mode == self.Edit or mode == self.Selection:
                self.mode = mode
                self.setHandlerKeyboardModifiers(QGLViewer.CAMERA, Qt.AltModifier)
                self.setHandlerKeyboardModifiers(QGLViewer.FRAME,  Qt.NoModifier)
                self.setHandlerKeyboardModifiers(QGLViewer.CAMERA, Qt.ControlModifier)
            elif mode == self.Rotate :
                self.mode = self.Rotate
                self.setHandlerKeyboardModifiers(QGLViewer.FRAME, Qt.AltModifier)
                self.setHandlerKeyboardModifiers(QGLViewer.CAMERA,  Qt.NoModifier)
                self.setHandlerKeyboardModifiers(QGLViewer.FRAME, Qt.ControlModifier)
    
    
    def removeSubtree(self):
        assert not self.selection is None
        self.createBackup()
        nid = self.selection.id
        self.showMessage("Remove subtree rooted in "+str(nid)+". Repaint.")
        self.mtg.remove_tree(nid)
        self.updateMTGView()
    
    def removeSelection(self):
        assert not self.selection is None
        self.createBackup()
        nid = self.selection.id
        self.showMessage("Remove "+str(nid)+".")
        parent = self.mtg.parent(nid)
        for son in self.mtg.children(nid):
            self.mtg.replace_parent(son,parent)
        self.mtg.remove_vertex(nid)
        
        del self.ctrlPoints[nid]
        del self.ctrlPointsRep[self.ctrlPointsRepIndex[nid]]
        self.ctrlPointsRepIndex = dict([(sh.id,i) for i,sh in enumerate(self.ctrlPointsRep)])
        
        del self.mtgrep[self.mtgrepindex[nid]]
        self.mtgrepindex = dict([(sh.id,i) for i,sh in enumerate(self.mtgrep)])
        
        self.selection = None
        self.focus = None
        self.__update_value__(parent)
        self.updateGL()
    
    def newChild(self):
        assert not self.selection is None
        self.createBackup()
        nid = self.selection.id
        self.showMessage("Add child to "+str(nid)+".")
        positions = self.mtg.property(self.propertyposition)
        l = positions[nid]-positions[self.mtg.parent(nid)]
        norml = norm(l)
        nbchild = len(list(self.mtg.children(nid)))
        if nbchild == 0:
            npos = positions[nid]+l
            npos, nbg = self.stickPosToPoints(npos)
        elif nbchild >= 1:
            ipos = positions[nid]
            dirl = direction(l)
            dirView = toV3(self.camera().viewDirection())
            nbcandidates = 10
            candidates = [ipos + Matrix3.axisRotation(dirView,ang*2*pi/nbcandidates)*l for ang in xrange(nbcandidates)]
            ocandidates = candidates
            candidates = [self.stickPosToPoints(c)[0] for c in candidates]
            siblings = list(self.mtg.siblings(nid))+list(self.mtg.children(nid))+[self.mtg.parent(nid)]
            siblingpos = [ipos+norml*direction(positions[sib]-ipos) for sib in siblings]
            # point set at a given distance criteria
            factor1 = [abs(norm(c-ipos) - norml) for c in candidates]
            # distance to other nodes criteria
            factor2 = [sum([norm(pos-c) for pos in siblingpos]) for c in candidates]
            max1, max2 = max(factor1), max(factor2)
            cmplist = [(i,(factor1[i]/max1)+2*(1-(factor2[i]/max2))) for i in xrange(nbcandidates)]
            # self.setTempInfoDisplay(Scene([Shape(PointSet(ocandidates,width = self.pointWidth+2),Material((255,0,255))),
                                    # Shape(PointSet(candidates,width = self.pointWidth+2),Material((255,255,0))),
                                    # Shape(PointSet(siblingpos,width = self.pointWidth+8),Material((255,255,255))),
                                    # Shape(Group([Translated(ocandidates[i],Text(str(int(100*cmplist[i][1])))) for i in xrange(len(candidates))]),Material((255,255,0)))
                                    # ]))
            cmplist.sort(lambda x,y : cmp(x[1],y[1]))
            print cmplist
            npos = candidates[cmplist[0][0]]
            
        if self.mtg.is_leaf(nid):
            cid = self.mtg.add_child(nid,position=npos,edge_type='<',label='N')
        else:
            cid = self.mtg.add_child(nid,position=npos,edge_type='+',label='B')
        
        ctrlPoint = createCtrlPoint(self.mtg,cid,self.ctrlPointColor,self.propertyposition,self.__update_value__)
        self.ctrlPoints[cid] = ctrlPoint
        self.ctrlPointsRep += ctrlPoint.representation(self.ctrlPointPrimitive)
        self.ctrlPointsRepIndex[cid] = len(self.ctrlPointsRep)-1
        self.mtgrep += createEdgeRepresentation(nid,cid,positions, self.edgePlusMaterial)
        self.mtgrepindex[cid] = len(self.mtgrep)-1 
        self.setSelection(ctrlPoint)
        self.updateGL()
        
    def splitEdge(self):
        assert not self.selection is None
        self.createBackup()
        nid = self.selection.id
        self.showMessage("Split edge before "+str(nid)+".")
        positions = self.mtg.property(self.propertyposition)
        cposition = positions[nid]
        pposition = positions[self.mtg.parent(nid)]
        newposition = (cposition+pposition)/2
        edge_type = self.mtg.edge_type(nid)
        cid = self.mtg.insert_parent(nid, edge_type = edge_type, position = newposition, label = 'N' if edge_type == '<' else 'B')
        self.mtg.property('edge_type')[nid] = '<'        
        ctrlPoint = createCtrlPoint(self.mtg,cid,self.ctrlPointColor,self.propertyposition,self.__update_value__)
        self.ctrlPoints[cid] = ctrlPoint
        self.ctrlPointsRep += ctrlPoint.representation(self.ctrlPointPrimitive)
        self.ctrlPointsRepIndex[cid] = len(self.ctrlPointsRep)-1
        self.mtgrep += createEdgeRepresentation(nid,cid,positions, self.edgePlusMaterial)
        self.mtgrepindex[cid] = len(self.mtgrep)-1 
        self.setSelection(ctrlPoint)
        self.updateGL()
        
    def beginReparentSelection(self):    
        self.setSelectionTrigger(self.endReparentSelection)
        self.setMode(self.Selection)
        self.showMessage("Select Parent")
        self.displayMessage("Select Parent",5000)
        
    def endReparentSelection(self,node):
        self.createBackup()
        nid = self.selection.id
        if node.id in mtgalgo.descendants(self.mtg,nid):
            QMessageBox.warning(self,"Invalid parent",'Cannot reparent a node with one of its descendants')
            return
        nsons = list(self.mtg.children(node.id))
        ndirectsons = [son for son in nsons if self.mtg.edge_type(son) == '<']
        
        self.mtg.replace_parent(nid,node.id)
        if len(ndirectsons) > 0:
            self.mtg.property('edge_type')[nid] = '+'
            self.mtg.property('label')[nid] = 'B'
        else:
            self.mtg.property('edge_type')[nid] = '<'
            self.mtg.property('edge_type')[nid] = 'N'
        self.showMessage("Parent selected : "+str(node.id)+".")
        self.__update_value__(nid)
        self.updateGL()
        #self.updateMTGView()
        
    def setBranchingPoint(self):
        assert not self.selection is None
        self.createBackup()
        nid = self.selection.id
        self.mtg.property('edge_type')[nid] = '+'
        self.mtg.property('label')[nid] = 'B'
        self.__update_value__(nid)
        self.updateGL()
        
    def setAxialPoint(self):
        assert not self.selection is None
        self.createBackup()
        nid = self.selection.id
        edge_type = self.mtg.property('edge_type')
        edge_type[nid] = '<'
        self.mtg.property('label')[nid] = 'N'
        siblings = self.mtg.siblings(nid)
        self.__update_value__(nid)
        for sib in siblings:
            if edge_type[sib] == '<' :
                edge_type[sib] = '+'
                self.mtg.property('label')[sib] = 'B'
                self.__update_value__(sib)
            
        self.updateGL()
        
        
    def stickPosToPoints(self, initpos):
        if not self.pointsRep : return initpos, ()
        if not self.pointsKDTree or len(self.pointsKDTree) != len(self.pointsRep[0].geometry.pointList):
            self.pointsKDTree = ANNKDTree3(self.pointsRep[0].geometry.pointList)
        
        nbg = self.pointsKDTree.k_closest_points(initpos, 5)
        newposition = centroid_of_group(self.pointsRep[0].geometry.pointList,nbg)
        return newposition, nbg
        
    def stickNodeToPoints(self, nid):        
        initpos = self.mtg.property(self.propertyposition)[nid]
        newposition, nbg = self.stickPosToPoints(initpos)
        self.ctrlPoints[nid].setPosition ( toVec(newposition) )
        self.__update_value__(nid)
        return nbg
        
    def stickToPoints(self, withupdate = True):
        assert not self.selection is None
        if not self.points: return
        nid = self.selection.id
        
        self.createBackup()
        nbg = self.stickNodeToPoints(nid)
        self.setTempInfoDisplay(Scene([Shape(PointSet(self.pointsRep[0].geometry.pointList.subset(nbg),width = self.pointWidth+2),Material((255,0,255)))]))
        self.showMessage("Stick "+str(nid)+" to points.")
        self.updateGL()
        
    def stickSubtree(self):
        assert not self.selection is None
        if not self.points: return
        nid = self.selection.id
                    
        self.createBackup()
        self.stickNodeToPoints(nid)
        nbg = []
        for ci in mtgalgo.descendants(self.mtg,nid):
            nbg += self.stickNodeToPoints(ci)
        self.setTempInfoDisplay(Scene([Shape(PointSet(self.pointsRep[0].geometry.pointList.subset(nbg),width = self.pointWidth+2),Material((255,0,255)))]))
        self.showMessage("Stick subtree of "+str(nid)+" to points.")
        self.updateGL()
        
    def revolveAroundSelection(self):
        self.camera().setRevolveAroundPoint(toVec(self.selection.position()))
        self.showMessage("Revolve around "+str(self.selection.id))
        
    def revolveAroundScene(self):
        self.camera().setRevolveAroundPoint(self.sceneCenter())
        self.showMessage("Revolve around scene center")
        
    def showMessage(self,message,timeout = 0):
        if 0:##self.statusBar:  # has no attribute 'statusBar'
            self.statusBar.showMessage(message,timeout)
        else:
            self.displayMessage(message,timeout)
        print message
        
    def printNodeProperties(self):
        nid = self.selection.id
        props = [ (name,self.mtg.property(name)[nid]) for name in self.mtg.properties().keys() if self.mtg.property(name).has_key(nid)]
        
        self.showMessage('Node Id :'+str( nid))
        self.displayMessage('Node Id :'+str( nid)+', Parent :'+str(self.mtg.parent(nid))+', Children:'+str(list(self.mtg.children(nid)))+', '+','.join([str(n)+':'+repr(v) for n,v in props]),60000)
        print
        print 'Node Id :', nid
        print 'Parent :', self.mtg.parent(nid)
        print 'Children :', list(self.mtg.children(nid))
        print 'Complex :', self.mtg.complex(nid)
        print 'Components :', list(self.mtg.components(nid))
        print 'Properties :'
        for name,val in props:
            print ' ',repr(name),':',repr(val)
   
# ---------------------------- DEBUG Information ----------------------------------------   

    def openNodesInfo(self):
        if self.nodesinfo:
            self.setNodesInfo()
            return
        
        initialname = get_shared_data('dbg')
        fname = QFileDialog.getOpenFileName(self, "Open Nodes Information file",
                                                initialname,
                                                "Nodes Info File (*.dbg);;All Files (*.*)")
        if not fname: return
        fname = str(fname)
        self.readNodesInfo(fname)
        
    def readNodesInfo(self, fname):
        nodesinfo = readfile(fname)
        self.showMessage("Read "+repr(fname))
        self.setNodesInfo(nodesinfo)
    
    
    def setNodesInfo(self,nodeinfo):
        self.nodesinfo = nodeinfo
        # self.ctrlPoints is dictionary {id: editablectrlpoint}
        #self.ctrlPointsRepIndex = dict([( sh.id , i) for i,sh in enumerate(self.ctrlPointsRep) ])
        self.nodesinfoRepIndex = dict([(n.NodeID() ,i) for i, n in enumerate(self.nodesinfo)])
        s = []
        for ctrlPoint in self.ctrlPoints.itervalues():
            shape = ctrlPoint.representation(self.ctrlPointPrimitive)
            idx = self.getNodeInfoIndex(shape.id)
            method = self.nodesinfo[idx].Method()
            if method == eConical:
                shape.appearance.ambient = (0,255,255) #blue
            elif method == eCluster:
                shape.appearance.ambient = (180,70,255) #violet
                
            s.append(shape)
            
        self.ctrlPointsRep = Scene(s)
                

    def cleanNodeInfo(self):
        self.attractors = None
        self.cones = None
    
    def printNodeInfo(self, i):
        print '------------------------------------------------'
        print 'NodeID : ', self.nodesinfo[i].NodeID()
        print 'Attractors len : ', len(self.nodesinfo[i].Attractors())
        print 'Method : ', self.nodesinfo[i].Method()
        print 'Density : ', self.nodesinfo[i].Density()
        print 'Di : ', self.nodesinfo[i].Di()
        print 'Dk : ', self.nodesinfo[i].Dk()
        print 'ConeAxis : ', self.nodesinfo[i].ConeAxis()
        print 'ConeAngle : ', self.nodesinfo[i].ConeAngle()
        print '------------------------------------------------'
            
    
    def showAttractors(self):
        assert not self.selection is None
        if self.contractedpoints is None or not self.contractedpointDisplay: 
            QMessageBox.warning(self,'contracted points','No contracted points loaded OR contracted points view is disable')
            return
        if self.nodesinfo is None:
            QMessageBox.warning(self,'Note','No debug information loaded..')
            return 
        
        nid = self.selection.id
        i = self.getNodeInfoIndex(nid)
        self.cleanNodeInfo()
        
        if i:
            self.attractors = self.getAttractors(self.nodesinfo[i].Attractors())
            self.attractorsRep = createAttractorsRepresentation(self.attractors, self.pointWidth, self.attractorsMaterial)
            self.printNodeInfo(i)
        else: QMessageBox.warning(self,'Note','No information of this node.')
        
    
    def showConePerception(self):
        assert not self.selection is None
        if self.nodesinfo is None:
            QMessageBox.warning(self,'Note','No debug information loaded..')
            return 
         
        nid = self.selection.id
        i = self.getNodeInfoIndex(nid)
        self.cleanNodeInfo()
        
        if i:
            if self.nodesinfo[i].Method() == eConical:
                self.cones = getConeDirections(self.nodesinfo[i].ConeAxis(), self.nodesinfo[i].ConeAngle())
                self.conesRep = createConeRepresentation(self.nodesinfo[i].Position(), self.cones, 
                                                     self.nodesinfo[i].Di(), self.nodesinfo[i].ConeAngle(),
                                                     self.coneMaterial)
                self.printNodeInfo(i)

        else: QMessageBox.warning(self,'Note','No information of this node.')
        


    def showConeofCreation(self):
        assert not self.selection is None
        if self.nodesinfo is None:
            QMessageBox.warning(self,'Note','No debug information loaded..')
            return 
 
        nid = self.selection.id
        pid = self.mtg.parent(nid)
        m = self.getNodeInfoIndex(pid)
        if self.nodesinfo[m].Method() <> eConical: return
        
        i = self.getNodeInfoIndex(nid)
        self.cleanNodeInfo()
        
        if i and m:
            self.cones = [direction(self.nodesinfo[i].Position() - self.nodesinfo[m].Position())]
            self.conesRep = createConeRepresentation(self.nodesinfo[m].Position(), self.cones, 
                                                     self.nodesinfo[m].Di(), self.nodesinfo[m].ConeAngle(),
                                                     self.coneMaterial)
            self.printNodeInfo(i)
        else: QMessageBox.warning(self,'Note','No information of this node.')
    
    # self.ctrlPointsRepIndex is dictionary
    # {2:0, 3:1, ..., 4362: 4360}
    def getNodeInfoIndex(self, nid):
        if self.nodesinfoRepIndex.has_key(nid):
            return self.nodesinfoRepIndex[nid]
        
        return None
    
    def getAttractors(self, attrs):
        p3list = self.contractedpoints.pointList
        return [p3list[i] for i in attrs]

# ---------------------------- End DEBUG Information ----------------------------------------  


# ------- Contraction ---------------------------------------- 

    def getContractParam(self):
        import contraction_ui
        from vplants.plantgl.gui.curve2deditor import FuncConstraint
        
        class ContractionDialog(QDialog, contraction_ui.Ui_Dialog) :
                def __init__(self, parent=None):
                    QDialog.__init__(self, parent)
                    contraction_ui.Ui_Dialog.__init__(self)
                    self.setupUi(self)
                    
     
        cdialog = ContractionDialog(self)
        nbN = 7
        denR = 10
        min_conR = 10
        max_conR = 25
        Rfunc = NurbsCurve2D([(0,0,1),(0.3,0.3,1),(0.7,0.7,1),(1,1,1)])
        geom_system = True 
        if hasattr(self,'cached_contraction_params'):
             nbN, denR, min_conR, max_conR, Rfunc, geom_system = self.cached_contraction_params
        
        if geom_system:
          cdialog.Z_radioButton.setChecked(True)
        else:
          cdialog.Y_radioButton.setChecked(True)
  
        cdialog.nbNeighborEditor.setValue(nbN)
        cdialog.densityRadiusEditor.setValue(denR)
        cdialog.min_contractRadiusEditor.setValue(min_conR)
        cdialog.max_contractRadiusEditor.setValue(max_conR)
        cdialog.radiusFuncEditor.pointsConstraints = FuncConstraint()
        cdialog.radiusFuncEditor.setCurve(Rfunc)
        if cdialog.exec_() == QDialog.Accepted:
            if cdialog.Y_radioButton.isChecked(): 
                geom_system = False
            elif cdialog.Z_radioButton.isChecked():
                geom_system = True
            nbN = cdialog.nbNeighborEditor.value()
            denR = cdialog.densityRadiusEditor.value()
            min_conR = cdialog.min_contractRadiusEditor.value()
            max_conR = cdialog.max_contractRadiusEditor.value()
            Rfunc = cdialog.radiusFuncEditor.getCurve()
            
            # check values
            # if 
            
            params = nbN, denR, min_conR, max_conR, Rfunc, geom_system
            self.cached_contraction_params = params 
            return params

    
    def contractPoints(self):
        if self.points is None: 
            QMessageBox.warning(self,'points','No point loaded ...')
            return
        
        from vplants.pointreconstruction.contractpoints import PointsContraction
        params = self.getContractParam()
        if not params is None:
            nbN, denR, min_conR, max_conR, Rfunc, geom_system = params
            progress = QProgressDialog(self)
            progress.setLabelText('Contraction')
            progress.setWindowModality(Qt.WindowModal)
            progress.setMinimumDuration(0)
            
            contraction = PointsContraction(self.points.pointList, nbN, denR, min_conR, max_conR, Rfunc, geom_system)
            contractPoints = contraction.run(progress)
            self.setContractedPoints(PointSet(contractPoints))
        
        

# ---------------------------- End Contraction ----------------------------------------     



# ------- Reconstruction ---------------------------------------- 

    def getSkeletonParam(self):
        import reconstruction_ui, math
        from vplants.plantgl.gui.curve2deditor import FuncConstraint
        
        class ReconstructionDialog(QDialog, reconstruction_ui.Ui_Dialog) :
            def __init__(self, parent=None):
                QDialog.__init__(self, parent)
                reconstruction_ui.Ui_Dialog.__init__(self)
                self.setupUi(self)

        nbNeighbor = 15
        pcaRadius = 10
        min_D = 6
        max_D = 8
        Di = 2.0
        Dk = 1.2
        delta = 20
        angleratio = 2
        Rfunc = NurbsCurve2D([(0,0,1),(0.3,0.3,1),(0.7,0.7,1),(1,1,1)])
        geom_system = True 
        if hasattr(self,'cached_reconstruction_params'):
            nbNeighbor, pcaRadius, Rfunc, min_D, max_D, Di, Dk, angleratio, geom_system, delta, denthreshold = self.cached_reconstruction_params
           
        cdialog = ReconstructionDialog(self)
        if geom_system:
          cdialog.Z_radioButton.setChecked(True)
        else:
          cdialog.Y_radioButton.setChecked(True)
        cdialog.nbNeighborEditor.setValue(nbNeighbor)
        cdialog.pcaRadiusEditor.setValue(pcaRadius)
        cdialog.min_DEditor.setValue(min_D)
        cdialog.max_DEditor.setValue(max_D)
        cdialog.DiEditor.setValue(Di)
        cdialog.DkEditor.setValue(Dk)
        cdialog.deltaEditor.setValue(delta)
        cdialog.distanceFuncEditor.pointsConstraints = FuncConstraint()
        cdialog.distanceFuncEditor.setCurve(Rfunc)
        cdialog.angleSlider.setValue(angleratio)
        
        if cdialog.exec_() == QDialog.Accepted:
            if cdialog.Y_radioButton.isChecked(): 
                geom_system = False
            elif cdialog.Z_radioButton.isChecked():
                geom_system = True
            nbNeighbor = cdialog.nbNeighborEditor.value()
            pcaRadius = cdialog.pcaRadiusEditor.value()
            min_D = cdialog.min_DEditor.value()
            max_D = cdialog.max_DEditor.value()
            Di = cdialog.DiEditor.value()
            Dk = cdialog.DkEditor.value()
            angleratio = cdialog.angleSlider.value()
            Rfunc = cdialog.distanceFuncEditor.getCurve()
            delta = cdialog.deltaEditor.value()
            denthreshold = cdialog.methodSlider.value()
            self.cached_reconstruction_params = nbNeighbor, pcaRadius, Rfunc, min_D, max_D, Di, Dk, angleratio, geom_system, delta, denthreshold
            
            angle = math.pi/angleratio
            return nbNeighbor, pcaRadius, Rfunc, min_D, max_D, Di, Dk, angle, geom_system, delta, denthreshold

    
    def createSkeleton(self):
        if self.contractedpoints is None: 
            QMessageBox.warning(self,'points','No contraction point loaded ...')
            return
        
        from vplants.pointreconstruction.scaskeleton import SCASkeleton
        params = self.getSkeletonParam()
        if not params is None:
            nbN, pcaR, Rfunc, min_D, max_D, Di, Dk, angle, geom_system, delta, denthreshold = params
            progress = QProgressDialog(self)
            progress.setLabelText('Reconstruction')
            progress.setWindowModality(Qt.WindowModal)
            progress.setMinimumDuration(0)
            
            skeleton = SCASkeleton(self.contractedpoints.pointList, nbN, pcaR,Rfunc, min_D, max_D, Di, Dk, angle, geom_system, delta, denthreshold)
            mtg, nodesinfo = skeleton.run(progress)
            progress.setRange(0,100)
            progress.setValue(100)
            self.setMTG(mtg,None)
            self.setNodesInfo(nodesinfo)
        

# ---------------------------- End Reconstruction ----------------------------------------     

# ------- 3D Model ---------------------------------------- 
    
    def getRadiusParam(self):
        import radius_ui
        from vplants.plantgl.gui.curve2deditor import FuncConstraint
        
        class RadiusDialog(QDialog, radius_ui.Ui_Dialog) :
            def __init__(self, parent=None):
                QDialog.__init__(self, parent)
                radius_ui.Ui_Dialog.__init__(self)
                self.setupUi(self)

        if hasattr(self,'cached_radius_param'):
            nc = self.cached_radius_param
        else:
            nc = NurbsCurve2D([(0,0,1),(0.3,0.3,1),(0.7,0.7,1),(1,1,1)])
        qfunc = None
        cdialog = RadiusDialog(self)
        cdialog.factorFuncEditor.pointsConstraints = FuncConstraint()
        cdialog.factorFuncEditor.setCurve(nc)
        if cdialog.exec_() == QDialog.Accepted:
            if cdialog.correctionBox.isChecked():
                qfunc = cdialog.factorFuncEditor.getCurve()
                self.cached_radius_param = qfunc
            return qfunc
        
        else: return -1
    
    def computeNodesRadius(self):
        if self.points is None:
            QMessageBox.warning(self,'points','No point loaded ...')
            return
        if self.mtg is None:
            QMessageBox.warning(self,'mtg','No MTG loaded ...')
            return
        
        qfunc = self.getRadiusParam()
        if qfunc == -1: return
        
        from vplants.pointreconstruction.radius import NodesRadius
        nr = NodesRadius(self.mtg, self.points.pointList)    
        self.mtg = nr.computing(qfunc)
        self.set3DModel()
        
    def averageNodesRadius(self):
        from vplants.pointreconstruction.radius import NodesRadius
        nr = NodesRadius(self.mtg, self.points.pointList)    
        self.mtg = nr.averaging()
        self.set3DModel()
    
    
    def filterNodesRadius(self):
        from vplants.pointreconstruction.radius import NodesRadius
        nr = NodesRadius(self.mtg, self.points.pointList)    
        self.mtg = nr.filtering()
        self.set3DModel()
        
    def correct_labelMTG(self):
        print 'Correcting label in MTG..'
        for vtx in self.mtg.vertices(scale=self.mtg.max_scale()):
            if vtx != 2: # root node
                if self.mtg.edge_type(vtx) == '<':
                    self.mtg.property('label')[vtx] = 'N'
                elif self.mtg.edge_type(vtx) == '+':
                    self.mtg.property('label')[vtx] = 'B'
                elif self.mtg.edge_type(vtx) == '':
                    print vtx
                    if self.mtg.label(vtx) == 'N': 
                        self.mtg.property('edge_type')[vtx] = '<'
                    else: self.mtg.property('edge_type')[vtx] = '+'
                    
                child = [c for c in self.mtg.children(vtx)]
                if len(child) == 1:
                    self.mtg.property('edge_type')[child[0]] = '<'
    
    def checkMTG(self):
        self.correct_labelMTG()
        
        error_vtx=[]
        for vtx in self.mtg.vertices(scale=self.mtg.max_scale()):
            if len([i for i in self.mtg.children(vtx) if self.mtg.edge_type(i) == '<']) > 1:
                error_vtx.append(vtx)
        
        if len(error_vtx) != 0:
            print 'Multiple direct sons of some nodes of the MGT : ', error_vtx
                 
        s = []
        for ctrlPoint in self.ctrlPoints.itervalues():
            shape = ctrlPoint.representation(self.ctrlPointPrimitive)
            if shape.id in  error_vtx:
                shape.appearance.ambient = (255,0,0) #blue                
            s.append(shape)
        
        self.ctrlPointsRep = Scene(s)
        
        print 'finish check'

# ---------------------------- End 3D Model ----------------------------------------     
    
def main():
    qapp = QApplication([])
    viewer = GLMTGEditor() #None,get_shared_data('contractdata/puu1_shortr140_n10x140.bgeom'),get_shared_data('mtgdata/puu1_attractors.mtg'))
    viewer.setWindowTitle("MTGEditor")
    viewer.show()
    qapp.exec_()

if __name__ == '__main__':
    main()
