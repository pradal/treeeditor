
def test_PASModel_add_branching():
    from treeeditor.tree.model import PASModel
    m = PASModel()
    s0 = m.new_vertex(position=(0,0,0))
    s1 = m.add_branching(s0,(1,0,0))[0]
    
    g  = m.mtg
    a0 = g.complex(s0)
    a1 = g.complex(s1)
    edg = g.property('edge_type')
    
    assert g.parent(s1)==s0, 'parent of new segment is not correct'
    assert g.parent(a1)==a0, 'parent of new axe is not the axe of parent segment'    
    assert edg[s1]=='+', 'new segment is not a branch'
    assert edg[a1]=='+', 'new axe is not a branch'
    assert g.complex(g.parent(s1))==g.parent(g.complex(s1)), 'branching &| parenting is not correct'

def test_PASModel_remove_vertex():
    from treeeditor.tree.model import PASModel
    m = PASModel()
    s0 = m.new_vertex(position=(0,0,0))   # plant 1 - axe1
    s1 = m.add_successor(s0,(1,0,0))[0]
    s2 = m.add_branching(s0,(1,2,0))[0]   # plant 1 - axe2
    s3 = m.new_vertex(position=(3,0,0))   # plant 2

    a0 = m.get_axe(s0)
    a2 = m.get_axe(s2)
    p0 = m.get_plant(s0)
    p3 = m.get_plant(s3)
    
    m.remove_vertex(s1)
    assert not m.mtg.has_vertex(s1), 'vertex was not deleted from mtg'
    m.remove_vertex(s2)
    assert not m.mtg.has_vertex(s2), 'vertex was not deleted from mtg'
    assert not m.mtg.has_vertex(a2), 'axe was not deleted from mtg'
    m.remove_vertex(s0)
    assert not m.mtg.has_vertex(s0), 'vertex was not deleted from mtg'
    assert not m.mtg.has_vertex(a0), 'axe was not deleted from mtg'
    assert not m.mtg.has_vertex(p0), 'plant was not deleted from mtg'
    
    assert m.mtg.has_vertex(p3), 'plant should not have been deleted from mtg'

def test_TreeModel_remove_successor():
    # test remove successor => child should keep edge_type
    from treeeditor.tree.model import TreeModel
    m = TreeModel()
    v1 = m.new_vertex(position=(0,0,0))
    v2 = m.add_successor(v1,(0,0,0))[0] 
    v3 = m.add_successor(v2,(0,0,0))[0]
    v4 = m.add_successor(v3,(0,0,0))[0]
    v5 = m.add_branching(v3,(0,0,0))[0]
    
    up = m.remove_vertex(v3)
    
    edg = m.mtg.property('edge_type')
    assert edg[v4]=='<',  'successor of removed vertex is not successor anymore'
    assert edg[v5]=='+',  'branch child of removed vertex is not branch anymore'
    assert up==set((v2,v4,v5)), 'unexpected update node list:'+str(up)
    
def test_TreeModel_remove_branch_no_successor_sibling():
    # test remove branch & parent has not successor => children keep edge_type
    from treeeditor.tree.model import TreeModel
    m = TreeModel()
    v1 = m.new_vertex(position=(0,0,0))
    v2 = m.add_successor(v1,(0,0,0))[0]
    v3 = m.add_branching(v2,(0,0,0))[0]
    v4 = m.add_successor(v3,(0,0,0))[0]
    v5 = m.add_branching(v3,(0,0,0))[0]
    
    up = m.remove_vertex(v3)
    
    edg = m.mtg.property('edge_type')
    assert edg[v4]=='<',  'successor of removed vertex is not successor anymore'
    assert edg[v5]=='+',  'branch child of removed vertex is not branch anymore'
    assert up==set((v2,v4,v5)), 'unexpected update node list:'+str(up)
    
def test_TreeModel_remove_branch_with_successor_sibling():
    # test remove branch & parent has successor => children should all be '+'
    from treeeditor.tree.model import TreeModel
    m = TreeModel()
    v1 = m.new_vertex(position=(0,0,0))
    v2 = m.add_successor(v1,(0,0,0))[0]
    v2s= m.add_successor(v2,(0,0,0))[0]
    v3 = m.add_branching(v2,(0,0,0))[0]
    v4 = m.add_successor(v3,(0,0,0))[0]
    v5 = m.add_branching(v3,(0,0,0))[0]
    
    up = m.remove_vertex(v3)
    
    edg = m.mtg.property('edge_type')
    assert edg[v4]=='+',  'successor of removed vertex should have become branch'
    assert edg[v5]=='+',  'branch child of removed vertex is not branch anymore'
    assert up==set((v2,v4,v5)), 'unexpected update node list:'+str(up)
