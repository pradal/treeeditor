"""
Implements Views to draw tree
"""
import openalea.plantgl.all as _pgl

if _pgl.PGL_VERSION > 0x20e00:
  from openalea.plantgl.gui.editablectrlpoint import CtrlPoint
else:
  from editablectrlpoint import CtrlPoint


def _pgl_vec(position):
    """ create a plantgl Vector3 from an iterable """
    return _pgl.Vector3(*position)
    

THEME_DEFAULT = {'diameter': 5,
                 'ctrl_point'     : (30,250,30),
                 'new_ctrl_point' : (30,250,250),
                 'selected_ctrl_points' : (30,250,30),
                 'edge_successor' : (255,255,255),
                 'edge_branching' : (255,255,0),
                 'edge_tupe'      : (128,64,0)}
                 
class AbstractView(object):
    """ Abstract class of views """
    def __init__(self, theme=None):
        """ Shared construcor behavior of view classes
        
        manage (default) theme and display flag 
        """
        # flag to display content
        self.display = True
        
        self.content = None      # main content as a dict (tree-id, plantgl objects) 
        self.scene = None        # graphical representation as a PlantGL.Scene object 
        self.scene_index = {}    # map key of `content`  to  index in `scene`

        # display parameters
        if theme is None:
            self.theme = THEME_DEFAULT
        else:
            for k,v in THEME_DEFAULT.iteritems():
                self.theme = theme
                theme.setdefault(k,v)

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
        self.graphical_primitive = _pgl.Scaled(self.theme['diameter'],_pgl.Sphere(1))
        

    def point_at(self, mouse, camera):
        """ 
        Find the control point selected by mouse click 
        
        `mouse` is the mouse position
        `camera is the PlantGL camera
        
        return None if mouse is too far from any control point
        """
        ## put back in TreeVC ?
        possibles = []
        if self.display and self.ctrl_points:
            for ctrl_point in self.ctrl_points.itervalues():
                ctrl_point.checkIfGrabsMouse(mouse.x(), mouse.y(), camera)
                if ctrl_point.grabsMouse():
                    pz = camera.viewDirection() * (ctrl_point.position()-camera.position()) 
                    z =  (pz - camera.zNear()) /(camera.zFar()-camera.zNear())
                    if 0<z<1:## > 0 and not self.clippigPlaneEnabled or self.frontVisibility <= z*2 <= self.backVisibility:
                        possibles.append((z,ctrl_point))
        if len(possibles) > 0:
            possibles.sort(lambda x,y : cmp(x[0],y[0]))
            return possibles[0][1]
        else:
            return None
        
    def draw(self,glrenderer):
        """ draw the control points """
        if display:
            if self.focus is None:
                self.content.apply(glrenderer)
            else:
                scene_index = self.scene_index[self.focus.id]
                self.scene[scene_index].apply(glrenderer)
        
    def fastdraw(self,glrenderer):
        """ draw the control points """
        if display and self.focus:
            scene_index = self.scene_index[self.focus.id]
            self.scene[scene_index].apply(glrenderer)
        
    def update(self,node_id):
        """ update representation of the control point related to `node_id` """
        scene_index = self.scene_index[node_id]
        self.scene[scene_index] = self.content[node_id].representation(self.graphical_primitive)
        
    def create(self, model, update_callback):
        """ Create the ControlPointView graphical content from  `model` """
        ## create ctrlPoint in create representation...
        self.content = ControlPointsView.create_ctrl_points(model=model, 
                                                            color=self.theme['ctrl_point'],
                                                            callback=update_callback)
        
        primitive = self.graphical_primitive
        content_repr = [obj.representation(primitive) for obj in self.content.itervalues()]
        self.scene = _pgl.Scene(content_repr)
        
        self.scene_index = dict((sh.id,i) for i,sh in enumerate(self.scene))

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
        
class _PositionSetter:
    """ Used as callback for CtrlPoint objects """
    def __init__(self,model,index):
        self.model = model
        self.index = index
    def __call__(self,pos):
        self.model.set_position(self.index,pos)
            
        
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

    def draw(self,glrenderer):
        """ draw the edges """
        if display:
            self.line_edges.apply(glrenderer)
        
        ##todo: draw cylinder
        ##_gl.glEnable(_gl.GL_LIGHTING)
        ##_gl.glEnable(_gl.GL_BLEND)
        ##_gl.glBlendFunc(_gl.GL_SRC_ALPHA,_gl.GL_ONE_MINUS_SRC_ALPHA)
        ##if self.modelDisplay and self.modelRep:
        ##    self.modelRep.apply(glrenderer)
        
    def fastdraw(glrenderer):
        """ efficient draw of edges """
        if display:
            self.line_edges.apply(glrenderer)
        ##todo: if cylinder, still draw lines
        
    def update(self, node_id, model):
        """ update representation of edges in contact to node `node_id` """
        scene_index = self.scene_index[node_id]
                
        color = model.color(node_id)
        node_pos   = model.get_position(node_id)
        parent_pos = model.get_position(model.parent(node_id))
        self.scene[scene_index] = EdgesView.create_edge(parent_pos,node_pos, color)
        
        for son_id in model.children(node_id):
            color = mode.color(son_id)
            son_pos = model.get_position(son_id)
            scene_index = self.scene_index[son_id]
            self.scene[scene_index] = EdgesView.create_edge(pos1=node_pos,
                                                            pos2=son_pos,
                                                            color=color,
                                                            edge_id=son_id)

    def create(self,model):
        """ Create the EdgesView graphical content from  `model` """
        self.content = dict(
            (node_id,EdgesView.create_edge(model.get_position(model.parent(node_id)),
                                           model.get_position(node_id),
                                           model.color(node_id)))
                              for node_id in model.get_nodes() 
                              if model.parent(node_id))
                            
        self.scene = _pgl.Scene(self.content.values())
        self.scene_index = dict((sh.id,i) for i,sh in enumerate(l))

    @staticmethod
    def create_edge(pos1,pos2,color, edge_id):
        line = _pgl.Polyline([_pgl_V3(pos1), _pgl_V3(pos2)],width=1)
        return _pgl.Shape(geometry=line,appearance=color,id=edge_id)
