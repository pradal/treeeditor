"""
File input and output
"""

import cPickle as _pickle

from os.path import join as _pjoin

from openalea.mtg    import io as _mtg_io
from openalea.mtg.io import read_mtg_file


# pickle
# ------
def writefile(filename, obj):
    """ pickle obj in filename """
    f = open(filename,'wb')
    _pickle.dump(obj, f, _pickle.HIGHEST_PROTOCOL)
    f.close()
    
def readfile(filename, mode='rb'):
    """ load pickled object from filename """
    f = open(filename,mode)
    obj = _pickle.load(f)
    f.close()
    return obj
    

# mtg
# ---
def write_mtg_file(filename, g, properties=[], nb_tab=20):
    """
    Write mtg `g` in file `filename`
    
    Same input parameters as mtg.io.write_mtg
    """
    if properties == []:
        properties = [(p, 'REAL') for p in g.property_names() if p not in ['edge_type', 'index', 'label']]
    str = _mtg_io.write_mtg(g, properties, nb_tab=nb_tab)
    with open(filename, 'w') as f:
        f.write(str)
        
        
# shared data
# -----------
def get_shared_data(*args):
    """
    Get absolute filename of shared data of TreeEditor package
    
    Example: 
        get_shared_data('folder','subfolder','file.name') return the absolute
        path of 'folder/subfolder/file.name'
    """
    from openalea.deploy.shared_data import get_shared_data_path
    import treeeditor
    shared_data_path = get_shared_data_path(treeeditor)
    if shared_data_path is None:
        # did not work
        return ''
    return _pjoin(shared_data_path, *args)

