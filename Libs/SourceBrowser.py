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
import subprocess
import logging
import traceback
from collections import OrderedDict, deque
import shutil
import uuid
import hashlib
from datetime import datetime
from time import time
from functools import partial
import re

##  FOR TESTING
from functools import wraps




PRISMROOT = r"C:\Prism2"                                            ###   TODO
prismRoot = os.getenv("PRISM_ROOT")
if not prismRoot:
    prismRoot = PRISMROOT

# if __name__ == "__main__":
#     sys.path.append(os.path.join(prismRoot, "Scripts"))
#     import PrismCore

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *


rootScripts = os.path.join(prismRoot, "Scripts")                                    #   TODO - CLEANUP
pluginPath = os.path.dirname(os.path.dirname(__file__))
pyLibsPath = os.path.join(pluginPath, "PythonLibs", "Python311")
uiPath = os.path.join(pluginPath, "Libs", "UserInterfaces")
iconDir = os.path.join(uiPath, "Icons")
audioDir = os.path.join(uiPath, "Audio")
sys.path.append(os.path.join(rootScripts, "Libs"))
sys.path.append(pyLibsPath)
sys.path.append(pluginPath)
sys.path.append(uiPath)


from playsound.playsound import playsound
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

import exiftool


from PrismUtils import PrismWidgets
from PrismUtils.Decorators import err_catcher


import TileWidget as TileWidget
from SourceFunctions import SourceFunctions
from PopupWindows import DisplayPopup, WaitPopup

import SourceBrowser_ui                                                 #   TODO


#   Colors
COLOR_GREEN = QColor(0, 150, 0)
COLOR_BLUE = QColor(115, 175, 215)
COLOR_ORANGE = QColor(255, 140, 0)
COLOR_RED = QColor(200, 0, 0)
COLOR_GREY = QColor(100, 100, 100)

#   Sounds
SOUND_SUCCESS = os.path.join(audioDir, "Success.wav")
SOUND_ERROR = os.path.join(audioDir, "Error.wav")


SOURCE_ITEM_HEIGHT = 70                                         #   TODO - Think about moving to Settings?
SOURCE_DIR_HEIGHT = 30 

logger = logging.getLogger(__name__)



