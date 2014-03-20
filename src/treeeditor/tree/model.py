"""
Implement TreeModel(s)
"""

class TreeModel(object):
    """
    TreeModel implement the interaction with a tree represented by an mtg
    
    The mtg is expected to have a set of segments at the highest scale, each
    with the associated position of the last node of the segment.

    Its purpose is to be used by TreeVC, ControlPointsView and EdgesView
    """
    
    def __init__(self, mtg, position=None, radius=None):
        """ create a TreeModel to interact with given `mtg` 
        
        `mtg`: 
            either a MTG object or a file name to load with `load_mtg`
        `position`: 
            indicates how is stored the position associated to segments end node
            It can be either:
              - the name (string) of the property storing the position as an 
                iterable triplet (tuple, list, vector with iterable api, ...)
              - a list of the name of the 3 properties for the x, y and z 
                coordinates, respectively. Eg: ['XX','YY','ZZ']
              - None to attempt automatic detection (see `select_mtg_api`)
        `radius`:
            name of the property storing the segments radius. If None, it tries
            to detect it automatically (see `select_mtg_api`) and if it does not
            find it, it create its.
            Unfound radius are set to 1
        """
        # backup (undo) system
        self.backupmtg = []
        self.maxbackup = 4

        if isinstance(mtg,basestring):
            self.load_mtg(mtg,position=position,radius=radius)
        else:
            self.set_mtg(mtg,None,position=position,radius=radius)
            
        
    def register_controler(self, controler):
        """ attache this TreeModel to `controler` """
        self._controler = controler
        
        if self.mtg:
            self._controler.update_views('reset')
        
    def set_mtg(self,mtg,filename=None, position=None, radius=None):
        """ set the `mtg` of this TreeModel """
        self.mtg       = mtg
        self.mtgfile   = filename
        
        self.select_mtg_api(self, position=position, radius=radius)
        
        if self._controler is not None:
            self._controler.update_views('reset')
            
        ## for generation of load/save dialogs
        ##__save_api__ = [self.save_mtg, ... ??
        ## return dict(save=[...],load=...) ??? 
            
    def select_mtg_api(self, position=None, radius=None):
        """ select position and radius api:
        
        if `position` is:
          - a name (string): use this property of the mtg
          - a list of names: use them as the x, y and z properties
          - None: tries and use the first found of these:
              * 'XX','YY','ZZ'
              * 'x','y','z'
              * 'position'
        
        if radius is 
          - a name: use this property of the mtg
          - None: tries and use the first found of these:
              * 'radius'
              * 'r'
              
        Raise an IOError if one of the automatic position detection does not work
        """
        # autodetect position
        if position is None:
            prop = self.mtg.property_names()
            if 'XX' in prop and 'YY' in prop and 'ZZ' in prop:
                position = ['XX','YY','ZZ']
            elif 'x' in prop and 'y' in prop and 'z' in prop:
                position = ['x','y','z']
            elif 'position' in prop:
                position = 'position'
            else:
                raise IOError("could not find position properties: either XX,YY,ZZ ; x,y,z ; position"
                    
        # autodetect position
        if radius is None:
            prop = self.mtg.property_names()
            if 'r' in prop:
                radius = 'r'
            else:
                radius = 'radius'
                    
        self.position_property = position
        self.radius_property = radius
        
        if isinstance(position,basestring):
            self.get_position = self.get_position_tuple
            self.set_position = self.set_position_tuple
        else:
            self.get_position = self.get_position_triplet
            self.set_position = self.set_position_triplet


    def default_directory(self):
        """ return a default directory to look for mtg files """
        import os
        if self.mtgfile:
            return os.path.dirname(self.mtgfile)
        else:
            return io.get_shared_data('mtgdata')
        
    # position and radius accessors
    # -----------------------------
    def get_position_tuple(self, vertex_id):
        """ get position stored as vectors """
        return self.mtg.property(self.position_property)[vertex_id]
    def get_position_triplet(self, vertex_id):
        """ get position stored in 3 properties """
        position = map(self.mtg.property,self.position_property)
        return [coordinate[vertex_id] for coordinate in position]
    def set_position_tuple(self, vertex_id, position):
        """ set position stored as vectors """
        self.mtg.property(self.position_property)[vertex_id] = tuple(position)
    def set_position_triplet(self, vertex_id, position):
        """ set position stored in 3 properties """
        position_properties = map(self.mtg.property,self.position_property)
        for coordinate,value in zip(position_properties,position):
            coordinate[vertex_id] = value
            
    def get_radius(self, vertex_id)
        """ return radius of vertex `vertex_id` """
        return self.mtg.property(self.radius_property).setdefault(vertex_id,1)
        
        
    # vertex ids accessors
    # --------------------
    def get_nodes(self):
        """ return the ids of the segments, i.e. the mtg vertices at max scale """
        return self.mtg.vertices(scale=self.mtg.max_scale())
        
    def parent(self,vid):
        """ return the id of the parent vertex of `vid` """
        return self.mtg.parent(vid)
        
    def children(self,vid):
        """ return the list of ids of the children vertices of `vid` """
        return self.mtg.children(vid)
        
    # appearance
    # ----------
    def color(self, vid):
        """ return the color associated to `vid`, as a rgb tiplet tuple """ 
        if self.mtg.edge_type(vid)=='>': # successor
            return  (255,255,255)
        else:                            # branching
            return (255,255,0)

    # file IO
    # -------
    def load_mtg(self,filename, position=None, radius=None):
        """ load mtg from `filename`, then call `set_mtg` """
        import os.path
        
        if os.path.splitext(filename)[1] == '.bmtg':
           mtg = io.readfile(filename)
        else: # .mtg
            mtg = io.read_mtg_file(filename)
            
        self.set_mtg(mtg,filename, position=position,radius=radius)
        
    def save_mtg(self,filename):
        """ Save the mtg in file `filename` """ 
        filename = str(filename)
        import os.path,shutil
        if os.path.exists(filename):
            shutil.copy(filename,filename+'~')
        if os.path.splitext(filename)[1] == '.bmtg':
           io.writefile(filename,self.mtg)
        else: # .mtg
            # readable mtg format from openalea.mtg module
            stdmtg, properties = self.get_standard_mtg()
            io.write_mtg_file(filename, mtg, properties=properties)
        self.mtgfile = filename
   
    def get_standard_mtg(self):
        """
        Return a copy the managed mtg with standard format:
            position are stored in triplet XX,YY,ZZ properties
            radius   are stored in 'radius' property
            
        ##todo: manage position triplet (but convert them to tuple)
                what's the saving type for such tuple ?? 'TUPLE(REAL)' ?
        """
        from copy import deepcopy
        newg = deepcopy(self.mtg)
        
        for vid in self.get_nodes():
            xx[i],yy[i],zz[i] = self.get_position(vid)
            r[i]  = self.get_radius(vid)
        
        newg.add_property('XX')
        newg.add_property('YY')
        newg.add_property('ZZ')
        newg.add_property('radius')
        newg.property('XX').update(xx)
        newg.property('YY').update(yy)
        newg.property('ZZ').update(zz)
        newg.property('radius').update(r)
        
        properties = [('XX','REAL'), ('YY','REAL'), ('ZZ','REAL'), ('radius','REAL')]
        
        return newg, properties
    
    
    # backup and undo
    # ---------------
    def createBackup(self):
        """ push a copy of current mtg in undo list (i.e. backup) """ 
        from copy import deepcopy
        if len(self.backupmtg) == self.maxbackup:
            del self.backupmtg[0]
        self.backupmtg.append(deepcopy(self.mtg))
        
    def undo(self):
        """ pop last backed up mtg """         
        if len(self.backupmtg) > 0:
            self.mtg = self.backupmtg.pop()
            self._controler.update_views('reset')
        ##else:                                        
        ##    self.showMessage("No backup available.")
        


## end
