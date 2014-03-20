"""
##for now, copy of pointreconstruction.gui.mtgeditor (made independant)

User interface for the edition of tree structures

  * Powered by PlantGL *
"""
# import
# ------
import os
import math

# QT, OpenGL and qglViewer
from openalea.vpltk.qt import QtGui, QtCore # (!) needs to called before any other qt import 

import PyQGLViewer  as qgl
import openalea.plantgl.all as pgl
from PyQGLViewer import QGLViewer
from OpenGL import GL


# mtg
import openalea.mtg.algo as mtgalgo


# local import
from . import io
from .shareddata import get_shared_data

## ----- dependencies to remove -----
from vplants.pointreconstruction._pointreconstruction import ConePerception
from vplants.pointreconstruction._pointreconstruction import eConical
from vplants.pointreconstruction._pointreconstruction import eCluster
## ----------------------------------


## to manage .ui files (from pointreconstruction.gui)
##import compile_ui as cui
##ldir    = os.path.dirname(__file__)
##cui.check_ui_generation(os.path.join(ldir, 'contraction.ui'))
##cui.check_ui_generation(os.path.join(ldir, 'reconstruction.ui'))
##cui.check_ui_generation(os.path.join(ldir, 'radius.ui'))




# mtg "shape" conversion
# ----------------------
# conversion of vector classes  
toVec = lambda v : qgl.Vec(v.x,v.y,v.z)
toV3  = lambda v : pgl.Vector3(v.x,v.y,v.z)