#   StopWatch Decorator
def stopWatch(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        timer = QElapsedTimer()
        timer.start()
        
        result = func(*args, **kwargs)
        
        elapsed_sec = round(timer.elapsed() / 1000.0, 2)
        print(f"[STOPWATCH]: Method '{func.__name__}' took {elapsed_sec:.2f} seconds")
        
        return result
    return wrapper



class SourceBrowser(QWidget, SourceBrowser_ui.Ui_w_sourceBrowser):
    def __init__(self, origin, core, projectBrowser=None, refresh=True):
        QWidget.__init__(self)
        self.setupUi(self)
        self.plugin = origin
        self.core = core
        self.projectBrowser = projectBrowser

        logger.debug("Initializing Source Browser")

        self.core.parentWindow(self)

        self.audioFormats = [".wav", ".aac", ".mp3", ".pcm", ".aiff", ".flac", ".alac", ".ogg", ".wma"]

        self.filterStates_source = {
                                    "Videos": True,
                                    "Images": True,
                                    "Audio": True,
                                    "Folders": True,
                                    "Other": True,
                                    }
        self.filterStates_dest = {
                                  "Videos": True,
                                  "Images": True,
                                  "Audio": True,
                                  "Folders": True,
                                  "Other": True,
                                  }


        self._sourceRowWidgets = []
        self._destinationRowWidgets = []


        #   Initialize Variables
        self.selectedTiles = set()
        self.lastClickedTile = None

        self.resolvedProxyPaths = None
        self.proxyEnabled = False
        self.proxyMode = None
        self.proxySettings = None
        self.ffmpegPresets = None
        self.calculated_proxyMults = []
        self.nameMods = []
        self.transferList = []
        self.initialized = False
        self.closeParm = "closeafterload"

        self.exifToolEXE = self.getExiftool()

        self.setupIcons()

        #   Load UI
        self.loadLayout()
        #   Reset Total Prog Bar
        self.reset_ProgBar()
        #   Signal Connections
        self.connectEvents()
        #   Load Settings from Prism Project Settings
        self.loadSettings()
        #   Setup Worker Threadpools and Semephore Slots
        self.setupThreadpools()

        #   Refreshes and Initializes
        self.refreshSourceItems()
        self.refreshDestItems()
        self.configTransUI("idle")
        self.setTransferStatus("Idle")

        #   Add Callback for SourceTab
        self.core.callback(name="onSourceBrowserOpen", args=[self])

        if refresh:
            self.entered()



    @err_catcher(name=__name__)                                         #   TODO - GET RID OF THIS WITHOUT ERROR
    def entityChanged(self, *args, **kwargs):
        pass
    @err_catcher(name=__name__)                                         #   TODO - GET RID OF THIS WITHOUT ERROR
    def getSelectedContext(self, *args, **kwargs):
        pass




    @err_catcher(name=__name__)
    def entered(self, prevTab=None, navData=None):
        if not self.initialized:
            self.oiio = self.core.media.getOIIO()

        #   Resize Splitter Panels
        QTimer.singleShot(10, lambda: self.setSplitterToThirds())


    #   Resizes Splitter Panels to Equal Thirds
    def setSplitterToThirds(self):
        totalWidth = self.splitter.size().width()
        oneThird = totalWidth // 3
        self.splitter.setSizes([oneThird, oneThird, totalWidth - 2 * oneThird])



    @err_catcher(name=__name__)
    def setupIcons(self):
        icon_names = [
            "sequence", "image", "video", "audio",
            "folder", "file", "error", "proxy",
            "date", "disk"
        ]

        for name in icon_names:
            path = os.path.join(iconDir, f"{name}.png")
            icon = self.core.media.getColoredIcon(path)
            setattr(self, f"icon_{name}", icon)


    @err_catcher(name=__name__)
    def loadLayout(self):
        #   Set Icons
        upIcon = self.getIconFromPath(os.path.join(iconDir, "up.png"))
        dirIcon = self.getIconFromPath(os.path.join(iconDir, "folder.png"))
        refreshIcon = self.getIconFromPath(os.path.join(iconDir, "reset.png"))
        tipIcon = self.getIconFromPath(os.path.join(iconDir, "help.png"))
        sortIcon = self.getIconFromPath(os.path.join(iconDir, "sort.png"))
        filtersIcon = self.getIconFromPath(os.path.join(iconDir, "filters.png"))
        sequenceIcon = self.getIconFromPath(os.path.join(iconDir, "sequence.png"))

        ##   Source Panel
        #   Set Button Icons
        self.b_sourcePathUp.setIcon(upIcon)
        self.b_browseSource.setIcon(dirIcon)
        self.b_refreshSource.setIcon(refreshIcon)
        self.b_sourceFilter_sort.setIcon(sortIcon)
        self.b_sourceFilter_filtersEnable.setIcon(filtersIcon)
        self.b_sourceFilter_combineSeqs.setIcon(sequenceIcon)
        self.b_tips_source.setIcon(tipIcon)

        #   Setup Cheatsheets
        sourceTip = self.getCheatsheet("source", tip=True)
        self.b_tips_source.setToolTip(sourceTip)

        destTip = self.getCheatsheet("dest", tip=True)
        self.b_tips_dest.setToolTip(destTip)

        #   Set Cheatsheet Button Size
        self.b_tips_source.setFixedWidth(30)
        self.b_tips_dest.setFixedWidth(30)

        #   Source Table setup
        self.lw_source.setObjectName("sourceTable")

        self.lw_source.setAcceptDrops(True)
        self.lw_source.dragEnterEvent = partial(self.onDragEnterEvent)
        self.lw_source.dragMoveEvent = partial(self.onDragMoveEvent, self.lw_source, "sourceTable")
        self.lw_source.dragLeaveEvent = partial(self.onDragLeaveEvent, self.lw_source)
        self.lw_source.dropEvent = partial(self.onDropEvent, self.lw_source, "source")

        ##  Destination Panel
        #   Set Button Icons
        self.b_destPathUp.setIcon(upIcon)
        self.b_browseDest.setIcon(dirIcon)
        self.b_refreshDest.setIcon(refreshIcon)
        self.b_destFilter_sort.setIcon(sortIcon)
        self.b_destFilter_filtersEnable.setIcon(filtersIcon)
        self.b_destFilter_combineSeqs.setIcon(sequenceIcon)
        self.b_tips_dest.setIcon(tipIcon)

        #   Destination Table setup
        self.lw_destination.setObjectName("destTable")

        self.lw_destination.setAcceptDrops(True)
        self.lw_destination.dragEnterEvent = partial(self.onDragEnterEvent)
        self.lw_destination.dragMoveEvent = partial(self.onDragMoveEvent, self.lw_destination, "destTable")
        self.lw_destination.dragLeaveEvent = partial(self.onDragLeaveEvent, self.lw_destination)
        self.lw_destination.dropEvent = partial(self.onDropEvent, self.lw_destination, "dest")

        ##  Right Side Panel
        self.lo_rightPanel = QVBoxLayout()

        #   MediaPlayerToolbar
        self.lo_playerToolbar = QHBoxLayout()

        #   Player Enable Switch
        self.chb_enablePlayer = QCheckBox("Enable Media Player")

        #   Prefer Proxis Switch
        self.chb_preferProxies = QCheckBox("Prefer Proxies")

        #   Add Widgets to MediaPlayerToolbar
        self.lo_playerToolbar.addWidget(self.chb_enablePlayer)
        self.spacer1 = QSpacerItem(40, 0, QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.lo_playerToolbar.addItem(self.spacer1)
        self.lo_playerToolbar.addWidget(self.chb_preferProxies)

        # Media Player Import
        self.mediaPlayer = MediaPlayer(self)

        #   Functions Import
        self.sourceFuncts = SourceFunctions(self.core, self)

        #   Add Panels to the Right Panel
        self.lo_rightPanel.addLayout(self.lo_playerToolbar)
        self.lo_rightPanel.addWidget(self.mediaPlayer)
        self.lo_rightPanel.addWidget(self.sourceFuncts)

        #   Create Container to hold the Right Panel
        self.w_rightPanelContainer = QWidget()
        self.w_rightPanelContainer.setLayout(self.lo_rightPanel)

        #   Add Right Panel Container to the Splitter
        self.splitter.addWidget(self.w_rightPanelContainer)

        self.setStyleSheet("QSplitter::handle{background-color: transparent}")

        self.setToolTips()

        logger.debug("Loaded SourceTab UI")


    @err_catcher(name=__name__)                                                     #   TODO - FINISH
    def setToolTips(self):
        tip = "Go to Parent Directory"
        self.b_sourcePathUp.setToolTip(tip)
        self.b_destPathUp.setToolTip(tip)

        tip = ("Source Media Directory (required)\n\n"
               "Please add Source by:\n"
               "   - Clicking the Browser button\n"
               "   - Typing the Direcory Path\n"
               "   - Paste Path\n"
               "   - Drag/drop Media Folder into List Window")
        self.le_sourcePath.setToolTip(tip)

        tip = ("Destination Directory (required)\n\n"
               "Please add Destination by:\n"
               "   - Clicking the Browser button\n"
               "   - Typing the Direcory Path\n"
               "   - Paste Path\n"
               "   - Drag/drop Destination Folder into List Window")
        self.le_destPath.setToolTip(tip)

        tip = "Open File Explorer to Choose Directory"
        self.b_browseSource.setToolTip(tip)
        self.b_browseDest.setToolTip(tip)

        self.b_refreshSource.setToolTip("Reload Source List")
        self.b_refreshDest.setToolTip("Reload Destination List")

        tip = ("Sorting\n\n"
               "   Click to Open Sort Menu")
        self.b_sourceFilter_sort.setToolTip(tip)
        self.b_destFilter_sort.setToolTip(tip)

        tip = ("File Filters\n\n"
               "   Click to Enable View Filters\n"
               "   Right-click to Select Filters")
        self.b_sourceFilter_filtersEnable.setToolTip(tip)
        self.b_destFilter_filtersEnable.setToolTip(tip)

        tip = "Group Image Sequences"
        self.b_sourceFilter_combineSeqs.setToolTip(tip)
        self.b_destFilter_combineSeqs.setToolTip(tip)

        tip = "Select (check) all Items in the List"
        self.b_source_checkAll.setToolTip(tip)
        self.b_dest_checkAll.setToolTip(tip)

        tip = "Un-Select all Items in the List"
        self.b_source_uncheckAll.setToolTip(tip)
        self.b_dest_uncheckAll.setToolTip(tip)

        self.b_source_addSel.setToolTip("Add Selected (checked) items to the Destination List.")
        self.b_dest_clearSel.setToolTip("Remove Selected Items")
        self.b_dest_clearAll.setToolTip("Remove All Items")

        tip = "Enable/Disable Media Player"
        self.chb_enablePlayer.setToolTip(tip)

        tip = ("Use Proxy file in the Media Player\n"
               "(if the Proxy exists)\n\n"
               "This does not affect the Transfer")
        self.chb_preferProxies.setToolTip(tip)


    @err_catcher(name=__name__)                                                     #   TODO - FINISH
    def getCheatsheet(self, mode, tip=False):

        cheatSheet = '''
Up-Arror:  Go up one level in the Directory
Folder:  Open Explorer to Choose Source Directory
Double-Click Item:  Toogles the Item's Checkbox
Double-Click Thumbnail:  Opens Media in External Player
Double-Click PXY Icon:  Opens Proxy Media in External Player

'''

        if tip:
            return cheatSheet
        
        else:
            DisplayPopup.display(cheatSheet, title="Help")


    # @err_catcher(name=__name__)
    # def setHeaderHeight(self, height):
    #     spacing = self.w_identifier.layout().spacing()
    #     self.w_entities.w_header.setMinimumHeight(height + spacing)
    #     self.l_identifier.setMinimumHeight(height)
    #     self.l_version.setMinimumHeight(height)
    #     self.mediaPlayer.l_layer.setMinimumHeight(height)
    #     self.headerHeightSet = True


    @err_catcher(name=__name__)
    def connectEvents(self):

        # self.b_refresh.clicked.connect(self.refreshRender)

        # self.lw_source.itemSelectionChanged.connect(self.sourceClicked)
        # self.lw_destination.itemSelectionChanged.connect(self.sourceClicked)
        # self.lw_destination.mmEvent = self.lw_destination.mouseMoveEvent
        # self.lw_destination.mouseMoveEvent = lambda x: self.w_preview.mediaPlayer.mouseDrag(x, self.lw_destination)
        # self.lw_destination.itemDoubleClicked.connect(self.onVersionDoubleClicked)

        #   Connect Right Click Menus
        #   Tables
        self.lw_source.setContextMenuPolicy(Qt.CustomContextMenu)
        self.lw_source.customContextMenuRequested.connect(lambda x: self.rclList(x, self.lw_source))
        self.lw_destination.setContextMenuPolicy(Qt.CustomContextMenu)
        self.lw_destination.customContextMenuRequested.connect(lambda x: self.rclList(x, self.lw_destination))

        #   Source Filters
        self.b_sourceFilter_filtersEnable.setContextMenuPolicy(Qt.CustomContextMenu)
        self.b_sourceFilter_filtersEnable.customContextMenuRequested.connect(lambda: self.filtersRCL("source"))
        #   Destination Filters
        self.b_destFilter_filtersEnable.setContextMenuPolicy(Qt.CustomContextMenu)
        self.b_destFilter_filtersEnable.customContextMenuRequested.connect(lambda: self.filtersRCL("destination"))

        #   Source Buttons
        self.b_sourcePathUp.clicked.connect(lambda: self.goUpDir("source"))
        self.le_sourcePath.returnPressed.connect(lambda: self.onPasteAddress("source"))
        self.b_browseSource.clicked.connect(lambda: self.explorer("source"))
        self.b_refreshSource.clicked.connect(self.refreshSourceItems)
        self.b_sourceFilter_sort.clicked.connect(lambda: self.showSortMenu("source"))
        self.b_sourceFilter_filtersEnable.toggled.connect(lambda: self.refreshSourceTable())
        self.b_sourceFilter_combineSeqs.toggled.connect(self.refreshSourceItems)
        self.b_tips_source.clicked.connect(lambda: self.getCheatsheet("source", tip=False))
        self.b_source_checkAll.clicked.connect(lambda: self.selectAll(checked=True, mode="source"))
        self.b_source_uncheckAll.clicked.connect(lambda: self.selectAll(checked=False, mode="source"))
        self.b_source_addSel.clicked.connect(self.addSelected)

        #   Destination Buttons
        self.b_destPathUp.clicked.connect(lambda: self.goUpDir("dest"))
        self.le_destPath.returnPressed.connect(lambda: self.onPasteAddress("dest"))
        self.b_browseDest.clicked.connect(lambda: self.explorer("dest"))
        self.b_refreshDest.clicked.connect(lambda: self.refreshDestItems(restoreSelection=True))
        self.b_destFilter_sort.clicked.connect(lambda: self.showSortMenu("destination"))
        self.b_destFilter_filtersEnable.toggled.connect(lambda: self.refreshDestTable())
        self.b_destFilter_combineSeqs.toggled.connect(self.refreshDestItems)
        self.b_tips_dest.clicked.connect(lambda: self.getCheatsheet("dest", tip=False))
        self.b_dest_checkAll.clicked.connect(lambda: self.selectAll(checked=True, mode="dest"))
        self.b_dest_uncheckAll.clicked.connect(lambda: self.selectAll(checked=False, mode="dest"))
        self.b_dest_clearSel.clicked.connect(lambda: self.clearTransferList(checked=True))
        self.b_dest_clearAll.clicked.connect(lambda: self.clearTransferList())

        #   Media Player
        self.chb_enablePlayer.toggled.connect(self.toggleMediaPlayer)
        self.chb_preferProxies.toggled.connect(self.togglePreferProxies)

        #   Functions Panel
        self.sourceFuncts.chb_ovr_proxy.toggled.connect(self.toggleProxy)
        self.sourceFuncts.chb_ovr_fileNaming.toggled.connect(lambda: self.modifyFileNames())
        self.sourceFuncts.b_transfer_start.clicked.connect(self.startTransfer)
        self.sourceFuncts.b_transfer_pause.clicked.connect(self.pauseTransfer)
        self.sourceFuncts.b_transfer_resume.clicked.connect(self.resumeTransfer)
        self.sourceFuncts.b_transfer_cancel.clicked.connect(self.cancelTransfer)
        self.sourceFuncts.b_transfer_reset.clicked.connect(self.resetTransfer)


####    MENUS   ####

    #   Right Click List for Source / Destination Tables (not on an item)
    @err_catcher(name=__name__)
    def rclList(self, pos, lw):
        cpos = QCursor.pos()
        item = lw.itemAt(pos)

        rcmenu = QMenu(self)

        if lw == self.lw_source and not item:
            refreshAct = QAction("Refresh List", self)
            refreshAct.triggered.connect(self.refreshSourceItems)
            rcmenu.addAction(refreshAct)
                # refresh = self.refreshSourceItems

        elif lw == self.lw_destination and not item:
            clearAct = QAction("Clear Transfer List", self)
            clearAct.triggered.connect(self.clearTransferList)
            rcmenu.addAction(clearAct)

        if rcmenu.isEmpty():
            return False

        rcmenu.exec_(cpos)


    #   Item Sorting Menu
    @err_catcher(name=__name__)
    def showSortMenu(self, table):
        cpos = QCursor.pos()
        sortMenu = QMenu(self)

        opts = self.sortOptions.get(table, {
            "groupTypes": True,
            "sortType": "name",
            "ascending": True
        })

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(10, 10, 10, 10)

        #   Group Types Checkbox
        cb_groupTypes = QCheckBox("Group Types")
        cb_groupTypes.setChecked(opts.get("groupTypes", True))
        cb_groupTypes.setToolTip("Sort File Items ")
        layout.addWidget(cb_groupTypes)

        #   Separator
        layout.addWidget(QGroupBox())

        #   Sort Type Radio Buttons
        sortTypeGroup = QButtonGroup(sortMenu)
        sortTypes = ["Name", "Date", "Size"]
        radioButtons = {}
        for label in sortTypes:
            rb = QRadioButton(label)
            if label.lower() == opts.get("sortType", "name").lower():
                rb.setChecked(True)
            sortTypeGroup.addButton(rb)
            radioButtons[label.lower()] = rb
            layout.addWidget(rb)

        #   Separator
        layout.addWidget(QGroupBox())

        #   Ascending/Descending
        sortDirGroup = QButtonGroup(sortMenu)
        rb_asc = QRadioButton("Ascending")
        rb_desc = QRadioButton("Descending")
        rb_asc.setChecked(opts.get("ascending", True))
        rb_desc.setChecked(not opts.get("ascending", True))
        sortDirGroup.addButton(rb_asc)
        sortDirGroup.addButton(rb_desc)
        layout.addWidget(rb_asc)
        layout.addWidget(rb_desc)

        #   Separator
        layout.addWidget(QGroupBox())

        #   Apply Button
        b_apply = QPushButton("Apply")
        b_apply.setFixedWidth(80)
        b_apply.setStyleSheet("font-weight: bold;")

        def applyAndClose():
            self.sortOptions[table] = {
                "groupTypes": cb_groupTypes.isChecked(),
                "ascending": rb_asc.isChecked(),
                "sortType": self._getSelectedSortType(radioButtons)
            }
            sortMenu.close()
            self.plugin.saveSettings(key="sortOptions", data=self.sortOptions)

            if table == "source":
                self.refreshSourceTable()
            elif table == "destination":
                self.refreshDestTable()

        b_apply.clicked.connect(applyAndClose)
        layout.addWidget(b_apply, alignment=Qt.AlignRight)

        wrapperAction = QWidgetAction(self)
        wrapperAction.setDefaultWidget(container)
        sortMenu.addAction(wrapperAction)

        sortMenu.exec_(cpos)

    #   Helper for Sort Menu
    @err_catcher(name=__name__)
    def _getSelectedSortType(self, radioButtons):
        for key, rb in radioButtons.items():
            if rb.isChecked():
                return key
        return "type"  # Fallback




    #   Right Click List for Filters
    @err_catcher(name=__name__)
    def filtersRCL(self, table):
        cpos = QCursor.pos()
        rcmenu = QMenu(self)

        #   Helper to Wrap Action in Widget
        def _wrapWidget( widget):
            action = QWidgetAction(self)
            action.setDefaultWidget(widget)
            return action
    

        #   Temporary State Dictionary
        if table == "source":
            tempStates = self.filterStates_source.copy()
        elif table == "destination":
            tempStates = self.filterStates_dest.copy()
        checkboxRefs = {}

        #   Checkboxes
        for label, checked in tempStates.items():
            cb = QCheckBox(label)
            cb.setChecked(checked)
            checkboxRefs[label] = cb
            rcmenu.addAction(_wrapWidget(cb))

        #   Vert Dummy Spacer
        spacer = QLabel(" ")
        rcmenu.addAction(_wrapWidget(spacer))

        if table == "source":
            pass

        elif table == "destination":
            pass

        #   Apply Button
        b_apply = QPushButton("Apply")
        b_apply.setFixedWidth(80)
        b_apply.setStyleSheet("font-weight: bold;")
        b_apply.clicked.connect(lambda: self._applyFilterStates(checkboxRefs, rcmenu, table))
        rcmenu.addAction(_wrapWidget(b_apply))

        if rcmenu.isEmpty():
            return False

        rcmenu.exec_(cpos)


    #   Helper for filtersRCL()
    def _applyFilterStates(self, checkboxRefs, menu, table):
        if table == "source":
            for label, cb in checkboxRefs.items():
                self.filterStates_source[label] = cb.isChecked()

            self.refreshSourceTable()

        elif table == "destination":
            for label, cb in checkboxRefs.items():
                self.filterStates_dest[label] = cb.isChecked()

            self.refreshDestTable()

        menu.close()


####    MOUSE ACTIONS   ####

    #   Checks if Dragged Object has a Path
    @err_catcher(name=__name__)
    def onDragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.accept()
        else:
            e.ignore()


    #   Adds Dashed Outline to Table During Drag
    @err_catcher(name=__name__)
    def onDragMoveEvent(self, widget, objName, e):
        if e.mimeData().hasUrls():
            e.accept()
            widget.setStyleSheet(
                f"QListWidget#{objName} {{ border-style: dashed; border-color: rgb(100, 200, 100); border-width: 2px; }}"
            )
        else:
            e.ignore()


    #   Removed Dashed Line
    @err_catcher(name=__name__)
    def onDragLeaveEvent(self, widget, e):
        widget.setStyleSheet("")


    #   Gets Directory from Dropped Item
    @err_catcher(name=__name__)
    def onDropEvent(self, widget, mode, e):
        widget.setStyleSheet("")

        if e.mimeData().hasUrls():
            logger.debug("Drop Event Detected")

            e.acceptProposedAction()

            #   Normal File/Folder Drop
            url = e.mimeData().urls()[0]
            path = os.path.normpath(url.toLocalFile())

            if os.path.isfile(path):
                logger.debug("Dropped File Detected")
                path = os.path.dirname(path)

            if os.path.isdir(path):
                logger.debug("Dropped Directory Detected")

                if mode == "source":
                    self.sourceDir = path
                    self.refreshSourceItems()
                elif mode == "dest":
                    self.destDir = path
                    self.refreshDestItems(restoreSelection=True)
            else:
                self.core.popup(f"ERROR: Dropped path is not a directory: {path}")

        elif e.mimeData().hasFormat("application/x-sourcefileitem"):
            ##  This is your custom item!
            e.acceptProposedAction()

            dataBytes = e.mimeData().data("application/x-sourcefileitem")
            dataString = bytes(dataBytes).decode('utf-8')

            fileItem = self.createDestFileTile(dataString)

            # Insert into QListWidget
            listItem = QListWidgetItem()
            listItem.setSizeHint(fileItem.sizeHint())  # Optional, if sizing matters

            self.lw_destination.addItem(listItem)
            self.lw_destination.setItemWidget(listItem, fileItem)

        else:
            e.ignore()


    @err_catcher(name=__name__)
    def mouseMoveEvent(self, event):
        if event.buttons() != Qt.LeftButton:
            return

        drag = QDrag(self)
        mimeData = QMimeData()

        #   Serialize the Item Data
        dataString = self.serializeData()

        mimeData.setData("application/x-sourcefileitem", dataString.encode('utf-8'))
        drag.setMimeData(mimeData)

        drag.exec_(Qt.CopyAction)


    @err_catcher(name=__name__)
    def serializeData(self):
        return self.path


    @err_catcher(name=__name__)
    def getAllSourceTiles(self):
        tiles = []

        try:
            for i in range(self.lw_source.count()):
                item = self.lw_source.item(i)
                widget = self.lw_source.itemWidget(item)
                if isinstance(widget, TileWidget.SourceFileTile):
                    tiles.append(widget)

            logger.debug("Fetched All Source Tiles")
            return tiles

        except Exception as e:
            logger.warning(f"ERROR:  Failed to Fetch All Source Tiles:\n{e}")

        

    @err_catcher(name=__name__)
    def getAllDestTiles(self, onlyChecked=False):
        tiles = []

        try:
            for i in range(self.lw_destination.count()):
                item = self.lw_destination.item(i)
                widget = self.lw_destination.itemWidget(item)
                if isinstance(widget, TileWidget.DestFileTile):
                    if onlyChecked:
                        if widget.isChecked():
                            tiles.append(widget)
                    else:
                        tiles.append(widget)

            logger.debug("Fetched All Destination Tiles")
            return tiles

        except Exception as e:
            logger.warning(f"ERROR:  Failed to Fetch All Destination Tiles:\n{e}")



    #   Configures UI from Saved Settings
    @err_catcher(name=__name__)
    def getSettings(self, key=None):
        return self.plugin.loadSettings(key)


    #   Configures UI from Saved Settings
    @err_catcher(name=__name__)
    def loadSettings(self):
        try:
            #   Get Saved Settings
            sData = self.getSettings()

            #   Get Main Settings
            settingData = sData["globals"]
            self.max_thumbThreads = settingData["max_thumbThreads"]
            self.max_copyThreads = settingData["max_copyThreads"]
            self.size_copyChunk = settingData["size_copyChunk"]
            self.max_proxyThreads = settingData["max_proxyThreads"]
            self.progUpdateInterval = settingData["updateInterval"]
            self.useCompletePopup = settingData["useCompletePopup"]
            self.useCompleteSound = settingData["useCompleteSound"]
            self.useTransferReport = settingData["useTransferReport"]
            self.useCustomIcon = settingData["useCustomIcon"]
            self.customIconPath = os.path.normpath(settingData["customIconPath"].strip().strip('\'"'))
            self.useViewLuts = settingData["useViewLut"]
            self.useCustomThumbPath = settingData["useCustomThumbPath"]
            self.customThumbPath = settingData ["customThumbPath"]

            #   Get OCIO View Presets
            lutPresetData = sData["viewLutPresets"]
            self.configureViewLut(lutPresetData)                 #   TODO - MOVE

            #   Get Tab (UI) Settings
            tabData = sData["tabSettings"]

            #   Sorting Options
            self.sortOptions = sData["sortOptions"]

            #   Media Player Enabled Checkbox
            playerEnabled = tabData["playerEnabled"]
            self.chb_enablePlayer.setChecked(playerEnabled)
            self.toggleMediaPlayer(playerEnabled)
            #   Prefer Proxies Checkbox
            preferProxies = tabData["preferProxies"]
            self.chb_preferProxies.setChecked(preferProxies)
            self.togglePreferProxies(preferProxies)

            #   Options
            self.sourceFuncts.chb_ovr_proxy.setChecked(tabData["enable_proxy"])
            self.sourceFuncts.chb_ovr_fileNaming.setChecked(tabData["enable_fileNaming"])
            self.sourceFuncts.chb_ovr_metadata.setChecked(tabData["enable_metadata"])
            self.sourceFuncts.chb_overwrite.setChecked(tabData["enable_overwrite"])
            self.proxyEnabled = tabData["enable_proxy"]
            self.proxyMode = tabData["proxyMode"]

            #   Proxy Options
            if "proxySettings" in sData:
                self.proxySettings = sData["proxySettings"]

            #   Proxy Presets
            if "ffmpegPresets" in sData:
                self.ffmpegPresets = sData["ffmpegPresets"]

            #   Name Mods
            if "activeNameMods" in sData:
                self.nameMods = sData["activeNameMods"]

            self.sourceFuncts.updateUI()

            logger.debug("Loaded SourceTab Settings")

        except Exception as e:
            logger.warning(f"ERROR:  Failed to Load SourceTab Settings:\n{e}")


    #   Initializes Worker Threadpools and Semephore Slots
    @err_catcher(name=__name__)
    def setupThreadpools(self):
        try:
            self.thumb_semaphore = QSemaphore(self.max_thumbThreads)
            self.copy_semaphore = QSemaphore(self.max_copyThreads)
            self.proxy_semaphore = QSemaphore(self.max_proxyThreads)

            self.thumb_threadpool = QThreadPool()
            self.thumb_threadpool.setMaxThreadCount(self.max_thumbThreads)

            self.dataOps_threadpool = QThreadPool()
            self.dataOps_threadpool.setMaxThreadCount(12)

        except Exception as e:
            logger.warning(f"ERROR:  Failed to Set Threadpools:\n{e}")



    @err_catcher(name=__name__)
    def configureViewLut(self, presets=None):
        self.mediaPlayer.container_viewLut.setVisible(self.useViewLuts)

        if presets:
            self.mediaPlayer.cb_viewLut.clear()

            for preset in presets:
                self.mediaPlayer.cb_viewLut.addItem(preset["name"])


    #   Returns FFprobe Path
    @err_catcher(name=__name__)
    def getFFprobePath(self):
        return os.path.join(pluginPath, "PythonLibs", "FFmpeg", "ffprobe.exe")


    #   Returns ExitTool Path
    @err_catcher(name=__name__)                                                     #   TODO - Remove once all is using FFmpeg/FFprobe
    def getExiftool(self):
        exifDir = os.path.join(pluginPath, "PythonLibs", "ExifTool")

        possible_names = ["exiftool.exe", "exiftool(-k).exe"]

        for root, dirs, files in os.walk(exifDir):
            for file in files:
                if file.lower() in [name.lower() for name in possible_names]:
                    self.exifToolEXE = os.path.join(root, file)
                    logger.debug(f"ExifTool found at: {self.exifToolEXE}")
                    return

        logger.warning(f"ERROR:  Unable to Find ExifTool")
        return None
    
    
    #   Returns QIcon with Both Normal and Disabled Versions
    @err_catcher(name=__name__)
    def getIconFromPath(self, imagePath, normalLevel=0.9, dimLevel=0.4):
        try:
            normal_pixmap = QPixmap(imagePath)
            normal_image = normal_pixmap.toImage().convertToFormat(QImage.Format_ARGB32)

            #   Darken Normal Version Slightly (normalLevel)
            darkened_normal_image = QImage(normal_image.size(), QImage.Format_ARGB32)

            for y in range(normal_image.height()):
                for x in range(normal_image.width()):
                    color = normal_image.pixelColor(x, y)

                    #   Reduce brightness to normalLevel
                    dark = int(color.red() * normalLevel)
                    color = QColor(dark, dark, dark, color.alpha())
                    darkened_normal_image.setPixelColor(x, y, color)

            darkened_normal_pixmap = QPixmap.fromImage(darkened_normal_image)

            #   Darken Disbled Version More (dimLevel)
            disabled_image = QImage(normal_image.size(), QImage.Format_ARGB32)

            for y in range(normal_image.height()):
                for x in range(normal_image.width()):
                    color = normal_image.pixelColor(x, y)

                    # Reduce brightness to 40%
                    dark = int(color.red() * dimLevel)
                    color = QColor(dark, dark, dark, color.alpha())
                    disabled_image.setPixelColor(x, y, color)

            disabled_pixmap = QPixmap.fromImage(disabled_image)

            #   Convert to QIcon
            icon = QIcon()
            icon.addPixmap(darkened_normal_pixmap, QIcon.Normal)
            icon.addPixmap(disabled_pixmap, QIcon.Disabled)

            logger.debug(f"Created Icon for {imagePath}")
            return icon
        
        except Exception as e:
            logger.warning(f"ERROR:  Failed to Create Icon:\n{e}")
    

    #   Returns File Size Formatted String
    @err_catcher(name=__name__)
    def getFileSizeStr(self, size_bytes):
        size_mb = size_bytes / 1024.0 / 1024.0

        #   Set Size Unit
        if size_mb < 1:
            size_kb = size_bytes / 1024.0
            size = size_kb
            unit = "KB"
        elif size_mb < 1024:
            size = size_mb
            unit = "MB"
        else:
            size = size_mb / 1024.0
            unit = "GB"

        #   Set Decimal Digits Based on Integer Digits
        int_digits = len(str(int(size)))
        if int_digits >= 3:
            fmt = "%.0f"
        elif int_digits == 2:
            fmt = "%.1f"
        else:
            fmt = "%.2f"

        sizeStr = f"{fmt % size} {unit}"
        return sizeStr
    

    #   Returns Time Formatted String
    @err_catcher(name=__name__)
    def getFormattedTimeStr(self, seconds):
        if seconds is None or seconds > 1e6:
            return "Estimating..."
        
        minutes, sec = divmod(int(seconds), 60)

        return f"{minutes:02}:{sec:02}"


    #   Configures the UI Buttons based on Transfer Status
    @err_catcher(name=__name__)
    def configTransUI(self, mode):
        try:
            displayMap = {
                "idle": {
                    "b_transfer_start": True,
                    "b_transfer_pause": False,
                    "b_transfer_resume": False,
                    "b_transfer_cancel": False,
                    "b_transfer_reset": False,
                    "l_time_elapsed": False,
                    "l_time_elapsedText": False,
                    "l_time_remain": False,
                    "l_time_remainText": False,
                    "l_size_copied": False,
                    "l_size_dash": False,
                },
                "transfer": {
                    "b_transfer_start": False,
                    "b_transfer_pause": True,
                    "b_transfer_resume": False,
                    "b_transfer_cancel": True,
                    "l_time_elapsed": True,
                    "l_time_elapsedText": True,
                    "l_time_remain": True,
                    "l_time_remainText": True,
                    "l_size_copied": True,
                    "l_size_dash": True,
                },
                "pause": {
                    "b_transfer_start": False,
                    "b_transfer_pause": False,
                    "b_transfer_resume": True,
                    "b_transfer_cancel": True,
                },
                "resume": {
                    "b_transfer_start": False,
                    "b_transfer_pause": True,
                    "b_transfer_resume": False,
                    "b_transfer_cancel": True,
                },
                "cancel": {
                    "b_transfer_start": False,
                    "b_transfer_pause": False,
                    "b_transfer_resume": False,
                    "b_transfer_cancel": False,
                    "b_transfer_reset": True,
                },
                "complete": {
                    "b_transfer_start": False,
                    "b_transfer_pause": False,
                    "b_transfer_resume": False,
                    "b_transfer_cancel": False,
                    "b_transfer_reset": True,
                    "l_time_elapsed": True,
                    "l_time_elapsedText": True,
                    "l_time_remain": False,
                    "l_time_remainText": False,
                    "l_size_copied": True,
                    "l_size_dash": True,
                }
            }

            config = displayMap.get(mode.lower())
            if not config:
                return

            for name, visible in config.items():
                widget = getattr(self.sourceFuncts, name, None)
                if widget:
                    widget.setVisible(visible)


            #   Enable/Disable During Transfer
            if mode in ["idle", "complete"]:
                enabled = True
            elif mode in ["transfer", "pause", "resume", "cancel"]:
                enabled = False

            lockItems = [self.sourceFuncts.gb_functions,
                        self.gb_sourcePath,
                        self.gb_sourceFooter,
                        self.gb_destPath,
                        self.gb_destFooter]

            for item in lockItems:
                item.setEnabled(enabled)

        except Exception as e:
            logger.warning(f"ERROR:  Failed to Configure Transfer UI:\n{e}")


    #   Reset Total Progess Bar
    @err_catcher(name=__name__)
    def reset_ProgBar(self):
        self.sourceFuncts.progBar_total.setValue(0)


    #   Get Transfer size from Each TileTile and Calculate Total
    @err_catcher(name=__name__)
    def getTotalTransferSize(self):
        try:
            listWidget = self.lw_destination
            total_transferSize = 0.0

            for i in range(listWidget.count()):
                listItem = listWidget.item(i)
                fileItem = listWidget.itemWidget(listItem)

                if fileItem is not None and fileItem.isChecked():
                    total_transferSize += fileItem.getTransferSize(self.proxyEnabled, self.proxyMode)

            logger.debug("Fetched Total Transfer Size")
            return total_transferSize

        except Exception as e:
            logger.warning(f"ERROR:  Failed to Fetch Total Transfer Size:\n{e}")



    @err_catcher(name=__name__)
    def getTimeElapsed(self):
        return (time() - self.transferStartTime)


    @err_catcher(name=__name__)
    def getTimeRemaining(self, copiedSize, totalSize):
        try:
            speed_bps = 0
            current_time = time()

            self.speedSamples.append((current_time, copiedSize))

            # Adaptive maxlen: increase as transfer progresses
            progress_ratio = copiedSize / totalSize if totalSize > 0 else 0
            adaptive_maxlen = int(5 + progress_ratio * 20)
            self.speedSamples = deque(self.speedSamples, maxlen=adaptive_maxlen)

            # Calculate rolling average speed
            if len(self.speedSamples) >= 2:
                t0, b0 = self.speedSamples[0]
                t1, b1 = self.speedSamples[-1]
                time_span = t1 - t0
                bytes_span = b1 - b0

                if time_span > 0 and bytes_span > 0:
                    speed_bps = bytes_span / time_span
                else:
                    speed_bps = 0

            # Estimate remaining time
            if speed_bps > 0:
                remaining_bytes = totalSize - copiedSize
                time_remaining = remaining_bytes / speed_bps
            else:
                time_remaining = None

            return time_remaining

        except Exception as e:
            logger.warning(f"ERROR:  Failed to get Time Remaining:\n{e}")


    #   Creates Transfer Report PDF
    @err_catcher(name=__name__)
    def getCustomIcon(self):
        #   Default Prism Icon
        prismIcon = os.path.join(prismRoot, "Scripts", "UserInterfacesPrism", "p_tray.png")

        #   Get Custom Icon if Selected
        try:
            if self.useCustomIcon and os.path.isfile(self.customIconPath):
                return self.customIconPath
            else:
                logger.debug("Using Default Prism Icon")
                return prismIcon
        except:
            logger.warning(f"ERROR:  Unable to get Icon")


    #	Creates UUID
    @err_catcher(name=__name__)
    def createUUID(self, simple=False, length=8):
        #	Creates simple Date/Time UID
        if simple:
            # Get the current date and time
            now = datetime.now()
            # Format as MMDDHHMM
            uid = now.strftime("%m%d%H%M")

            logger.debug(f"Created Simple UID: {uid}")
        
            return uid
        
        # Generate a 8 charactor UUID string
        else:
            uid = uuid.uuid4()
            # Create a SHA-256 hash of the UUID
            hashObject = hashlib.sha256(uid.bytes)
            # Convert the hash to a hex string and truncate it to the desired length
            shortUID = hashObject.hexdigest()[:length]

            logger.debug(f"Created UID: {shortUID}")

            return shortUID


    @err_catcher(name=__name__)
    def refreshUI(self):
        self.core.media.invalidateOiioCache()                               #   TODO

        if hasattr(self, "sourceDir"):
            self.le_sourcePath.setText(self.sourceDir)
        if hasattr(self, "destDir"):
            self.le_destPath.setText(self.destDir)
        
        self.refreshSourceItems()
        self.refreshDestItems(restoreSelection=True)

        # self.entityChanged()
        self.refreshStatus = "valid"


    #   Toggles Media Player Visability
    @err_catcher(name=__name__)
    def toggleMediaPlayer(self, checked):
        self.mediaPlayer.setVisible(checked)
        self.chb_preferProxies.setVisible(checked)


    #   Sets Prefer Proxies
    @err_catcher(name=__name__)
    def togglePreferProxies(self, checked):
        self.preferProxies = checked


    @err_catcher(name=__name__)
    def selectAll(self, checked=True, mode=None):
        logger.debug(f"Selecting All - checked: {checked}")

        if mode == "source":
            listWidget = self.lw_source
        elif mode == "dest":
            listWidget = self.lw_destination
        else:
            return

        # Capture Current Scroll Position
        scrollPos = listWidget.verticalScrollBar().value()

        item_count = listWidget.count()

        for i in range(item_count):
            item = listWidget.item(i)
            fileItem = listWidget.itemWidget(item)

            if (
                fileItem is not None
                and not item.isHidden()
                and getattr(fileItem, "data", {}).get("tileType") == "file"
                ):

                fileItem.setChecked(checked, refresh=False)

        if mode == "dest":
            self.refreshTotalTransSize()

        # Restore Scroll Position
        QTimer.singleShot(50, lambda: listWidget.verticalScrollBar().setValue(scrollPos))



    @err_catcher(name=__name__)
    def explorer(self, mode, dir=None):
        if not dir:
            if mode == "source" and hasattr(self, "sourceDir"):
                dir = self.sourceDir
            elif mode == "dest" and hasattr(self, "destDir"):
                dir = self.destDir

        # Create file dialog
        dialog = QFileDialog(None, f"Select {mode.capitalize()} Directory", dir or "")
        
        # Set mode to allow selecting both files and directories
        dialog.setFileMode(QFileDialog.FileMode.AnyFile)  # Allow file selection
        dialog.setOption(QFileDialog.Option.ShowDirsOnly, False)  # Show directories too
        dialog.setOption(QFileDialog.Option.DontUseNativeDialog, False)  # Use native dialog

        # Add an option to select directories
        dialog.setOption(QFileDialog.Option.ReadOnly, True)  # Prevent accidental editing
        dialog.setFileMode(QFileDialog.FileMode.Directory)  # Allow directory selection

        if dialog.exec():  # Open dialog and check if selection is made
            selected_path = dialog.selectedFiles()[0]  # Get selected file or directory

            if os.path.isfile(selected_path):  # If it's a file, get its parent directory
                selected_path = os.path.dirname(selected_path)

            if mode == "source":
                self.sourceDir = os.path.normpath(selected_path)
                self.refreshSourceItems()
            elif mode == "dest":
                self.destDir = os.path.normpath(selected_path)
                self.refreshDestItems(restoreSelection=True)

            return selected_path


#########   TESTING - TO GET LIBRARIES TAB TO OPEN AND SELECT DIRECTORY ##########
#########   vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv ##########

    # #   Launch Libraries window and return selected Import Path(s)
    # @err_catcher(name=__name__)
    # def launchLibBrowser(self):
    #     try:
    #         #   Get Libraries Plugin
    #         libs = self.core.getPlugin("Libraries")
    #         if not libs:
    #             raise Exception
    #     except:
    #         logger.warning("ERROR:  Libraries Plugin not installed.  Use the 'Open Explorer' button to choose Texture Set.")
    #         self.core.popup("Libraries Plugin not installed.\n\n"
    #                        "Use the 'Open Explorer' button to choose Texture Set.")
    #         return None

    #     # try:


    #     #   Call Libraries popup and return selected file path(s)



    #     self.list_props(libs)                                   #   TESTING
    #     self.list_props(entity.plugin)



    #     # self.deep_inspect(libs, max_depth=1)
    #     # self.find_line_edits_and_views(libs)


    #     paths = libs.getAssetImportPaths()

    #     if not paths:
    #         logger.debug("Texture selection canceled.")
    #         return None
        
    #     return paths
            
    #     # except Exception as e:
    #     #     self.core.popup(f"ERROR: Failed  Texture Set: {e}")
    #     #     logger.warning(f"ERROR: selecting Texture Set: {e}")
    #     #     return None



    # def find_line_edits_and_views(self, widget):
    #     for child in widget.findChildren(QtWidgets.QWidget):
    #         if isinstance(child, QtWidgets.QLineEdit):
    #             print(f"QLineEdit: {child.objectName()} = {child.text()}")
    #         elif isinstance(child, (QtWidgets.QTreeView, QtWidgets.QListView)):
    #             print(f"{child.__class__.__name__}: {child.objectName()}")
    #         elif hasattr(child, "currentIndex"):
    #             try:
    #                 idx = child.currentIndex()
    #                 if hasattr(idx, "data"):
    #                     print(f"{child.__class__.__name__}: {child.objectName()} currentIndex = {idx.data()}")
    #             except Exception as e:
    #                 print(f"Error reading currentIndex for {child.objectName()}: {e}")


    # #   TEMP TESTING                                        #   TESTING
    # def list_props(self, entity):
    #     import inspect
    #     print("########################")
    #     print(f"{entity} > Type: {str(type(entity))}")
    #     print("----")
    #     methods = [func for func in dir(entity) if callable(getattr(entity, func)) and not func.startswith("__")]
    #     for method in methods:
    #         func = getattr(entity, method)
    #         try:
    #             sig = inspect.signature(func)
    #             print(f"Method: {method}, Arguments: {sig}")
    #         except:
    #             print(f"Method: {method}")
    #     for attribute_name, attribute in entity.__dict__.items():
    #         print(f"Attribute: {attribute_name} | {str(type(attribute))}")
    #     print("########################")


    # def deep_inspect(self, obj, depth=0, max_depth=3, seen=None):
    #     import inspect
    #     indent = "  " * depth
    #     seen = seen or set()
    #     if id(obj) in seen or depth > max_depth:
    #         return
    #     seen.add(id(obj))

    #     print(f"{indent}Inspecting: {obj} ({type(obj)})")
    #     try:
    #         methods = [m for m in dir(obj) if callable(getattr(obj, m)) and not m.startswith("__")]
    #         for m in methods:
    #             try:
    #                 sig = inspect.signature(getattr(obj, m))
    #                 print(f"{indent}  Method: {m}{sig}")
    #             except Exception:
    #                 print(f"{indent}  Method: {m} (signature not available)")
    #     except Exception as e:
    #         print(f"{indent}  Error inspecting methods: {e}")

    #     try:
    #         for attr in dir(obj):
    #             if attr.startswith("__"):
    #                 continue
    #             try:
    #                 val = getattr(obj, attr)
    #                 print(f"{indent}  Attr: {attr} ({type(val)})")
    #                 self.deep_inspect(val, depth+1, max_depth, seen)
    #             except Exception as e:
    #                 print(f"{indent}  Attr: {attr} (unreadable: {e})")
    #     except Exception as e:
    #         print(f"{indent}  Error accessing attributes: {e}")

########    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^    ###########
#########   TESTING - TO GET LIBRARIES TAB TO OPEN AND SELECT DIRECTORY ##########



    #   Handles Addressbar Logic
    @err_catcher(name=__name__)
    def onPasteAddress(self, mode):
        try:
            if mode == "source":
                attribute = "sourceDir"
                addrBar = self.le_sourcePath
                refreshFunc = self.refreshSourceItems

            elif mode == "dest":
                attribute = "destDir"
                addrBar = self.le_destPath
                refreshFunc = lambda: self.refreshDestItems(restoreSelection=True)
            else:
                return

            origDir = getattr(self, attribute, "")
            pastedAddr = addrBar.text().strip().strip('\'"')

            if not os.path.exists(pastedAddr):
                addrBar.setText(origDir)
                return

            if os.path.isdir(pastedAddr):
                newAddr = os.path.normpath(pastedAddr)
            elif os.path.isfile(pastedAddr):
                newAddr = os.path.normpath(os.path.dirname(pastedAddr))
            else:
                addrBar.setText(origDir)
                return

            setattr(self, attribute, newAddr)
            refreshFunc()

        except Exception as e:
            logger.warning(f"ERROR:  Paste Address Failed:\n{e}")


    @err_catcher(name=__name__)
    def openInExplorer(self, path):
        if os.path.isdir(path):
            dir = path
        elif os.path.isfile(path):
            dir = os.path.dirname(path)
        else:
            logger.warning(f"ERROR:  Unable to open {path} in File Explorer")
            return

        self.core.openFolder(dir)


    @err_catcher(name=__name__)
    def goUpDir(self, mode):
        if mode == "source":
            attribute = "sourceDir"
            refreshFunc = self.refreshSourceItems

        elif mode == "dest":
            attribute = "destDir"
            refreshFunc = lambda: self.refreshDestItems(restoreSelection=True)
        else:
            return

        if hasattr(self, attribute):
            currentDir = getattr(self, attribute)
            parentDir = os.path.dirname(currentDir)
            setattr(self, attribute, parentDir)

            refreshFunc()


    #   Returns Bool if File in Prism Supported Formats
    @err_catcher(name=__name__)
    def isSupportedFormat(self, path=None, ext=None):
        try:
            if path:
                _, extension = os.path.splitext(os.path.basename(path))
            elif ext:
                extension = ext
            else:
                extension = self.getFileExtension()
            
            return  extension.lower() in self.core.media.supportedFormats
        
        except Exception as e:
            logger.warning(f"ERROR:  isSupportedFormat() Failed:\n{e}")



    #   Returns Bool if File in Prism Video Formats
    @err_catcher(name=__name__)
    def isVideo(self, path=None, ext=None):
        try:
            if path:
                _, extension = os.path.splitext(os.path.basename(path))
            elif ext:
                extension = ext
            else:
                extension = self.getFileExtension()
            
            return  extension.lower() in self.core.media.videoFormats
        
        except Exception as e:
            logger.warning(f"ERROR:  isVideo() Failed:\n{e}")
    

    #   Returns Bool if File in Prism Video Formats
    @err_catcher(name=__name__)
    def isAudio(self, path=None, ext=None):
        if path:
            _, extension = os.path.splitext(os.path.basename(path))
        elif ext:
            extension = ext
        else:
            extension = self.getFileExtension()
        
        return  extension.lower() in self.audioFormats


    @err_catcher(name=__name__)
    def getFileType(self, filePath):
        if os.path.isdir(filePath):
            return "Folders"
        
        else:
            if self.isSupportedFormat(path=filePath) and not self.isVideo(path=filePath):
                fileType = "Images"
            elif self.isVideo(path=filePath):
                fileType = "Videos"
            elif self.isAudio(path=filePath):
                fileType = "Audio"
            else:
                fileType = "Other"

            return fileType



    #   Show/Hide FileTiles Based on Table Filters
    @err_catcher(name=__name__)
    def applyTableFilters(self, table, sortedList):
        try:
            #   Get Filter Settings
            if table == "source":
                filterEnabled = self.b_sourceFilter_filtersEnable.isChecked()
                filterStates = self.filterStates_source
            elif table == "destination":
                filterEnabled = self.b_destFilter_filtersEnable.isChecked()
                filterStates = self.filterStates_dest
            else:
                #   Fallback Return Original List
                return sortedList

            #   If Filters Not Enabled, Skip Filtering
            if not filterEnabled:
                return sortedList

            #   Make Filtered List
            filteredList = []
            for item in sortedList:
                data = item.get("data", {})
                fileType = data.get("fileType", "Other").capitalize()
                if filterStates.get(fileType, True):
                    filteredList.append(item)

            return filteredList

        except Exception as e:
            logger.warning(f"ERROR: Unable to Apply '{table}' Table Filters:\n{e}")

            return sortedList


    ####  TESTING   SEQUENCES   ####

    def groupSequences(self, imageFiles):
        remaining = set(imageFiles)
        sequences = []

        while remaining:
            current = remaining.pop()
            base, frame, ext = self.splitFilename(current)

            if (
                frame and
                ext.lower() in self.core.media.supportedFormats and
                ext.lower() not in self.core.media.videoFormats
            ):
                pattern = re.escape(base) + r"\d+" + re.escape(ext)
                regex = re.compile(pattern)
                matched = [f for f in remaining if regex.fullmatch(f)]
                matched.append(current)

                # Only treat as sequence if multiple files
                if len(matched) > 1:
                    remaining.difference_update(matched)
                    padded = "#" * len(frame)
                    display_name = f"{base}{padded}{ext}"
                    sequences.append((display_name, True, sorted(matched)))
                else:
                    # Only one file, so standalone
                    sequences.append((current, False, [current]))
            else:
                sequences.append((current, False, [current]))

        return sequences

    

    def splitFilename(self, filename):
        """
        Splits a filename like 'plate_0001.exr' -> ('plate_', '0001', '.exr')
        If no digits are found, returns (name, '', ext)
        """
        name, ext = os.path.splitext(filename)
        match = re.search(r'(\d+)$', name)
        if match:
            frame = match.group(1)
            base = name[:match.start(1)]
        else:
            base = name
            frame = ''
        return base, frame, ext
    
    ######################

   


    #   Sort Items According to User Selection
    @err_catcher(name=__name__)
    def applySorting(self, table, origList):
        #   Get Selected Options
        opts = self.sortOptions.get(table, {})
        sortType = opts.get("sortType", "name")
        ascending = opts.get("ascending", True)
        groupTypes = opts.get("groupTypes", True)

        #   Folder/File Separation
        folderList = [item for item in origList if item["data"].get("tileType") == "folder"]
        fileList = [item for item in origList if item["data"].get("tileType") != "folder"]

        # Sort Folders Alphabetically
        sortedFolders = sorted(folderList, key=lambda x: x["data"].get("displayName", "").lower())

        #   Sorting Order for Tile Types
        typePriority = {
            "Videos": 0,
            "Image Sequence": 1,
            "Images": 2,
            "Audio": 3,
            "Other": 4
        }

        #   Sort Order
        reverse = not ascending

        #   Get Sort Key
        def get_sort_key(item):
            data = item["data"]
            match sortType:
                case "name":
                    return data.get("displayName", "").lower()
                case "size":
                    return data.get("source_mainFile_size_raw", 0)
                case "date":
                    return data.get("source_mainFile_date_raw", 0)
                case _:
                    return data.get("displayName", "").lower()

        #   Flat sort
        if not groupTypes:
            sortedFiles = sorted(fileList, key=get_sort_key, reverse=reverse)

        #   Grouped Sort
        else:
            grouped = {}
            for item in fileList:
                ftype = item["data"].get("fileType", "Other")
                grouped.setdefault(ftype, []).append(item)

            #   Sort Groups by typePriority, then Sort Each Group
            sortedFiles = []
            for ftype in sorted(grouped.keys(), key=lambda t: typePriority.get(t, 99)):
                groupItems = sorted(grouped[ftype], key=get_sort_key, reverse=reverse)
                sortedFiles.extend(groupItems)

        return sortedFolders + sortedFiles


    #   Update Table using Filters and Sorting
    @err_catcher(name=__name__)
    def sortTable(self, table, origList):
        #   Make Copy of Item List
        origList_copy = origList.copy()

        #   Sort the Items
        sortedList = self.applySorting(table, origList_copy)

        #   Filter the Items
        sortedList = self.applyTableFilters(table, sortedList)

        return sortedList



    #   Build List of Items in Source Directory
    @err_catcher(name=__name__)
    def refreshSourceItems(self, restoreSelection=False):
        WaitPopup.showPopup(parent=self.projectBrowser)

        try:
            #   Get Dir and Set Short Name
            sourceDir = getattr(self, "sourceDir", "")
            metrics = QFontMetrics(self.le_sourcePath.font())
            elided_text = metrics.elidedText(sourceDir, Qt.ElideMiddle, self.le_sourcePath.width())
            self.le_sourcePath.setText(elided_text)

            #   Color Dir LineEdit if Invalid
            if not os.path.exists(sourceDir):
                self.le_sourcePath.setStyleSheet("QLineEdit { border: 1px solid #cc6666; }")
            else:
                self.le_sourcePath.setToolTip(sourceDir)
                self.le_sourcePath.setStyleSheet("")

            #   Return if there is no Dir set
            if not hasattr(self, "sourceDir"):
                return

            #   Capture Scrollbar Position
            scrollPos = self.lw_destination.verticalScrollBar().value()

            #   Get all Items from the Source Dir
            allFileItems = os.listdir(self.sourceDir)

            self.sourceDataItems = []

            #   Create Data Item for Each Item in Dir
            for file in allFileItems:
                fullPath = os.path.join(self.sourceDir, file)
                fileType = self.getFileType(fullPath)

                self.createSourceItem(file, fullPath, fileType)

            #   Sort / Filter / Refresh Source Table
            self.refreshSourceTable()

            #   Reposition Scrollbar
            QTimer.singleShot(50, lambda: self.lw_destination.verticalScrollBar().setValue(scrollPos))

        except Exception as e:
            logger.warning(f"ERROR:  Failed to Refresh Source Items:\n{e}")

        finally:
            WaitPopup.closePopup()



    #   Sort / Filter / Refresh Source Table
    @err_catcher(name=__name__)
    def refreshSourceTable(self):
        WaitPopup.showPopup(parent=self.projectBrowser)

        try:
            #   Sort the Table Items
            sourceDataItems_sorted = self.sortTable("source", self.sourceDataItems)

            # Reset Table
            self.lw_source.clear()
            row = 0

            #   Itterate Sorted Items and Create Tile UI Widgets
            for dataItem in sourceDataItems_sorted:
                fileItem = dataItem["tile"]
                fileType = dataItem["tileType"]
                data = dataItem["data"]

                if fileType == "folder":
                    itemTile = TileWidget.FolderItem(self, data)
                    rowHeight = SOURCE_DIR_HEIGHT
                else:
                    itemTile = TileWidget.SourceFileTile(fileItem)
                    rowHeight = SOURCE_ITEM_HEIGHT

                #   Set Row Size and Add File Tile widget and Data to Row
                list_item = QListWidgetItem()
                list_item.setSizeHint(QSize(0, rowHeight))
                list_item.setData(Qt.UserRole, {
                    # "displayName": displayName,
                    "fileType": fileType
                    # "isSequence": isSequence,
                    # "seqFiles": seqFiles
                })


                self.lw_source.addItem(list_item)
                self.lw_source.setItemWidget(list_item, itemTile)

                row += 1

        except Exception as e:
            logger.warning(f"ERROR:  Failed to Refresh Source Table:\n{e}")

        finally:
            WaitPopup.closePopup()


    #   Build List of Items in Destination Directory
    @err_catcher(name=__name__)
    def refreshDestItems(self, restoreSelection=False):
        WaitPopup.showPopup(parent=self.projectBrowser)

        try:
            destDir = getattr(self, "destDir", "")

            #   Save Selection State if Needed
            if restoreSelection:
                self.fileItemSelectionState = {}
                for row in range(self.lw_destination.count()):
                    item = self.lw_destination.item(row)
                    fileTile = self.lw_destination.itemWidget(item)
                    if fileTile:
                        key = fileTile.data["uuid"]
                        self.fileItemSelectionState[key] = fileTile.isChecked()

            #   Get Dir and Set Short Name
            metrics = QFontMetrics(self.le_destPath.font())
            elided_text = metrics.elidedText(destDir, Qt.ElideMiddle, self.le_destPath.width())
            self.le_destPath.setText(elided_text)

            #   Color Dir LineEdit if Invalid
            if not os.path.exists(destDir):
                self.le_destPath.setStyleSheet("QLineEdit { border: 1px solid #cc6666; }")
            else:
                self.le_destPath.setToolTip(destDir)
                self.le_destPath.setStyleSheet("")

            #   Capture Scrollbar Position
            scrollPos = self.lw_destination.verticalScrollBar().value()

            self.destDataItems = []

            #   Create Data Item for Each Item in Dir
            for iData in self.transferList:
                self.createDestItem(iData)

            #   Sort / Filter / Refresh Destination Table
            self.refreshDestTable()

            #   Reposition Scrollbar
            QTimer.singleShot(50, lambda: self.lw_destination.verticalScrollBar().setValue(scrollPos))

            logger.debug("Refreshed Destination Items")

        except Exception as e:
            logger.warning(f"ERROR:  Failed to Refresh Destination Items:\n{e}")

        finally:
            WaitPopup.closePopup()


    #   Sort / Filter / Refresh Destination Table
    @err_catcher(name=__name__)
    def refreshDestTable(self):
        WaitPopup.showPopup(parent=self.projectBrowser)

        try:
            #   Sort the Table Items
            destDataItems_sorted = self.sortTable("destination", self.destDataItems)

            # Reset Table
            self.lw_destination.clear()
            row = 0

            #   Itterate Sorted Items and Create Tile UI Widgets
            for dataItem in destDataItems_sorted:
                fileItem = dataItem["tile"]
                fileType = dataItem["tileType"]

                itemTile = TileWidget.DestFileTile(fileItem)
                rowHeight = SOURCE_ITEM_HEIGHT

                #   Set Row Size and Add File Tile widget and Data to Row
                list_item = QListWidgetItem()
                list_item.setSizeHint(QSize(0, rowHeight))
                list_item.setData(Qt.UserRole, {
                    # "displayName": displayName,
                    "fileType": fileType
                    # "isSequence": isSequence,
                    # "seqFiles": seqFiles
                })

                self.lw_destination.addItem(list_item)
                self.lw_destination.setItemWidget(list_item, itemTile)

                row += 1

            #   Refresh Transfer Size UI
            self.refreshTotalTransSize()

        except Exception as e:
            logger.warning(f"ERROR:  Failed to Refresh Destination Table:\n{e}")

        finally:
            WaitPopup.closePopup()


    #   Create Source Data Item (this is the class that will calculate and hold all the data)
    @err_catcher(name=__name__)
    def createSourceItem(self, file, fullPath, fileType):
        try:
            #   Separate Folders and Files
            tileType = "folder" if fileType == "Folders" else "file"
            
            #   Create Data
            data = {}
            data["displayName"] = file
            data["tileType"] = tileType
            data["fileType"] = fileType
            data["uuid"] = self.createUUID()

            if fileType == "Folders":
                #    Create Folder Data Item
                data["dirPath"] = fullPath
                dataItem = TileWidget.FolderItem(self, data)

            else:
                #    Create File Data Item
                data["source_mainFile_path"] = fullPath
                dataItem = TileWidget.SourceFileItem(self, data)

            #   Get Item Data and Add to the List
            fData = dataItem.getData()
            self.sourceDataItems.append({"tile": dataItem, "tileType": tileType, "data": fData})

            logger.debug(f"Created Source Data Item for: {file}")
        
        except Exception as e:
            logger.warning(f"ERROR:  Failed to Create Source Data Item for:\n{file}\n\n{e}")


    #   Create Dest Data Item (this is the class that will calculate and hold all the data)
    @err_catcher(name=__name__)
    def createDestItem(self, data):
        try:
            #    Create File Data Item
            dataItem = TileWidget.DestFileItem(self, data)

            #   Get Item Data and Add to the List
            fData = dataItem.getData()
            self.destDataItems.append({"tile": dataItem, "tileType": data["tileType"], "data": fData})

            logger.debug("Created Destination Data Item")

        except Exception as e:
            logger.warning(f"ERROR:  Failed to Create Destination Data Item:\n{e}")


    #   Sets Each Tile Widget Proxy UI
    @err_catcher(name=__name__)
    def toggleProxy(self, checked):
        self.proxyEnabled = checked
        self.sourceFuncts.updateUI()
        self.refreshTotalTransSize()

        for item in self.getAllDestTiles():
            item.toggleProxyProgbar()


    #   Calls Each Tile Widget to Modify Name if Enabled
    @err_catcher(name=__name__)
    def modifyFileNames(self):
        try:
            # Iterate through all QListWidgetItems and call setModifiedName on each widget
            count = self.lw_destination.count()
            for i in range(count):
                item = self.lw_destination.item(i)
                widget = self.lw_destination.itemWidget(item)

                if widget and hasattr(widget, "setModifiedName"):
                    widget.setModifiedName()

            self.sourceFuncts.updateUI()

            logger.debug("Modified Filenames")

        except Exception as e:
            logger.warning(f"ERROR:  Failed to Modify Filenames:\n{e}")


    #   Called from Tile Widget to Modify Original Name based on Active Mods
    @err_catcher(name=__name__)
    def applyMods(self, origName):
        #   Start with Orig Name
        newName = origName
        try:
            from FileNameMods import getModClassByName as GetModClass
            from FileNameMods import createModifier as CreateMod

            #    Loop Through All Modifiers
            for mod in self.nameMods:
                if mod["enabled"]:
                    modClass = GetModClass(mod["mod_type"])
                    modifier = CreateMod(modClass)
                    newName = modifier.applyMod(newName, mod["settings"])

            return newName
        
        except Exception as e:
            logger.warning(f"ERROR:  Failed to Apply Filename Mods:\n{e}")


    @err_catcher(name=__name__)
    def refreshTotalTransSize(self):
        try:
            #   Get Size Info
            self.total_transferSize = self.getTotalTransferSize()
            copySize_str = self.getFileSizeStr(self.total_transferSize)
            #   Default Tip
            totalSizeTip = "Total Transfer Size"
            #   If there will be Proxy Generation add the Asterisk and Note
            if self.proxyEnabled and self.proxyMode in ["generate", "missing"]:
                copySize_str = copySize_str + "*"
                totalSizeTip = ("Estimated Total Transfer Size\n"
                                "(may be inaccurate due to Proxy generation estimation)")
            #   Set Label and ToolTip
            self.sourceFuncts.l_size_total.setText(copySize_str)
            self.sourceFuncts.l_size_total.setToolTip(totalSizeTip)
        
        except Exception as e:
            logger.warning(f"ERROR:  Failed to Refresh Total Transfer Size:\n{e}")


    #   Opens clicked Folder and refreshes
    @err_catcher(name=__name__)
    def doubleClickFolder(self, filepath, mode):
        if mode == "source":
            self.sourceDir = filepath
            self.refreshSourceItems()


    #   Plays Media in External Player
    @err_catcher(name=__name__)
    def openInShell(self, filePath, prog=""):
        if prog == "default":
            progPath = ""
        else:
            progPath = self.mediaPlayerPath or ""

        comd = []

        fileName = os.path.basename(filePath)
        baseName, extension = os.path.splitext(fileName)
        if extension.lower() in self.core.media.supportedFormats:
            logger.debug("Opening Media File in Shell Application")

            if not progPath:
                cmd = ["start", "", "%s" % self.core.fixPath(filePath)]
                subprocess.call(cmd, shell=True)
                return
            else:
                if self.mediaPlayerPattern:
                    filePath = self.core.media.getSequenceFromFilename(filePath)

                    comd = [progPath, filePath]

        if comd:
            logger.debug("Opening File in Shell Application")

            with open(os.devnull, "w") as f:
                logger.debug("launching: %s" % comd)
                try:
                    subprocess.Popen(comd, stdin=subprocess.PIPE, stdout=f, stderr=f)
                except:
                    comd = "%s %s" % (comd[0], comd[1])
                    try:
                        subprocess.Popen(
                            comd, stdin=subprocess.PIPE, stdout=f, stderr=f, shell=True
                        )
                    except Exception as e:
                        raise RuntimeError("%s - %s" % (comd, e))


    @err_catcher(name=__name__)
    def addToDestList(self, data, refresh=False):

        #   Do Not Add if Already in the Destination List
        if self.isDuplicate(data):
            return
        
        #   If Not a Image Sequence, just Add File
        # if not data["isSequence"]:

        self.transferList.append(data)

        #   If Image Sequence
        # else:
        #     sourceDir = os.path.dirname(data["source_mainFile_path"])

        #     for image in data["seqFiles"]:
        #         print(f"*** image:  {image}")                                              #    TESTING

                

        #         iData = data.copy()
        #         iData["source_displayName"] = image
        #         iData["isSequence"] = False
        #         iData["seqFiles"] = [image]
        #         iData["source_mainFile_path"] = os.path.join(sourceDir, image)

        #         self.transferList.append(iData)



        if refresh:
            self.refreshDestItems(restoreSelection=True)


    @err_catcher(name=__name__)
    def isDuplicate(self, data):
        return data in self.transferList 
    

    @err_catcher(name=__name__)
    def addSelected(self):
        try:
            row_count = self.lw_source.count()

            for row in range(row_count):
                listItem = self.lw_source.item(row)
                fileItem = self.lw_source.itemWidget(listItem)
                
                if fileItem is not None and fileItem.objectName() == "FileTile":
                    if fileItem.isChecked():
                        self.addToDestList(fileItem.getData())

            self.refreshDestItems(restoreSelection=True)

        except Exception as e:
            logger.warning(f"ERROR:  Failed to Add Selected Item to Destination List:\n{e}")


    @err_catcher(name=__name__)
    def removeFromDestList(self, data):
        try:
            delUid = data["uuid"]

            for item in self.transferList:
                if delUid == item["uuid"]:
                    self.transferList.remove(item)
                    break

        except Exception as e:
            logger.warning(f"ERROR:  Failed to Remove Item from Destination List:\n{e}")


    @err_catcher(name=__name__)
    def clearTransferList(self, checked=False):
        try:
            if not checked:
                self.transferList = []

            else:
                row_count = self.lw_destination.count()

                for row in range(row_count):
                    listItem = self.lw_destination.item(row)
                    fileItem = self.lw_destination.itemWidget(listItem)

                    if fileItem is not None:
                        if fileItem.isChecked():
                            self.transferList.remove(fileItem.getData())

            self.refreshDestItems()

        except Exception as e:
            logger.warning(f"ERROR:  Failed to Clear Transfer List:\n{e}")


    #   Get Destination Proxy Dir from Existing Proxies
    @err_catcher(name=__name__)
    def getResolvedProxyPaths(self):
        try:
            self.resolvedProxyPaths = set()
            #   Get All Cehcked Tiles
            tiles = self.getAllDestTiles(onlyChecked=True)

            for tile in tiles:
                #   If it Has a Proxy Already
                if tile.data["hasProxy"]:
                    #   Get the Destination Proxy Dir
                    proxyDir = tile.getResolvedDestProxyPath(dirOnly=True)
                    if proxyDir:                
                        self.resolvedProxyPaths.add(proxyDir)
            logger.debug("Resolved Proxy Path(s)")

        except Exception as e:
            logger.warning(f"ERROR:  Resolving Proxy Path Failed:\n{e}")


    #   Get Storage Space Stats
    @err_catcher(name=__name__)                                         #   TODO  Move
    def getDriveSpace(self, path):
        try:
            total, used, free = shutil.disk_usage(path)   
            return free 
        except Exception as e:
            logger.warning(f"ERROR:  Failed to get Drive Space Stats:\n{e}")
    

    #   Return List of Checked Dest File Tiles
    @err_catcher(name=__name__)                                         #   TODO  Move
    def getCopyList(self):
        row_count = self.lw_destination.count()
        self.copyList = []

        for row in range(row_count):
            listItem = self.lw_destination.item(row)
            fileItem = self.lw_destination.itemWidget(listItem)

            if fileItem is not None:
                if fileItem.isChecked():
                    self.copyList.append(fileItem)

        return self.copyList


    @err_catcher(name=__name__)                                         #   TODO  Move
    def getTransferErrors(self):
        errors = {}
        warnings = {}

        ##   Check Drive Space Available
        #   Get Stats
        spaceAvail = self.getDriveSpace(os.path.normpath(self.le_destPath.text()))
        transferSize = self.getTotalTransferSize()

        #   Not Enough Space
        if transferSize >= spaceAvail:
            transSize_str = self.getFileSizeStr(transferSize)
            spaceAvail_str = self.getFileSizeStr(spaceAvail)
            errors["Not Enough Storage Space:"] = f"Transfer: {transSize_str} - Available: {spaceAvail_str}"

        #   Low Space
        elif (spaceAvail - transferSize) < 100 * 1024 * 1024:  # 100 MB
            transSize_str = self.getFileSizeStr(transferSize)
            spaceAvail_str = self.getFileSizeStr(spaceAvail)
            warnings["Storage Space Low:"] = f"Transfer: {transSize_str} - Available: {spaceAvail_str}"

        ##  File Exists
        for fileTile in self.copyList:
            if fileTile.destFileExists():
                basename = os.path.basename(fileTile.getDestMainPath())
                if self.sourceFuncts.chb_overwrite.isChecked():
                    warnings[f"{basename}: "] = "File Exists in Destination"
                else:
                    errors[f"{basename}: "] = "File Exists in Destination"

        hasErrors = True if len(errors) > 0 else False

        #   NO ERRORS
        if not errors:
            errors["None"] = ""

        #   NO ERRORS
        if not warnings:
            warnings["None"] = ""

        #   Add Blank Line at the End
        errors[""] = ""

        #   Add Blank Line at the End
        warnings[""] = ""

        return errors, warnings, hasErrors


    @err_catcher(name=__name__)                                         #   TODO  Move
    def generateTransferPopup(self):
        try:
            ##  HEADER SECTION
            header = {
                "Destination Path": self.le_destPath.text(),
                "Number of Files": len(self.copyList),
                "Total Transfer Size": self.getFileSizeStr(self.total_transferSize),                #   TODO - Get Actual Size
                "Allow Overwrite": self.sourceFuncts.chb_overwrite.isChecked(),
                "Proxy Mode:": "Disabled" if not self.proxyEnabled else self.proxyMode,
                # "Copy Proxy Files": copyProxy,
                # "Generate Proxy": self.sourceFuncts.chb_generateProxy.isChecked(),
                "": ""
            }

            ##   WARNINGS SECTION
            errors, warnings, hasErrors = self.getTransferErrors()

            ##   FILES SECTION
            file_list = []

            for item in self.copyList:
                filename = os.path.basename(item.getDestMainPath())
                
                # Create a separate group for each file
                group_box = QGroupBox(filename)
                form_layout = QFormLayout()

                # Add individual data items in separate lines
                form_layout.addRow("Date:", QLabel(item.data.get('source_mainFile_date', 'Unknown')))
                form_layout.addRow("Path:", QLabel(item.getSource_mainfilePath()))
                form_layout.addRow("Size:", QLabel(item.data.get('source_mainFile_size', 'Unknown')))

                if item.data.get('hasProxy'):
                    proxyPath = item.getSource_proxyfilePath()
                else:
                    proxyPath = "None"

                form_layout.addRow("Proxy:", QLabel(proxyPath))

                group_box.setLayout(form_layout)
                file_list.append(group_box)  # Add group box to the list

            # Combine header and file groups into a final data dict
            data = {
                "Transfer:": header,
                "Errors:": errors,
                "Warnings": warnings,
                "Files": file_list
            }

            logger.debug("Created Transfer Popup")
            return data, hasErrors
        
        except Exception as e:
            logger.warning(f"ERROR:  Failed to Create Transfer Popup:\n{e}")
        

    #   Sets Transfer Status and Prog Bar Color and Tooltip
    @err_catcher(name=__name__)
    def setTransferStatus(self, status, tooltip=None):
        try:
            self.transferState = status

            match status:
                case "Idle":
                    statusColor = COLOR_BLUE
                case "Transferring":
                    statusColor = COLOR_BLUE
                case "Generating Proxy":
                    statusColor = COLOR_BLUE
                case "Paused":
                    statusColor = COLOR_GREY
                case "Cancelled":
                    statusColor = COLOR_RED
                case "Warning":
                    statusColor = COLOR_ORANGE
                case "Complete":
                    statusColor = COLOR_GREEN
                case "Error":
                    statusColor = COLOR_RED

            #   Set the Prog Bar Tooltip
            if tooltip:
                self.sourceFuncts.progBar_total.setToolTip(tooltip)
            else:
                self.sourceFuncts.progBar_total.setToolTip(status)

            #   Convert Color to rgb format string
            color_str = f"rgb({statusColor.red()}, {statusColor.green()}, {statusColor.blue()})"
            
            #   Set Prog Bar StyleSheet
            self.sourceFuncts.progBar_total.setStyleSheet(f"""
                QProgressBar::chunk {{
                    background-color: {color_str};  /* Set the chunk color */
                }}
            """)

            # logger.debug(f"Set Transfer Status: {status}")

        except Exception as e:
            logger.warning(f"ERROR:  Failed to Set Transfer Status:\n{e}")



    @err_catcher(name=__name__)                                         #   TODO  Move
    def startTransfer(self):
        # Timer for Progress Updates
        self.progressTimer = QTimer(self)
        self.progressTimer.setInterval(self.progUpdateInterval * 1000)
        self.progressTimer.timeout.connect(self.updateTransfer)

        #   Capture Time for Elapsed Calc
        self.transferStartTime = time()

        #   Initialize Time Remaining Calc
        self.speedSamples = deque(maxlen=10)

        self.refreshTotalTransSize()

        self.copyList = self.getCopyList()

        if len(self.copyList) == 0:
            self.core.popup("There are no Items Selected to Transfer")
            return False
        
        if not os.path.isdir(self.le_destPath.text()):
            self.core.popup("YOU FORGOT TO SELECT DEST DIR")
            return False

        #   Reset Calculated Proxy Multipliers
        self.calculated_proxyMults = [] 

        #   If Override is NOT Selected Attempt to Get Resolved Path
        resolved_proxyDir = None
        self.getResolvedProxyPaths()

        if self.resolvedProxyPaths:
            resolved_proxyDir = next(iter(self.resolvedProxyPaths))
            

        #   Get Formatted Transfer Details
        popupData, hasErrors = self.generateTransferPopup()

        #   Add Buttons
        buttons = ["Start Transfer", "Cancel"]
        #   Call Transfer Popup
        result = DisplayPopup.display(popupData, title="Transfer", buttons=buttons)

        #   If User Selects Transfer
        if result == "Start Transfer":
            #   Abort if there are Any Errors
            if hasErrors:
                errors = popupData.get('Errors:', {})
                errorText = "\n".join(f"{key}   {value}" for key, value in errors.items())

                self.core.popup("Unable to Start Transfer.\n\n"
                                "Errors:\n\n"
                                f"{errorText}")
                
                #   Abort if there are Errors
                return

            options = {}
            if self.proxyEnabled:
                #   Get Proxy Preset Data
                try:
                    presets = self.ffmpegPresets
                    preset = presets[self.proxySettings["proxyPreset"]]
                except KeyError:
                    raise RuntimeError(f"Proxy preset {self.proxySettings['proxyPreset']} not found in settings")

                proxySettings = self.proxySettings.copy()

                proxySettings.update({
                    "resolved_proxyDir": resolved_proxyDir,
                    "scale"            : self.proxySettings["proxyScale"],
                    "Video_Parameters" : preset["Video_Parameters"],
                    "Audio_Parameters" : preset["Audio_Parameters"],
                    "Extension"        : preset["Extension"],
                    "Multiplier"        : preset["Multiplier"]
                })

                options["proxySettings"] = proxySettings

            self.progressTimer.start()
            self.setTransferStatus("Transferring")
            self.configTransUI("transfer")
            logger.status("Transfer Started")

            #   Start Transfer for Every Item
            for item in self.copyList:
                item.start_transfer(self, options, self.proxyEnabled, self.proxyMode)


    @err_catcher(name=__name__)
    def pauseTransfer(self):
        for item in self.copyList:
            item.pause_transfer(self)

        self.progressTimer.stop()
        self.setTransferStatus("Paused")
        self.configTransUI("pause")

        logger.status("Pausing Transfer")


    @err_catcher(name=__name__)
    def resumeTransfer(self):
        #   Initialize Time Remaining Calc
        self.speedSamples = deque(maxlen=10)

        for item in self.copyList:
            item.resume_transfer(self)

        self.progressTimer.start()
        self.setTransferStatus("Transferring")
        self.configTransUI("resume")

        logger.status("Resuming Transfer")


    @err_catcher(name=__name__)
    def cancelTransfer(self):
        for item in self.copyList:
            item.cancel_transfer(self)

        self.progressTimer.stop()
        self.setTransferStatus("Cancelled")
        self.configTransUI("cancel")

        logger.status("Cancelling Transfer")


    @err_catcher(name=__name__)
    def resetTransfer(self):
        self.progressTimer.stop()
        self.reset_ProgBar()
        self.setTransferStatus("Idle")
        self.configTransUI("idle")

        self.refreshDestItems()


    #   Update Total Progess Bar based on self.progressTimer
    @err_catcher(name=__name__)
    def updateTransfer(self):
        try:
            # Get Transferred Amount from Every FileTile
            total_copied = sum(item.getCopiedSize() for item in self.copyList)
            #   Update Copied Size in the UI
            totalSize_str = self.getFileSizeStr(total_copied)
            self.sourceFuncts.l_size_copied.setText(totalSize_str)

            #   Calculate the Time Elapsed
            timeElapsed = self.getTimeElapsed()
            self.timeElapsed = timeElapsed
            self.sourceFuncts.l_time_elapsed.setText(self.getFormattedTimeStr(timeElapsed))

            #   Calculate the Estimated Time Remaining
            timeRemaining = self.getTimeRemaining(total_copied, self.total_transferSize)
            #   Update Time Remaining in the UI
            self.sourceFuncts.l_time_remain.setText(self.getFormattedTimeStr(timeRemaining))

            #   Get Tranfer Status for Every FileTile
            overall_statusList = [transfer.transferState for transfer in self.copyList]

            #   Determine Overall Status based on Priority
            if "Cancelled" in overall_statusList:
                overall_status = "Cancelled"
            elif "Error" in overall_statusList:
                overall_status = "Error"
            elif "Warning" in overall_statusList:
                overall_status = "Warning"
            elif all(status == "Complete" for status in overall_statusList):
                overall_status = "Complete"
            elif any(status == "Paused" for status in overall_statusList):
                overall_status = "Paused"
            elif any(status == "Transferring" for status in overall_statusList):
                overall_status = "Transferring"
            elif any(status == "Generating Proxy" for status in overall_statusList):
                overall_status = "Generating Proxy"
            else:
                overall_status = "Idle"

            self.setTransferStatus(overall_status)

            # Update progress bar
            progress = (total_copied / self.total_transferSize) * 100 if self.total_transferSize > 0 else 0
            self.sourceFuncts.progBar_total.setValue(progress)

            if overall_status in ["Cancelled", "Complete"]:
                self.completeTranfer(overall_status)

            logger.debug(f"Updated Overall Status: {overall_status}")

        except Exception as e:
            logger.warning(f"ERROR:  Failed to Update Transfer Progress:\n{e}")


    @err_catcher(name=__name__)                                                 #   TODO
    def completeTranfer(self, result):
        self.progressTimer.stop()
        self.setTransferStatus(result)
        self.sourceFuncts.progBar_total.setValue(100)
        logger.status(f"Transfer Result: {result}")

        self.configTransUI("complete")                      #   TODO

        if self.useTransferReport:
            self.createTransferReport()

        if self.calculated_proxyMults:
            #   Updates Presets Multiplier
            self.updateProxyPresetMultipliers()

        if self.useCompleteSound:
            try:
                if result == "Complete":
                    playsound(SOUND_SUCCESS)
                else:
                    playsound(SOUND_ERROR)
            except:
                QApplication.beep()

        if self.useCompletePopup:
            text = "Transfer Complete"
            title = "Transfer Complete"

            if self.useTransferReport:
                buttons = ["Open in Explorer", "Open Report", "Close"]
            else:
                buttons = ["Open in Explorer", "Close"]

            result = self.core.popupQuestion(text, title=title, buttons=buttons, doExec=True)

            if result == "Open in Explorer":
                self.openInExplorer(os.path.normpath(self.le_destPath.text()))

            elif result == "Open Report":
                self.core.openFile(self.transferReportPath)


    #   Creates Transfer Report PDF
    @err_catcher(name=__name__)
    def createTransferReport(self):
        try:
            #   Gets Destination Directory for Save Path
            saveDir = self.le_destPath.text()
            #   Uses CopyList for Report
            reportData = self.copyList

            #   Header Data Items
            report_uuid = self.createUUID()
            timestamp_file = datetime.now().strftime("%Y-%m-%d_%H%M%S")
            timestamp_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            projectName = self.core.projectName
            user = self.core.username
            transferSize = self.getFileSizeStr(self.total_transferSize)
            transferTime = self.getFormattedTimeStr(self.timeElapsed)

            #   Creates Report Filename
            reportFilename = f"TransferReport_{timestamp_file}_{report_uuid}.pdf"
            self.transferReportPath = os.path.join(saveDir, reportFilename)

            #   Creates New PDF Canvas
            c = canvas.Canvas(self.transferReportPath, pagesize=A4)
            width, height = A4

            #   Icon
            icon = self.getCustomIcon()
            icon_size = 18
            icon_x = 50
            icon_y = height - 48

            #   Margin and Spacing
            left_margin = 50
            col_spacing = 75

            #   Page number helper
            def draw_page_number():
                page_num = c.getPageNumber()
                c.setFont("Helvetica", 9)
                c.drawRightString(width - 50, 30, f"Page {page_num}")

            def next_page():
                draw_page_number()
                c.showPage()
                c.setFont("Helvetica", 11)

            ## --- Page 1: Header info ---  ##

            #   Add Prims Icon to Left of Title Line
            if os.path.exists(icon):
                try:
                    c.drawImage(icon, icon_x, icon_y, width=icon_size, height=icon_size, mask='auto')
                except Exception as e:
                    logger.warning(f"ERROR: Failed to load icon: {e}")

            #   Add Title Line
            c.setFont("Helvetica-Bold", 16)
            c.drawString(icon_x + icon_size + 5, height - 45, "File Transfer Completion Report")

            #   Header Data Spacing
            header_y = height - 70
            header_line_height = 14
            c.setFont("Helvetica", 10)

            #   Add Header Data Items
            header_data = [
                ("Transfer Date:", timestamp_text),
                ("Report ID:", report_uuid),
                ("Project:", projectName),
                ("User:", user),
                ("Number of Files:", str(len(reportData))),
                ("Transfer Size:", transferSize),
                ("Transfer Time:", transferTime)
            ]

            #   Add Each Data Item
            for label, value in header_data:
                c.drawString(left_margin, header_y, label)
                c.drawString(left_margin + col_spacing, header_y, value)
                header_y -= header_line_height

            ## --- Page 2 (and on): File info ---    ##

            next_page()

            #   Files Section Spacing
            y = height - 50
            line_height = 11
            block_spacing = 10

            #   If No Transferd Files
            if not reportData:
                c.setFont("Helvetica", 10)
                c.drawString(left_margin, y, "No files were transferred.")

            #   Add Files Section Title Line
            else:
                c.setFont("Helvetica-Bold", 12)
                c.drawString(left_margin, y, f"Transferred {len(reportData)} file(s):")
                y -= line_height + 4

                #   Font for Files Section
                c.setFont("Helvetica", 9)

                #   File Data Items
                for item in reportData:
                    baseName = os.path.basename(item.getDestMainPath())
                    date_str = item.data['source_mainFile_date']
                    sourcePath = item.getSource_mainfilePath()
                    destPath = item.getDestMainPath()
                    size_str = item.data['source_mainFile_size']
                    time_str = item.data["transferTime"]
                    hash_source = item.data['source_mainFile_hash']
                    hash_dest = item.data['dest_mainFile_hash']
                    hasProxy = item.data['hasProxy']

                    file_lines = [
                        ("Filename:", baseName),
                        ("Date:", date_str),
                        ("Source:", sourcePath),
                        ("Destination:", destPath),
                        ("Size:", size_str),
                        ("Transfer Time:", time_str),
                        ("Hash (source):", hash_source),
                        ("Hash (dest):", hash_dest),
                        ("Proxy present:", str(hasProxy))
                    ]

                    #   Check if the Current File Block Can Fit on Page
                    block_height = len(file_lines) * line_height + block_spacing
                    if y - block_height < 50:
                        next_page()
                        c.setFont("Helvetica", 9)
                        y = height - 50

                    #   Create File Block
                    for label, value in file_lines:
                        c.drawString(left_margin, y, label)
                        c.drawString(left_margin + col_spacing, y, value)
                        y -= line_height

                    y -= block_spacing

            draw_page_number()
            c.save()

            logger.status("Created Transfer Report")
        
        except Exception as e:
            logger.warning(f"ERROR:  Failed to Create Transfer Report:\n{e}")



    @err_catcher(name=__name__)
    def updateProxyPresetMultipliers(self):
        try:
            #   Get Preset Info
            presetName = self.proxySettings.get("proxyPreset", "")
            allPresets = self.getSettings(key="ffmpegPresets")
            preset = allPresets.get(presetName)

            if not preset:
                logger.warning(f"Preset '{presetName}' not found in ffmpegPresets.")
                return

            #   Get Saved Multiplier
            old_mult = float(preset["Multiplier"])

            #   Make Copy of New Mults and add the Old Mult
            new_mults = [float(m) for m in self.calculated_proxyMults]
            new_mults.append(old_mult)

            #   Average All Multipliers
            new_averageMulti = round(sum(new_mults) / len(new_mults), 2) if new_mults else 0.0

            #   Clamp and Round New Multiplier
            new_averageMulti = round(max(0.01, min(new_averageMulti, 5.0)), 2)

            #   Save New Multiplier to Settings
            preset["Multiplier"] = new_averageMulti
            self.plugin.saveSettings(key="ffmpegPresets", data=allPresets)

            logger.status(f"Updated Proxy Multiplier for preset '{presetName}': {new_averageMulti}")

        except Exception as e:
            logger.warning(f"ERROR: Failed to Update Proxy Preset Multiplier:\n{e}")




    @err_catcher(name=__name__)
    def getSelectedContexts(self):
        contexts = []
        if len(self.lw_source.selectedItems()) > 1:
            contexts = self.lw_source.selectedItems()
        elif len(self.lw_destination.selectedItems()) > 1:
            contexts = self.lw_destination.selectedItems()
        else:
            data = self.getCurrentFilelayer()
            if not data:
                data = self.getCurrentSource()
                if not data:
                    data = self.getCurrentAOV()
                    if not data:
                        items = self.lw_destination.selectedItems()
                        if items:
                            data = items[0].data(Qt.UserRole)

            if data:
                contexts = [data]

        return contexts
    

    # @err_catcher(name=__name__)
    # def taskClicked(self):
    #     self.updateVersions()


    # @err_catcher(name=__name__)
    # def sourceClicked(self):
    #     self.mediaPlayer.updateLayers(restoreSelection=True)


    # @err_catcher(name=__name__)
    # def onVersionDoubleClicked(self, item):
    #     mods = QApplication.keyboardModifiers()
    #     if mods == Qt.ControlModifier:
    #         for selItem in self.lw_destination.selectedItems():
    #             self.core.openFolder(selItem.data(Qt.UserRole).get("path"))
    #     else:
    #         self.showVersionInfoForItem(item)


    # @err_catcher(name=__name__)
    # def mouseDrag(self, event, element):
    #     if (
    #         (event.buttons() != Qt.LeftButton and element != self.cb_layer)
    #         or (
    #             event.buttons() == Qt.LeftButton
    #             and (event.modifiers() & Qt.ShiftModifier)
    #         )
    #     ):
    #         element.mmEvent(event)
    #         return
    #     elif element == self.cb_layer and event.buttons() != Qt.MiddleButton:
    #         element.mmEvent(event)
    #         return

    #     contexts = self.getCurRenders()
    #     urlList = []
    #     mods = QApplication.keyboardModifiers()
    #     for context in contexts:
    #         if element == self.cb_layer:
    #             version = self.getCurrentSource()
    #             aovs = self.core.mediaProducts.getAOVsFromVersion(version)
    #             for aov in aovs:
    #                 url = os.path.normpath(aov["path"])
    #                 urlList.append(QUrl(url))
    #             break
    #         else:
    #             if mods == Qt.ControlModifier:
    #                 url = os.path.normpath(context["path"])
    #                 urlList.append(url)
    #             else:
    #                 imgSrc = self.core.media.getImgSources(context["path"], sequencePattern=False)
    #                 for k in imgSrc:
    #                     url = os.path.normpath(k)
    #                     urlList.append(url)

    #     if len(urlList) == 0:
    #         return

    #     drag = QDrag(self)
    #     mData = QMimeData()

    #     urlData = [QUrl.fromLocalFile(urll) for urll in urlList]
    #     mData.setUrls(urlData)
    #     drag.setMimeData(mData)

    #     drag.exec_(Qt.CopyAction | Qt.MoveAction)


    @err_catcher(name=__name__)
    def setPreview(self):
        entity = self.getCurrentEntity()
        pm = self.mediaPlayer.mediaPlayer.l_preview.pixmap()
        self.core.entities.setEntityPreview(entity, pm)
        self.core.pb.sceneBrowser.refreshEntityInfo()
        self.w_entities.getCurrentPage().refreshEntities(restoreSelection=True)




class MediaPlayer(QWidget):
    def __init__(self, origin):
        super(MediaPlayer, self).__init__()


        # self.mediaVersionPlayer = origin
        # self.origin = self.mediaVersionPlayer.origin


        self.origin = origin


        self.core = self.origin.core

        self.renderResX = 300
        self.renderResY = 169
        self.videoReaders = {}
        self.currentMediaPreview = None
        self.mediaThreads = []
        self.timeline = None
        self.tlPaused = False
        self.seq = []
        self.pduration = 0
        self.pwidth = 0
        self.pheight = 0
        self.pstart = 0
        self.pend = 0
        self.openMediaPlayer = False
        self.emptypmap = self.createPMap(self.renderResX, self.renderResY)
        self.previewTooltip = "Left mouse drag to drag media files.\nCtrl+Left mouse drag to drag media folder."
        self.previewEnabled = True
        self.state = "enabled"
        self.core.registerCallback("onUserSettingsSave", self.onUserSettingsSave)
        self.updateExternalMediaPlayer()
        self.setupUi()
        self.connectEvents()

    @err_catcher(name=__name__)
    def sizeHint(self):
        return QSize(400, 100)

    @err_catcher(name=__name__)
    def setupUi(self):
        self.lo_main = QVBoxLayout(self)
        self.lo_main.setContentsMargins(0, 0, 0, 0)
        self.l_info = QLabel(self)
        self.l_info.setText("")
        self.l_info.setObjectName("l_info")
        self.lo_main.addWidget(self.l_info)


        self.container_viewLut = QWidget()
        self.lo_viewLut = QHBoxLayout(self.container_viewLut)
        self.l_viewLut = QLabel("View Lut Preset:")
        self.cb_viewLut = QComboBox()
        self.lo_viewLut.addWidget(self.l_viewLut)
        self.lo_viewLut.addWidget(self.cb_viewLut)
        self.lo_main.addWidget(self.container_viewLut)


        self.l_preview = QLabel(self)
        self.l_preview.setContextMenuPolicy(Qt.CustomContextMenu)
        self.l_preview.setText("")
        self.l_preview.setAlignment(Qt.AlignCenter)
        self.l_preview.setObjectName("l_preview")
        self.lo_main.addWidget(self.l_preview)

        #   Proxy Icon Label
        pxyIconPath = os.path.join(iconDir, "pxy_icon.png")
        pxyIcon = self.core.media.getColoredIcon(pxyIconPath)
        self.l_pxyIcon = QLabel(self.l_preview)
        self.l_pxyIcon.setPixmap(pxyIcon.pixmap(40, 40))
        self.l_pxyIcon.setStyleSheet("background-color: rgba(0,0,0,0);")
        self.l_pxyIcon.setVisible(False)

        self.l_loading = QLabel(self)
        self.l_loading.setAlignment(Qt.AlignCenter)
        self.l_loading.setVisible(False)

        self.w_timeslider = QWidget()
        self.lo_timeslider = QHBoxLayout(self.w_timeslider)
        self.lo_timeslider.setContentsMargins(0, 0, 0, 0)
        self.l_start = QLabel()
        self.l_end = QLabel()
        self.sl_preview = QSlider(self)
        sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.sl_preview.sizePolicy().hasHeightForWidth())
        self.sl_preview.setSizePolicy(sizePolicy)
        self.sl_preview.setOrientation(Qt.Horizontal)
        self.sl_preview.setObjectName("sl_preview")
        self.sl_preview.setMaximum(999)
        self.lo_timeslider.addWidget(self.l_start)
        self.lo_timeslider.addWidget(self.sl_preview)
        self.lo_timeslider.addWidget(self.l_end)
        self.sp_current = QSpinBox()
        self.sp_current.sizeHint = lambda: QSize(30, 0)
        self.sp_current.setStyleSheet("min-width: 30px;")
        self.sp_current.setValue(self.pstart)
        self.sp_current.setButtonSymbols(QAbstractSpinBox.NoButtons)
        sizePolicy = self.sp_current.sizePolicy()
        sizePolicy.setHorizontalPolicy(QSizePolicy.Preferred)
        self.sp_current.setSizePolicy(sizePolicy)
        self.lo_timeslider.addWidget(self.sp_current)
        self.lo_main.addWidget(self.w_timeslider)

        self.w_playerCtrls = QWidget()
        self.lo_playerCtrls = QHBoxLayout(self.w_playerCtrls)
        self.lo_playerCtrls.setContentsMargins(0, 0, 0, 0)
        
        self.b_first = QToolButton()
        self.b_first.clicked.connect(self.onFirstClicked)
        self.b_prev = QToolButton()
        self.b_prev.clicked.connect(self.onPrevClicked)
        self.b_play = QToolButton()
        self.b_play.clicked.connect(self.onPlayClicked)
        self.b_next = QToolButton()
        self.b_next.clicked.connect(self.onNextClicked)
        self.b_last = QToolButton()
        self.b_last.clicked.connect(self.onLastClicked)
        
        self.lo_playerCtrls.addWidget(self.b_first)
        self.lo_playerCtrls.addStretch()
        self.lo_playerCtrls.addWidget(self.b_prev)
        self.lo_playerCtrls.addWidget(self.b_play)
        self.lo_playerCtrls.addWidget(self.b_next)
        self.lo_playerCtrls.addStretch()
        self.lo_playerCtrls.addWidget(self.b_last)
        self.lo_main.addWidget(self.w_playerCtrls)

        path = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "first.png"
        )
        icon = self.core.media.getColoredIcon(path)
        self.b_first.setIcon(icon)
        self.b_first.setToolTip("First Frame")

        path = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "prev.png"
        )
        icon = self.core.media.getColoredIcon(path)
        self.b_prev.setIcon(icon)
        self.b_prev.setToolTip("Previous Frame")

        path = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "play.png"
        )
        icon = self.core.media.getColoredIcon(path)
        self.b_play.setIcon(icon)
        self.b_play.setToolTip("Play")

        path = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "next.png"
        )
        icon = self.core.media.getColoredIcon(path)
        self.b_next.setIcon(icon)
        self.b_next.setToolTip("Next Frame")

        path = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "last.png"
        )
        icon = self.core.media.getColoredIcon(path)
        self.b_last.setIcon(icon)
        self.b_last.setToolTip("Last Frame")

        if self.core.appPlugin.pluginName != "Standalone":
            ssheet = "QWidget{padding: 0; border-width: 0px;background-color: transparent} QWidget:hover{border-width: 0px;background-color: rgba(255,255,255,50) }"
            self.b_first.setStyleSheet(ssheet)
            self.b_prev.setStyleSheet(ssheet)
            self.b_play.setStyleSheet(ssheet)
            self.b_next.setStyleSheet(ssheet)
            self.b_last.setStyleSheet(ssheet)

        self.l_preview.setAcceptDrops(True)
        self.l_preview.dragEnterEvent = self.previewDragEnterEvent
        self.l_preview.dragMoveEvent = self.previewDragMoveEvent
        self.l_preview.dragLeaveEvent = self.previewDragLeaveEvent
        self.l_preview.dropEvent = self.previewDropEvent
        self.l_preview.setStyleSheet("QWidget { border-style: dashed; border-color: rgba(0, 0, 0, 0);  border-width: 2px; }")

        self.l_preview.setMinimumWidth(self.renderResX)
        self.l_preview.setMinimumHeight(self.renderResY)
        self.l_preview.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)


    @err_catcher(name=__name__)
    def connectEvents(self):
        self.l_preview.clickEvent = self.l_preview.mouseReleaseEvent
        self.l_preview.mouseReleaseEvent = self.previewClk
        self.l_preview.dclickEvent = self.l_preview.mouseDoubleClickEvent
        self.l_preview.mouseDoubleClickEvent = self.previewDclk
        self.l_preview.resizeEventOrig = self.l_preview.resizeEvent
        self.l_preview.resizeEvent = self.previewResizeEvent
        self.l_preview.customContextMenuRequested.connect(self.rclPreview)
        self.l_preview.mouseMoveEvent = lambda x: self.mouseDrag(x, self.l_preview)

        self.sl_preview.valueChanged.connect(self.sliderChanged)
        self.sl_preview.sliderPressed.connect(self.sliderClk)
        self.sl_preview.sliderReleased.connect(self.sliderRls)
        self.sl_preview.origMousePressEvent = self.sl_preview.mousePressEvent
        self.sl_preview.mousePressEvent = self.sliderDrag
        self.sp_current.valueChanged.connect(self.onCurrentChanged)


    @err_catcher(name=__name__)
    def onUserSettingsSave(self, origin):
        self.updateExternalMediaPlayer()


    @err_catcher(name=__name__)
    def setPreviewEnabled(self, state):
        self.previewEnabled = state
        self.l_preview.setVisible(state)
        self.w_timeslider.setVisible(state)
        self.w_playerCtrls.setVisible(state)


    @err_catcher(name=__name__)
    def onFirstClicked(self):
        self.timeline.setCurrentTime(0)


    @err_catcher(name=__name__)
    def onPrevClicked(self):
        time = self.timeline.currentTime() - self.timeline.updateInterval()
        if time < 0:
            time = self.timeline.duration() - self.timeline.updateInterval()

        self.timeline.setCurrentTime(time)


    @err_catcher(name=__name__)
    def onPlayClicked(self):
        if not self.seq:
            return

        self.setTimelinePaused(self.timeline.state() == QTimeLine.Running)


    @err_catcher(name=__name__)
    def onNextClicked(self):
        time = self.timeline.currentTime() + self.timeline.updateInterval()
        time = min(self.timeline.duration(), time)
        self.timeline.setCurrentTime(time)


    @err_catcher(name=__name__)
    def onLastClicked(self):
        self.timeline.setCurrentTime(self.timeline.updateInterval() * (self.pduration - 1))


    @err_catcher(name=__name__)
    def sliderChanged(self, val):
        if not self.seq:
            return

        time = int(val / self.sl_preview.maximum() * self.timeline.duration())
        if time == self.timeline.duration():
            time -= 1

        self.timeline.setCurrentTime(time)


    @err_catcher(name=__name__)
    def onCurrentChanged(self, value):
        if not self.timeline:
            return

        time = (value - self.pstart) * self.timeline.updateInterval()
        self.timeline.setCurrentTime(time)


    # @err_catcher(name=__name__)
    # def getAutoplay(self):
    #     if not getattr(self.origin, "projectBrowser", None):
    #         return

    #     return self.origin.projectBrowser.actionAutoplay.isChecked()


    @err_catcher(name=__name__)
    def getSelectedImage(self):
        return self.mediaFiles


    # @err_catcher(name=__name__)
    # def getFilesFromContext(self, context):
    #     return self.core.mediaProducts.getFilesFromContext(context)

    @err_catcher(name=__name__)
    def updatePreview(self, mediaFiles, isProxy=False, regenerateThumb=False):
        if not self.previewEnabled:
            return
        
        self.l_pxyIcon.setVisible(isProxy)

        if self.timeline:
            curFrame = self.getCurrentFrame()

            if self.timeline.state() != QTimeLine.NotRunning:
                if self.timeline.state() == QTimeLine.Running:
                    self.tlPaused = False
                elif self.timeline.state() == QTimeLine.Paused:
                    self.tlPaused = True

                self.timeline.stop()
        else:
            self.tlPaused = True
            curFrame = 0

        for thread in reversed(self.mediaThreads):
            if thread.isRunning():
                thread.requestInterruption()

        prevFrame = self.pstart + curFrame
        self.sl_preview.setValue(0)
        self.sp_current.setValue(0)
        self.seq = []
        self.prvIsSequence = False

        QPixmapCache.clear()
        for videoReader in self.videoReaders:
            if not self.core.isStr(self.videoReaders[videoReader]):
                try:
                    self.videoReaders[videoReader].close()
                except:
                    pass

        self.videoReaders = {}
        # contexts = self.getSelectedContexts()
        # if len(contexts) > 1:
        #     self.l_info.setText("\nMultiple items selected\n")
        #     self.l_info.setToolTip("")
        #     self.l_preview.setToolTip("")
        # else:

        if mediaFiles:
            # mediaFiles = self.getFilesFromContext(contexts[0])
            # validFiles = self.core.media.filterValidMediaFiles(mediaFiles)


            # self.mediaFiles = mediaFiles
            # mediaFiles = [mediaFiles]

            self.mediaFiles = mediaFiles = [mediaFiles]


            # if validFiles:
            validFiles = sorted(mediaFiles, key=lambda x: x if "cryptomatte" not in os.path.basename(x) else "zzz" + x)

            baseName, extension = os.path.splitext(validFiles[0])
            extension = extension.lower()
            seqFiles = self.core.media.detectSequence(validFiles)

            if (
                len(seqFiles) > 1
                and extension not in self.core.media.videoFormats
                ):
                self.seq = seqFiles
                self.prvIsSequence = True
                (
                    self.pstart,
                    self.pend,
                ) = self.core.media.getFrameRangeFromSequence(seqFiles)

            else:
                self.prvIsSequence = False
                self.seq = validFiles

            self.pduration = len(self.seq)

            imgPath = validFiles[0]
            if (
                self.pduration == 1
                and os.path.splitext(imgPath)[1].lower() in self.core.media.videoFormats
                ):
                self.vidPrw = "loading"
                self.updatePrvInfo(
                    imgPath,
                    vidReader="loading",
                    frame=prevFrame,
                )

            else:
                self.updatePrvInfo(imgPath, frame=prevFrame)

            if self.tlPaused:
                self.changeImage_threaded(regenerateThumb=regenerateThumb)
            elif self.pduration < 3:
                self.changeImage_threaded(regenerateThumb=regenerateThumb)

            return True

            self.updatePrvInfo()

        pmap = self.core.media.scalePixmap(self.emptypmap, self.getThumbnailWidth(), self.getThumbnailHeight())
        self.currentMediaPreview = pmap
        self.l_preview.setPixmap(pmap)
        self.sl_preview.setEnabled(False)
        self.l_start.setText("")
        self.l_end.setText("")
        self.w_playerCtrls.setEnabled(False)
        self.sp_current.setEnabled(False)
        if hasattr(self, "loadingGif") and self.loadingGif.state() == QMovie.Running:
            self.l_loading.setVisible(False)
            self.loadingGif.stop()




    @err_catcher(name=__name__)
    def updatePrvInfo(self, prvFile="", vidReader=None, seq=None, frame=None):
        if seq is not None:
            if self.seq != seq:
                logger.debug("exit preview info update")
                return

        if not os.path.exists(prvFile):
            self.l_info.setText("\nNo image found\n")
            self.l_info.setToolTip("")
            self.l_preview.setToolTip("")
            return

        if self.state == "disabled" or os.getenv("PRISM_DISPLAY_MEDIA_RESOLUTION") == "0":
            self.pwidth = "?"
            self.pheight = "?"
        else:
            if vidReader == "loading":
                self.pwidth = "loading..."
                self.pheight = ""
            else:
                resolution = self.core.media.getMediaResolution(prvFile, videoReader=vidReader)
                self.pwidth = resolution["width"]
                self.pheight = resolution["height"]
                pass

        ext = os.path.splitext(prvFile)[1].lower()
        if ext in self.core.media.videoFormats:
            if len(self.seq) == 1:
                if self.core.isStr(vidReader) or self.state == "disabled":
                    duration = 1
                else:
                    # duration = self.core.media.getVideoDuration(prvFile, videoReader=vidReader)
                    duration = self.getVideoDuration(prvFile)
                    if not duration:
                        duration = 1

                self.pduration = duration

        self.pformat = "*" + ext

        pdate = self.core.getFileModificationDate(prvFile)
        self.sl_preview.setEnabled(True)
        start = "1"
        end = "1"
        if self.prvIsSequence:
            start = str(self.pstart)
            end = str(self.pend)
        elif ext in self.core.media.videoFormats:
            if self.pwidth != "?":
                end = str(int(start) + self.pduration - 1)

        self.l_start.setText(start)
        self.l_end.setText(end)
        self.sp_current.setMinimum(int(start))
        self.sp_current.setMaximum(int(end))
        self.w_playerCtrls.setEnabled(True)
        self.sp_current.setEnabled(True)

        if self.timeline:
            self.timeline.stop()

        fps = self.core.projects.getFps() or 25
        self.timeline = QTimeLine(
            int(1000/float(fps)) * self.pduration, self
        )
        self.timeline.setEasingCurve(QEasingCurve.Linear)
        self.timeline.setLoopCount(0)
        self.timeline.setUpdateInterval(int(1000/float(fps)))
        self.timeline.valueChanged.connect(
            lambda x: self.changeImg(x)
        )
        QPixmapCache.setCacheLimit(2097151)
        frame = frame or self.pstart
        if frame != self.sp_current.value():
            self.sp_current.setValue(frame)
        else:
            self.onCurrentChanged(self.sp_current.value())

        self.timeline.resume()

        if self.tlPaused or self.state == "disabled":
            self.setTimelinePaused(True)

        if self.pduration == 1:
            frStr = "frame"
        else:
            frStr = "frames"

        width = self.pwidth if self.pwidth is not None else "?"
        height = self.pheight if self.pheight is not None else "?"

        if self.prvIsSequence:
            infoStr = "%sx%s   %s   %s-%s (%s %s)" % (
                width,
                height,
                self.pformat,
                self.pstart,
                self.pend,
                self.pduration,
                frStr,
            )
        elif len(self.seq) > 1:
            infoStr = "%s files %sx%s   %s\n%s" % (
                self.pduration,
                width,
                height,
                self.pformat,
                os.path.basename(prvFile),
            )
        elif ext in self.core.media.videoFormats:
            if self.pwidth == "?":
                duration = "?"
                frStr = "frames"
            else:
                duration = self.pduration

            if self.pwidth == "loading...":
                infoStr = "\n" + os.path.basename(prvFile)
            else:
                infoStr = "%sx%s   %s %s\n%s" % (
                    width,
                    height,
                    duration,
                    frStr,
                    os.path.basename(prvFile),
                )
                if self.core.isStr(duration) or duration <= 1:
                    self.sl_preview.setEnabled(False)
                    self.l_start.setText("")
                    self.l_end.setText("")
                    self.w_playerCtrls.setEnabled(False)
                    self.sp_current.setEnabled(False)
        else:
            infoStr = "%sx%s\n%s" % (
                width,
                height,
                os.path.basename(prvFile),
            )
            self.sl_preview.setEnabled(False)
            self.l_start.setText("")
            self.l_end.setText("")
            self.w_playerCtrls.setEnabled(False)
            self.sp_current.setEnabled(False)

        infoStr += "\n" + pdate

        if self.core.getConfig("globals", "showFileSizes"):
            size = 0
            for file in self.seq:
                if os.path.exists(file):
                    size += float(os.stat(file).st_size / 1024.0 / 1024.0)

            infoStr += " - %.2f mb" % size

        if self.state == "disabled":
            infoStr += "\nPreview is disabled"
            self.sl_preview.setEnabled(False)
            self.w_playerCtrls.setEnabled(False)
            self.sp_current.setEnabled(False)

        self.setInfoText(infoStr)
        self.l_info.setToolTip(infoStr)
        self.l_preview.setToolTip(self.previewTooltip)


