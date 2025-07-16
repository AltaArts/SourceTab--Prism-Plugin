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
#                SOURCE TAB PLUGIN
#
#                 Joshua Breckeen
#                    Alta Arts
#                josh@alta-arts.com
#
#   This PlugIn adds an additional Main Tab to the
#   Prism Standalone Project Browser.
#
#   This adds functionality to Ingest Media such as Camera clips,
#   as well as handling Proxy's and Metadata.
#
#
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

from MetadataEditor_ui import Ui_w_metadataEditor


logger = logging.getLogger(__name__)


class MetadataEditor(QWidget, Ui_w_metadataEditor):
    def __init__(self, core, origin, parent=None):
        super(MetadataEditor, self).__init__(parent)

        self.core = core
        self.sourceBrowser = origin

        #   Setup UI from Ui_w_sourceFunctions
        self.setupUi(self)
        self.setToolTips()
        self.configureUI()
        self.connectEvents()

        self.updateUI()

        logger.debug("Loaded Metadata Editor")


    @err_catcher(name=__name__)
    def setToolTips(self):
        pass
        


    @err_catcher(name=__name__)
    def connectEvents(self):
        pass


    @err_catcher(name=__name__)
    def configureUI(self):
        #   Set up Sizing and Position
        screen = QGuiApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        calc_width = screen_geometry.width() // 1.5
        width = max(1700, min(2500, calc_width))
        calc_height = screen_geometry.height() // 1.2
        height = max(900, min(2500, calc_height))
        x_pos = (screen_geometry.width() - width) // 2
        y_pos = (screen_geometry.height() - height) // 2
        self.setGeometry(x_pos, y_pos, width, height)

        #   Resize Splitter Panels
        QTimer.singleShot(10, lambda: self.setSplitterToThirds())

        # self.setStyleSheet("background-color: #465A78;")

        self.setStyleSheet("""
            #w_metadataEditor {
                background-color: #323537;
                color: #ccc;
            }
        """)


    #   Resizes Splitter Panels to Equal Thirds
    @err_catcher(name=__name__)
    def setSplitterToThirds(self):
        totalWidth = self.splitter.size().width()
        oneThird = totalWidth // 3
        self.splitter.setSizes([oneThird, oneThird, totalWidth - 2 * oneThird])



    @err_catcher(name=__name__)
    def updateUI(self):
        pass


    @err_catcher(name=__name__)
    def openInExplorer(self, path):
        self.sourceBrowser.openInExplorer(os.path.normpath(path))

