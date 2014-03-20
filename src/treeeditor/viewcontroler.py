"""
Definition of ViewControler API
"""

class AbstractViewControler(object):
    """
    Abstract class content to be displayed / edited by the editor 
    
    At minima, the following methods should be implemented by subclasses:
     - draw(glrenderer):   draw the content in glrenderer object
     - get_bounding_box(): return the 3d bounding box of the content
    """
    def __init_gl__(self):
        """ called by the editor at opengl init - by default do nothing"""
        pass

    def draw(self, glrenderer):
        """ Draw content to given `glrenderer` """
        raise NotImplementedError('method of the abstract class')
        
    def fastDraw(self,glrenderer):
        """ implement fast drawing - by default call `draw` """
        self.draw(glrenderer)

    def get_bounding_box(self):
        """ return the bounding box of the content to display """
        raise NotImplementedError('method of the abstract class')

    def register_editor(self, editor):   ## to be re-thought
        """ Attach this view to the given `editor` """
        self._editor = editor