####################    TESTING ####################





    @err_catcher(name=__name__)
    def getVideoDuration(self, filePath):
        ffprobePath = self.origin.getFFprobePath()

        kwargs = {
            "stdout": subprocess.PIPE,
            "stderr": subprocess.PIPE,
            "text":   True,
        }

        if sys.platform == "win32":
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

        #   Execute Quick Method
        result = subprocess.run(
            [
                ffprobePath,
                "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=nb_frames",
                "-of", "default=nokey=1:noprint_wrappers=1",
                filePath
            ],
            **kwargs
        )

        #   Get Frames from Output
        frames = result.stdout.strip()

        #   If Quick Method didnt work, try Slower Fallback Method
        if frames == 'N/A' or not frames.isdigit():
            result = subprocess.run(
                [
                    ffprobePath,
                    "-v", "error",
                    "-select_streams", "v:0",
                    "-count_frames",
                    "-show_entries", "stream=nb_read_frames",
                    "-of", "default=nokey=1:noprint_wrappers=1",
                    filePath
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            frames = result.stdout.strip() 


        return int(frames)




##################################



    @err_catcher(name=__name__)
    def setInfoText(self, text):
        metrics = QFontMetrics(self.l_info.font())
        lines = []
        for line in text.split("\n"):
            elidedText = metrics.elidedText(line, Qt.ElideRight, self.l_preview.width()-20)
            lines.append(elidedText)

        self.l_info.setText("\n".join(lines))


    @err_catcher(name=__name__)
    def createPMap(self, resx, resy):
        fbFolder = self.core.projects.getFallbackFolder()
        if resx == 300:
            imgFile = os.path.join(fbFolder, "noFileBig.jpg")
        else:
            imgFile = os.path.join(fbFolder, "noFileSmall.jpg")

        pmap = self.core.media.getPixmapFromPath(imgFile)
        if not pmap:
            pmap = QPixmap()

        return pmap


    @err_catcher(name=__name__)
    def moveLoadingLabel(self):
        geo = QRect()
        pos = self.l_preview.parent().mapToGlobal(self.l_preview.geometry().topLeft())
        pos = self.mapFromGlobal(pos)
        geo.setWidth(self.l_preview.width())
        geo.setHeight(self.l_preview.height())
        geo.moveTopLeft(pos)
        self.l_loading.setGeometry(geo)


    @err_catcher(name=__name__)
    def changeImage_threaded(self, frame=0, regenerateThumb=False):
        for thread in reversed(self.mediaThreads):
            if thread.isRunning():
                thread.requestInterruption()
            else:
                self.mediaThreads.remove(thread)

        self.moveLoadingLabel()
        path = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "loading.gif"
        )
        self.loadingGif = QMovie(path, QByteArray(), self) 
        self.loadingGif.setCacheMode(QMovie.CacheAll) 
        self.loadingGif.setSpeed(100) 
        self.l_loading.setMovie(self.loadingGif)
        self.loadingGif.start()
        self.l_loading.setVisible(True)

        # if (self.getSelectedImage() or [{}])[0].get("channel") == "Loading...":
        # if (self.getSelectedImage() or [{}])[0].get("channel") == "Loading...":
        #     return

        thread = self.core.worker(self.core)
        thread.function = lambda x=list(self.seq): self.changeImg(
            frame=frame, seq=x, thread=thread, regenerateThumb=regenerateThumb
        )
        thread.errored.connect(self.core.writeErrorLog)
        thread.finished.connect(self.onMediaThreadFinished)
        thread.warningSent.connect(self.core.popup)
        thread.dataSent.connect(self.onChangeImgDataSent)
        # self.mediaThreads.append(thread)
        if not getattr(self, "curMediaThread", None):
            self.curMediaThread = thread
            thread.start()
        else:
            self.nextMediaThread = thread


    @err_catcher(name=__name__)
    def onMediaThreadFinished(self):
        if getattr(self, "nextMediaThread", None):
            self.curMediaThread = self.nextMediaThread
            self.nextMediaThread = None
            self.curMediaThread.start()
        else:
            self.curMediaThread = None
            self.l_loading.setVisible(False)
            self.loadingGif.stop()


    @err_catcher(name=__name__)
    def onChangeImgDataSent(self, data):
        getattr(self, data["function"])(*data["args"], **data["kwargs"])


    @err_catcher(name=__name__)
    def getThumbnailWidth(self):
        return self.l_preview.width()


    @err_catcher(name=__name__)
    def getThumbnailHeight(self):
        return self.l_preview.height()


    @err_catcher(name=__name__)
    def getCurrentFrame(self):
        if not self.timeline:
            return

        return int(self.timeline.currentTime() / self.timeline.updateInterval())


    @err_catcher(name=__name__)
    def changeImg(self, frame=0, seq=None, thread=None, regenerateThumb=False):
        if seq is not None:
            if self.seq != seq:
                logger.debug("exit thread")
                return

        if thread and thread.isInterruptionRequested():
            return

        if not self.seq:
            return

        curFrame = self.getCurrentFrame()
        pmsmall = QPixmap()
        if (
            len(self.seq) == 1
            and os.path.splitext(self.seq[0])[1].lower()
            in self.core.media.videoFormats
        ):
            fileName = self.seq[0]
        else:
            fileName = self.seq[curFrame]

        _, ext = os.path.splitext(fileName)
        ext = ext.lower()
        if self.state == "disabled":
            pmsmall = self.core.media.scalePixmap(self.emptypmap, self.getThumbnailWidth(), self.getThumbnailHeight())
        else:
            pmsmall = QPixmapCache.find(("Frame" + str(curFrame)))
            if not pmsmall:
                if ext in [
                    ".jpg",
                    ".jpeg",
                    ".JPG",
                    ".png",
                    ".PNG",
                    ".tif",
                    ".tiff",
                    ".tga",
                    ".exr",
                    ".dpx",
                    ".hdr"
                ]:
                    pm = self.core.media.getPixmapFromPath(fileName, self.getThumbnailWidth(), self.getThumbnailHeight(), colorAdjust=True)
                    if pm:
                        if pm.width() == 0 or pm.height() == 0:
                            filename = "%s.jpg" % ext[1:].lower()
                            imgPath = os.path.join(
                                self.core.projects.getFallbackFolder(), filename
                            )
                            pmsmall = self.core.media.getPixmapFromPath(imgPath)
                            pmsmall = self.core.media.scalePixmap(
                                pmsmall, self.getThumbnailWidth(), self.getThumbnailHeight()
                            )
                        elif (pm.width() / float(pm.height())) > 1.7778:
                            pmsmall = pm.scaledToWidth(self.getThumbnailWidth())
                        else:
                            pmsmall = pm.scaledToHeight(self.getThumbnailHeight())
                    else:
                        pmsmall = self.core.media.getPixmapFromPath(
                            os.path.join(
                                self.core.projects.getFallbackFolder(),
                                "%s.jpg" % ext[1:].lower(),
                            )
                        )
                        pmsmall = self.core.media.scalePixmap(
                            pmsmall, self.getThumbnailWidth(), self.getThumbnailHeight()
                        )

                # elif ext in [".exr", ".dpx", ".hdr"]:
                #     channel = (self.getSelectedImage() or [{}])[0].get("channel")
                #     try:
                #         pmsmall = self.core.media.getPixmapFromExrPath(
                #             fileName,
                #             self.getThumbnailWidth(),
                #             self.getThumbnailHeight(),
                #             channel=channel,
                #             allowThumb=self.mediaVersionPlayer.cb_filelayer.currentIndex() == 0,
                #             regenerateThumb=regenerateThumb,
                #         )
                #         if not pmsmall:
                #             raise RuntimeError("no image loader available")
                #     except Exception as e:
                #         logger.debug(e)
                #         pmsmall = self.core.media.getPixmapFromPath(
                #             os.path.join(
                #                 self.core.projects.getFallbackFolder(),
                #                 "%s.jpg" % ext[1:].lower(),
                #             )
                #         )
                #         pmsmall = self.core.media.scalePixmap(
                #             pmsmall, self.getThumbnailWidth(), self.getThumbnailHeight()
                #         )

                elif ext in self.core.media.videoFormats:
                    try:
                        if len(self.seq) > 1:
                            imgNum = 0
                            vidFile = self.core.media.getVideoReader(fileName)
                        else:
                            imgNum = curFrame
                            vidFile = self.vidPrw
                            if vidFile == "loading":
                                if fileName in self.videoReaders:
                                    vidFile = self.videoReaders[fileName]
                                else:
                                    self.vidPrw = self.core.media.getVideoReader(fileName)
                                    vidFile = self.vidPrw
                                    if self.core.isStr(vidFile):
                                        logger.warning(vidFile)

                                    self.videoReaders[fileName] = vidFile

                                if thread:
                                    data = {"function": "updatePrvInfo", "args": [fileName], "kwargs": {"vidReader": vidFile, "seq": seq}}
                                    thread.dataSent.emit(data)
                                else:
                                    self.updatePrvInfo(fileName, vidReader=vidFile, seq=seq)

                        pm = self.core.media.getPixmapFromVideoPath(
                                fileName,
                                videoReader=vidFile,
                                imgNum=imgNum,
                                regenerateThumb=regenerateThumb
                            )
                        pmsmall = self.core.media.scalePixmap(
                            pm, self.getThumbnailWidth(), self.getThumbnailHeight()
                        ) or QPixmap()
                    except Exception as e:
                        logger.debug(traceback.format_exc())
                        imgPath = os.path.join(
                            self.core.projects.getFallbackFolder(),
                            "%s.jpg" % ext[1:].lower(),
                        )
                        pmsmall = self.core.media.getPixmapFromPath(imgPath)
                        pmsmall = self.core.media.scalePixmap(
                            pmsmall, self.getThumbnailWidth(), self.getThumbnailHeight()
                        )
                else:
                    return False

                if seq is not None:
                    if self.seq != seq:
                        logger.debug("exit preview update")
                        return

                QPixmapCache.insert(("Frame" + str(curFrame)), pmsmall)

        if not self.prvIsSequence and len(self.seq) > 1:
            fileName = self.seq[curFrame]
            if thread:
                thread.dataSent.emit({"function": "updatePrvInfo", "args": [fileName], "kwargs": {"seq": seq}})
            else:
                self.updatePrvInfo(fileName, seq=seq)

        if thread:
            thread.dataSent.emit({"function": "completeChangeImg", "args": [pmsmall, curFrame, ext], "kwargs": {}})
        else:
            self.completeChangeImg(pmsmall, curFrame, ext)


    @err_catcher(name=__name__)
    def completeChangeImg(self, pmsmall, curFrame, ext):
        self.currentMediaPreview = pmsmall
        self.l_preview.setPixmap(pmsmall)
        if self.pduration > 1:
            newVal = int(self.sl_preview.maximum() * (curFrame / float(self.pduration-1)))
        else:
            newVal = 0

        curSliderVal = int((self.sl_preview.value() / self.sl_preview.maximum()) * float(self.pduration))
        if curSliderVal != curFrame:
            self.sl_preview.blockSignals(True)
            self.sl_preview.setValue(newVal)
            self.sl_preview.blockSignals(False)

        if ext in self.core.media.videoFormats:
            curFrame += 1

        if self.sp_current.value() != (self.pstart + curFrame):
            self.sp_current.blockSignals(True)
            self.sp_current.setValue((self.pstart + curFrame))
            self.sp_current.blockSignals(False)


    @err_catcher(name=__name__)
    def setTimelinePaused(self, state):
        self.timeline.setPaused(state)
        if state:
            path = os.path.join(
                self.core.prismRoot, "Scripts", "UserInterfacesPrism", "play.png"
            )
            icon = self.core.media.getColoredIcon(path)
            self.b_play.setIcon(icon)
            self.b_play.setToolTip("Play")
        else:
            path = os.path.join(
                self.core.prismRoot, "Scripts", "UserInterfacesPrism", "pause.png"
            )
            icon = self.core.media.getColoredIcon(path)
            self.b_play.setIcon(icon)
            self.b_play.setToolTip("Pause")


    @err_catcher(name=__name__)
    def previewClk(self, event):
        if (len(self.seq) > 1 or self.pduration > 1) and event.button() == Qt.LeftButton:
            if (
                self.timeline.state() == QTimeLine.Paused
                and not self.openMediaPlayer
            ):
                self.setTimelinePaused(False)
            else:
                if self.timeline.state() == QTimeLine.Running:
                    self.setTimelinePaused(True)
                self.openMediaPlayer = False
        self.l_preview.clickEvent(event)


    @err_catcher(name=__name__)
    def previewDclk(self, event):
        if self.seq != [] and event.button() == Qt.LeftButton:
            self.openMediaPlayer = True
            self.compare()

        self.l_preview.dclickEvent(event)


    @err_catcher(name=__name__)
    def rclPreview(self, pos):
        menu = self.getMediaPreviewMenu()
        # self.core.callback(
        #     name="mediaPlayerContextMenuRequested",
        #     args=[self, menu],
        # )
        if not menu or menu.isEmpty():
            return

        menu.exec_(QCursor.pos())


    @err_catcher(name=__name__)
    def getMediaPreviewMenu(self):
        # contexts = self.getCurRenders()
        # if not contexts or not contexts[0].get("version"):
            # return

        # data = contexts[0]
        # path = data["path"]

        # if not path:
            # return

        path = self.seq[0]

        rcmenu = QMenu(self)

        if len(self.seq) > 0:
            # if len(self.seq) == 1:
            #     path = os.path.join(path, self.seq[0])

            playMenu = QMenu("Play in", self)
            iconPath = os.path.join(
                self.core.prismRoot, "Scripts", "UserInterfacesPrism", "play.png"
            )
            icon = self.core.media.getColoredIcon(iconPath)
            playMenu.setIcon(icon)

            if self.mediaPlayerPath is not None:
                pAct = QAction(self.mediaPlayerName, self)
                pAct.triggered.connect(self.compare)
                playMenu.addAction(pAct)

            pAct = QAction("Default", self)
            pAct.triggered.connect(
                lambda: self.compare(prog="default")
            )
            playMenu.addAction(pAct)
            rcmenu.addMenu(playMenu)


        if (
            len(self.seq) == 1
            and os.path.splitext(self.seq[0])[1].lower()
            in self.core.media.videoFormats
        ):
            curSeqIdx = 0
        else:
            curSeqIdx = self.getCurrentFrame()

        # if len(self.seq) > 0 and self.core.media.getUseThumbnailForFile(self.seq[curSeqIdx]):
        #     prvAct = QAction("Use thumbnail", self)
        #     prvAct.setCheckable(True)
        #     prvAct.setChecked(self.core.media.getUseThumbnails())
        #     prvAct.toggled.connect(self.core.media.setUseThumbnails)
        #     prvAct.triggered.connect(self.updatePreview)
        #     rcmenu.addAction(prvAct)

        #     if self.core.media.getUseThumbnails():
        #         prvAct = QAction("Regenerate thumbnail", self)
        #         prvAct.triggered.connect(self.regenerateThumbnail)
        #         rcmenu.addAction(prvAct)

        # if len(self.seq) > 0 and hasattr(self.origin, "getCurrentEntity"):
        #     entity = self.origin.getCurrentEntity()
        #     if entity["type"] == "asset":
        #         prvAct = QAction("Set as assetpreview", self)
        #         prvAct.triggered.connect(self.origin.setPreview)
        #         rcmenu.addAction(prvAct)

        #     elif entity["type"] == "shot":
        #         prvAct = QAction("Set as shotpreview", self)
        #         prvAct.triggered.connect(self.origin.setPreview)
        #         rcmenu.addAction(prvAct)

        act_refresh = QAction("Refresh", self)
        iconPath = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "refresh.png"
        )
        icon = self.core.media.getColoredIcon(iconPath)
        act_refresh.setIcon(icon)
        act_refresh.triggered.connect(self.updatePreview)
        rcmenu.addAction(act_refresh)

        # act_disable = QAction("Disabled", self)
        # act_disable.setCheckable(True)
        # act_disable.setChecked(self.state == "disabled")
        # act_disable.triggered.connect(self.onDisabledTriggered)
        # rcmenu.addAction(act_disable)

        exp = QAction("Open in Explorer", self)
        exp.triggered.connect(lambda: self.core.openFolder(path))
        rcmenu.addAction(exp)

        copAct = QAction("Copy", self)
        iconPath = os.path.join(
            self.core.prismRoot, "Scripts", "UserInterfacesPrism", "copy.png"
        )
        icon = self.core.media.getColoredIcon(iconPath)
        copAct.setIcon(icon)
        copAct.triggered.connect(lambda: self.core.copyToClipboard(path, file=True))
        rcmenu.addAction(copAct)

        return rcmenu


    # @err_catcher(name=__name__)
    # def onDisabledTriggered(self):
    #     if self.state == "enabled":
    #         self.state = "disabled"
    #     else:
    #         self.state = "enabled"

    #     self.updatePreview()


    @err_catcher(name=__name__)
    def regenerateThumbnail(self):
        self.clearCurrentThumbnails()
        self.updatePreview(regenerateThumb=True)


    @err_catcher(name=__name__)
    def clearCurrentThumbnails(self):
        if not self.seq:
            return

        thumbdir = os.path.dirname(self.core.media.getThumbnailPath(self.seq[0]))
        if not os.path.exists(thumbdir):
            return

        try:
            shutil.rmtree(thumbdir)
        except Exception as e:
            logger.warning("Failed to remove thumbnail: %s" % e)


    @err_catcher(name=__name__)
    def previewResizeEvent(self, event):
        self.l_preview.resizeEventOrig(event)
        height = int(self.l_preview.width()*(self.renderResY/self.renderResX))
        self.l_preview.setMinimumHeight(height)
        self.l_preview.setMaximumHeight(height)
        if self.currentMediaPreview:
            pmap = self.core.media.scalePixmap(
                self.currentMediaPreview, self.getThumbnailWidth(), self.getThumbnailHeight()
            )
            self.l_preview.setPixmap(pmap)

        if hasattr(self, "loadingGif") and self.loadingGif.state() == QMovie.Running:
            self.moveLoadingLabel()

        QPixmapCache.clear()
        text = self.l_info.toolTip()
        if not text:
            text = self.l_info.text()

        self.setInfoText(text)


    @err_catcher(name=__name__)
    def sliderDrag(self, event):
        custEvent = QMouseEvent(
            QEvent.MouseButtonPress,
            event.pos(),
            Qt.MidButton,
            Qt.MidButton,
            Qt.NoModifier,
        )
        self.sl_preview.origMousePressEvent(custEvent)


    @err_catcher(name=__name__)
    def sliderClk(self):
        if (
            self.timeline
            and self.timeline.state() == QTimeLine.Running
        ):
            self.slStop = True
            self.setTimelinePaused(True)
        else:
            self.slStop = False


    @err_catcher(name=__name__)
    def sliderRls(self):
        if self.slStop:
            self.setTimelinePaused(False)


    @err_catcher(name=__name__)
    def previewDragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            dragPath = os.path.normpath(e.mimeData().urls()[0].toLocalFile())
            if self.seq:
                path = os.path.dirname(self.seq[0])
            else:
                path = ""

            if not dragPath or os.path.dirname(dragPath.strip("/\\")) == path.strip("/\\"):
                e.ignore()
            else:
                e.accept()
        else:
            e.ignore()


    @err_catcher(name=__name__)
    def previewDragMoveEvent(self, e):
        if e.mimeData().hasUrls():
            e.accept()
            self.l_preview.setStyleSheet(
                "QWidget { border-style: dashed; border-color: rgb(100, 200, 100);  border-width: 2px; }"
            )
        else:
            e.ignore()


    @err_catcher(name=__name__)
    def previewDragLeaveEvent(self, e):
        self.l_preview.setStyleSheet("QWidget { border-style: dashed; border-color: rgba(0, 0, 0, 0);  border-width: 2px; }")


    @err_catcher(name=__name__)
    def previewDropEvent(self, e):
        if e.mimeData().hasUrls():
            self.l_preview.setStyleSheet("QWidget { border-style: dashed; border-color: rgba(0, 0, 0, 0);  border-width: 2px; }")
            e.setDropAction(Qt.LinkAction)
            e.accept()

            files = [
                os.path.normpath(str(url.toLocalFile())) for url in e.mimeData().urls()
            ]
            entity = self.origin.getCurrentEntity()
            self.origin.ingestMediaToSelection(entity, files)
        else:
            e.ignore()


    @err_catcher(name=__name__)
    def compare(self, prog=""):
        if (
            self.timeline
            and self.timeline.state() == QTimeLine.Running
        ):
            self.setTimelinePaused(True)

        if prog == "default":
            progPath = ""
        else:
            progPath = self.mediaPlayerPath or ""

        comd = []
        filePath = ""
        contexts = self.getCurRenders()
        if contexts:
            files = self.getFilesFromContext(contexts[0])
            if files:
                filePath = files[0]
                baseName, extension = os.path.splitext(filePath)
                if extension in self.core.media.supportedFormats:
                    if not progPath:
                        cmd = ["start", "", "%s" % self.core.fixPath(filePath)]
                        subprocess.call(cmd, shell=True)
                        return
                    else:
                        if self.mediaPlayerPattern:
                            filePath = self.core.media.getSequenceFromFilename(filePath)

                        comd = [progPath, filePath]

        if comd:
            with open(os.devnull, "w") as f:
                logger.debug("launching: %s" % comd)
                try:
                    subprocess.Popen(comd, stdin=subprocess.PIPE, stdout=f, stderr=f)
                except:
                    comd = "%s %s" % (comd[0], comd[1])
                    try:
                        subprocess.Popen(
                            comd, stdin=subprocess.PIPE, stdout=f, stderr=f, shell=True
                        )
                    except Exception as e:
                        raise RuntimeError("%s - %s" % (comd, e))


    @err_catcher(name=__name__)
    def mouseDrag(self, event, element):
        if event.buttons() != Qt.LeftButton:
            return

        contexts = self.getCurRenders()
        urlList = []
        mods = QApplication.keyboardModifiers()
        for context in contexts:
            if mods == Qt.ControlModifier:
                url = os.path.normpath(context["path"])
                urlList.append(url)
            else:
                imgSrc = self.getFilesFromContext(context)
                for k in imgSrc:
                    url = os.path.normpath(k)
                    urlList.append(url)

        if len(urlList) == 0:
            return

        drag = QDrag(self.l_preview)
        mData = QMimeData()
        self.core.callback(name="onPreMediaPlayerDragged", args=[self, urlList])
        urlData = [QUrl.fromLocalFile(urll) for urll in urlList]
        mData.setUrls(urlData)
        drag.setMimeData(mData)

        drag.exec_(Qt.CopyAction | Qt.MoveAction)

    # @err_catcher(name=__name__)
    # def getCurRenders(self):
    #     return self.origin.getCurRenders()


    @err_catcher(name=__name__)
    def updateExternalMediaPlayer(self):
        player = self.core.media.getExternalMediaPlayer()
        self.mediaPlayerPath = player.get("path", None)
        self.mediaPlayerName = player.get("name", None)
        self.mediaPlayerPattern = player.get("framePattern", None)


    @err_catcher(name=__name__)
    def getRVdLUT(self):
        dlut = None

        assets = self.core.getConfig("paths", "assets", configPath=self.core.prismIni)

        if assets is not None:
            lutPath = os.path.join(self.core.projectPath, assets, "LUTs", "RV_dLUT")
            if os.path.exists(lutPath) and len(os.listdir(lutPath)) > 0:
                dlut = os.path.join(lutPath, os.listdir(lutPath)[0])

        return dlut


    @err_catcher(name=__name__)
    def convertImgs(self, extension, checkRes=True, settings=None):
        if not extension:
            if settings:
                extension = settings.get("extension")

            if not extension:
                logger.warning("No extension specified")
                return

            settings.pop("extension")

        if extension[0] != ".":
            extension = "." + extension

        inputpath = self.seq[0].replace("\\", "/")
        inputExt = os.path.splitext(inputpath)[1]

        if checkRes:
            if self.pwidth and self.pwidth == "?":
                self.core.popup("Cannot read media file.")
                return

            if (
                extension == ".mp4"
                and self.pwidth is not None
                and self.pheight is not None
                and (
                    int(self.pwidth) % 2 == 1
                    or int(self.pheight) % 2 == 1
                )
            ):
                self.core.popup("Media with odd resolution can't be converted to mp4.")
                return

        conversionSettings = settings or OrderedDict()

        if extension == ".mov" and not settings:
            conversionSettings["-c"] = "prores"
            conversionSettings["-profile"] = 2
            conversionSettings["-pix_fmt"] = "yuv422p10le"

        if self.prvIsSequence:
            inputpath = (
                os.path.splitext(inputpath)[0][: -self.core.framePadding]
                + "%04d".replace("4", str(self.core.framePadding))
                + inputExt
            )

        context = self.origin.getCurrentAOV()
        if not context:
            context = self.origin.getCurrentVersion()
        outputpath = self.core.paths.getMediaConversionOutputPath(
            context, inputpath, extension
        )

        if not outputpath:
            return

        if self.prvIsSequence:
            startNum = self.pstart
        else:
            startNum = 0
            conversionSettings["-start_number"] = None
            conversionSettings["-start_number_out"] = None

        result = self.core.media.convertMedia(
            inputpath, startNum, outputpath, settings=conversionSettings
        )

        if (
            extension not in self.core.media.videoFormats
            and self.prvIsSequence
        ):
            outputpath = outputpath % int(startNum)

        self.origin.updateVersions(restoreSelection=True)

        if os.path.exists(outputpath) and os.stat(outputpath).st_size > 0:
            self.core.copyToClipboard(outputpath, file=True)
            msg = "The images were converted successfully. (path is in clipboard)"
            self.core.popup(msg, severity="info")
        else:
            msg = "The images could not be converted."
            logger.debug("expected outputpath: %s" % outputpath)
            self.core.ffmpegError("Image conversion", msg, result)


    # @err_catcher(name=__name__)
    # def compGetImportSource(self):
    #     sourceFolder = os.path.dirname(self.seq[0]).replace("\\", "/")
    #     sources = self.core.media.getImgSources(sourceFolder)
    #     sourceData = []

    #     for curSourcePath in sources:
    #         if "####" in curSourcePath:
    #             if self.pstart == "?" or self.pend == "?":
    #                 firstFrame = None
    #                 lastFrame = None
    #             else:
    #                 firstFrame = self.pstart
    #                 lastFrame = self.pend

    #             filePath = curSourcePath.replace("\\", "/")
    #         else:
    #             filePath = curSourcePath.replace("\\", "/")
    #             firstFrame = None
    #             lastFrame = None

    #         sourceData.append([filePath, firstFrame, lastFrame])

    #     return sourceData


    # @err_catcher(name=__name__)
    # def compGetImportPasses(self):
    #     sourceFolder = os.path.dirname(
    #         os.path.dirname(self.seq[0])
    #     ).replace("\\", "/")
    #     passes = [
    #         x
    #         for x in os.listdir(sourceFolder)
    #         if x[-5:] not in ["(mp4)", "(jpg)", "(png)"]
    #         and os.path.isdir(os.path.join(sourceFolder, x))
    #     ]
    #     sourceData = []

    #     for curPass in passes:
    #         curPassPath = os.path.join(sourceFolder, curPass)

    #         imgs = os.listdir(curPassPath)
    #         if len(imgs) == 0:
    #             continue

    #         if (
    #             len(imgs) > 1
    #             and self.pstart
    #             and self.pend
    #             and self.pstart != "?"
    #             and self.pend != "?"
    #         ):
    #             firstFrame = self.pstart
    #             lastFrame = self.pend

    #             curPassName = imgs[0].split(".")[0]
    #             increment = "####"
    #             curPassFormat = imgs[0].split(".")[-1]

    #             filePath = os.path.join(
    #                 sourceFolder,
    #                 curPass,
    #                 ".".join([curPassName, increment, curPassFormat]),
    #             ).replace("\\", "/")
    #         else:
    #             filePath = os.path.join(curPassPath, imgs[0]).replace("\\", "/")
    #             firstFrame = None
    #             lastFrame = None

    #         sourceData.append([filePath, firstFrame, lastFrame])

    #     return sourceData


    # @err_catcher(name=__name__)
    # def triggerAutoplay(self, checked=False):
    #     self.core.setConfig("browser", "autoplaypreview", checked)

    #     if self.timeline:
    #         if checked and self.timeline.state() == QTimeLine.Paused:
    #             self.setTimelinePaused(False)
    #         elif not checked and self.timeline.state() == QTimeLine.Running:
    #             self.setTimelinePaused(True)
    #     else:
    #         self.tlPaused = not checked


