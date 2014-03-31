"""
Implements Views to draw tree
"""
import openalea.plantgl.all as _pgl

if _pgl.PGL_VERSION > 0x20e00:
  from openalea.plantgl.gui.editablectrlpoint import CtrlPoint
else:
  from editablectrlpoint import CtrlPoint

from treeeditor.mvp import View as _View

def _pgl_vec(position):
    """ create a plantgl Vector3 from an iterable """
    return _pgl.Vector3(*position)
    
                 
class AbstractView(_View):
    """ Abstract class of views """
    def __init__(self, theme=None):
        """ Shared construcor behavior of view classes
        
        manage (default) theme and display flag 
        """
        _View.__init__(self)
        self.clear()
                
    def clear(self):
        self.content = None      # main content as a dict (tree-id, plantgl objects) 
        self.scene = None        # graphical representation as a PlantGL.Scene object 
        self.scene_index = {}    # map key of `content`  to  index in `scene`

        

class ControlPointsView(AbstractView):
    """
    Class that implements a graphical representation of a control points set
    """
    def __init__(self, theme=None):
        """ Construct an empty ControlPointView 
        
        `theme` can be a alternative dictionary to this module's THEME_DEFAULT
        """
        AbstractView.__init__(self,theme=theme)
        self.focus = None
        scale  = self.theme['point_diameter']
        sphere = _pgl.Sphere(radius=.5,slices=self.theme['point_slices'],
                                       stacks=self.theme['point_stacks'])
        self.graphical_primitive = _pgl.Scaled(scale,sphere)

    def set_focus(self,point):
        """ Set focus to given control point
        
        When a node is set as focussed, the others are not drawn
        """
        if self.focus:
            self.focus.hasFocus = False
            self.update(self.focus.id)
        self.focus = point
        if self.focus:
            point.hasFocus = True
            self.update(self.focus.id)

    # accessors
    # ---------
    def point_at(self, line_start, direction, z_min, z_max, factor=10):
        """ 
        Find the control point intersected by a line (for mouse selections) 
        
        `line_start` start position of the line
        `direction`  unit vector giving the direction of the line
        `z_min` minimum distance from line_start allowed
        `z_min` maximum distance from line_start allowed
        `factor` if no intersection, still return a point if it is close enough
        
        return None if mouse is too far from any control point
        
        If no control point is found in the intersection with the line, `factor`
        allows to look for close enough points: it will return the closest point
        (in depth along the line) that is a less that `factor`*point-radius 
        perpendicular distance to the line.
        """
        norm = _pgl.norm
        
        possibles = []
        if self.display and self.content:
            start = line_start
            ray_dir  = direction
            for ctrl_point in self.content.itervalues():
                p = (ctrl_point.position()-start)  # position relative to line start
                z = ray_dir * p                    # distance from start along line (depth)
                d = norm(p-z*ray_dir)              # distance from p to line
                
                radius = self.theme['point_diameter']/2.
                if d<factor*radius and z_min<=z<=z_max:
                    if d>radius: z = float('inf')  ## induce a sort by d only
                    possibles.append((z,d,ctrl_point))
                    
        if len(possibles) > 0:
            possibles.sort()
            return possibles[0][2]
        else:
            return None
        
    def get_point(self, node_id):
        """ return the control point related to model vertex `node_id` """
        return self.content[node_id]

    # draw
    # ----
    def draw(self,glrenderer):
        """ draw the control points """
        if self.display and self.scene:
            if self.focus is None:
                self.scene.apply(glrenderer)
            else:
                scene_index = self.scene_index[self.focus.id]
                self.scene[scene_index].apply(glrenderer)
        
    def fastDraw(self,glrenderer):
        """ draw the control points """
        if self.display and self.focus and self.scene:
            scene_index = self.scene_index[self.focus.id]
            self.scene[scene_index].apply(glrenderer)
        

    # edition and update
    # ------------------
    def create(self, model, update_callback):
        """ Create the ControlPointView graphical content from  `model` """
        if model is None:
            self.clear()
            return

        ## create ctrlPoint in create representation...
        self.content = ControlPointsView.create_ctrl_points(model=model, 
                                                            color=self.theme['point_color'].ambient,
                                                            callback=update_callback)
        
        primitive = self.graphical_primitive
        point_repr = [point.representation(primitive) for point in self.content.itervalues()]
        
        self.scene = _pgl.Scene(point_repr)
        self.scene_index = dict((point.id,i) for i,point in enumerate(self.scene))

    def update(self,node_id):
        """ update representation of the control point related to `node_id` """
        scene_index = self.scene_index[node_id]
        self.scene[scene_index] = self.content[node_id].representation(self.graphical_primitive)
        
    def add_point(self, node_id, model, update_callback):
        """ add node `node_id` from model """
        point = ControlPointsView.create_ctrl_point(model,node_id,
                                                    color=self.theme['point_color'].ambient,
                                                    callback=update_callback)
        self.content[node_id] = point
        self.scene += point.representation(self.graphical_primitive)
        self.scene_index[point.id] = len(self.scene)-1
        
        return point
        
    def delete_points(self, node_ids):
        """ remove all node in `node_ids` from model """
        for node_id in node_ids:
            print 'del node', node_id
            del self.content[node_id]
            scene_index = self.scene_index[node_id]
            del self.scene[scene_index]
            self.scene_index = dict((point.id,i) for i,point in enumerate(self.scene))
        
    @staticmethod
    def create_ctrl_points(model, color, callback):
        """ return a set of control point, as a dict (mtg-node-id, ctrl-pt-obj) """
        return dict((node,ControlPointsView.create_ctrl_point(model,node,color,callback)) 
                                for node in model.get_nodes())
    
    @staticmethod
    def create_ctrl_point(model,node_id,color, callback):
        """ create a CtrlPoint for node `node_id` of `mtg` """
        pos_setter = _PositionSetter(model,node_id)
        ccp = CtrlPoint(model.get_position(node_id), pos_setter,color=color,id=node_id)
        if callback: 
            ccp.setCallBack(callback)
        return ccp
        
    # appearance
    # ----------
    def inc_point_size(self):
        """ scale control point sphere by 25% """
        self.theme['point_diameter'] *= 1.25
        diameter = self.theme['point_diameter']
        scale = self.scene[0].geometry.geometry.scale
        scale[0] = scale[1] = scale[2] = diameter
            
    def dec_point_size(self):
        """ scale down control point sphere by 20% """
        self.theme['point_diameter'] *= 0.8
        diameter = self.theme['point_diameter']
        scale = self.scene[0].geometry.geometry.scale
        scale[0] = scale[1] = scale[2] = diameter
        
