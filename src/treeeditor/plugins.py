""" Plugin for OpenAleaLab """

from openalea.deploy.shared_data import shared_data
import treeeditor

ICON = shared_data(treeeditor, 'icon_rhizolab.png')


class TreeEditorWidgetPlugin(object):

    name = 'TreeEditor'
    alias = 'TreeEditor'
    icon = ICON

    def __call__(self):
        """ Create widget """

        # widget
        from treeeditor.editor import TreeEditorWidget
        return TreeEditorWidget

    def graft(self, **kwds):
        mainwindow = kwds['oa_mainwin'] if 'oa_mainwin' in kwds else None
        applet = kwds['applet'] if 'applet' in kwds else None
        if applet is None or mainwindow is None:
            return

        mainwindow.add_applet(applet, self.alias, area='outputs')

        # actions
        actions = applet.get_plugin_actions()
        if actions:
            for action in actions:
                # Add actions in PanedMenu
                mainwindow.menu.addBtnByAction('TreeEditor', *action)

                # add action in classical menu
                group_name, act, btn_type = action
                mainwindow.add_action_to_existing_menu(action=act, menu_name='TreeEditor', sub_menu_name=group_name)