# class VersionDelegate(QStyledItemDelegate):
#     def __init__(self, origin):
#         super(VersionDelegate, self).__init__()
#         self.origin = origin
#         self.widget = self.origin.lw_destination

#     def paint(self, painterQPainter, optionQStyleOptionViewItem, indexQModelIndex):
#         item = self.widget.itemFromIndex(indexQModelIndex)
#         QStyledItemDelegate.paint(
#             self, painterQPainter, optionQStyleOptionViewItem, indexQModelIndex
#         )

#         data = item.data(Qt.UserRole)
#         offset = 0
#         if len(self.origin.projectBrowser.locations) > 1:
#             for location in reversed(self.origin.projectBrowser.locations):
#                 if location.get("name") not in data.get("locations", {}):
#                     continue

#                 if "icon" not in location:
#                     location["icon"] = self.origin.projectBrowser.getLocationIcon(location["name"])

#                 if location["icon"]:
#                     rect = QRect(optionQStyleOptionViewItem.rect)
#                     curRight = rect.right() - offset
#                     rect.setTop(rect.top() + 2)
#                     rect.setBottom(rect.bottom() - 2)
#                     rect.setLeft(curRight - 30)
#                     rect.setRight(curRight - 0)
#                     painterQPainter.setRenderHint(QPainter.Antialiasing)
#                     location["icon"].paint(painterQPainter, rect)
#                     offset += 25






