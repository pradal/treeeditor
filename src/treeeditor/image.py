"""
Package that provide image view
"""
from OpenGL import GL as _gl
from openalea.plantgl.all import BoundingBox as _BoundingBox

from .mvp import View as _View

# View class to display image in Background Presenter
# ---------------------------------------------------
class ImageView(_View):
    def __init__(self, image=None, presenter=None):
        """ Create a View on a simple quad textured with an image """
        _View.__init__(self)
        self.image = image
        self.tex_image = None
        
    def __gl_init__(self):
        """ Create an opengl texture from this View image
        
        note: the image is converted to 'uint8' if necessary
        """
        if self.image is None: 
            print "ImageView: cant init gl"
            return
        
        import numpy as _np
        
        # load image array
        # ----------------
        if isinstance(self.image, basestring):
            from scipy.ndimage import imread
            image = imread(self.image)
        else:
            image = self.image
        
        np_image = _np.asarray(image,dtype='uint8')
        
        # prepare texture array
        # ---------------------
        # make an power-of-2 shaped image
        # with max dimension size min(4096, accepted opengl texture size) 
        max_tex_size = min(2**12, _gl.glGetIntegerv(_gl.GL_MAX_TEXTURE_SIZE))
        max_tex_po2 = int(_np.log(max_tex_size)/_np.log(2)+1-2**-5)
        
        h1,w1 = np_image.shape[:2]
        self.img_height,self.img_width = np_image.shape[:2]
        hpo2 = int(_np.log(self.img_height)/_np.log(2)+1-2**-5)
        wpo2 = int(_np.log(self.img_width) /_np.log(2)+1-2**-5)
        img_max_po2 = max(hpo2,wpo2)

        if img_max_po2>max_tex_po2:
            # resize image to upload
            sample = 2**(img_max_po2-max_tex_po2)
            np_image = np_image[::sample,::sample]
            hpo2 = int(_np.log(np_image.shape[0])/_np.log(2)+1-2**-5)
            wpo2 = int(_np.log(np_image.shape[1])/_np.log(2)+1-2**-5)
            self.show_message('ImageView: displayed image is sampled by '+str(sample)) 
        
        self.tex_height = 1<<hpo2
        self.tex_width  = 1<<wpo2
        
        if len(np_image.shape)==3:
            # RGB
            po2_image = _np.empty((self.tex_height,self.tex_width,np_image.shape[2]),dtype='uint8')
            po2_image[map(slice,np_image.shape)] = np_image
            color_flag = _gl.GL_RGB
        else:
            po2_image = _np.empty((self.tex_height,self.tex_width),dtype='uint8')
            po2_image[map(slice,np_image.shape)] = np_image
            color_flag = _gl.GL_LUMINANCE
            
        
        self.tex_hratio = np_image.shape[0]/float(self.tex_height)
        self.tex_wratio = np_image.shape[1]/float(self.tex_width)
        
        # create texture
        # --------------
        self.tex_image = _gl.glGenTextures(1)
        
        _gl.glPixelStorei(_gl.GL_UNPACK_ALIGNMENT,1)
        _gl.glBindTexture(_gl.GL_TEXTURE_2D, self.tex_image)
        _gl.glTexParameterf(_gl.GL_TEXTURE_2D, _gl.GL_TEXTURE_WRAP_S, _gl.GL_CLAMP)
        _gl.glTexParameterf(_gl.GL_TEXTURE_2D, _gl.GL_TEXTURE_WRAP_T, _gl.GL_CLAMP)
        _gl.glTexParameterf(_gl.GL_TEXTURE_2D, _gl.GL_TEXTURE_MAG_FILTER, _gl.GL_LINEAR)
        _gl.glTexParameterf(_gl.GL_TEXTURE_2D, _gl.GL_TEXTURE_MIN_FILTER, _gl.GL_LINEAR)
        _gl.glTexImage2D(_gl.GL_TEXTURE_2D, 0, _gl.GL_RGB, 
                         self.tex_width, self.tex_height, 
                         0, color_flag, _gl.GL_UNSIGNED_BYTE, 
                         po2_image)
        
        self.update_boundingbox()
        
    def clear(self):
        """ release opengl texture """
        if self.tex_image is not None:
            _gl.glDeleteTextures([self.tex_image])
            self.tex_image = None
        
    def _compute_boundingbox(self):
        """ return the bounding box of this textured quad """
        if hasattr(self,'img_width'):
            bbox = _BoundingBox((0,0,0),(self.img_width,self.img_height,0))
        else:
            bbox = None
        _View._compute_boundingbox(self,bbox)
        
    def draw(self, glrenderer):
        """ Draw background """
        if self.display is None:   return
        if self.image is None:     return
        if self.tex_image is None: return ##self.__gl_init__(self)
        
        from OpenGL.GL import glEnable, glDisable, glBindTexture, glClear
        from OpenGL.GL import glColor3f, glNormal3f, glTexCoord2f, glVertex2i
        from OpenGL.GL import glBegin, glEnd
        from OpenGL.GL import GL_LIGHTING, GL_TEXTURE_2D, GL_DEPTH_BUFFER_BIT, GL_QUADS
        
        glDisable(GL_LIGHTING)
        glBindTexture(GL_TEXTURE_2D, self.tex_image)
        glEnable(GL_TEXTURE_2D)
        glColor3f(1,1,1);                 
      
        # Draws the background quad
        w = self.img_width
        h = self.img_height
        wr = self.tex_wratio
        hr = self.tex_hratio
        
        glNormal3f(0.0, 0.0, 1.0);
        glBegin(GL_QUADS);
        glTexCoord2f(0.0, 0.0);   glVertex2i(0,0);
        glTexCoord2f(0.0,  hr);   glVertex2i(0,h);
        glTexCoord2f( wr,  hr);   glVertex2i(w,h);
        glTexCoord2f( wr, 0.0);   glVertex2i(w,0);
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
        
        

