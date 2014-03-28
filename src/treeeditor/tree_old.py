"""
MTG related component of TreeEditor
"""
import os

from openalea.vpltk.qt import QtGui, QtCore

import PyQGLViewer          as _qgl
import openalea.plantgl.all as _pgl
from OpenGL import GL       as _gl

if _pgl.PGL_VERSION > 0x20e00:
  from openalea.plantgl.gui.editablectrlpoint import CtrlPoint
else:
  from editablectrlpoint import CtrlPoint

import openalea.mtg.algo as _mtgalgo

from .viewcontroler import ViewControler as _ViewControler        
from . import io


# data format conversion
_toV3  = lambda v : _pgl.Vector3(v.x,v.y,v.z)
_toVec = lambda v : _qgl.Vec(v.x,v.y,v.z)

def convert_to_std_mtg(g):
    """
    Copy `g` and convert property 'position' triplet into XX,YY,ZZ properties
    """
    from copy import deepcopy
    newg = deepcopy(g)
    
    pdic = newg.property('position')
    rdic = newg.property('radius')
    xx = {}
    yy = {}
    zz = {}
    r = {}
                                           
    for i,v in pdic.iteritems():
        xx[i] = v.x
        yy[i] = v.y
        zz[i] = v.z
        r[i]  = rdic[i]
    
    newg.add_property('XX')
    newg.add_property('YY')
    newg.add_property('ZZ')
    newg.add_property('radius')
    newg.property('XX').update(xx)
    newg.property('YY').update(yy)
    newg.property('ZZ').update(zz)
    newg.property('radius').update(r)
    del newg.properties()['position']
    return newg