# class MediaVersionPlayer(QWidget):
#     def __init__(self, origin):
#         super(MediaVersionPlayer, self).__init__()
#         self.origin = origin
#         self.core = self.origin.core
#         self.setupUi()


#     @err_catcher(name=__name__)
#     def setupUi(self):
#         self.lo_main = QVBoxLayout(self)
#         self.lo_main.setContentsMargins(0, 0, 0, 0)

#         self.l_layer = QLabel("AOVs:")
#         self.cb_layer = QComboBox()
#         self.lo_main.addWidget(self.l_layer)
#         self.lo_main.addWidget(self.cb_layer)

#         self.l_source = QLabel("Source:")
#         self.cb_source = QComboBox()
#         self.lo_main.addWidget(self.l_source)
#         self.lo_main.addWidget(self.cb_source)

#         self.l_filelayer = QLabel("Channel:")
#         self.cb_filelayer = QComboBox()



#         #   HIDE --                                                             TESTING
#         self.l_layer.hide()
#         self.l_source.hide()
#         self.l_filelayer.hide()
#         self.cb_layer.hide()
#         self.cb_source.hide()
#         self.cb_filelayer.hide()




#         self.lo_main.addWidget(self.l_filelayer)
#         self.lo_main.addWidget(self.cb_filelayer)

