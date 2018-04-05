# -*- coding: utf-8 -*-
__revision__ = "$Id: $"

import sys
import os

from setuptools import setup, find_packages

# Reads the metainfo file
from openalea.deploy.metainfo import read_metainfo
metainfo = read_metainfo('metainfo.ini', verbose=True)


# Packages list, namespace and root directory of packages

packages = find_packages('src')
package_dir = dict([('','src')])

# dependencies to other eggs
setup_requires = ['openalea.deploy']
install_requires = []

# web sites where to find eggs
dependency_links = ['http://openalea.gforge.inria.fr/pi']
setup(
    name            = metainfo['name'],
    version         = metainfo['version'],
    description     = metainfo['description'],
    long_description= metainfo['long_description'],
    author          = metainfo['authors'],
    author_email    = metainfo['authors_email'],
    url             = metainfo['url'],
    license         = metainfo['license'],
    keywords        = metainfo.get('keywords',''),

    # package installation
    packages= packages,
    package_dir= package_dir,

    # Namespace packages creation by deploy
    #namespace_packages = [metainfo['namespace']],
    #create_namespaces = False,
    zip_safe= False,

    # Dependencies
    setup_requires = setup_requires,
    install_requires = install_requires,
    dependency_links = dependency_links,

    # Binary installation (if necessary)
    # Define what to execute with scons
    # Eventually include data in your package
    # (flowing is to include all versioned files other than .py)
    include_package_data = True,
    # (you can provide an exclusion dictionary named exclude_package_data to remove parasites).
    # alternatively to global inclusion, list the file to include
    package_data = {'' : ['*.png','*.jpg', '*.ini','*.pyd', '*.so'],},
    share_dirs={'share':'share', 'test':'test'},

    # postinstall_scripts = ['',],

    # Declare scripts and wralea as entry_points (extensions) of your package
    entry_points = {
        #'wralea' : ['treeeditor = vplants.treeeditor_wralea' if has_project else 'treeeditor = treeeditor_wralea' ],
         'gui_scripts':  ['TreeEditor = treeeditor.editor:main'],
         'oalab.applet': ['TreeEditorApp = treeeditor.plugins:TreeEditorWidgetPlugin'],
        },

    )