class TreeVC(_ViewControler):
    """
    Default ViewControler for mtg tree structure
    """
    FREE,EDITION,REPARENT = range(3)
    
    def __init__(self, mtg=None, position='position'):
        """ Create the TreeVC object
        
           `mtg` is either a MTG instance or the name of a file to be loaded
        """
        # backup (undo) system
        self.backupmtg = []
        self.maxbackup = 4

        # default attributes (unset) 
        self.focus = None
        self.selection = None                      
        self.selectionTrigger = None
        
        self._editor = None
        
        # flag for content to display
        self.mtgDisplay       = True
        self.ctrlPointDisplay = True
        self.modelDisplay     = True

        self.edit_mode = self.FREE

        # mtg & graphical representations
        self.mtg = None
        self.mtgfile = None
        self.propertyposition = position  ## to move in the MTGModel class?
        
        self._point_diameter = 5
        self.mtgrep = None
        self.ctrlPointsRep = None
        self.modelRep = None

        # set/load mtg
        if isinstance(mtg,basestring): 
            self.read_mtg(mtg)
        elif mtg is not None:
            self.set_mtg(mtg)
        
        # registered event
        # ----------------
        # keybord edit event
        self.key_edit_callback = {'R':self.revolveAroundSelection,  ##?? 
                                  'N':self.add_child,
                                  'M':self.set_axial_point,
                                  'P':self.begin_reparent_selection,
                                  'E':self.split_edge,
                                  'Del':self.delete_selection,
                                  'Backspace':self.delete_selection,
                                  'Shift+Del':self.delete_subtree,
                                  'Ctrl+Z':self.undo,
                                  
                                  'Esc': self.unselect,
                                  
                                  'Ctrl+O':self.load_mtg_dialog,
                                  'Ctrl+S':self.save_mtg_dialog, 
        
                                  '-':self.dec_point_size,
                                  '+':self.inc_point_size,
                                  '=':self.inc_point_size}
        ##for PointVC
        ##QtCore.Qt.Key_T=self.stickToPoints,
        ##QtCore.Qt.Key_G=self.stickSubtree,
        
        # mouse event
                                 
    
    def register_editor(self, editor):
        """ Attach this view to the given `editor` """
        _ViewControler.register_editor(self,editor)
        
        # display parameters
        self.ctrlPointColor     = self._editor.theme['CtrlPoints']
        self.newCtrlPointColor  = self._editor.theme['NewCtrlPoints']                       
        self.edgeInfMaterial    = _pgl.Material(self._editor.theme['EdgeInf'],1)
        self.edgePlusMaterial   = _pgl.Material(self._editor.theme['EdgePlus'],1)
        self.selectedPointColor = _pgl.Material(self._editor.theme['SelectedCtrlPoints'],1)
        self.modelMaterial      = _pgl.Material(self._editor.theme['3DModel'],1)
        
        
        # register key event
        for key in self.key_edit_callback.keys():
            self._editor.register_key(key, self.key_edit_event)
        
        
        # create graphical representation
        if self.mtg is not None:
            self.create_representations()
        
    # manage user interaction
    # -----------------------
    def key_edit_event(self, key):##, mouse, camera):
        """ distribute key event """
        ##ctrl_point = self.get_ctrlpoint_at(mouse,camera)
        self.key_edit_callback[key]()
    
    def mousePressEvent(self, button, position, camera):
        """ Process mouse press event
            
            Check for eventual operations the user asks: 
            shift start rectangular selection
            else check for which point is selected
        """
        processed = False
        
        if button=='Left':
            # select ctrl_point
            ctrl_point = self.get_ctrlpoint_at(position, camera)
            print 'left click:', ctrl_point.id if ctrl_point else None, position
            
            # (end of) reparent - parent of selected node is set the clicked one
            if self.edit_mode == self.REPARENT:
                processed = self.reparent_selection(ctrl_point)

            # no control point
            elif ctrl_point is None:
                self.set_selection(None)
                self.edit_mode = self.FREE
                self._editor.showMessage('Cannot find a node to select')
                processed = False
                
            # edition of node position
            elif self.edit_mode == self.FREE:
                self.set_selection(ctrl_point)
                self.set_edition_mode(True)
                processed = False ## for QGLViewer to still be called
            
        # context menu
        elif button=='Right':
            self.set_selection(None)
            ctrl_point = self.get_ctrlpoint_at(position, camera)
            if ctrl_point:
                self.set_selection(ctrl_point)
                ##self.contextMenu(event.globalPos())  ## make context menu
                self._editor.updateGL()
                processed = True
                
        return processed
        
    def mouseDoubleClickEvent(self, button, position, camera):
        """ simply select node """
        ctrl_point = self.get_ctrlpoint_at(position,camera)
        self.set_selection(ctrl_point)
        self.set_edition_mode(False)
        return bool(self.selection)

    def mouseReleaseEvent(self, button, position, camera):
        """ stop edition (of node position) mode """
        # clear manipulated object
        self.set_edition_mode(False)
        return False
    
    def set_edition_mode(self, edit=True):
        """ set mode edition if `edit`, or stop it otherwise """
        if edit:
            self.set_focus(self.selection)
            self.edit_mode = self.EDITION
            self.createBackup()
        else:
            self.set_focus(None)
            self.edit_mode = self.FREE
        self._editor.setManipulatedFrame(self.selection)
        
    def get_ctrlpoint_at(self, mouse, camera):
        """ return the control point for mouse selection (or None) """
        possibles = []
        if self.ctrlPoints and self.ctrlPointDisplay:
            for cCtrlPoint in self.ctrlPoints.itervalues():
                cCtrlPoint.checkIfGrabsMouse(mouse.x(), mouse.y(), camera)
                if cCtrlPoint.grabsMouse():
                    pz = camera.viewDirection() * (cCtrlPoint.position()-camera.position()) 
                    z =  (pz - camera.zNear()) /(camera.zFar()-camera.zNear())
                    if 0<z<1:## > 0 and not self.clippigPlaneEnabled or self.frontVisibility <= z*2 <= self.backVisibility:
                        possibles.append((z,cCtrlPoint))
        if len(possibles) > 0:
            possibles.sort(lambda x,y : cmp(x[0],y[0]))
            return possibles[0][1]
        return None
        
    def set_selection(self,point):
        """ Set focus to the given control point """
        # remove previous selection
        if self.selection:
            self.selection.selected = False
            self.__update_ctrlpoint__(self.selection.id)
            
        # select given point
        self.selection = point
        if self.selection:
            point.selected = True
            self.__update_ctrlpoint__(point.id)
            self._editor.camera().setRevolveAroundPoint(_toVec(point.position()))
            self._editor.showMessage('Node %d selected' % self.selection.id)
        else:
            self._editor.camera().setRevolveAroundPoint(self._editor.sceneCenter())
            self._editor.showMessage('Node unselected')

    def unselect(self):
        """ set selection to None"""
        self.set_selection(None)
    ##todo doc reparent selection stuff...   
    def begin_reparent_selection(self):
        """ set reparent edition mode: i.e. wait of new parent selection
        
        If mode is already on reparent, switch to none """
        if self.edit_mode==self.REPARENT:
            self.edit_mode = self.FREE
        else:
            self.edit_mode = self.REPARENT
            self._editor.showMessage("Select Parent")
        return True
        
    def reparent_selection(self,parent_node):
        """ reparent selected node by `parent_node` 
        
        return True if reparenting is done
        """
        if self.edit_mode!=self.REPARENT:
            return False
        
        if not self.get_selection(): return
        self.createBackup()
        nid = self.selection.id
        if parent_node.id in _mtgalgo.descendants(self.mtg,nid):
            QtGui.QMessageBox.warning(self,"Invalid parent",'Cannot reparent a node with one of its descendants')
            return False
        nsons = list(self.mtg.children(parent_node.id))
        ndirectsons = [son for son in nsons if self.mtg.edge_type(son) == '<']
        
        self.mtg.replace_parent(nid,parent_node.id)
        if len(ndirectsons) > 0:
            self.mtg.property('edge_type')[nid] = '+'
            self.mtg.property('label')[nid] = 'B'      ## property label: 'B' ?? 
        else:
            self.mtg.property('edge_type')[nid] = '<'
            self.mtg.property('edge_type')[nid] = 'N'  ## property label: 'N' ?? 
        self._editor.showMessage("New parent selected : "+str(parent_node.id)+".")
        self.__update_repr__(nid)
        self._editor.updateGL()
        
        self.edit_mode = self.FREE
        
        return True

    def get_selection(self):
        """ return the selected object or None and print a message"""
        if not self.selection:
            self._editor.showMessage('no node selected')
        return self.selection
    
    # mtg edition
    # -----------
    def add_child(self):
        """ add child to selected vertex  - key N event """
        if not self.get_selection(): return
        self.createBackup()
        nid = self.selection.id
        self._editor.showMessage("Add child to "+str(nid)+".")
        
        # general values
        positions = self.mtg.property(self.propertyposition)
        for vid,pos in positions.iteritems():
            positions[vid] = _pgl.Vector3(pos) 
        segment_vec = positions[nid]-positions[self.mtg.parent(nid)]
        segment_len = _pgl.norm(segment_vec)
        
        # choose new node position
        # ------------------------
        nbchild = len(list(self.mtg.children(nid)))
        if nbchild == 0:
            npos = positions[nid]+segment_vec
            ##PointVC: npos, nbg = self.stickPosToPoints(npos)
            
        elif nbchild >= 1:
            import math
            # select best (candidate) position with respect to some distance criteria
            ipos = positions[nid]
            view_dir = _toV3(self._editor.camera().viewDirection())
            nbcandidates = 10
            candidates = [ipos + _pgl.Matrix3.axisRotation(view_dir,candidate*2*math.pi/nbcandidates)*segment_vec for candidate in xrange(nbcandidates)]
            ##PointVC: candidates = [self.stickPosToPoints(c)[0] for c in candidates]
            siblings = list(self.mtg.siblings(nid))+list(self.mtg.children(nid))+[self.mtg.parent(nid)]
            siblingpos = [ipos+segment_len*_pgl.direction(positions[sib]-ipos) for sib in siblings]
            
            factor1 = [abs(_pgl.norm(c-ipos) - segment_len) for c in candidates]          # |d(node,candidate) - segment-length|
            factor2 = [sum([_pgl.norm(pos-c) for pos in siblingpos]) for c in candidates] # sum d(node-sibling,candidate)
            max1, max2 = max(factor1), max(factor2)
            
            cmplist = [(i,(factor1[i]/max1)+2*(1-(factor2[i]/max2))) for i in xrange(nbcandidates)]
            cmplist.sort(lambda x,y : cmp(x[1],y[1]))
            npos = candidates[cmplist[0][0]]
            
        # update mtg and mtgrep/index
        # ---------------------------
        if self.mtg.is_leaf(nid):   ## nbChild==0 ?
            cid = self.mtg.add_child(nid,position=npos,edge_type='<',label='N')
            mat = self.edgeInfMaterial
        else:
            cid = self.mtg.add_child(nid,position=npos,edge_type='+',label='B')
            mat = self.edgePlusMaterial
        self.mtgrep += createEdgeRepresentation(nid,cid,positions, mat)
        self.mtgrepindex[cid] = len(self.mtgrep)-1 
        
        # update ctrlPoints and ctrlPointsRep/index
        # -----------------------------------------
        ctrlPoint = createCtrlPoint(self.mtg,cid,self.ctrlPointColor,self.propertyposition,self.__update_repr__)
        self.ctrlPoints[cid] = ctrlPoint
        self.ctrlPointsRep += ctrlPoint.representation(self.ctrlPointPrimitive)
        self.ctrlPointsRepIndex[cid] = len(self.ctrlPointsRep)-1
        self.set_selection(ctrlPoint)
        self._editor.updateGL()

    def set_axial_point(self):                                                         
        """ set selected vertex to be the axial successor of its parent """
        if not self.get_selection(): return
        self.createBackup()
        nid = self.selection.id
        edge_type = self.mtg.property('edge_type')
        edge_type[nid] = '<'
        self.mtg.property('label')[nid] = 'N'  ## what's this label property?
        siblings = self.mtg.siblings(nid)
        self.__update_repr__(nid)
        for sib in siblings:
            if edge_type[sib] == '<' :
                edge_type[sib] = '+'
                self.mtg.property('label')[sib] = 'B'
                self.__update_repr__(sib)
            
        self._editor.updateGL()
                
    def split_edge(self):
        """ add vertex between selected vertex and its parent """
        if not self.get_selection(): return
        self.createBackup()
        nid = self.selection.id
        self._editor.showMessage("Split edge before "+str(nid)+".")
        positions = self.mtg.property(self.propertyposition)
        cposition = positions[nid]
        pposition = positions[self.mtg.parent(nid)]
        newposition = (cposition+pposition)/2
        edge_type = self.mtg.edge_type(nid)
        cid = self.mtg.insert_parent(nid, edge_type = edge_type, position = newposition, label = 'N' if edge_type == '<' else 'B') ##label N&B ??
        self.mtg.property('edge_type')[nid] = '<'        
        ctrlPoint = createCtrlPoint(self.mtg,cid,self.ctrlPointColor,self.propertyposition,self.__update_repr__)
        self.ctrlPoints[cid] = ctrlPoint
        self.ctrlPointsRep += ctrlPoint.representation(self.ctrlPointPrimitive)
        self.ctrlPointsRepIndex[cid] = len(self.ctrlPointsRep)-1
        self.mtgrep += createEdgeRepresentation(nid,cid,positions, self.edgePlusMaterial)
        self.mtgrepindex[cid] = len(self.mtgrep)-1 
        self.set_selection(ctrlPoint)
        self._editor.updateGL()
        
    def delete_selection(self):
        """ delete selected vertex """
        if not self.get_selection(): return
        self.createBackup()
        nid = self.selection.id
        self._editor.showMessage("Remove "+str(nid)+".")
        parent = self.mtg.parent(nid)
        for son in self.mtg.children(nid):
            self.mtg.replace_parent(son,parent)
        self.mtg.remove_vertex(nid)
        
        del self.ctrlPoints[nid]
        del self.ctrlPointsRep[self.ctrlPointsRepIndex[nid]]
        self.ctrlPointsRepIndex = dict([(sh.id,i) for i,sh in enumerate(self.ctrlPointsRep)])
        
        del self.mtgrep[self.mtgrepindex[nid]]
        self.mtgrepindex = dict([(sh.id,i) for i,sh in enumerate(self.mtgrep)])
        
        self.selection = None  # set selection to parent vertex?
        self.focus = None
        self.__update_repr__(parent)
        self._editor.updateGL()
    
                
    def delete_subtree(self):
        """ Delete selected node and all nodes blow (i.e. the subtree)"""
        if not self.get_selection(): return
        self.createBackup()
        nid = self.selection.id
        self._editor.showMessage("Remove subtree rooted in "+str(nid)+".")
        self.selection = None
        self.edit_mode = self.FREE
        self.mtg.remove_tree(nid)
        self.create_representations(update_scene=False) ## too brutal?
    

    # mtg IO
    # ------
    def set_mtg(self,mtg,filename=None):
        """ set the `mtg` of this TreeVC """
        self.selection = None
        self.focus     = None
        self.mtg       = mtg
        self.mtgfile   = filename
        
        if self._editor is not None:
            self.create_representations()

    def load_mtg(self,filename):
        """ load mtg from `filename`, then call `set_mtg` """
        import os.path
        
        self._editor.showMessage("Reading "+repr(filename))
        if os.path.splitext(filename)[1] == '.bmtg':
           mtg = io.readfile(filename)
        else: # .mtg
            stdmtg = io.read_mtg_file(filename)
            mtg = convert_to_std_mtg(stdmtg)
            
        self.set_mtg(mtg,filename)
        
    def save_mtg(self,filename):
        """ Save the mtg in file `filename` """ 
        filename = str(filename)
        import os.path,shutil
        if os.path.exists(filename):
            shutil.copy(filename,filename+'~')
        if os.path.splitext(filename)[1] == '.bmtg':
           io.writefile(filename,self.mtg)
        else: # .mtg
            # readable mtg format from openalea.mtg module
            stdmtg = convert_to_std_mtg(self.mtg)
            io.write_mtg_file(filename, stdmtg, properties=[('XX','REAL'), ('YY','REAL'), ('ZZ','REAL'), ('radius','REAL')])
        self.mtgfile = filename
        self._editor.showMessage("MTG saved in "+filename)
   

    ## make a generic open/save api in TreeEditor
    #  eg: editor.add_open/save_dialog(keySeq,self.load/save_file, 'Open/Save MTG file',self.load/save_dir?,["MTG Files (*.mtg;*.bmtg)"])
    def load_mtg_dialog(self):
        """ select a mtg file with a user dialog window, then call `load_mtg` """
        from openalea.vpltk.qt import QtGui
        
        if self.mtgfile:
            load_dir = os.path.dirname(self.mtgfile)
        else:
            load_dir = io.get_shared_data('mtgdata')
        filename = QtGui.QFileDialog.getOpenFileName(self._editor, "Open MTG file",
                                                load_dir,
                                                "MTG Files (*.mtg;*.bmtg);;All Files (*.*)",
                                                QtGui.QFileDialog.DontUseNativeDialog)
        if not filename: return
        filename = str(filename)
        self.load_mtg(filename)
        
    def save_mtg_dialog(self):
        """ select a mtg file with a user dialog window, then call `save_mtg` """
        if self.mtgfile:
            load_dir = os.path.dirname(self.mtgfile)
        else:
            load_dir = io.get_shared_data('mtgdata')
        filename = QtGui.QFileDialog.getSaveFileName(self._editor, "Save MTG file",
                                                load_dir,
                                                "MTG Files (*.mtg;*.bmtg);;All Files (*.*)",
                                                QtGui.QFileDialog.DontUseNativeDialog)
        if not filename: return
        self.save_mtg(filename)
        
    # graphical representations
    # -------------------------
    # a TreeVC has 3 set of graphical objects to represent:
    #   - the mtg as a line-skeleton    representation stored in 'mtgrep'
    #   - the control point             representation stored in 'ctrlPointsRep'
    #   - the 3d model                  representation stored in 'modelRep'
    def create_representations(self, update_scene=True):
        """ Make PlantGL objects to be drawn """
        self.create_mtg_representation()
        self.create_ctrlpoint_representation()
        
        # update editor
        if update_scene:
            self._editor.update_scene_bbox(lookAT=self.mtgrep)
       
    def create_mtg_representation(self):
        """ create mtgrep and mtgrepindex """
        self.mtgrep, self.mtgrepindex = createMTGRepresentation(self.mtg,
                                                                self.edgeInfMaterial,
                                                                self.edgePlusMaterial)
        
    def create_ctrlpoint_representation(self):
        ## create ctrlPoint in create representation...
        self.ctrlPoints = createCtrlPoints(self.mtg,
                                           self.ctrlPointColor,
                                           self.propertyposition,
                                           self.__update_repr__)
        
        self.ctrlPointPrimitive = _pgl.Scaled(self._point_diameter,_pgl.Sphere(1))
        
        ctrl_repr = [ctrlpt.representation(self.ctrlPointPrimitive) for ctrlpt in self.ctrlPoints.itervalues()]
        self.ctrlPointsRep = _pgl.Scene(ctrl_repr)
        
        self.ctrlPointsRepIndex = dict([(sh.id,i) for i,sh in enumerate(self.ctrlPointsRep)])

    def inc_point_size(self):
        """ scale control point sphere by 25% """
        self._point_diameter *= 1.25
        scale = self.ctrlPointsRep[0].geometry.geometry.scale
        scale[0] = self._point_diameter
        scale[1] = self._point_diameter
        scale[2] = self._point_diameter
        self._editor.updateGL()
    def dec_point_size(self):
        """ scale down control point sphere by 20% """
        self._point_diameter *= 0.8
        scale = self.ctrlPointsRep[0].geometry.geometry.scale
        scale[0] = self._point_diameter
        scale[1] = self._point_diameter
        scale[2] = self._point_diameter
        self._editor.updateGL()

    def __update_repr__(self,pid):
        """ update graphical representation of mtg vertex `pid` """
        self.__update_ctrlpoint__(pid)
        self.__update_edges__(pid)
        
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
    
    # opengl draw
    # -----------
    def draw(self, glrenderer):
        """ draw the tree in given `glrenderer` """
        
        if self.mtgDisplay and self.mtgrep:
            self.mtgrep.apply(glrenderer)
        
        if self.ctrlPointDisplay and self.ctrlPointsRep:
            if self.focus is None:
                self.ctrlPointsRep.apply(glrenderer)
            else:
                scid = self.ctrlPointsRepIndex[self.focus.id]
                self.ctrlPointsRep[scid].apply(glrenderer)
            
        _gl.glEnable(_gl.GL_LIGHTING)
        _gl.glEnable(_gl.GL_BLEND)
        _gl.glBlendFunc(_gl.GL_SRC_ALPHA,_gl.GL_ONE_MINUS_SRC_ALPHA)
        if self.modelDisplay and self.modelRep:
            self.modelRep.apply(glrenderer)
            
    def fastDraw(self, glrenderer):
        """ fast (re)draw of the tree in given `glrenderer` """
        
        if self.mtgDisplay and self.mtgrep:
            self.mtgrep.apply(glrenderer)
        
        if self.ctrlPointDisplay and self.focus:
            scid = self.ctrlPointsRepIndex[self.focus.id]
            self.ctrlPointsRep[scid].apply(glrenderer)

    def revolveAroundSelection(self, camera):
        camera.setRevolveAroundPoint(_toVec(self.selection.position()))
        self._editor.showMessage("Revolve around "+str(self.selection.id))
        


    # backup and undo
    # ---------------
    def createBackup(self):
        """ push a copy of current mtg in undo list (i.e. backup) """ 
        from copy import deepcopy
        if len(self.backupmtg) == self.maxbackup:
            del self.backupmtg[0]
        self.backupmtg.append(deepcopy(self.mtg))
        
        ##self._editor.emit(SIGNAL('undoAvailable(bool)'),True)   ## SIGNAL
        ##self._editor.discardTempInfoDisplay()
        
    def undo(self):
        """ pop last backed up mtg """         
        if len(self.backupmtg) > 0:
            self.mtg = self.backupmtg.pop()
            self._editor.showMessage("Undo to "+repr(self.mtg))
            self.mtgrep, self.mtgrepindex  = createMTGRepresentation(self.mtg,self.edgeInfMaterial,self.edgePlusMaterial)
            self.ctrlPoints = createCtrlPoints(self.mtg,self.ctrlPointColor,self.propertyposition,self.__update_repr__)
            self.createCtrlPointRepresentation()
            self._editor.updateGL()
            ##if len(self.backupmtg) > 0:
            ##    self._editor.emit(SIGNAL('undoAvailable(bool)'),False)   ## SIGNAL
        else:                                        
            self._editor.showMessage("No backup available.")
            ##self.emit(SIGNAL('undoAvailable(bool)'),False)   ## SIGNAL
        


    def set_focus(self,point):
        """ Set focus to given control point
        
        When a node is set as focussed, only this one is drawn
        """
        if self.focus:
            self.focus.hasFocus = False
            self.__update_ctrlpoint__(self.focus.id)
        self.focus = point
        if self.focus:
            point.hasFocus = True
            self.__update_ctrlpoint__(self.focus.id)
            self.last_focus = self.focus
        