#         self.mediaPlayer = self.getMediaPlayer()
#         self.lo_main.addWidget(self.mediaPlayer)

#         # self.cb_layer.currentIndexChanged.connect(self.layerChanged)
#         self.cb_layer.mmEvent = self.cb_layer.mouseMoveEvent
#         self.cb_layer.mouseMoveEvent = lambda x: self.mediaPlayer.mouseDrag(x, self.cb_layer)
#         self.cb_layer.setContextMenuPolicy(Qt.CustomContextMenu)
#         self.cb_layer.customContextMenuRequested.connect(self.rclLayer)
#         self.cb_source.currentIndexChanged.connect(self.sourceChanged)
#         self.cb_filelayer.currentIndexChanged.connect(self.filelayerChanged)


#     @err_catcher(name=__name__)
#     def getMediaPlayer(self):
#         return MediaPlayer(self)


#     # @err_catcher(name=__name__)
#     # def getCurrentAOV(self):
#     #     data = self.cb_layer.currentData(Qt.UserRole)
#     #     return data

#     # @err_catcher(name=__name__)
#     # def getCurrentSource(self):
#     #     data = self.cb_source.currentData(Qt.UserRole)
#     #     return data

#     # @err_catcher(name=__name__)
#     # def getCurrentFilelayer(self):
#     #     data = self.cb_filelayer.currentData(Qt.UserRole)
#     #     return data

