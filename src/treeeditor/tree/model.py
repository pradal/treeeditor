"""
Implement TreeModel(s)
"""
from openalea.mtg import algo as _mtgalgo
from openalea.mtg import MTG  as _MTG
from treeeditor import io
from treeeditor.mvp import Model as _Model

##todo: register model classes and associated test functions
def create_mtg_model(presenter, tree, **kargs):
    def test_mtg(g):
        if g is None or g.max_scale()!=3: return TreeModel
        else:                             return PASModel


    if isinstance(tree,basestring):
        tree = TreeModel(presenter=presenter, mtg=tree, **kargs)
        if test_mtg(tree.mtg) is PASModel:
            tree = PASModel(presenter=presenter, mtg=tree.mtg, **kargs) ## tree.__class__ = PASModel?
        return tree
        
    elif isinstance(tree, TreeModel):
        tree.set_presenter(presenter)
        return tree
        
    else:
        model = test_mtg(tree)
        return model(presenter=presenter, mtg=tree, **kargs)

class TreeModel(_Model):
    """
    TreeModel are generalized interface for (axial) trees stored as mtg
    
    The purpose of a TreeModel is to provide a standard interface to read and 
    edit the tree mtg by a TreePresenter. It provides two main features:
      - A standardized IO API to the segments positions
      - Compared to a general mtg, it models an axial tree: each vertex has at
        most one successor child (i.e. with edge_type='<')
    
    Note that it manages explicitly only the highest scale: the tree segments.
    The other scale are implicitely maintained by the MTG procedures. But if a
    specific behavior is expected, a subclass should be implemented for that
    purpose.
    
    Expected mtg format:
      - The highest scale should contain a set of segments, each with associated 
        attributes giving the position of the (last) node of the segment, and 
        optional radius. These can be stored in several ways. 
        See `select_mtg_api` for details
      - It should represent an axial tree: each segment have maximum 1 successor 
        child (edge_type='<') but any number of branch children (edge_type='+')
    """
    open_title   = 'open mtg file'
    save_title   = 'save mtg file'
    saveas_title = 'save mtg file as'
    opened_extension = ['.mtg','.bmtg']
    
    def __init__(self, presenter=None, mtg=None, position='position', radius='radius'):
        """ create a TreeModel to interact with given `mtg` 
        
        `mtg`: 
            either a MTG object or a file name to load with `load_model`
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
        _Model.__init__(self, presenter=presenter)
        # backup (undo) system
        self.backupmtg = []
        self.maxbackup = 10

        # color
        self._color_fct = [('branch',self.branch_color)]
        self._current_color = -2
        self.next_color()

        self.set_presenter(presenter)
        
        if isinstance(mtg,basestring):
            filename = mtg
            mtg = self.load_model(filename)
        else:
            filename = None
        self.set_mtg(mtg,filename,position=position,radius=radius)
            
        
        
    def set_mtg(self,mtg,filename=None, position=None, radius=None):
        """ set the `mtg` of this TreeModel """
        if mtg is None:
            # create a default mtg with one 'segment' vertex
            mtg = _MTG()
            self._segment_scale = 1
        else:
            self._segment_scale = mtg.max_scale()
            
        self.mtg     = mtg
        self.mtgfile = filename
        
        self.select_mtg_api(position=position, radius=radius)
            
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
            elif position is None:
                raise IOError("could not find position properties: either XX,YY,ZZ ; x,y,z ; position")
                    
        # autodetect radius
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

        # assert position and radius properties exists
        prop = self.mtg.properties()
        if isinstance(position,basestring):
            prop.setdefault(position,{})
        else:
            for pos in position:
                prop.setdefault(pos,{})
                
        prop.setdefault(radius,{})

    # position and radius accessors
    # -----------------------------
    def get_position_tuple(self, vertex):
        """ get position stored as vectors """
        return self.mtg.property(self.position_property)[vertex]
    def get_position_triplet(self, vertex):
        """ get position stored in 3 properties """
        position = map(self.mtg.property,self.position_property)
        return [coordinate[vertex] for coordinate in position]
    def set_position_tuple(self, vertex, position):
        """ set position stored as vectors """
        self.mtg.property(self.position_property)[vertex] = tuple(position)
    def set_position_triplet(self, vertex, position):
        """ set position stored in 3 properties """
        position_properties = map(self.mtg.property,self.position_property)
        for coordinate,value in zip(position_properties,position):
            coordinate[vertex] = value
            
    def get_radius(self, vertex):
        """ return radius of vertex `vertex` """
        return self.mtg.property(self.radius_property).setdefault(vertex,1)
        
    def set_radius(self, vertex, radius):
        """ return radius of vertex `vertex` """
        self.mtg.property(self.radius_property)[vertex] = radius
        
        
    # vertex ids accessors
    # --------------------
    def get_nodes(self):
        """ return the ids of the segments, i.e. the mtg vertices at max scale """
        return self.mtg.vertices(scale=self._segment_scale)
        
    def parent(self,vid):
        """ return the id of the parent vertex of `vid` """
        return self.mtg.parent(vid)
        
    def children(self,vid):
        """ return the list of ids of the children vertices of `vid` """
        return self.mtg.children(vid)
    def successor(self,vid):
        """ return the id of the successor ('<') child of `vid` (or None) """
        children = dict((self.mtg.edge_type(c),c) for c in self.mtg.children(vid))
        return children.get('<',None)
        
    def siblings(self,vid):
        """ return the list of ids of the children vertices of `vid` """
        return self.mtg.siblings(vid)
        
    # mtg edition
    # -----------
    def new_vertex(self, position, radius=1):
        """ add a new *unconnected* vertex """
        vid = self.mtg.root
        for s in range(self._segment_scale-1):
            vid = self.mtg.add_component(vid)
        vid = self.mtg.add_component(vid, edge_type='+')
        self.set_position(vid, position=position)
        self.set_radius(vid, radius=radius)
        return vid
        
    def add_successor(self, vertex, position):
        """ add a successor (i.e. edge_type '<') to vertex `vertex` 
        
        return 
          - the id of the created vertex
          - the set of updated vertices
        """
        # set all existing successors as branching
        edge_type = self.mtg.property('edge_type')
        successors = [vid for vid in self.mtg.children(vertex) if edge_type[vid]=='<']
        for s in successors:
            edge_type[child] = '+'
        updated = set(successors)
            
        # add new successor
        child = self.mtg.add_child(vertex,edge_type='<')
        self.set_position(child,position)
        updated.add(child)
        updated.add(vertex)
        
        return child, updated
        
    def add_branching(self, vertex, position):
        """ add a branching vertex (i.e. edge_type '+') to vertex `vertex` 
        
        return 
          - the id of the created vertex
          - the set of updated vertices
        """
        child = self.mtg.add_child(vertex,edge_type='+')
        self.set_position(child,position)
        
        return child, set([child, vertex])
    
    def insert_parent(self, child, position):
        """
        Insert a new vertex as parent of `child`
        
        The new vertex has same edge_type as `child` and `child` becomes
        the axial child (successor) of the new vertex.
        
        if there is multiple scale, the added vertex is attached to the complex 
        of `child` 
        
        return 
          - the id of the created vertex
          - the set of updated vertices
        """
        # insert the vertex
        mtg = self.mtg
        parent = mtg.parent(child)
        if parent is None:
            self.show_message('Only vertex with parent can insert a node')
            return child, []
            
        child_edge = mtg.edge_type(child)
        if mtg.max_scale()>1 and mtg.complex(child)!=mtg.complex(parent):
            complex_id = mtg.complex(child)
            vertex = mtg.add_component(complex_id, edge_type=child_edge)
            mtg.replace_parent(child, vertex, edge_type='<')
            mtg.replace_parent(vertex, parent)
        else:
            vertex = self.mtg.insert_parent(child)
            #mtg.add_child(parent, vertex, edge_type=child_edge) ## not done by in mtg.insert_parent
        self.set_position(vertex, position)
        
        # select edge type
        up = set([child,vertex,parent])
        if child_edge=='+':
            edge_type = mtg.property('edge_type')
            edge_type[child] = '<'
            ##up.update(self.replace_parent(child,  vertex, edge_type='<'))

        return vertex, up
        
        
    def replace_parent(self, vertex, new_parent, edge_type=None):
        """ set the parent of `vertex` by `new_parent` 
        
        Set the edge_type of `vertex` to `edge_type`. If None (or not given),
        it select successor edge_type ('<') if the new parent does not already 
        have one. And it selects branching edge_type ('+') otherwise.
        If edge_type is '<', existing succesor of parent is set to branching.
        
        return the set of updated vertices
        """
        if new_parent in _mtgalgo.descendants(self.mtg,vertex):
            raise TypeError("Invalid parent: cannot reparent a node with one of its descendants")
            
        if edge_type is None:
            if self.successor(new_parent): edge_type = '+'
            else:                          edge_type = '<'
        
        mtg = self.mtg
        updated = [vertex, new_parent]
        
        # assert parent has no other successor
        mtg_edge_type = mtg.property('edge_type')
        if edge_type=='<':
            successors = [vid for vid in mtg.children(new_parent) if mtg_edge_type[vid]=='<']
            for s in successors:
                mtg_edge_type[s] = '+'
            updated.extend(successors)
            
        mtg.replace_parent(vertex, new_parent)
        mtg_edge_type[vertex] = edge_type
            
        return set(updated)
                    
    def remove_vertex(self, vertex, reparent_child=True):
        """ remove `vertex` from tree 
        
        If `reparent_children` is False, `vertex` should not have child.
        Otherwise, if vertex is a successor or if parent had no successor, 
        children keep their edge_type.
        otherwise, all children become branch edge_type (+)
        
        return the set of updated vertices
        """
        parent   = self.parent(vertex)
        children = self.children(vertex)
        updated = set([parent]+children)
        
        if parent is None and len(children):
            raise TypeError("cannot remove root vertex with children")
            
        if self.mtg.edge_type(vertex)=='+' and self.successor(parent) is not None:
            s = self.successor(vertex)
            if s:
                self.mtg.property('edge_type')[s] = '+'
        
        ##if parent:
        self.mtg.remove_vertex(vertex, reparent_child=reparent_child)
        ##else:
        ##    for child in children[:]:  # make a copy cuz loop modify children 
        ##        print vertex, child, children
        ##        self._disconnect_tree(vertex, child)
        ##    self.mtg.remove_vertex(vertex, reparent_child=False)

        return updated
        
    def remove_tree(self, vertex):
        """ remove the subtree rooted at `vertx` 
        
            return the set of delted vertices
        """
        removed = _mtgalgo.descendants(self.mtg, vertex)
        self.mtg.remove_tree(vertex)
        return set(removed)

    def _disconnect_tree(self, parent, vertex):
        """ 
        Disconnect tree starting at `vertex` from `parent` 
        ** works only if scale(parent)==scale(vertex)==max_scale **
        """
        del self.mtg._parent[vertex]
        self.mtg._children[parent].remove(vertex)
        ## in general: components(parent)&components(vertex)) should be disconnnected
        
    # appearance
    # ----------
    def next_color(self, name=None):
        """ select next color type 
        If `fct_index`, select color function with this index
        """
        if name:
            index = [name for name,fct in self._color_fct].index(name)
            self._current_color = index
        else:
            self._current_color = (self._current_color+1)%len(self._color_fct)
            
        name,color_fct = self._color_fct[self._current_color]
        self.color = color_fct
        self.show_message('color model: '+name)
        ## return update, removed, added[, selection?]
        ##return self.get_nodes(), [],[]#,self.selection?
        
    def branch_color(self, vid):
        """ return the color associated to `vid`
        
        Standard TreeEditor Theme are, either:
         - one of the (string) key of treeeditor.THEME, such as 'default',  
           'highlight', 'highlight2'
         - an integer that is use to lookup in a colormap such that 
           THEME['colormap']
           
        TreeModel colors are:
         - 'default'   if `vid` is a successor
         - 'highlight' if `vid` is a branching vertex
        """ 
        if self.mtg.edge_type(vid)=='<': # successor
            return 'default'
        else:                            # branching
            return 'highlight'

    # file IO
    # -------
    @staticmethod
    def load_model(filename):
        """ load mtg from `filename`, then call `set_mtg` """
        import os.path
        
        if os.path.splitext(filename)[1] == '.bmtg':
           mtg = io.readfile(filename)
        else: # .mtg
           mtg = io.read_mtg_file(filename)
        return mtg
        
    def save_model_assert_filename(self, filename, default_ext=None):
        import os.path,shutil
        
        # test if filename is provided
        if filename is None or filename is False:
            filename = getattr(self,'mtgfile',None)
        if filename is None:
            raise TypeError("No file registered: use 'save as' first") 
        filename = str(filename)
        
        # test extension
        ext = os.path.splitext(filename)[1]
        if default_ext and len(ext)==0:
            ext = default_ext
            filename += ext
            
        # save a copy, in case the save fails
        if os.path.exists(filename):
            shutil.copy(filename,filename+'~')
            
        return filename, ext
        
    def save_model(self,filename=None):
        """ Save the mtg in file `filename` """ 
        filename,ext = self.save_model_assert_filename(filename, '.bmtg')
        
        if ext=='.bmtg':
           io.writefile(filename,self.mtg)
        else: # .mtg
            # readable mtg format from openalea.mtg module
            stdmtg, properties = self.get_standard_mtg()
            io.write_mtg_file(filename, stdmtg, properties=properties)
            
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
        
        xx = {}
        yy = {}
        zz = {}
        r  = {}
        for vid in self.get_nodes():
            xx[vid],yy[vid],zz[vid] = self.get_position(vid)
            r[vid]  = self.get_radius(vid)
        
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
    
    
    def default_directory(self):
        """ return a default directory to look for mtg files """
        import os
        if self.mtgfile:
            return os.path.dirname(self.mtgfile)
        else:
            return io.get_shared_data('mtgdata')
        
    # backup and undo
    # ---------------
    def push_backup(self, state=None):
        """ store a copy of mtg and given state in undo list (i.e. backup) """ 
        from copy import deepcopy
        if len(self.backupmtg) == self.maxbackup:
            del self.backupmtg[0]
        self.backupmtg.append([deepcopy(self.mtg),state])
        
    def undo(self):
        """ pop last backed up mtg and state, and return state """         
        if len(self.backupmtg) > 0:
            self.mtg, state = self.backupmtg.pop()
            return state
        else:
            return False
        
    def undo_number(self):
        """ number of undo available """
        return len(self.backupmtg)


        
class PASModel(TreeModel):
    """ A TreeModel which manages the Plant,Axe,Segment scales """
    def __init__(self, presenter=None, mtg=None, position='position', radius='radius'):
        """ create a PASModel to interact with given `mtg` 
        
        `mtg`: 
            either a MTG object or a file name to load with `load_model`
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
        TreeModel.__init__(self,presenter=presenter, mtg=mtg,
                           position=position, radius=radius)
        
        # color
        self._color_fct.append(('axe',self.axe_color))
        self._color_fct.append(('plant',self.plant_color))
    
    def set_mtg(self,mtg,filename=None, position=None, radius=None):
        """ set the `mtg` of this PASModel """
        TreeModel.set_mtg(self,mtg=mtg,filename=filename,position=position,radius=radius)
        self._segment_scale = 3
        
    # mtg accessor
    # ------------
    def get_axe(self, segment):
        """ return the axe id which own `segment` """    
        return self.mtg.complex(segment)
    def get_plant(self, segment):
        """ return the plant id which own `segment` """
        complex = self.mtg.complex
        return complex(complex(segment))
    
    # mtg edition
    # -----------
    def add_branching(self, segment, position):
        """ add a branching vertex (i.e. edge_type '+') to `segment` 

        And add an axe accordingly
        
        return 
          - the id of the created segment
          - the set of updated segment
        """
        parent_axe = self.get_axe(segment)
        child_seg,child_axe = self.mtg.add_child_and_complex(segment, edge_type='+')
        self.mtg.property('edge_type')[child_axe] = '+'
        self.set_position(child_seg,position)
        
        return child_seg, set([child_seg, segment])
        
    def replace_parent(self, segment, new_parent, edge_type=None):
        """ set the parent of `segment` by `new_parent` 
        
        Set the edge_type of `segment` to `edge_type`. If None (or not given),
        it select successor edge_type ('<') if the new parent does not already 
        have one. And it selects branching edge_type ('+') otherwise.
        If edge_type is '<', existing succesor of parent is set to branching.
        
        New axes are create if necessary
        
        return the set of updated vertices
        """
        prev_parent = self.parent(segment)
        up = TreeModel.replace_parent(self,segment,new_parent, edge_type)
        
        self._check_axe_validity(new_parent, up)

        # case where part of an axe has been attached as a branch to another
        # axe. The previous step find nothing but the *separeted* segments still 
        # have the same axe complex as its previous ancestor segments
        if prev_parent!=new_parent and self.get_axe(segment)==self.get_axe(prev_parent):
            self._new_axe_branch(segment, up)

        return up
        
    def remove_vertex(self, segment, reparent_child=True):
        """ remove `segment` from tree 
        
        If `reparent_children` is False, `segment` should not have child.
        Otherwise, reparent children preserving axe scale.
        
        return the set of updated vertices
        """
        axe   = self.get_axe(segment)
        plant = self.get_plant(segment)
        
        parent = self.parent(segment)
        children = self.children(segment)
        up = TreeModel.remove_vertex(self, segment, reparent_child)
        self._check_axe_validity(parent, up)

        # remove axe and plant if empty
        if len(self.mtg.components(axe))==0:
            self.mtg.remove_vertex(axe)
        if len(self.mtg.components(plant))==0:
            self.mtg.remove_vertex(plant)

        return up
        
    def remove_tree(self, segment):
        """ remove the subtree starting at `segment` """
        axe   = self.get_axe(segment)
        plant = self.get_plant(segment)
        
        up = TreeModel.remove_tree(self, segment)
        
        # remove empty axes
        if len(self.mtg.components(axe))==0:
            self.mtg.remove_tree(axe)
            
            # remove plant if empty
            if len(self.mtg.components(plant))==0:
                self.mtg.remove_tree(plant)
        else:
            for a in self.mtg.children(axe):
                self.mtg.remove_tree(axe)
            
        return up
        
        
        
    # private edition
    # ---------------
    # used internally by public edition methods
    def _new_axe_branch(self, child, up):
        """ create missing branch axe 
        segment scale should be already connected 
        """
        parent_axe = self.get_axe(self.parent(child))
        new_branch = self.mtg.add_child(parent_axe, edge_type='+')
        successors = list(_mtgalgo.local_axis(self.mtg,child))
        up.update(successors)
        
        self._change_axe(successors, new_branch)
            
    def _change_axe(self, successors, axe):
        """ attach all successors to axe """
        g = self.mtg
        for sid in successors:
            g.add_component(axe,sid)

    def _change_plant(self, axes, plant):
        """ attach all axes to plant - blindly - """
        g = self.mtg
        for aid in axes:
            g.add_component(plant,aid)
            
    def _check_axe_validity(self, segment, up):
        """ check for structural validity of axe scale """
        edge = lambda vid: self.mtg.edge_type(vid)
        
        segment_axe = self.get_axe(segment)
        
        for child in self.children(segment):
            child_axe = self.get_axe(child)
            if edge(child)=='<' and child_axe!=segment_axe:
                # successor should have same axe as parent
                successors = list(_mtgalgo.local_axis(self.mtg,child))
                up.update(successors)
                
                self._change_axe(successors, segment_axe)
                    
            elif edge(child)=='+' and child_axe==segment_axe:
                # branch should not have same axe as parent 
                self._new_axe_branch(child, up)

    def _check_plant_validity(self, segment, up):
        """ check that all descendants of segment's axe have same plant """
        plant = self.get_plant(segment)
        
        axes = []
        map(axes.extend, (_mtgalgo.descendants(axe) for axe in self.mtg.components(plant)))
            
        complex = self.mtg.complex
        self._change_plant([a for a in axes if complex(a)!=plant])
        
    
    # appearance
    # ----------
    def axe_color(self, segment):
        """ return the color associated to `segment` axe """ 
        return self.get_axe(segment)
    def plant_color(self, segment):
        """ return the color associated to `segment` plant """ 
        return self.get_plant(segment)


