"""
background Presenter for TreeEditor
"""
from openalea.vpltk.qt import QtGui
from openalea.plantgl  import all as _pgl
from OpenGL import GL as _gl
import PyQGLViewer as _qgl


from .mvp import Presenter as _Presenter
from .mvp import View as _View


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
                             dialog='open', keys=['Ctrl+I'])
        self.add_file_action('Load pointset background',self.set_points, 
                             dialog='open', keys=['Ctrl+P'])

    def set_image(self, image):
        """ set this BackgroundPresenter image View
        
        image can be a View object or a valid input of the ImageView constructor
        """
        if not isinstance(image, _View):
            try:
                image = ImageView(image)
                image.__gl_init__()
            except IOError as e:
                self.show_message('could not load image: ' + e.message)
                return
                
        self.attach_view('image',image)
        
        self._presenter.set_2d_camera()
        self.update_content()
        
        ## for the image to exactly fit the screen height
        w,h = self.image.img_width, self.image.img_height
        self._presenter.camera().fitSphere(_qgl.Vec(w/2,h/2,0),h/2)
        self.updateGL()

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
                
        self.attach_view('points',points)
        self._presenter.update_scene_bbox(lookAt=self.points.get_boundingbox())
        
        
    def draw(self, glrenderer):
        """ Draw background """
        self._presenter.setBackgroundColor(self.bg_color)  ## can we use glrenderer?
        _Presenter.draw(self,glrenderer)
        
        
# View class to display image in Background Presenter
# ---------------------------------------------------
class ImageView(_View):
    def __init__(self, image):
        """ Create a View on a simple quad textured with an image """
        _View.__init__(self)
        self.image = image
        
    def __gl_init__(self):
        """ Create an opengl texture from this View image
        
        note: the image is converted to 'uint8' if necessary
        """
        import numpy as _np
        
        if isinstance(self.image, basestring):
            from scipy.ndimage import imread
            image = imread(self.image)
        else:
            image = self.image
        
        np_image = _np.asarray(image,dtype='uint8')
        
        self.tex_image = _gl.glGenTextures(1)
        self.img_height,self.img_width = np_image.shape[:2]
        
        _gl.glPixelStorei(_gl.GL_UNPACK_ALIGNMENT,1)
        _gl.glBindTexture(_gl.GL_TEXTURE_2D, self.tex_image)
        _gl.glTexParameterf(_gl.GL_TEXTURE_2D, _gl.GL_TEXTURE_WRAP_S, _gl.GL_CLAMP)
        _gl.glTexParameterf(_gl.GL_TEXTURE_2D, _gl.GL_TEXTURE_WRAP_T, _gl.GL_CLAMP)
        _gl.glTexParameterf(_gl.GL_TEXTURE_2D, _gl.GL_TEXTURE_MAG_FILTER, _gl.GL_LINEAR)
        _gl.glTexParameterf(_gl.GL_TEXTURE_2D, _gl.GL_TEXTURE_MIN_FILTER, _gl.GL_LINEAR)
        _gl.glTexImage2D(_gl.GL_TEXTURE_2D, 0, _gl.GL_RGB, 
                         self.img_width, self.img_height, 
                         0, _gl.GL_RGB, _gl.GL_UNSIGNED_BYTE, 
                         np_image)
        
        self.update_boundingbox()
        
    def update_boundingbox(self):
        """ return the bounding box of this textured quad """
        if hasattr(self,'img_width'):
            self.boundingbox = _pgl.BoundingBox((0,0,0),(self.img_width,self.img_height,0))
        else:
            self.boundingbox = None
        
    def draw(self, glrenderer):
        """ Draw background """
        if not self.display: return
        
        from OpenGL.GL import glEnable, glDisable, glBindTexture, glClear
        from OpenGL.GL import glColor3f, glNormal3f, glTexCoord2f, glVertex2i
        from OpenGL.GL import glBegin, glEnd
        from OpenGL.GL import GL_LIGHTING, GL_TEXTURE_2D, GL_DEPTH_BUFFER_BIT, GL_QUADS
        
        glDisable(GL_LIGHTING);
        glBindTexture(GL_TEXTURE_2D, self.tex_image)
        glEnable(GL_TEXTURE_2D);
        glColor3f(1,1,1);
      
        # Draws the background quad
        w = self.img_width
        h = self.img_height
        
        glNormal3f(0.0, 0.0, 1.0);
        glBegin(GL_QUADS);
        glTexCoord2f(0.0, 0.0);   glVertex2i(0,0);
        glTexCoord2f(0.0, 1.0);   glVertex2i(0,h);
        glTexCoord2f(1.0, 1.0);   glVertex2i(w,h);
        glTexCoord2f(1.0, 0.0);   glVertex2i(w,0);
        glEnd();
      
        # Depth clear is not absolutely needed. An other option would have been to draw the
        # QUAD with a 0.999 z value (z ranges in [0, 1[ with startScreenCoordinatesSystem()).
        glClear(GL_DEPTH_BUFFER_BIT);
        glDisable(GL_TEXTURE_2D);
        glEnable(GL_LIGHTING);
        
        ##DEBUG
        from OpenGL.GL import glColor, glPointSize, GL_POINTS
        glColor(255,255,0)
        glPointSize(2)
        glBegin(GL_POINTS)
        glVertex2i(0,0)
        glVertex2i(0,h)
        glVertex2i(w,h)
        glVertex2i(w,0)
        glEnd()
        
        
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
            
        self.points = points
        self.update_boundingbox()
        
        # compute point color                
        if self.points.colorList is None: 
            bbx = self.get_boundingbox()
            colorList = [(100+int(100*((i.x-bbx.getXMin())/bbx.getXRange())),
                          100+int(100*((i.y-bbx.getYMin())/bbx.getYRange())),
                          100+int(100*((i.z-bbx.getZMin())/bbx.getZRange())),0) for i in self.points.pointList]
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

    def update_boundingbox(self):
        """ (re)compute the view boundingbox """
        if hasattr(self,'points') and hasattr(self.points,'pointList'):
            self.boundingbox = _pgl.BoundingBox(*self.points.pointList.getBounds())
        else:
            self.boundingbox = None
        return self.boundingbox