#     # @err_catcher(name=__name__)
#     # def layerChanged(self, layer=None):
#     #     self.updateSources(restoreSelection=True)

#     @err_catcher(name=__name__)
#     def sourceChanged(self, layer=None):
#         self.updateFilelayers(restoreSelection=True)

#     @err_catcher(name=__name__)
#     def filelayerChanged(self, layer=None):
#         self.mediaPlayer.updatePreview()

#     @err_catcher(name=__name__)
#     def getCurrentVersions(self):
#         return self.origin.getCurrentSources()
    

#     @err_catcher(name=__name__)
#     def updateLayers(self, restoreSelection=False):
#         if restoreSelection:
#             curLayer = self.cb_layer.currentText()

#         wasBlocked = self.cb_layer.signalsBlocked()
#         if not wasBlocked:
#             self.cb_layer.blockSignals(True)
    
#         self.cb_layer.clear()

#         versions = self.getCurrentVersions()



#         # if len(versions) == 1:
#         #     aovs = self.core.mediaProducts.getAOVsFromVersion(versions[0])
#         #     for aov in aovs:
#         #         self.cb_layer.addItem(aov["aov"], aov)

#         selectFirst = True
#         if restoreSelection and curLayer:
#             bIdx = self.cb_layer.findText(curLayer)
#             if bIdx != -1:
#                 self.cb_layer.setCurrentIndex(bIdx)
#                 selectFirst = False