# generator of mtg graphical representation
# -----------------------------------------
def createMTGRepresentation(mtg,segment_inf_material,segment_plus_material,translation = None,positionproperty= 'position'):
    scene = _pgl.Scene()
    shindex = {}
    positions = mtg.property(positionproperty)
    i = 0                                                                                        
    r = list(mtg.component_roots_at_scale(mtg.root,scale=mtg.max_scale()))
    def choose_mat(mtg,nid,segment_inf_material,segment_plus_material):
        if mtg.edge_type(nid) == '<': return segment_inf_material
        else : return segment_plus_material
    l = [createEdgeRepresentation(mtg.parent(nodeID),nodeID,positions,choose_mat(mtg,nodeID,segment_inf_material,segment_plus_material),translation) for nodeID in mtg.vertices(scale=mtg.max_scale()) if not nodeID in r]
    scene = _pgl.Scene(l)
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
    res = _pgl.Polyline([positions[begnode], positions[endnode]],width=1)
    #res = _pgl.Group([res,_pgl.Translated((positions[begnode]+positions[endnode])/2,_pgl.Text(str(endnode)))])
    if translation:
        res = _pgl.Translated(translation, res)
    return _pgl.Shape(res,material,endnode)
    

## PlantGL position stored in mtg....
def createCtrlPoints(mtg,color,positionproperty='position',callback = None):
    """ return the set of control point, as a dict (mtg-node-id, ctrl-pt-obj """
    return dict((node,createCtrlPoint(mtg,node,color,positionproperty,callback)) 
                                for node in mtg.vertices(scale=mtg.max_scale()))

def createCtrlPoint(mtg,node_id,color,positionproperty, callback = None):
    """ create a CtrlPoint for node `node_id` of `mtg` """
    ##ccp = CtrlPoint(mtg.property(positionproperty)[node_id], Pos3Setter(mtg.property(positionproperty),node_id),color=color,id=node_id)
    
    pos_setter = CtrlPointPositionSetter(mtg.property(positionproperty),node_id)
    ccp = CtrlPoint(mtg.property(positionproperty)[node_id], pos_setter,color=color,id=node_id)
    if callback: 
        ccp.setCallBack(callback)
    return ccp
    
class CtrlPointPositionSetter:
    """ Used as callback for CtrlPoint objects """
    def __init__(self,ctrlpointset,index):
        self.ctrlpointset = ctrlpointset
        self.index = index
    def __call__(self,pos):
        import inspect
        st = inspect.stack()
        self.ctrlpointset[self.index] = _toV3(pos)
            

