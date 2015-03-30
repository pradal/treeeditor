from openalea.plantgl.scenegraph import Material as _Material



LGRAY   = _Material((200,200,200))
LGREEN  = _Material(( 80,250, 80))

BLACK   = _Material((  0,  0,  0))
WHITE   = _Material((255,255,255))
RED     = _Material((255,  0,  0))
GREEN   = _Material((  0,255,  0))
BLUE    = _Material((  0,  0,255))
BROWN   = _Material((170, 80,  0))
ORANGE  = _Material((220,110,  0))
YELLOW  = _Material((255,200,  0))
CYAN    = _Material((  0,200,200))
PURPLE  = _Material((150,  0,255))
MAGENTA = _Material((220,  0,100))


THEME = {'point_diameter': 30,
         'point_slices': 8,
         'point_stacks': 8,
         'point_color':    LGREEN,
         'pointset_color': BROWN,
         'background':     LGRAY,
         'default':        BLACK,
         'highlight':      ORANGE,
         'highlight2':     WHITE,
         'colormap':      [BLACK,RED,GREEN,BLUE,YELLOW,PURPLE,CYAN,MAGENTA],
         
         'key_open':   'Ctrl+O',
         'key_save':   'Ctrl+S',
         'key_saveas': 'Ctrl+Shift+S',
        }