#         if selectFirst:
#             bIdx = self.cb_layer.findText("beauty")
#             if bIdx != -1:
#                 self.cb_layer.setCurrentIndex(bIdx)
#             else:
#                 bIdx = self.cb_layer.findText("rgba")
#                 if bIdx != -1:
#                     self.cb_layer.setCurrentIndex(bIdx)
#                 else:
#                     self.cb_layer.setCurrentIndex(0)

#         if not wasBlocked:
#             self.cb_layer.blockSignals(False)
#             # self.updateSources(restoreSelection=True)


#     # @err_catcher(name=__name__)
#     # def updateSources(self, restoreSelection=False):

#     #     self.core.popup("IN UPDATE SOURCES")                                      #    TESTING
#     #     if restoreSelection:
#     #         curSource = self.cb_source.currentText()

#     #     wasBlocked = self.cb_source.signalsBlocked()
#     #     if not wasBlocked:
#     #         self.cb_source.blockSignals(True)
    
#     #     self.cb_source.clear()
#     #     versions = self.getCurrentVersions()
#     #     if len(versions) == 1:
#     #         curAov = self.getCurrentAOV()
#     #         if not curAov:
#     #             curAov = versions[0]

#     #         if curAov:
#     #             # mediaFiles = self.core.mediaProducts.getFilesFromContext(curAov)
#     #             validFiles = self.core.media.filterValidMediaFiles(curAov)

#     #             if validFiles:
#     #                 validFiles = sorted(validFiles, key=lambda x: x if "cryptomatte" not in os.path.basename(x) else "zzz" + x)
#     #                 baseName, extension = os.path.splitext(validFiles[0])
#     #                 seqFiles = self.core.media.detectSequences(validFiles)
#     #                 for seqFile in seqFiles:
#     #                     source = curAov.copy()
#     #                     source["source"] = os.path.basename(seqFile)
#     #                     self.cb_source.addItem(source["source"], source)

#     #     selectFirst = True
#     #     if restoreSelection and curSource:
#     #         bIdx = self.cb_source.findText(curSource)
#     #         if bIdx != -1:
#     #             self.cb_source.setCurrentIndex(bIdx)
#     #             selectFirst = False

#     #     if selectFirst:
#     #         self.cb_source.setCurrentIndex(0)

#     #     self.l_source.setHidden(self.cb_source.count() < 2)
#     #     self.cb_source.setHidden(self.cb_source.count() < 2)

#     #     if not wasBlocked:
#     #         self.cb_source.blockSignals(False)
#     #         self.updateFilelayers(restoreSelection=True)


#     @err_catcher(name=__name__)
#     def updateFilelayers(self, restoreSelection=False, threaded=True, layers=None):
#         if restoreSelection:
#             curFileLayer = self.cb_filelayer.currentText()

#         wasBlocked = self.cb_filelayer.signalsBlocked()
#         if not wasBlocked:
#             self.cb_filelayer.blockSignals(True)
    
#         self.cb_filelayer.clear()
#         versions = self.getCurrentVersions()
#         if len(versions) == 1 and os.getenv("PRISM_SHOW_EXR_LAYERS") != "0":
#             curSource = self.getCurrentSource()
#             if curSource:
#                 mediaFiles = self.core.mediaProducts.getFilesFromContext(curSource)
#                 validFiles = self.core.media.filterValidMediaFiles(mediaFiles)

#                 if validFiles:
#                     if threaded:
#                         layers = ["Loading..."]

#                         thread = self.core.worker(self.core)
#                         thread.function = lambda: self.getLayersFromFileThreaded(
#                             validFiles[0], thread, restoreSelection
#                         )
#                         thread.errored.connect(self.core.writeErrorLog)
#                         thread.finished.connect(self.onWorkerThreadFinished)
#                         thread.warningSent.connect(self.core.popup)
#                         thread.dataSent.connect(self.onWorkerDataSent)
#                         # self.mediaThreads.append(thread)
#                         if not getattr(self, "curMediaThread", None):
#                             self.curMediaThread = thread
#                             thread.start()
#                         else:
#                             self.nextMediaThread = thread

#                     elif layers and layers.get("file") == validFiles[0]:
#                         layers = layers.get("layers", [])
#                     else:
#                         layers = self.core.media.getLayersFromFile(validFiles[0])

#                     for flayer in layers:
#                         layer = curSource.copy()
#                         layer["channel"] = flayer
#                         self.cb_filelayer.addItem(layer["channel"], layer)

#         selectFirst = True
#         if restoreSelection and curFileLayer:
#             bIdx = self.cb_filelayer.findText(curFileLayer)
#             if bIdx != -1:
#                 self.cb_filelayer.setCurrentIndex(bIdx)
#                 selectFirst = False

#         if selectFirst:
#             self.cb_filelayer.setCurrentIndex(0)

#         self.l_filelayer.setHidden(self.cb_filelayer.count() < 2)
#         self.cb_filelayer.setHidden(self.cb_filelayer.count() < 2)

#         if not wasBlocked:
#             self.cb_filelayer.blockSignals(False)
#             self.mediaPlayer.updatePreview()

#     @err_catcher(name=__name__)
#     def getLayersFromFileThreaded(self, filepath, thread, restoreSelection):
#         if thread.isInterruptionRequested():
#             return

#         layers = self.core.media.getLayersFromFile(filepath)
#         layerData = {"file": filepath, "layers": layers}
#         data = {"function": "updateFilelayers", "args": [], "kwargs": {"restoreSelection": restoreSelection, "threaded": False, "layers": layerData}}
#         thread.dataSent.emit(data)

#     @err_catcher(name=__name__)
#     def onWorkerDataSent(self, data):
#         getattr(self, data["function"])(*data["args"], **data["kwargs"])

#     @err_catcher(name=__name__)
#     def onWorkerThreadFinished(self):
#         if getattr(self, "nextMediaThread", None):
#             self.curMediaThread = self.nextMediaThread
#             self.nextMediaThread = None
#             self.curMediaThread.start()
#         else:
#             self.curMediaThread = None

#     @err_catcher(name=__name__)
#     def navigate(self, aov=None, source=None, filelayer=None, restoreSelection=False):
#         prevLayer = self.getCurrentAOV()
#         self.cb_layer.blockSignals(True)
#         self.updateLayers(restoreSelection=True)
#         if not aov:
#             self.cb_layer.blockSignals(False)
#             if prevLayer != self.getCurrentAOV() or not self.origin.initialized:
#                 self.layerChanged()
#                 return True

#             return

#         idx = self.cb_layer.findText(aov)
#         if idx != -1:
#             self.cb_layer.setCurrentIndex(idx)

#         self.cb_layer.blockSignals(False)
#         prevSource = self.getCurrentSource()
#         self.cb_source.blockSignals(True)
#         if prevLayer != self.getCurrentAOV():
#             self.layerChanged()

#         if not source:
#             self.cb_source.blockSignals(False)
#             if prevSource != self.getCurrentSource() or not self.origin.initialized:
#                 self.sourceChanged()
#                 return True

#             return

#         idx = self.cb_source.findText(aov)
#         if idx != -1:
#             self.cb_source.setCurrentIndex(idx)

#         self.cb_source.blockSignals(False)
#         prevFilelayer = self.getCurrentFilelayer()
#         self.cb_filelayer.blockSignals(True)
#         if prevSource != self.getCurrentSource():
#             self.sourceChanged()

#         if not filelayer:
#             self.cb_filelayer.blockSignals(False)
#             if prevFilelayer != self.getCurrentFilelayer() or not self.origin.initialized:
#                 self.filelayerChanged()
#                 return True

#             return

#         idx = self.cb_filelayer.findText(aov)
#         if idx != -1:
#             self.cb_filelayer.setCurrentIndex(idx)

#         self.cb_filelayer.blockSignals(False)
#         if prevFilelayer != self.getCurrentFilelayer():
#             self.filelayerChanged()
#             return True

#     @err_catcher(name=__name__)
#     def rclLayer(self, pos):
#         cpos = QCursor.pos()
#         if not hasattr(self.origin, "getCurrentIdentifier"):
#             return

#         identifier = self.origin.getCurrentIdentifier()
#         if not identifier or identifier["mediaType"] != "3drenders":
#             return

#         data = self.getCurrentAOV()
#         if data:
#             path = data["path"]
#         else:
#             version = self.origin.getCurrentVersion()
#             if not version:
#                 return

#             path = self.core.mediaProducts.getAovPathFromVersion(version)

#         rcmenu = QMenu(self)

#         depAct = QAction("Create AOV...", self)
#         depAct.triggered.connect(self.createAovDlg)
#         rcmenu.addAction(depAct)

#         act_refresh = QAction("Refresh", self)
#         iconPath = os.path.join(
#             self.core.prismRoot, "Scripts", "UserInterfacesPrism", "refresh.png"
#         )
#         icon = self.core.media.getColoredIcon(iconPath)
#         act_refresh.setIcon(icon)
#         act_refresh.triggered.connect(lambda: self.updateLayers(restoreSelection=True))
#         rcmenu.addAction(act_refresh)

#         if os.path.exists(path):
#             opAct = QAction("Open in Explorer", self)
#             opAct.triggered.connect(lambda: self.core.openFolder(path))
#             rcmenu.addAction(opAct)

#             copAct = QAction("Copy", self)
#             iconPath = os.path.join(
#                 self.core.prismRoot, "Scripts", "UserInterfacesPrism", "copy.png"
#             )
#             icon = self.core.media.getColoredIcon(iconPath)
#             copAct.setIcon(icon)
#             copAct.triggered.connect(lambda: self.core.copyToClipboard(path, file=True))
#             rcmenu.addAction(copAct)

#         if rcmenu.isEmpty():
#             return False

#         rcmenu.exec_(cpos)

#     @err_catcher(name=__name__)
#     def createAovDlg(self):
#         entity = self.origin.getCurrentEntity()
#         identifier = self.origin.getCurrentIdentifier().get("identifier")
#         version = identifier = self.origin.getCurrentVersion().get("version")
#         context = entity.copy()
#         context["identifier"] = identifier
#         context["version"] = version

#         self.newItem = PrismWidgets.CreateItem(
#             core=self.core, showType=False, mode="aov", startText="rgb"
#         )
#         self.newItem.setModal(True)
#         self.core.parentWindow(self.newItem)
#         self.newItem.e_item.setFocus()
#         self.newItem.setWindowTitle("Create AOV")
#         self.newItem.l_item.setText("AOV:")
#         self.newItem.accepted.connect(self.createAov)
#         self.core.callback(name="onCreateAovDlgOpen", args=[self, self.newItem])
#         self.newItem.show()

#     @err_catcher(name=__name__)
#     def createAov(self):
#         self.activateWindow()
#         itemName = self.newItem.e_item.text()
#         curEntity = self.origin.getCurrentEntity()
#         identifier = self.origin.getCurrentIdentifier()
#         identifierName = identifier.get("identifier")
#         version = self.origin.getCurrentVersion().get("version")
#         if self.core.mediaProducts.getLinkedToTasks():
#             curEntity["department"] = identifier.get("department", "unknown")
#             curEntity["task"] = identifier.get("task", "unknown")

#         self.core.mediaProducts.createAov(entity=curEntity, identifier=identifierName, version=version, aov=itemName)
#         self.updateLayers()
#         if itemName is not None:
#             idx = self.cb_layer.findText(itemName)
#             if idx != -1:
#                 self.cb_layer.setCurrentIndex(idx)
