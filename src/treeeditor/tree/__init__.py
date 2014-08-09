"""
MTG related component of TreeEditor
"""
import os

from openalea.vpltk.qt import QtGui, QtCore

import openalea.plantgl.all as _pgl

from treeeditor.mvp        import Presenter         as _Presenter        
from treeeditor.tree.model import TreeModel         as _TreeModel
from treeeditor.tree.model import create_mtg_model  as _create_model
from treeeditor.tree.view  import ControlPointsView as _ControlPointsView
from treeeditor.tree.view  import EdgesView         as _EdgesView


# data format conversion
_toV3  = lambda v : _pgl.Vector3(*v)

class TreePresenter(_Presenter):
    """
    Default Presenter class managing (mtg) tree structure
    """
    FREE,EDITION,REPARENT,SKETCH_AXE = range(4)
    create_model = staticmethod(_create_model)
    
    def __init__(self, tree=None, theme=None, editor=None):
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
        _Presenter.__init__(self,theme=theme, editor=editor)
        
        # model and views
        ctrl_points = _ControlPointsView(theme=self.theme)
        edges       = _EdgesView(theme=self.theme)
        self.attach_viewable('ctrl_points',ctrl_points)
        self.attach_viewable('edges',edges)
        self.set_model(tree)

        # edition attributes
        self.set_edition_mode(self.FREE)
        self.focus = None      # id of the focussed control point (if any) 
        self.selection = None  # id of the selected control point (if any)

        # register actions
        self.add_file_action(self.model.open_title,self.set_model, dialog='open', keys= [self.theme['key_open']],
                             warning=lambda : False if self.is_empty() else 'Current tree will be lost. Continue?',
                             opened_extension=self.model.opened_extension)
        self.add_file_action(self.model.save_title,  self.save_model, dialog='save', keys= [self.theme['key_saveas']])
        self.add_file_action(self.model.saveas_title,self.save_model,                keys= [self.theme['key_save']])

        self.add_edit_action('undo',            self.undo,         keys=['Ctrl+Z'], isenable=self.has_undo)
        
        self.add_edit_action('add child',       self.add_child,    keys=['A'],      isenable=self.get_selection)
        self.add_edit_action('set successor',   self.set_axial,    keys=['<'],      isenable=self.get_selection)
        self.add_edit_action('reparent',        self.reparent_mode,keys=['P'],      isenable=self.get_selection)
        self.add_edit_action('new node on edge',self.insert_parent,keys=['E'],      isenable=self.get_selection)
        self.add_edit_action('sketch axe',      self.sketch_axe,   keys=['S'],      isenable=self.get_selection)
        
        self.add_edit_action('delete node',     self.delete_selection, keys=['Del','Backspace'], isenable=self.get_selection)
        self.add_edit_action('delete subtree',  self.delete_subtree,   keys=['Shift+Del','Shift+Backspace'], isenable=self.get_selection)
                                                                      
        self.add_edit_action('select parent',    self.select_parent,    keys=['Up'],   isenable=self.get_selection)
        self.add_edit_action('select successor', self.select_successor, keys=['Down'], isenable=self.get_selection)
        self.add_edit_action('unselect',         self.unselect,         keys=['Esc'],  isenable=self.get_selection)
        
        self.add_edit_action('dec point size', self.ctrl_points.dec_point_size, keys=['-'])
        self.add_edit_action('inc point size', self.ctrl_points.inc_point_size, keys=['+','='])

        self.add_view_action(description='display ctrl points',
                                 function=self.ctrl_points.show,
                                 checked=self.ctrl_points.display,
                                 keys=['Shift+P'])
        self.add_view_action(description='display edges',
                                 function=self.edges.show,
                                 checked=self.edges.display,
                                 keys=['Shift+E'])

        self.add_view_action(description='next color', function=self.next_color,  keys=['Shift+C'])
        self.add_view_action(description='refresh view', function=self.reset_views, keys=['Ctrl+Shift+R'])

    def set_model(self, tree=None):
        """ set the tree model managed by this TreePresenter 
        
        `tree` is either
          - a string of the name of a file storing a mtg 
          - a MTG instance
          - a TreeModel object
        """
        self.selection = None
        
        if not isinstance(tree,_TreeModel):
            if isinstance(tree,bool): # for call by Qt
                tree = None
            self.model = self.create_model(tree=tree, presenter=self)
        else:
            tree.set_presenter(self)
            self.model = tree
        
        self.reset_views(update_camera=True)
        
    def save_model(self, filename):
        self.model.save_model(filename)

    def is_empty(self):
        """ return True if tree model is emtpy """
        return len(self.model.get_nodes())==0
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
        self.ctrl_points.clear()
        self.edges.clear()
        node_number = len(self.model.get_nodes())
        if node_number:
            self.ctrl_points.create(self.model,self.update_views)
            self.edges.create(self.model)
            ##self.edges.update_boundingbox()
            
        self._point_to_update = set()
        self._edges_to_update = set()
        self._added_view_node = set()
        self._deleted_view_node = set()
        
        if node_number and update_camera:
            self.look_at()
            
        self.updateGL()

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
        ##    self.ctrl_points.delete_points(self._deleted_view_node)
        ##    self.edges.delete_edges(self._deleted_view_node)
        ##    
        ##    self._point_to_update.symmetric_difference_update(self._deleted_view_node)
        ##    self._edges_to_update.symmetric_difference_update(self._deleted_view_node)
            
        if len(self._added_view_node):
            for new_node in self._added_view_node:
                self.ctrl_points.add_point(new_node,self.model,self.update_views)
                self.edges.add_edge(new_node,self.model)
            self.update_views(self._added_view_node)
        
        for node_id in filter(None,self._point_to_update):
            self.ctrl_points.update(node_id)
        for node_id in filter(None,self._edges_to_update):
            self.edges.update(node_id, self.model)
            
        self._point_to_update = set()
        self._edges_to_update = set()
        self._added_view_node = set()
        self._deleted_view_node = set()
        
    # events
    # ------                                        
    def mousePressEvent(self, keys, position, camera):
        """ Process mouse press event
            
            Check for eventual operations the user asks: 
            shift start rectangular selection
            else check for which point is selected
        """
        processed = False
        self.apply_view_update()
        
        # axe drawing: each click create a child on the z=0 plane
        if self.edit_mode == self.SKETCH_AXE:
            # compute position of ray projected on z=0 plane 
            self.sketch_segment(position, camera)
            return True
            
        # find ctrl_point clicked by mouse
        ctrl_point = self.get_ctrl_point_at(position, camera)
        
        # (end of) reparent - parent of selected node is set the clicked one
        if self.edit_mode == self.REPARENT:
            processed = self.reparent_selection(ctrl_point)

        # no control point
        elif ctrl_point is None:
            self.set_selection(None)
            self.set_edition_mode(self.FREE)
            
        # edition of node position
        elif self.edit_mode == self.FREE:
            self.set_selection(ctrl_point)
            self.set_edition_mode(True)
            processed = False ## for QGLViewer to still be called
            
        return processed
        
    def mouseReleaseEvent(self, buttons, position, camera):
        """ stop edition (of node position) mode """
        # clear manipulated object
        if self.edit_mode!=self.SKETCH_AXE:
            self.set_edition_mode(False)
        return False
    
    
    def contextMenuEvent(self, buttons, position, camera):
        """ return list of items for context menu """
        self.apply_view_update()
        
        if self.edit_mode==self.FREE:
            ctrl_point = self.get_ctrl_point_at(position, camera)
            if ctrl_point:
                self.set_selection(ctrl_point)
            return self.get_edit_actions()
        
        return None
    # edition mode and selection
    # --------------------------
    def set_edition_mode(self, mode):
        """ set mode edition if `edit`, or stop it otherwise """
        self.edit_mode = mode
        if mode==self.EDITION:
            self.push_backup()
            self.ctrl_points.set_focus(self.selection)
            if self._presenter:
                self._presenter.setManipulatedFrame(self.selection)
        else:
            self.ctrl_points.set_focus(None)
            if self._presenter:
                self._presenter.setManipulatedFrame(None)
        
    def set_selection(self,point=None, model_id=None, message=True):
        """ Set focus to the given control point """
        # remove previous selection
        if self.selection:
            self.selection.selected = False
            self.ctrl_points.update(self.selection.id)
            
        # select given point
        if point is None and model_id is not None:
            self.apply_view_update()
            point = self.ctrl_points.get_point(model_id)
            
        self.selection = point
        if self.selection:
            self.selection.selected = True
            self.ctrl_points.update(self.selection.id)
            self._presenter.setRevolveAroundPoint(self.selection.position())
            if message:
                self.show_message('Node %d selected' % self.selection.id)

        self.updateGL()
        
    def unselect(self):
        """ set selection to None and set FREE mode """
        self.set_selection(None)
        self.set_edition_mode(self.FREE)
        self.show_message('UNSELECT')
        
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
            view_dir = _toV3(self._presenter.camera().viewDirection())
            
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
                
    def set_axial(self):
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
                
    def insert_parent(self):
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
            
        print 'added:', new_id, 'up:', up
        print 'node for update:', self._point_to_update, self._added_view_node, self._deleted_view_node
        # update self
        self.set_selection(model_id=new_id)
        
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
                                        

    def sketch_axe(self):
        """ set reparent edition mode: i.e. wait of new parent selection
        
        If mode is already on reparent, switch to none """
        if self.edit_mode==self.SKETCH_AXE:
            self.set_edition_mode(self.FREE)
            self.show_message("Stop axe drawing")
        elif self.get_selection():
            self.set_edition_mode(self.SKETCH_AXE)
            self.show_message("Draw axe")
        else:#if self.get_selection():
            self.set_edition_mode(self.SKETCH_AXE)
            self.show_message("Draw new axe")
        return True
        
    def sketch_segment(self, position, camera):
        """ add a segment at mouse click
        
        Currently, the position is the intersection of the line generated by 
        mouse click (contructed using mouse `position` and `camera`) with the
        z=0 plane.
        
        The new tree node is added as the child of the current selection, as a 
        successor if the selected node has no successor, or as a branch 
        otherwise.
        
        
        TODO1: create a "start" segment if selection is None - done
        
        TODO2: intersection with the view-plane (perpendicular to camera dir)
        positioned at the same view-depth as the selection point.
        
        TODO3: TODO1 with TODO2, what view-depth should to use?
               the plane intersecting (0,0,0)? scene center?
        """
        self.push_backup()

        # get position on z=0 plane
        eye, ray_dir = camera.convertClickToLine(position)
        alpha = -eye.z/ray_dir.z
        x,y,z = map(lambda x: x[0]+alpha*x[1], zip(eye,ray_dir))

        selection = self.get_selection()
        if selection:
            node_id = selection.id
            children = self.model.children(node_id)
            nbchild = len(children)
            if nbchild==0: 
                new_child_id, up = self.model.add_successor(node_id,position=(x,y,0))
            else:
                new_child_id, up = self.model.add_branching(node_id,position=(x,y,0))
        else:
            new_child_id = self.model.new_vertex(position=(x,y,0))
            up = [new_child_id]

        # update views
        # ------------
        self.add_view_node(new_child_id)
        self.update_views(up)
            
        # update self
        self.set_selection(model_id=new_child_id, message=False)
        self.show_message('New node sketched: '+str(new_child_id))
        
    def reparent_mode(self):
        """ set reparent edition mode: i.e. wait of new parent selection
        
        If mode is already on reparent, switch to none """
        if self.edit_mode==self.REPARENT:
            self.set_edition_mode(self.FREE)
            self.show_message("Stop new parent selection")
        else:
            self.set_edition_mode(self.REPARENT)
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

    # rendering
    # ---------
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

        
    def _compute_boundingbox(self):
        """ update and return the bounding box """
        _Presenter._compute_boundingbox(self,self.ctrl_points.get_boundingbox())
        
    def next_color(self):
        """ switch color model """
        self.model.next_color()
        self.reset_views()
    # backup and undo
    # ---------------
    def push_backup(self):
        """ push a copy of current mtg in undo list (i.e. backup) """ 
        if self.model:
            state = dict(mode=self.edit_mode)
            if self.selection:
                state['selection_id'] = self.selection.id
            self.model.push_backup(state=state)
        
    def undo(self):
        """ pop last backed up mtg """
        if not self.model:
            self.show_message("undo impossible: no tree loaded")
            return
            
        if not self.has_undo():
            self.show_message("undo impossible: no backup available.")
            return
            
        # reload model and views  
        self.set_selection(None)
        state = self.model.undo()
        self.reset_views()
        
        self.set_selection(model_id=state.get('selection_id'), message=False)
        ##self.set_edition_mode(state.get('mode', self.FREE))
        self.show_message("Last stored tree reloaded")

    def has_undo(self):
        return self.model.undo_number()>0

