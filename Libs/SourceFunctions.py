# -*- coding: utf-8 -*-
#
####################################################
#
# PRISM - Pipeline for animation and VFX projects
#
# www.prism-pipeline.com
#
# contact: contact@prism-pipeline.com
#
####################################################
#
#
# Copyright (C) 2016-2023 Richard Frangenberg
# Copyright (C) 2023 Prism Software GmbH
#
# Licensed under GNU LGPL-3.0-or-later
#
# This file is part of Prism.
#
# Prism is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Prism is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with Prism.  If not, see <https://www.gnu.org/licenses/>.
####################################################
#
#           ########### PLUGIN
#           by Joshua Breckeen
#                Alta Arts
#
#   This PlugIn adds an additional tab to the Prism Settings menu to ##########################
#   allow a user to choose a directory that contains scene presets.###############################
#
        #       TODO


####################################################



import os
import sys
import logging


from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *


pluginPath = os.path.dirname(os.path.dirname(__file__))
uiPath = os.path.join(pluginPath, "Libs", "UserInterfaces")
sys.path.append(uiPath)

from PrismUtils.Decorators import err_catcher


from SourceFunctions_ui import Ui_w_sourceFunctions

from PopupWindows import NamingPopup


logger = logging.getLogger(__name__)


class SourceFunctions(QWidget, Ui_w_sourceFunctions):
    def __init__(self, core, origin, parent=None):
        super(SourceFunctions, self).__init__(parent)

        self.core = core
        self.sourceBrowser = origin

        self.setupUi(self)  # This comes from Ui_w_sourceFunctions
        self.connections()



    @err_catcher(name=__name__)
    def connections(self):
        self.b_openDestDir.clicked.connect(lambda: self.openInExplorer(self.sourceBrowser.le_destPath.text()))
        self.b_ovr_config_fileNaming.clicked.connect(self.configFileNaming)
        self.b_ovr_config_proxy.clicked.connect(self.configProxy)
        self.b_ovr_config_metadata.clicked.connect(self.configMetadata)


    @err_catcher(name=__name__)
    def openInExplorer(self, path):
        self.sourceBrowser.openInExplorer(os.path.normpath(path))


    @err_catcher(name=__name__)
    def configFileNaming(self):

        destList = self.sourceBrowser.tw_destination
        row_count = destList.rowCount()

        if row_count < 2:
            fileName = "EXAMPLE"
        
        else:
            fileItem = self.sourceBrowser.tw_destination.cellWidget(0, 0)
            filePath = fileItem.getSource_mainfilePath()
            fileName = os.path.basename(filePath)

        NamingPopup.display(fileName)




    @err_catcher(name=__name__)
    def configProxy(self):
        self.core.popup("Configureing Proxy Not Yet Implemented")


    @err_catcher(name=__name__)
    def configMetadata(self):
        self.core.popup("Configureing Metadata Not Yet Implemented")