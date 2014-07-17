
def test_load_mtg():
    from treeeditor.io import get_shared_data
    from treeeditor.tree.model import TreeModel
    from openalea.mtg import MTG
    
    mtg = get_shared_data('root.bmtg')
    mtg = TreeModel.load_model(mtg)
    assert isinstance(mtg, MTG)

    return mtg
    
    
def save_mtg(mtg, model_class):
    from treeeditor.io import get_shared_data
    import os
    
    model = model_class(mtg=mtg, presenter=None)
    
    bmtg_file = get_shared_data('tmp_save.bmtg')
    mtg_file  = get_shared_data('tmp_save.mtg')
    try:
        model.save_model(bmtg_file)
        assert os.path.exists(bmtg_file),\
               model_class.__name__+': file not saved, or not in correct place'
        os.remove(bmtg_file)

        model.save_model(mtg_file)
        assert os.path.exists(mtg_file),\
               model_class.__name__+': file not saved, or not in correct place'
        os.remove(mtg_file)

    finally:
        if os.path.exists(bmtg_file):
            os.remove(bmtg_file)
        if os.path.exists(mtg_file):
            os.remove(mtg_file)
            
def test_save_mtg():
    from treeeditor.tree.model import TreeModel, PASModel

    mtg = test_load_mtg()
    save_mtg(mtg, TreeModel)
    save_mtg(mtg, PASModel)

    ##todo: test save to .mtg (no binary)
