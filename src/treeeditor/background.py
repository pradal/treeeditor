"""
background Presenter for TreeEditor


Possible improvement:
  - put background stuff in editor
  - and image&point views in image&point package
  - merge pointSetView and CtrlPointView in some PointView class
"""
from openalea.vpltk.qt import QtGui
from openalea.plantgl  import all as _pgl
import PyQGLViewer as _qgl


from .mvp   import View      as _View
from .mvp   import Presenter as _Presenter
from .image import ImageView as _ImageView


class BackgroundPresenter(_Presenter):
    """ Implement a background Presenter for the editor 
    
    By default, it simply manage background color. Then it can contain an
    ImageView and a PointsView
    """
    def __init__(self, theme=None, editor=None):
        """ Uniform background with color `color` """
        _Presenter.__init__(self, theme=theme, editor=editor)
        
        color = self.theme['background']
        if isinstance(color, _pgl.Material):
            color = color.ambient
            color = (color.red,color.green,color.blue)
        
        self.bg_color = QtGui.QColor(*color)
        self.image  = None
        self.points = None
        
        self.add_file_action('Load image background',self.set_image, 
                             dialog='open', keys=['Ctrl+I'], 
                             opened_extension=['.png','.jpg','.jpeg','.tif','.tiff','.bmp'])
        self.add_file_action('Load pointset background',self.set_points, 
                             dialog='open', keys=['Ctrl+P'],
                             opened_extension=['.bgeom'])

    def set_image(self, image):
        """ set this BackgroundPresenter image View
        
        image can be a View object or a valid input of the ImageView constructor
        """
        if self.image:
            self.image.clear()
            
        if not isinstance(image, _View):
            try:
                image = _ImageView(image)
            except IOError as e:
                self.show_message('*** Error: could not load image ' + e.message + ' ***')
                return

        self.attach_viewable('image',image)

        if not 'display image' in [a['description'] for a in self._view_actions]:
            self.add_view_action(description='display image', 
                                 function=self.image.show,
                                 checked=self.image.display)

        # update editor
        editor = self.get_editor()
        if editor:
            editor.set_camera('2D')
            self.__gl_init__() ## required to have img_width/height below
            ## for the image to exactly fit the screen height
            w,h = self.image.img_width, self.image.img_height
            editor.camera().fitSphere(_qgl.Vec(w/2,h/2,0),h/2)
            editor.updateGL()

    def set_points(self, points):
        """ set this BackgroundPresenter points View
        
        points can be any of the valid input of PointSetView constructor
        """
        if not isinstance(points, _View):
            try:
                points = PointSetView(points, theme=self.theme)
            except IOError as e:
                self.show_message('could not load pointset: ' + e.message)
                return
                
        self.attach_viewable('points',points)
        editor = self.get_editor()
        if editor:
            editor.look_at(self.points.get_boundingbox())
        
        
    def draw(self, glrenderer):
        """ Draw background """
        self._presenter.setBackgroundColor(self.bg_color)  ## can we use glrenderer?
        _Presenter.draw(self,glrenderer)
        
        
# View class to display a point cloud
# -----------------------------------
class PointSetView(_View):
    def __init__(self, point_scene, theme=None):
        """ Create a PointSetView from the plangl Scene `point_scene` """
        _View.__init__(self,theme=theme)
        if isinstance(point_scene,basestring):
            self.read_points(point_scene)
        else:
            self.set_points(point_scene)
        
    def read_points(self,filename):
        """ load point set from `filename` """
        scene = _pgl.Scene(str(filename))
        self.set_points(scene)
        
    def set_points(self,point_scene):
        """ set this PointSetView content """
        # remove translation
        try:
            points = point_scene[0].geometry.geometry
            translation =  point_scene[0].geometry.translation
            points.pointList.translate(translation)
        except AttributeError:
            points = point_scene[0].geometry
            
        self.attach_viewable('points',points)
        
        if not 'display points' in [a['description'] for a in self._view_actions]:
            self.add_view_action(description='display points',
                                 function=self.image.show,
                                 checked=self.image.display)
        
        # compute point color                
        if self.points.colorList is None: 
            bbx = self.get_boundingbox()
            colorList = [(100+int(100*((i.x-bbx.getXMin())/bbx.getXRange())),
                          100+int(100*((i.y-bbx.getYMin())/bbx.getYRange())),
                          100+int(100*((i.z-bbx.getZMin())/bbx.getZRange())),0) 
                          for i in self.points.pointList]
            self.points.colorList = colorList
            
        ## self.filter_points()  w.r.t mtg...
        
        self.pointWidth = int(self.theme['point_diameter']*.7)
        self.create()
        
    def create(self):
        """ create the plantgl scene """
        pointList  = self.points.pointList
        colorList  = self.points.colorList
        material = self.theme['pointset_color']
        pointset   = _pgl.PointSet(pointList,colorList,width=self.pointWidth)
        self.scene = _pgl.Scene([_pgl.Shape(pointset, material)])

    def _compute_boundingbox(self):
        """ (re)compute the view boundingbox """
        if hasattr(self,'points') and hasattr(self.points,'pointList'):
            bbox = _pgl.BoundingBox(*self.points.pointList.getBounds())
        else:
            bbox = None
        _View._compute_boundingbox(self,bbox)

