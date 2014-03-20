"""
MTG related component of TreeEditor
"""
import os

from openalea.vpltk.qt import QtGui, QtCore

import PyQGLViewer          as _qgl
import openalea.plantgl.all as _pgl
from OpenGL import GL       as _gl

import openalea.mtg.algo as _mtgalgo

from treeeditor.viewcontroler import AbstractViewControler as _AbstractViewControler        
from treeeditor import io
from treeeditor.tree.view import ControlPointsView as _ControlPointsView
from treeeditor.tree.view import EdgesView         as _EdgesView


# data format conversion
_toV3  = lambda v : _pgl.Vector3(v.x,v.y,v.z)
_toVec = lambda v : _qgl.Vec(v.x,v.y,v.z)

class TreeVC(_AbstractViewControler):
    """
    Default ViewControler for mtg tree structure
    """
    FREE,EDITION,REPARENT = range(3)
    
    def __init__(self, mtg=None, position='position'):
        """ Create the TreeVC object
        
           `mtg` is either a MTG instance or the name of a file to be loaded
        """
        # link to the calling TreeEditor (QGLViewer) object
        self._editor = None
        
        # TreeView object
        self.ctrl_points = _ControlPointsView()
        self.edges = _EdgesView()

        # default attributes
        self.focus = None      # id of the focussed control point (if any) 
        self.selection = None  # id of the selected control point (if any)
        
        self.edit_mode = self.FREE

        # mtg & graphical representations
        self.mtg = None
        self.mtgfile = None
        self.propertyposition = position  ## to move in the MTGModel class?
        
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
                                  'Shift+Del':self.delete_subtree,
                                  'Backspace':self.undo,
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
        _AbstractViewControler.register_editor(self,editor)
        
        # register key event
        for key in self.key_edit_callback.keys():
            self._editor.register_key(key, self.key_edit_event)
        
    # manage user interaction
    # -----------------------
    def key_edit_event(self, key):##, mouse, camera):
        """ distribute key event """
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
            ctrl_point = self.view.get_ctrlpoint_at(position, camera)
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
            ctrl_point = self.view.get_ctrlpoint_at(position, camera)
            if ctrl_point:
                self.set_selection(ctrl_point)
                ##self.contextMenu(event.globalPos())  ## make context menu
                self._editor.updateGL()
                processed = True
                
        return processed
        
    def mouseDoubleClickEvent(self, button, position, camera):
        """ simply select node """
        ctrl_point = self.view.get_ctrlpoint_at(position,camera)
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
        
    def set_selection(self,point):
        """ Set focus to the given control point """
        # remove previous selection
        if self.selection:
            self.selection.selected = False
            self.update_views(self.selection.id)
            
        # select given point
        self.selection = point
        if self.selection:
            point.selected = True
            self.update_ctrlpoint_view(point.id)
            self._editor.camera().setRevolveAroundPoint(_toVec(point.position()))
            self._editor.showMessage('Node %d selected' % self.selection.id)
        else:
            self._editor.camera().setRevolveAroundPoint(self._editor.sceneCenter())
            self._editor.showMessage('Node unselected')

    def unselect(self):
        """ set selection to None"""
        self.set_selection(None)
    def set_focus(self,point):
        """ Set focus to given control point
        
        When a node is set as focussed, the others are not drawn
        """
        if self.focus:
            self.focus.hasFocus = False
            self.ctrl_points.update(self.focus.id)
        self.focus = point
        if self.focus:
            point.hasFocus = True
            self.ctrl_points.update(self.focus.id)
            self.last_focus = self.focus
    def get_selection(self):
        """ return the selected object, or None and print a message"""
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
        ctrlPoint = createCtrlPoint(self.mtg,cid,self.ctrlPointColor,self.propertyposition,self.update_views)
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
        self.update_views(nid)
        for sib in siblings:
            if edge_type[sib] == '<' :
                edge_type[sib] = '+'
                self.mtg.property('label')[sib] = 'B'
                self.update_views(sib)
            
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
        ctrlPoint = createCtrlPoint(self.mtg,cid,self.ctrlPointColor,self.propertyposition,self.update_views)
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
        self.update_views(parent)
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
        self.update_views(nid)
        self._editor.updateGL()
        
        self.edit_mode = self.FREE
        
        return True

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

    def update_views(self,node_id):
        """ 
        Update graphical representation of mtg vertex `node_id`
        or recreate all if `node_id` == 'reset'
        """
        if node_id=='all':
            self.ctrl_points.create(self.model,self.update_views)
            self.edges.create(self.model)
        else:
            self.ctrl_points.update(node_id)
            self.edges.update(node_id)
        
    # opengl draw
    # -----------
    def draw(self, glrenderer):
        """ draw the tree in given `glrenderer` """
        self.edges.draw(glrenderer)
        self.ctrl_points.draw(glrenderer)
            
    def fastDraw(self, glrenderer):
        """ fast (re)draw of the tree in given `glrenderer` """
        
        self.edges.fastdraw(glrenderer)
        self.ctrl_points.fastdraw(glrenderer)

    def revolveAroundSelection(self):
        self._editor.camera().setRevolveAroundPoint(_toVec(self.selection.position()))
        self._editor.showMessage("Revolve around "+str(self.selection.id))
        


        



