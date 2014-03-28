"""
MTG related component of TreeEditor
"""
import os

from openalea.vpltk.qt import QtGui, QtCore

import openalea.plantgl.all as _pgl

from treeeditor.mvp        import Presenter         as _Presenter        
from treeeditor.tree.model import TreeModel         as _TreeModel
from treeeditor.tree.view  import ControlPointsView as _ControlPointsView
from treeeditor.tree.view  import EdgesView         as _EdgesView


# data format conversion
_toV3  = lambda v : _pgl.Vector3(*v)

class TreePresenter(_Presenter):
    """
    Default Presenter class managing (mtg) tree structure
    """
    FREE,EDITION,REPARENT,DRAW_AXE = range(4)
    
    def __init__(self, tree=None, theme=None):
        """ Create the TreePresenter object
        
           `tree` is either
             - a string of the name of a file storing an mtg (*) 
             - a MTG instance (*)
             - a TreeModel object
             
             (*) with be open/wrapped by a TreeModel object
             
            `theme` passed to views objects (control point and edges)
        See also: `treeeeditor.tree.model.TreeModel documentation`
        """
        # link to the calling TreeEditor (QGLViewer) object
        self._editor = None
        self.set_theme(theme)
        
        # model and views
        self.ctrl_points = _ControlPointsView(theme=self.theme)
        self.edges       = _EdgesView(theme=self.theme)
        _Presenter.__init__(self,[self.ctrl_points,self.edges])
        self.set_model(tree)

        # edition attributes
        self.edit_mode = self.FREE
        self.focus = None      # id of the focussed control point (if any) 
        self.selection = None  # id of the selected control point (if any)


        # registered event
        # ----------------
        # keybord edit event
        self.key_edit_callback = {'N':self.add_child,
                                  'M':self.set_axial_point,
                                  'P':self.begin_reparent_selection,
                                  'E':self.split_edge,
                                  'D': self.draw_axe,
                                  'Del':self.delete_selection,
                                  'Backspace':self.delete_selection,
                                  'Shift+Del':self.delete_subtree,
                                  'Shift+Backspace':self.delete_subtree,
                                  'Ctrl+Z':self.undo,
                                  
                                  'Up':   self.select_parent,
                                  'Down': self.select_successor,
                                  'Esc':  self.unselect,
                                  
                                  'Ctrl+O':self.load_mtg_dialog,
                                  'Ctrl+S':self.save_mtg_dialog, 
        
                                  '-':self.ctrl_points.dec_point_size,
                                  '+':self.ctrl_points.inc_point_size,
                                  '=':self.ctrl_points.inc_point_size}
                                 
    
    def register_editor(self, editor):
        """ Attach this view to the given `editor` """
        _Presenter.register_editor(self,editor)
        self.register_key_event()
        
    def register_key_event(self):
        """ register key event """
        if hasattr(self,'_editor'):
            for key,fct in self.key_edit_callback.iteritems():
                self._editor.register_key(key, fct)
        
            self._editor.bind_openfile_dialog('Ctrl+O','Open mtg file (.mtg or .bmtg)',self.set_model, warning='Current tree will be lost. Continue?')
            self._editor.bind_savefile_dialog('Ctrl+S','Save mtg file (.mtg or .bmtg)',self.save_model)
                    
    def set_model(self, tree):
        """ set the tree model managed by this TreePresenter 
        
        `tree` is either
          - a string of the name of a file storing a mtg 
          - a MTG instance
          - a TreeModel object
        """
        self.selection = None
        
        if not isinstance(tree,_TreeModel):
            if hasattr(self,'model'): 
                model_class = self.model.__class__
            else: 
                model_class = _TreeModel
            self.model = model_class(mtg=tree, presenter=self)
        else:
            tree.set_presenter(self)
            self.model = tree
        
        self.reset_views(update_camera=True)
        
    def save_model(self, filename):
        self.model.save_mtg(filename)

    def set_theme(self, theme):
        """ set given `theme` for the Presenter """
        self.theme = theme
    
    # updating views
    # --------------
    def update_views(self,node_id):
        """ 
        flag relative graphical content for update
        
        node_id is either an integer or a n iterable (list) of integer 
        
        See also: `apply_view_update`
        """
        if isinstance(node_id, int):
            node_ids = [node_id]
        else:
            node_ids = node_id
            
        for node_id in node_ids:
            self._point_to_update.add(node_id)
            self._edges_to_update.add(node_id)
            for child_id in self.model.children(node_id):
                self._edges_to_update.add(child_id)
                
    def reset_views(self, update_camera=False):
        """ Reset all views from model """
        if self.model.mtg is None: ## is_ready(), is_empty...?
            self.ctrl_points.clear()
            self.edges.clear()
        else:
            self.ctrl_points.create(self.model,self.update_views)
            self.edges.create(self.model)
            self.edges.update_boundingbox()
            
        self._point_to_update = set()
        self._edges_to_update = set()
        self._added_view_node = set()
        self._deleted_view_node = set()
        
        if self._editor:
            if update_camera:
                update_camera = self.edges.boundingbox
            self._editor.update_scene_bbox(lookAt=update_camera)

    def delete_view_node(self, node_id):
        """ delete view content related to node_id """
        self._deleted_view_node.add(node_id)
        
    def add_view_node(self, node_id):
        """ add view content related to added node_id """
        self._added_view_node.add(node_id)
        
    def apply_view_update(self):
        """ apply all the required updates since last call """
        if len(self._deleted_view_node):
            self.reset_views()
            return
            
        if len(self._added_view_node):
            self.update_views(self._added_view_node)
            for new_node in self._added_view_node:
                self.ctrl_points.add_point(new_node,self.model,self.update_views)
                self.edges.add_edge(new_node,self.model)
        
        ##if len(self._deleted_view_node):
        ##    self.ctrl_points.delete_points(self._deleted_view_node)
        ##    self.edges.delete_edges(self._deleted_view_node)
        ##    
        ##    self._point_to_update.symmetric_difference_update(self._deleted_view_node)
        ##    self._edges_to_update.symmetric_difference_update(self._deleted_view_node)
        
        for node_id in self._point_to_update:
            self.ctrl_points.update(node_id)
        for node_id in self._edges_to_update:
            self.edges.update(node_id, self.model)
            
        self._point_to_update = set()
        self._edges_to_update = set()
        self._added_view_node = set()
        self._deleted_view_node = set()
        
    # manage user interaction
    # -----------------------
    def mousePressEvent(self, button, position, camera):
        """ Process mouse press event
            
            Check for eventual operations the user asks: 
            shift start rectangular selection
            else check for which point is selected
        """
        processed = False
        self.apply_view_update()
        
        if button=='Left':
            # axe drawing: each click create a child on the z=0 plane
            if self.edit_mode == self.DRAW_AXE:
                # compute position of ray projected on z=0 plane 
                self.draw_segment(position, camera)
                return True
                
            # find ctrl_point clicked by mouse
            ctrl_point = self.get_ctrl_point_at(position, camera)
            
            # (end of) reparent - parent of selected node is set the clicked one
            if self.edit_mode == self.REPARENT:
                processed = self.reparent_selection(ctrl_point)

            # no control point
            elif ctrl_point is None:
                self.set_selection(None)
                self.edit_mode = self.FREE
                
            # edition of node position
            elif self.edit_mode == self.FREE:
                self.set_selection(ctrl_point)
                self.set_edition_mode(True)
                processed = False ## for QGLViewer to still be called
            
        # context menu
        elif button=='Right':
            ctrl_point = self.get_ctrl_point_at(position, camera)
            if ctrl_point:
                self.set_selection(ctrl_point)
                ##self.contextMenu(event.globalPos())  ## make context menu
                ##self._editor.updateGL()
                processed = True
                
        return processed
        
    def mouseDoubleClickEvent(self, button, position, camera):
        """ simply select node """
        self.apply_view_update()
        ctrl_point = self.get_ctrl_point_at(position,camera)
        self.set_selection(ctrl_point)
        self.set_edition_mode(False)
        return bool(self.selection)

    def mouseReleaseEvent(self, button, position, camera):
        """ stop edition (of node position) mode """
        # clear manipulated object
        if self.edit_mode!=self.DRAW_AXE:
            self.set_edition_mode(False)
        return False
    
    def set_edition_mode(self, edit=True):
        """ set mode edition if `edit`, or stop it otherwise """
        if edit:
            self.edit_mode = self.EDITION
            self.push_backup()
            self.ctrl_points.set_focus(self.selection)
            self._editor.setManipulatedFrame(self.selection)
        else:
            self.edit_mode = self.FREE
            self.ctrl_points.set_focus(None)
            self._editor.setManipulatedFrame(None)
        
    def set_selection(self,point=None, model_id=None):
        """ Set focus to the given control point """
        # remove previous selection
        if self.selection:
            self.selection.selected = False
            self.ctrl_points.update(self.selection.id)
            
        # select given point
        self.apply_view_update() # only if required?
        if point is None and model_id is not None:
            point = self.ctrl_points.get_point(model_id)
            
        self.selection = point
        if self.selection:
            self.selection.selected = True
            self.ctrl_points.update(self.selection.id)
            self._editor.setRevolveAroundPoint(self.selection.position())
            self.show_message('Node %d selected' % self.selection.id)
            self.ctrl_points.set_focus(None)
            self._editor.setRevolveAroundPoint(None)

        self._editor.updateGL()
        
    def unselect(self):
        """ set selection to None"""
        self.set_selection(None)
    def get_selection(self):
        """ return the selected object, or None and print a message"""
        if not self.selection:
            self.show_message('no node selected')
        return self.selection
    
    def select_parent(self):
        """ select parent of current selection """
        selection = self.get_selection()
        if not selection or self.edit_mode!=self.FREE: return
        parent_id = self.model.parent(selection.id)
        if parent_id:
            parent_pt = self.ctrl_points.get_point(parent_id)
            self.set_selection(parent_pt)
            self.show_message('Parent vertex selected: %d' % parent_id)
        else:
            self.show_message('Select vertex has no parent')
        
    def select_successor(self):
        """ select successor ('<' child') of current selection """
        selection = self.get_selection()
        if not selection or self.edit_mode!=self.FREE: return
        successor_id = self.model.successor(selection.id)
        if successor_id:
            successor_pt = self.ctrl_points.get_point(successor_id)
            self.set_selection(successor_pt)
            self.show_message('Successor vertex selected: %d' % successor_id)
        else:
            self.show_message('Select vertex has no successor')

    def get_ctrl_point_at(self, mouse, camera):
        """ Return the control point selected by mouse """
        eye, ray_dir = camera.convertClickToLine(mouse)
        ## clippigPlaneEnabled or frontVisibility <= z*2 <= self.backVisibility
        return self.ctrl_points.point_at(eye,ray_dir, camera.zNear(), camera.zFar)

    # mtg edition
    # -----------
    def add_child(self):
        """ add child to selected vertex  - key N event """
        if not self.get_selection(): return
        self.push_backup()
        
        # general variables/fct
        node_id = self.selection.id
        parent_id = self.model.parent(node_id)
        position = lambda nid: _toV3(self.model.get_position(nid))
        
        node_pos = position(node_id)
        if parent_id: segment_vec = node_pos-position(parent_id)
        else:         segment_vec = _toV3((0,2*self.theme['point_diameter'],0))
        segment_len = _pgl.norm(segment_vec)
        
        # choose new node position
        # ------------------------
        children = self.model.children(node_id)
        nbchild = len(children)
        if nbchild == 0:
            child_pos = position(node_id)+segment_vec
            ##PointVC: npos, nbg = self.stickPosToPoints(npos)
            
        elif nbchild >= 1:
            import math
            # select best (candidate) position with respect to some distance criteria
            view_dir = _toV3(self._editor.camera().viewDirection())
            
            # select candidate position for child
            nbcandidates = 10
            candidates = [node_pos + _pgl.Matrix3.axisRotation(view_dir,candidate*2*math.pi/nbcandidates)*segment_vec for candidate in xrange(nbcandidates)]
            ##PointVC: candidates = [self.stickPosToPoints(c)[0] for c in candidates]
            
            # find all neighboring nodes
            neighbors = list(self.model.siblings(node_id))+list(children)
            if parent_id:
                neighbors.append(parent_id)
            nbor_pos = [node_pos+segment_len*_pgl.direction(position(nbor)-node_pos) for nbor in neighbors]
            
            # select best candidates from distances to all neighbors
            factor1 = [abs(_pgl.norm(c-node_pos) - segment_len) for c in candidates]
            factor2 = [sum([_pgl.norm(pos-c) for pos in nbor_pos]) for c in candidates]
            max1, max2 = max(factor1), max(factor2)
            
            cmplist = [(i,(factor1[i]/max1)+2*(1-(factor2[i]/max2))) for i in xrange(nbcandidates)]
            cmplist.sort(lambda x,y : cmp(x[1],y[1]))
            child_pos = candidates[cmplist[0][0]]
            
        # update model
        # ------------
        if nbchild==0: new_child_id, up = self.model.add_successor(node_id,position=child_pos)
        else:          new_child_id, up = self.model.add_branching(node_id,position=child_pos)

        # update views
        # ------------
        self.add_view_node(new_child_id)
        self.update_views(up)
            
        # update self
        self.set_selection(model_id = new_child_id)#self.ctrl_points.get_point(new_child_id))
        self.show_message("Child ("+str(new_child_id)+") added to node "+str(node_id)+".")

    def delete_selection(self):
        """ delete selected vertex """
        if not self.get_selection(): return
        self.push_backup()
        node_id   = self.selection.id
        parent_id = self.model.parent(node_id)
        
        # edit mtg model
        up = self.model.remove_vertex(node_id)
        
        # edit views
        self.delete_view_node(node_id)
        self.update_views(up)
        
        # update selections
        self.selection = None  # should not call set_selection (?)
        if parent_id:
            self.set_selection(self.ctrl_points.get_point(parent_id))
        self.show_message("vertex "+str(node_id)+" removed.")
                
    def set_axial_point(self):
        """ set selected vertex to be the axial successor of its parent """
        if not self.get_selection(): return
        self.push_backup()
        node_id = self.selection.id
        parent_id = self.model.parent(node_id)
        
        # edit mtg model
        up = self.model.replace_parent(node_id,parent_id,edge_type='<')
        
        # edit views
        self.update_views(up)
        self.show_message("set "+str(node_id)+" as its parent axial child")
                
    def split_edge(self):
        """ add vertex between selected vertex and its parent """
        if not self.get_selection(): return
        self.push_backup()
        vertex_id = self.selection.id
        parent_id = self.model.parent(vertex_id)
        vertex_pos = self.model.get_position(vertex_id)
        parent_pos = self.model.get_position(parent_id)
        
        # create new vertex in model
        new_position = map(lambda x: (x[0]+x[1])/2, zip(vertex_pos,parent_pos))
        new_id, up = self.model.insert_parent(vertex_id, position=new_position)
        
        # update views
        self.add_view_node(new_id)
        self.update_views(up)
            
        # update self
        self.set_selection(self.ctrl_points.get_point(new_id))
        
    def delete_subtree(self):
        """ Delete selected node and all nodes blow (i.e. the subtree)"""
        if not self.get_selection(): return
        self.push_backup()
        node_id = self.selection.id
        self.set_selection(None)
        
        removed = self.model.remove_tree(node_id)
        for node in removed:
            self.delete_view_node(node)
        self.show_message("subtree rooted in "+str(node_id)+"Removed.")
                                        

    def draw_axe(self):
        """ set reparent edition mode: i.e. wait of new parent selection
        
        If mode is already on reparent, switch to none """
        if self.edit_mode==self.DRAW_AXE:
            self.edit_mode = self.FREE
            self.show_message("Stop axe drawing")
        elif self.get_selection():
            self.edit_mode = self.DRAW_AXE
            self.show_message("Draw axe")
        return True
        
    def draw_segment(self, position, camera):
        """ add a segment at mouse click
        
        Currently, the position is the intersection of the line generated by 
        mouse click (contructed using mouse `position` and `camera`) with the
        z=0 plane.
        
        The new tree node is added as the child of the current selection, as a 
        successor if the selected node has no successor, or as a branch 
        otherwise.
        
        
        TODO1: create a "start" segment if selection is None
        
        TODO2: intersection with the view-plane (perpendicular to camera dir)
        positioned at the same view-depth as the selection point.
        
        TODO3: TODO1 with TODO2, what view-depth should to use?
               the plane intersecting (0,0,0)?
        """
        selection = self.get_selection()
        if not selection: return
        self.push_backup()

        # get position on z=0 plane
        eye, ray_dir = camera.convertClickToLine(position)
        alpha = -eye.z/ray_dir.z
        x,y,z = map(lambda x: x[0]+alpha*x[1], zip(eye,ray_dir))

        node_id = selection.id
        children = self.model.children(node_id)
        nbchild = len(children)
        if nbchild==0: new_child_id, up = self.model.add_successor(node_id,position=_toV3((x,y,0)))
        else:          new_child_id, up = self.model.add_branching(node_id,position=_toV3((x,y,0)))

        # update views
        # ------------
        self.add_view_node(new_child_id)
        self.update_views(up)
            
        # update self
        self.set_selection(model_id=new_child_id)
        
    def begin_reparent_selection(self):
        """ set reparent edition mode: i.e. wait of new parent selection
        
        If mode is already on reparent, switch to none """
        if self.edit_mode==self.REPARENT:
            self.edit_mode = self.FREE
            self.show_message("Stop new parent selection")
        else:
            self.edit_mode = self.REPARENT
            self.show_message("Select new parent")
        return True
        
    def reparent_selection(self,parent_node):
        """ reparent selected node by `parent_node` 
        
        return True if reparenting is done
        """
        if self.edit_mode!=self.REPARENT:
            return False
        
        if not self.get_selection(): return
        self.push_backup()
        
        # edit mtg model
        node_id = self.selection.id
        try:
            up = self.model.replace_parent(node_id, parent_node.id, edge_type=None)
        except TypeError as e:
            self.show_message(e.message)
            return False
        
        # edit views
        self.update_views(up)
        self.show_message("New parent selected: "+str(parent_node.id)+" for vertex "+str(node_id)+".")
        
        return True

    # mtg IO
    # ------
    ## make a generic open/save api in TreeEditor
    #  eg: editor.add_open/save_dialog(keySeq,self.load/save_file, 'Open/Save MTG file',self.load/save_dir?,["MTG Files (*.mtg;*.bmtg)"])
    def load_mtg_dialog(self):
        """ select a mtg file with a user dialog window, then call `load_mtg` """
        from openalea.vpltk.qt import QtGui
        filename = QtGui.QFileDialog.getOpenFileName(self._editor, "Open MTG file",
                                                self.model.default_directory(),
                                                "MTG Files (*.mtg;*.bmtg);;All Files (*.*)",
                                                QtGui.QFileDialog.DontUseNativeDialog)
        if not filename: return
        self.set_model(filename)
        
    def save_mtg_dialog(self):
        """ select a mtg file with a user dialog window, then call `save_mtg` """
        from openalea.vpltk.qt import QtGui
        filename = QtGui.QFileDialog.getSaveFileName(self._editor, "Save MTG file",
                                                self.model.default_directory(),
                                                "MTG Files (*.mtg;*.bmtg);;All Files (*.*)",
                                                QtGui.QFileDialog.DontUseNativeDialog)
        if not filename: return
        self.model.save_mtg(filename)

        
    # opengl draw
    # -----------
    def draw(self, glrenderer):
        """ draw the tree in given `glrenderer` """
        self.apply_view_update()
        self.edges.draw(glrenderer)
        self.ctrl_points.draw(glrenderer)
            
    def fastDraw(self, glrenderer):
        """ fast (re)draw of the tree in given `glrenderer` """
        self.apply_view_update()
        self.edges.fastDraw(glrenderer)
        self.ctrl_points.fastDraw(glrenderer)

        
    def get_bounding_box(self):
        """ update and return the bounding box """
        self.ctrl_points.update_boundingbox()
        return self.ctrl_points.boundingbox
        
    # backup and undo
    # ---------------
    def push_backup(self):
        """ push a copy of current mtg in undo list (i.e. backup) """ 
        if self.model:
            self.model.push_backup()
        
    def undo(self):
        """ pop last backed up mtg """
        if self.model:
            if self.model.undo():
                self.show_message("Last stored tree reloaded")
            else:
                self.show_message("undo impossible: no backup available.")
            self.reset_views()
        else:
            self.show_message("undo impossible: no tree loaded")



