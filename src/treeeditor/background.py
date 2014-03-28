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
    def __init__(self, color=None):
        """ Uniform background with color `color` """
        _Presenter.__init__(self)
        
        if color is None:
            from treeeditor import THEME
            color = THEME['background']
        if isinstance(color, _pgl.Material):
            color = color.ambient
            color = (color.red,color.green,color.blue)
        
        self.bg_color = QtGui.QColor(*color)
        self.image  = None
        self.points = None
        
    def get_view_list(self):
        return filter(None,[self.image,self.points]+self.view_list)
        
    def set_image(self, image):
        """ set this BackgroundPresenter image View
        
        image can be a View object or a valid input of the ImageView constructor
        """
        if not isinstance(image, _View):
            try:
                image = ImageView(image)
                image.__gl_init__()
            except IOError as e:
                print 'could not load image: ' + e.message
                return
                
        self.image = image
        
        if len(self.view_list)==0:
            self.view_list.append(self.image)
            
        self.image.set_presenter(self)
        self._editor.set_2d_camera()
        self._editor.update_scene_bbox(lookAt=self.image.boundingbox)
        
        # for the image to exactly fit the screen height
        w,h = self.image.img_width, self.image.img_height
        self._editor.camera().fitSphere(_qgl.Vec(w/2,h/2,0),h/2)
        self._editor.updateGL()

    def register_editor(self, editor):
        """ Attach this view to the given `editor` """
        _Presenter.register_editor(self,editor)
        self._editor.bind_openfile_dialog('Ctrl+I','Load image background',self.set_image)

    def set_points(self, points):
        """ set this BackgroundPresenter points (cloud) View
        
        points can be any of the valid input of PointsView constructor
        
        *** not implemented ***
        """
        raise NotImplementedError("background points is not implemented") 
        
    def draw(self, glrenderer):
        """ Draw background """
        self._editor.setBackgroundColor(self.bg_color)  ## can we use glrenderer?
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
        from OpenGL.GL import glEnable, glDisable, glBindTexture, glClear
        from OpenGL.GL import glColor3f, glNormal3f, glTexCoord2f, glVertex2i
        from OpenGL.GL import glBegin, glEnd
        from OpenGL.GL import GL_LIGHTING, GL_TEXTURE_2D, GL_DEPTH_BUFFER_BIT, GL_QUADS
        
        glDisable(GL_LIGHTING);
        glBindTexture(GL_TEXTURE_2D, self.tex_image)
        glEnable(GL_TEXTURE_2D);
        glColor3f(1,1,1);
      
        #self._editor.startScreenCoordinatesSystem(True);
      
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
      
        #self._editor.stopScreenCoordinatesSystem();
      
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
        
        
        
