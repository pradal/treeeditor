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

from openalea.oalab.plugins.labs.minilab import MiniLab


class TreeEditorLabPlugin(MiniLab):
    name = 'treeeditor'
    alias = 'Rhizome'
    icon = ICON
    applet_names = [
        'TreeEditor',
        'ProjectManager2',
        'ControlManager',
        'PkgManagerWidget',
        'EditorManager',
        'Logger',
        'HelpWidget',
        'HistoryWidget',
        'Viewer3D',
        'World',
        'Plot2d',
    ]

    def __call__(self, mainwin=None):
        if mainwin is None:
            return self.__class__

        from openalea.vpltk.plugin import iter_plugins
        session = mainwin.session

        # 1. Load applet
        # 2. Place applet following given order,
        plugins = {}
        for plugin in iter_plugins('oalab.applet', debug=session.debug_plugins):
            if plugin.name in self.applet_names:
                plugin = plugin()
                plugins[plugin.name] = plugin
                mainwin.add_plugin(plugin)

        # 3. Once the applet is loaded, init them
        mainwin.initialize()