class EdgesView(AbstractView):
    """
    Class that implements a graphical representation of an edges set
    
    Edges are represented by graphical lines
    
    ##TODO: alternative "cylinder" reprensentation
    """
    def __init__(self, theme=None):
        """ 
        Construct an empty EdgesView 
        
        `theme` can be a alternative dictionary to this module's THEME_DEFAULT
        """
        AbstractView.__init__(self,theme=theme)
        self.not_rendered = set()  # list of node id that are not rendered (no parent)
        
    ## todo: 
    ##   draw cylinder if selected
    ##   fastDraw, edge even if cylinder selected
        
    # edition and update
    # ------------------
    def create(self,model):
        """ Create the EdgesView graphical content from  `model` """
        if model is None:
            self.clear()
            return

        self.content = dict(
            (node_id,EdgesView.create_edge(model.get_position(model.parent(node_id)),
                                           model.get_position(node_id),
                                           model.color(node_id),
                                           node_id,
                                           self.theme))
                              for node_id in model.get_nodes() 
                              if model.parent(node_id))
        self.not_rendered.update(node_id for node_id in model.get_nodes() if model.parent(node_id) is None)
        
        self.scene = _pgl.Scene(self.content.values())
        self.scene_index = dict((edge.id,i) for i,edge in enumerate(self.scene))

    def update(self, node_id, model):
        """ update representation of edges in contact to node `node_id` """
        if node_id in self.not_rendered:
            return
            
        scene_index = self.scene_index[node_id]
                
        color = model.color(node_id)
        node_pos   = model.get_position(node_id)
        parent_pos = model.get_position(model.parent(node_id))
        self.scene[scene_index] = EdgesView.create_edge(parent_pos,node_pos,color,node_id,self.theme)

    def add_edge(self, node_id, model):
        """ add edge for `node_id` of model """
        if model.parent(node_id) is None:
            self.not_rendered.add(node_id)
            return None
            
        edge = EdgesView.create_edge(model.get_position(model.parent(node_id)),
                                     model.get_position(node_id),
                                     model.color(node_id),
                                     node_id,
                                     self.theme)
        self.content[node_id] = edge
            
        
        self.scene += edge
        self.scene_index[edge.id] = len(self.scene)-1
        
        return edge
        
    def delete_edges(self, node_ids):
        """ remove all nodes from `node_ids` from model """
        for node_id in node_ids:
            if node_id in self.not_rendered:
                self.not_rendered.remove(node_id)
            else:
                del self.content[node_id]
                scene_index = self.scene_index[node_id]
                del self.scene[scene_index]
                self.scene_index = dict((point.id,i) for i,point in enumerate(self.scene))
        
    @staticmethod
    def create_edge(pos1,pos2,color, edge_id, theme):
        line = _pgl.Polyline([_pgl_vec(pos1), _pgl_vec(pos2)],width=1)
        if color in theme.keys():
            appearance = theme[color]
        else:
            cmap = theme['colormap']
            appearance = cmap[color%len(cmap)]
        return _pgl.Shape(geometry=line,appearance=appearance,id=edge_id)


# control point callback that update models
# -----------------------------------------
class _PositionSetter:
    """ Used as callback for CtrlPoint objects """
    def __init__(self,model,index):
        self.model = model
        self.index = index
    def __call__(self,pos):
        self.model.set_position(self.index,pos)
        

