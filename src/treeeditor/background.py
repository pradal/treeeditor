"""
background ViewControler for TreeEditor
"""
from openalea.vpltk.qt import QtGui
from OpenGL import GL as _gl
import PyQGLViewer as _qgl


from .viewcontroler import AbstractViewControler as _AbstractViewControler



class UniformBackgroundVC(_AbstractViewControler):
    """ Implement a simple background with uniform color """
    def __init__(self, color=(0,0,0)):
        """ Uniform background with color `color` """
        self.bg_color = color
        
    def draw(self, glrenderer):
        """ Draw background """
        self._editor.setBackgroundColor(QtGui.QColor(*self.bg_color))  ## can we use glrenderer?
        

class ImageBackgroundVC(UniformBackgroundVC):
    """ Implement a simple background with uniform color """
    def __init__(self, image, bg_color=(0,0,0)):
        """ Uniform background with color `color` """
        UniformBackgroundVC.__init__(self,color=bg_color)
        self.image = image
        
    def __init_gl__(self):
        """ called by the editor at opengl init """
        self.load_texture(self.image)
        
        # constraint rotation
        h,w = self.image.shape[:2]
        cam = self._editor.camera()
        cam.setType(cam.ORTHOGRAPHIC)
        cam.setUpVector(_qgl.Vec(0,-1,0))
        cam.setViewDirection(_qgl.Vec(0,0,1))
        
        constraint = _qgl.WorldConstraint()
        constraint.setRotationConstraintType(_qgl.AxisPlaneConstraint.FORBIDDEN)
        cam.frame().setConstraint(constraint)
        
        cam.fitSphere(_qgl.Vec(w/2,h/2,0),h/2)
        
    def draw(self, glrenderer):
        """ Draw background """
        UniformBackgroundVC.draw(self, glrenderer)
                     
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
        
        
    def load_texture(self,np_image):
        """ Create an opengl texture from image
        
        note: the image is converted to 'uint8' if necessary
        """
        import numpy as _np
        
        np_image = _np.asarray(np_image,dtype='uint8')
        
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
        
        
        