class GLMTGEditor(QGLViewer):

    Edit,Rotate,Selection = range(3)

    def init(self):
        self.setHandlerKeyboardModifiers(QGLViewer.CAMERA, QtCore.Qt.AltModifier)
        self.setHandlerKeyboardModifiers(QGLViewer.FRAME,  QtCore.Qt.NoModifier)
        self.setHandlerKeyboardModifiers(QGLViewer.CAMERA, QtCore.Qt.ControlModifier)
        self.setMouseBinding(QtCore.Qt.LeftButton,QGLViewer.FRAME,QGLViewer.TRANSLATE)
        self.setMouseBindingDescription(QtCore.Qt.ShiftModifier+QtCore.Qt.LeftButton,"Rectangular selection")
        self.setMouseBindingDescription(QtCore.Qt.LeftButton,"Camera/Control Points manipulation")
        self.setMouseBindingDescription(QtCore.Qt.LeftButton,"When double clicking on a line, create a new line",True)
        self.setMode(self.Rotate)
        self.camera().setViewDirection(qgl.Vec(0,-1,0))
        self.camera().setUpVector(qgl.Vec(0,0,1))
        self.setBackgroundColor(QtGui.QColor(255,255,255))
    
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
        GL.glDisable(GL.GL_LIGHTING)
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
            GL.glPushMatrix()
            GL.glLoadIdentity()
            zNear = self.camera().zNear()
            zFar = self.camera().zFar()
            zDelta = (zFar-zNear) / 2
            viewDir = self.camera().viewDirection()
            if self.frontVisibility > 0:
                eq = [0.,0.,-1., -(zNear+  zDelta * self.frontVisibility)]
                GL.glClipPlane(GL.GL_CLIP_PLANE0,eq)
                GL.glEnable(GL.GL_CLIP_PLANE0)
            if self.backVisibility < 1.0:
                eq2 = [0.,0.,1., (zNear+  zDelta * self.backVisibility)]
                GL.glClipPlane(GL.GL_CLIP_PLANE1,eq2)
                GL.glEnable(GL.GL_CLIP_PLANE1)
            
            GL.glPopMatrix()           
        else:
            GL.glDisable(GL.GL_CLIP_PLANE0)
            GL.glDisable(GL.GL_CLIP_PLANE1)
        GL.glDisable(GL.GL_LIGHTING)
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
            
        GL.glEnable(GL.GL_LIGHTING)
        GL.glEnable(GL.GL_BLEND)
        GL.glBlendFunc(GL.GL_SRC_ALPHA,GL.GL_ONE_MINUS_SRC_ALPHA)
        if self.modelDisplay and self.modelRep:
            self.modelRep.apply(self.glrenderer)
            

        if self.conesDisplay and self.cones:
            self.conesRep.apply(self.glrenderer)
        GL.glDisable(GL.GL_BLEND)
        GL.glDisable(GL.GL_LIGHTING)
         
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
        
    def updateMTGView(self):
        pt = self.camera().revolveAroundPoint()
        self.setMTG(self.mtg,self.mtgfile)
        self.camera().setRevolveAroundPoint(pt)
       
    def getCtrlPointSize(self):
        scradius = self.sceneRadius()
        return  scradius/800.
        
    def createCtrlPointRepresentation(self):
        self.ctrlPointsRep = pgl.Scene([ ctrlPoint.representation(self.ctrlPointPrimitive) for ctrlPoint in self.ctrlPoints.itervalues() ])
        self.ctrlPointsRepIndex = dict([( sh.id , i) for i,sh in enumerate(self.ctrlPointsRep) ])
        # self.ctrlPointsRepIndex = {2:0, 3:1, ..., 4362: 4360}

    def save(self):
        if self.mtgfile :
            self.write_mtg(self.mtgfile)
        else:
            self.saveMTG()
        
    
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
            distantpoints = pgl.points_at_distance_from_skeleton(pointset.pointList,nodes, parents, -self.pointfilter,1)
            print len(distantpoints)
            if pointset.colorList:
                return pointset.pointList.subset(distantpoints), pointset.colorList.subset(distantpoints)
            else:
                return pointset.pointList.subset(distantpoints), pointset.colorList
        else :
            return pointset.pointList, pointset.colorList
            
    
    def createPointsRepresentation(self):
        pointList, colorList = self.filter_points(self.points)
        self.pointsRep = pgl.Scene([pgl.Shape(pgl.PointSet(pointList,colorList, width = self.pointWidth), self.pointMaterial)])
    
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
        pointList, colorList = self.filter_points(pgl.PointSet(self.contractedpoints.pointList))
        self.contractedpointsRep = pgl.Scene([pgl.Shape(pgl.PointSet(pointList, width = self.pointWidth), self.contractedpointMaterial)])

    def create3DModelRepresentation(self, translation=None):
        scene = pgl.Scene()
        from vplants.pointreconstruction.mtgdata import MTGData
        mtgdata = MTGData()
        mtgdata.initMTG(self.mtg)
        section= pgl.Polyline2D.Circle(1,30)
        if translation:
            for axe in mtgdata.treeAxes():
                points = [self.mtg.property('position').get(nodeID) for nodeID in axe]
                radius = [(self.mtg.property('radius').get(nodeID), self.mtg.property('radius').get(nodeID)) for nodeID in axe]
                scene += pgl.Shape(pgl.Translated(translation,pgl.Extrusion(pgl.Polyline(points), section, radius)), self.modelMaterial)
            self.modelRep =  scene
            
        else:
            for axe in mtgdata.treeAxes():
                points = [self.mtg.property('position').get(nodeID) for nodeID in axe]
                radius = [(self.mtg.property('radius').get(nodeID), self.mtg.property('radius').get(nodeID)) for nodeID in axe]
                scene += pgl.Shape(pgl.Extrusion(pgl.Polyline(points), section, radius), self.modelMaterial)
                
            self.modelRep = scene
        
    
    def importPoints(self):
        initialname = get_shared_data('pointset')
        fname = QtGui.QFileDialog.getOpenFileName(self, "Open Points file",
                                                initialname,
                                                "Points Files (*.asc;*.xyz;*.pwn;*.pts;*.bgeom);;All Files (*.*)")
        if not fname: return
        fname = str(fname)
        self.readPoints(fname)
        
        
    def readPoints(self,fname):
        sc = pgl.Scene(fname)
        print
        try:
            points = sc[0].geometry.geometry
            self.translation =  sc[0].geometry.translation
            points.pointList.translate(self.translation)
        except AttributeError:
            points = sc[0].geometry
            self.translation =  pgl.Vector3(0,0,0)
        self.setPoints(points)
        
    def setPoints(self,points):
        self.points = points
        if self.points.colorList is None: 
            bbx = pgl.BoundingBox(self.points)
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
        fname = QtGui.QFileDialog.getOpenFileName(self, "Open Points file",
                                                initialname,
                                                "Points Files (*.asc;*.xyz;*.pwn;*.pts;*.bgeom);;All Files (*.*)")
        if not fname: return
        fname = str(fname)
        self.readContractedPoints(fname)
        
        
    def readContractedPoints(self,fname):
        points = pgl.Scene(fname)[0].geometry.geometry
        self.setContractedPoints(points)
        
    def setContractedPoints(self,points):
        self.contractedpoints = points
        self.adjustTo(points)
        self.createContractedPointsRepresentation()
        self.showEntireScene()
        
    def exportContractedPoints(self):
        if self.contractedpointsRep is None:
            QtGui.QMessageBox.warning(self,'data error','No contracted points to save')
        initialname = get_shared_data('contractdata')
        fname = QtGui.QFileDialog.getSaveFileName(self, "Save Points file",
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
        fname = QtGui.QFileDialog.getSaveFileName(self, "Save Geom file",
                                                initialname,
                                                "GEOM Files (*.bgeom;*.geom);;All Files (*.*)")
        if not fname: return
        fname = str(fname)
        self.saveAsGeom(fname)
        
    def saveAsGeom(self,fname):
        sc = pgl.Scene()
        if self.attractorsDisplay and self.attractors:
            #sc += self.attractorsRep
            pointset = pgl.PointSet(self.attractors)
            pointset.width = self.pointWidth
            sc += pgl.Shape(pgl.Translated(self.translation,pgl.PointSet(pointset)), self.attractorsMaterial)
        
        if self.pointDisplay and self.points:
            #sc += self.pointsRep
            sc += pgl.Shape(pgl.Translated(self.translation,pgl.PointSet(self.points.pointList)), self.pointMaterial)
            
        if self.contractedpointDisplay and self.contractedpoints:
            #sc += self.contractedpointsRep
            sc += pgl.Shape(pgl.Translated(self.translation,pgl.PointSet(self.contractedpoints.pointList)), self.contractedpointMaterial)
            
        if self.mtgDisplay and self.mtgrep:
            #sc +=  self.mtgrep
            mtgrep, mtgrepindex  = createMTGRepresentation(self.mtg,self.edgeInfMaterial,self.edgePlusMaterial, translation=self.translation)
            sc += mtgrep
        
        #if self.conesDisplay and self.cones:
        #    sc += self.conesRep
         
        if self.ctrlPointDisplay and self.ctrlPointsRep: pass
            #sc += self.ctrlPointsRep
            #sc += pgl.Scene([ ctrlPoint.representation(self.ctrlPointPrimitive) for ctrlPoint in self.ctrlPoints.itervalues() ])
            
        if self.modelDisplay and self.modelRep:
            sc += self.create3DModelRepresentation(self.translation)
            
        sc.save(fname)
         
    def exportNodeList(self):
        initialname = os.path.dirname(self.mtgfile)+'/'+os.path.basename(self.mtgfile)+'.txt' if self.mtgfile else get_shared_data('mtgdata')
        fname = QtGui.QFileDialog.getSaveFileName(self, "Save Geom file",
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
   
        

    
    def contextMenu(self,pos):
        menu = QtGui.QMenu(self)
        action = menu.addAction("Node "+str(self.selection.id))
        f = QtGui.QFont()
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
        if self.nodesinfo is not None:
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
                self.setHandlerKeyboardModifiers(QGLViewer.CAMERA, QtCore.Qt.AltModifier)
                self.setHandlerKeyboardModifiers(QGLViewer.FRAME,  QtCore.Qt.NoModifier)
                self.setHandlerKeyboardModifiers(QGLViewer.CAMERA, QtCore.Qt.ControlModifier)
            elif mode == self.Rotate :
                self.mode = self.Rotate
                self.setHandlerKeyboardModifiers(QGLViewer.FRAME,  QtCore.Qt.AltModifier)
                self.setHandlerKeyboardModifiers(QGLViewer.CAMERA, QtCore.Qt.NoModifier)
                self.setHandlerKeyboardModifiers(QGLViewer.FRAME,  QtCore.Qt.ControlModifier)
    
    
    def setBranchingPoint(self):
        assert not self.selection is None
        self.createBackup()
        nid = self.selection.id
        self.mtg.property('edge_type')[nid] = '+'
        self.mtg.property('label')[nid] = 'B'
        self.__update_value__(nid)
        self.updateGL()
        
    def stickPosToPoints(self, initpos):
        if not self.pointsRep : return initpos, ()
        if not self.pointsKDTree or len(self.pointsKDTree) != len(self.pointsRep[0].geometry.pointList):
            self.pointsKDTree = pgl.ANNKDTree3(self.pointsRep[0].geometry.pointList)
        
        nbg = self.pointsKDTree.k_closest_points(initpos, 5)
        newposition = pgl.centroid_of_group(self.pointsRep[0].geometry.pointList,nbg)
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
        self.setTempInfoDisplay(pgl.Scene([pgl.Shape(pgl.PointSet(self.pointsRep[0].geometry.pointList.subset(nbg),width = self.pointWidth+2),pgl.Material((255,0,255)))]))
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
        self.setTempInfoDisplay(pgl.Scene([pgl.Shape(pgl.PointSet(self.pointsRep[0].geometry.pointList.subset(nbg),width = self.pointWidth+2),pgl.Material((255,0,255)))]))
        self.showMessage("Stick subtree of "+str(nid)+" to points.")
        self.updateGL()
        
        
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
        fname = QtGui.QFileDialog.getOpenFileName(self, "Open Nodes Information file",
                                                initialname,
                                                "Nodes Info File (*.dbg);;All Files (*.*)")
        if not fname: return
        fname = str(fname)
        self.readNodesInfo(fname)
        
    def readNodesInfo(self, fname):
        nodesinfo = io.readfile(fname)
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
            
        self.ctrlPointsRep = pgl.Scene(s)
                

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
            QtGui.QMessageBox.warning(self,'contracted points','No contracted points loaded OR contracted points view is disable')
            return
        if self.nodesinfo is None:
            QtGui.QMessageBox.warning(self,'Note','No debug information loaded..')
            return 
        
        nid = self.selection.id
        i = self.getNodeInfoIndex(nid)
        self.cleanNodeInfo()
        
        if i:
            self.attractors = self.getAttractors(self.nodesinfo[i].Attractors())
            self.attractorsRep = createAttractorsRepresentation(self.attractors, self.pointWidth, self.attractorsMaterial)
            self.printNodeInfo(i)
        else: QtGui.QMessageBox.warning(self,'Note','No information of this node.')
        
    
    def showConePerception(self):
        assert not self.selection is None
        if self.nodesinfo is None:
            QtGui.QMessageBox.warning(self,'Note','No debug information loaded..')
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

        else: QtGui.QMessageBox.warning(self,'Note','No information of this node.')
        


    def showConeofCreation(self):
        assert not self.selection is None
        if self.nodesinfo is None:
            QtGui.QMessageBox.warning(self,'Note','No debug information loaded..')
            return 
 
        nid = self.selection.id
        pid = self.mtg.parent(nid)
        m = self.getNodeInfoIndex(pid)
        if self.nodesinfo[m].Method() <> eConical: return
        
        i = self.getNodeInfoIndex(nid)
        self.cleanNodeInfo()
        
        if i and m:
            self.cones = [pgl.direction(self.nodesinfo[i].Position() - self.nodesinfo[m].Position())]
            self.conesRep = createConeRepresentation(self.nodesinfo[m].Position(), self.cones, 
                                                     self.nodesinfo[m].Di(), self.nodesinfo[m].ConeAngle(),
                                                     self.coneMaterial)
            self.printNodeInfo(i)
        else: QtGui.QMessageBox.warning(self,'Note','No information of this node.')
    
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
        
        class ContractionDialog(QtGui.QDialog, contraction_ui.Ui_Dialog) :
                def __init__(self, parent=None):
                    QtGui.QDialog.__init__(self, parent)
                    contraction_ui.Ui_Dialog.__init__(self)
                    self.setupUi(self)
                    
     
        cdialog = ContractionDialog(self)
        nbN = 7
        denR = 10
        min_conR = 10
        max_conR = 25
        Rfunc = pgl.NurbsCurve2D([(0,0,1),(0.3,0.3,1),(0.7,0.7,1),(1,1,1)])
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
        if cdialog.exec_() == QtGui.QDialog.Accepted:
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
            QtGui.QMessageBox.warning(self,'points','No point loaded ...')
            return
        
        from vplants.pointreconstruction.contractpoints import PointsContraction
        params = self.getContractParam()
        if not params is None:
            nbN, denR, min_conR, max_conR, Rfunc, geom_system = params
            progress = QtGui.QProgressDialog(self)
            progress.setLabelText('Contraction')
            progress.setWindowModality(QtCore.Qt.WindowModal)
            progress.setMinimumDuration(0)
            
            contraction = PointsContraction(self.points.pointList, nbN, denR, min_conR, max_conR, Rfunc, geom_system)
            contractPoints = contraction.run(progress)
            self.setContractedPoints(pgl.PointSet(contractPoints))
        
        

# ---------------------------- End Contraction ----------------------------------------     



# ------- Reconstruction ---------------------------------------- 

    def getSkeletonParam(self):
        import reconstruction_ui, math
        from vplants.plantgl.gui.curve2deditor import FuncConstraint
        
        class ReconstructionDialog(QtGui.QDialog, reconstruction_ui.Ui_Dialog) :
            def __init__(self, parent=None):
                QtGui.QDialog.__init__(self, parent)
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
        Rfunc = pgl.NurbsCurve2D([(0,0,1),(0.3,0.3,1),(0.7,0.7,1),(1,1,1)])
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
        
        if cdialog.exec_() == QtGui.QDialog.Accepted:
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
            QtGui.QMessageBox.warning(self,'points','No contraction point loaded ...')
            return
        
        from vplants.pointreconstruction.scaskeleton import SCASkeleton
        params = self.getSkeletonParam()
        if not params is None:
            nbN, pcaR, Rfunc, min_D, max_D, Di, Dk, angle, geom_system, delta, denthreshold = params
            progress = QtGui.QProgressDialog(self)
            progress.setLabelText('Reconstruction')
            progress.setWindowModality(QtCore.Qt.WindowModal)
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
        
        class RadiusDialog(QDialog, QtGui.radius_ui.Ui_Dialog) :
            def __init__(self, parent=None):
                QtGui.QDialog.__init__(self, parent)
                radius_ui.Ui_Dialog.__init__(self)
                self.setupUi(self)

        if hasattr(self,'cached_radius_param'):
            nc = self.cached_radius_param
        else:
            nc = pgl.NurbsCurve2D([(0,0,1),(0.3,0.3,1),(0.7,0.7,1),(1,1,1)])
        qfunc = None
        cdialog = RadiusDialog(self)
        cdialog.factorFuncEditor.pointsConstraints = FuncConstraint()
        cdialog.factorFuncEditor.setCurve(nc)
        if cdialog.exec_() == QtGui.QDialog.Accepted:
            if cdialog.correctionBox.isChecked():
                qfunc = cdialog.factorFuncEditor.getCurve()
                self.cached_radius_param = qfunc
            return qfunc
        
        else: return -1
    
    def computeNodesRadius(self):
        if self.points is None:
            QtGui.QMessageBox.warning(self,'points','No point loaded ...')
            return
        if self.mtg is None:
            QtGui.QMessageBox.warning(self,'mtg','No MTG loaded ...')
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
        
        self.ctrlPointsRep = pgl.Scene(s)
        
        print 'finish check'

# ---------------------------- End 3D Model ----------------------------------------     
    
def main():
    qapp = QtGui.QApplication([])
    viewer = GLMTGEditor() #None,get_shared_data('contractdata/puu1_shortr140_n10x140.bgeom'),get_shared_data('mtgdata/puu1_attractors.mtg'))
    viewer.setWindowTitle("MTGEditor")
    viewer.show()
    qapp.exec_()

if __name__ == '__main__':
    main()
