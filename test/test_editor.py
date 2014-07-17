""" test to start the editor """

def test_import_qt():
    from openalea.vpltk.qt import QtGui
    return QtGui
    
def test_start_editor():
    from treeeditor import editor
    QtGui = test_import_qt()
    qapp = QtGui.QApplication([])
    editor.TreeEditorWidget()