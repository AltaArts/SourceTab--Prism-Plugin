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
from collections import OrderedDict, deque
import shutil
import uuid
import hashlib
from datetime import datetime
from time import time
from functools import partial
import re
from pathlib import Path


from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *


prismRoot = os.getenv("PRISM_ROOT")

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


#   Python Libs
import simpleaudio as sa
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader


#   Prism Libs
from PrismUtils import PrismWidgets
from PrismUtils.Decorators import err_catcher


#   SourceTab Libs
import TileWidget as TileWidget
from SourceFunctions import SourceFunctions
from PopupWindows import DisplayPopup, WaitPopup
from ElapsedTimer import ElapsedTimer
from PreviewPlayer import PreviewPlayer
import SourceTab_Utils as Utils

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



class SourceBrowser(QWidget, SourceBrowser_ui.Ui_w_sourceBrowser):
    def __init__(self, origin, core, projectBrowser=None, refresh=True):
        QWidget.__init__(self)
        self.setupUi(self)
        self.plugin = origin
        self.core = core
        self.projectBrowser = projectBrowser
        self.pluginPath = pluginPath
        self.iconDir = iconDir

        logger.debug("Initializing Source Browser")

        self.core.parentWindow(self)

        self.supportedCodecs = ["h264", "hevc", "mpeg4", "mpeg2video", "prores",
                                "dnxhd", "dnxhr", "mjpeg", "jpeg2000", "rawvideo",
                                "vp8","vp9","av1"]

        self.audioFormats = [".wav", ".aac", ".mp3", ".pcm", ".aiff",
                             ".flac", ".alac", ".ogg", ".wma"]

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
                                  "Other": True,
                                  }


        self._sourceRowWidgets = []
        self._destinationRowWidgets = []


        #   Initialize Variables
        self.sourceDir = ""
        self.destDir = ""
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

        #   Time to Detect Stalled Worker Threads
        self.stallInterval = 30
        
        #   Controls the "Smoothness" of the Estmated Transfer Time Remaining
        #   (1st value is Min samples at the start, 2nd is the Max Samples at the end)
        # self.adaptiveProgUpdate = [5, 10]   #   Sensitive - for small files
        self.adaptiveProgUpdate = [20, 60]  #   Medium - for normal files
        # self.adaptiveProgUpdate = [30, 100] #   Smoother - for large files

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

        self.TESTING_INIT()                             #   TESTING



    def TESTING_INIT(self):
        self.sourceDir = r"C:\Users\Alta Arts\Desktop\SINGLE ITEM"
        # tiles = self.getAllSourceTiles()
        # print(f"***  tiles:  {tiles}")								#	TESTING
        self.refreshSourceItems()

        
        self.selectAll(checked=True, mode="source")
        QTimer.singleShot(500, lambda: self.addSelected())




    @err_catcher(name=__name__)                                         #   TODO - GET RID OF THIS WITHOUT ERROR
    def getSelectedContext(self, *args, **kwargs):
        pass


    @err_catcher(name=__name__)
    def entered(self, prevTab=None, navData=None):
        if not self.initialized:
            self.initialized = True

            #   Get OIIO from Core
            self.oiio = self.core.media.getOIIO()

            #   Resize Splitter Panels
            QTimer.singleShot(10, lambda: self.setSplitterToThirds())


    #   Resizes Splitter Panels to Equal Thirds
    @err_catcher(name=__name__)
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


    #   Plays Audio with Simple Audio
    @err_catcher(name=__name__)
    def playSound(self, path):
        try:
            wave_obj = sa.WaveObject.from_wave_file(path)
            play_obj = wave_obj.play()
            play_obj.wait_done()

        except Exception:
            QApplication.beep()


    @err_catcher(name=__name__)
    def loadLayout(self):
        #   Set Icons
        upIcon = self.getIconFromPath(os.path.join(iconDir, "up.png"))
        dirIcon = self.getIconFromPath(os.path.join(iconDir, "folder.png"))
        refreshIcon = self.getIconFromPath(os.path.join(iconDir, "reset.png"))
        tipIcon = self.getIconFromPath(os.path.join(iconDir, "help.png"))
        sortIcon = self.getIconFromPath(os.path.join(iconDir, "sort.png"))
        durationIcon = self.getIconFromPath(os.path.join(iconDir, "duration.png"))
        filtersIcon = self.getIconFromPath(os.path.join(iconDir, "filters.png"))
        sequenceIcon = self.getIconFromPath(os.path.join(iconDir, "sequence.png"))

        ##   Source Panel
        #   Set Button Icons
        self.b_sourcePathUp.setIcon(upIcon)
        self.b_browseSource.setIcon(dirIcon)
        self.b_refreshSource.setIcon(refreshIcon)
        self.b_source_sorting_sort.setIcon(sortIcon)
        self.b_source_sorting_duration.setIcon(durationIcon)
        self.b_source_sorting_filtersEnable.setIcon(filtersIcon)
        self.b_source_sorting_combineSeqs.setIcon(sequenceIcon)
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
        self.b_dest_sorting_sort.setIcon(sortIcon)
        self.b_dest_sorting_filtersEnable.setIcon(filtersIcon)
        self.b_dest_sorting_combineSeqs.setIcon(sequenceIcon)
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

        #   PreviewPlayer Toolbar
        self.lo_playerToolbar = QHBoxLayout()

        #   Player Enable Switch
        self.chb_enablePlayer = QCheckBox("Enable Media Player")

        #   Prefer Proxis Switch
        self.chb_preferProxies = QCheckBox("Prefer Proxies")

        #   Add Widgets to PreviewPlayer Toolbar
        self.lo_playerToolbar.addWidget(self.chb_enablePlayer)
        self.spacer1 = QSpacerItem(40, 0, QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.lo_playerToolbar.addItem(self.spacer1)
        self.lo_playerToolbar.addWidget(self.chb_preferProxies)

        # Media Player Import
        self.PreviewPlayer = PreviewPlayer(self)

        #   Functions Import
        self.sourceFuncts = SourceFunctions(self.core, self)

        #   Add Panels to the Right Panel
        self.lo_rightPanel.addLayout(self.lo_playerToolbar)
        self.lo_rightPanel.addWidget(self.PreviewPlayer)
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
        self.b_source_sorting_sort.setToolTip(tip)
        self.b_dest_sorting_sort.setToolTip(tip)

        tip = ("Duration Display Toggle\n\n"
               "   - Min:Sec\n"
               "   - Frames / FPS")
        self.b_source_sorting_duration.setToolTip(tip)

        tip = ("File Filters\n\n"
               "   Click to Enable View Filters\n"
               "   Right-click to Select Filters")
        self.b_source_sorting_filtersEnable.setToolTip(tip)
        self.b_dest_sorting_filtersEnable.setToolTip(tip)

        tip = "Group Image Sequences"
        self.b_source_sorting_combineSeqs.setToolTip(tip)
        self.b_dest_sorting_combineSeqs.setToolTip(tip)

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


    @err_catcher(name=__name__)
    def connectEvents(self):
        #   Connect Right Click Menus
        self.lw_source.setContextMenuPolicy(Qt.CustomContextMenu)
        self.lw_source.customContextMenuRequested.connect(lambda x: self.rclList(x, self.lw_source))
        self.lw_destination.setContextMenuPolicy(Qt.CustomContextMenu)
        self.lw_destination.customContextMenuRequested.connect(lambda x: self.rclList(x, self.lw_destination))

        #   Source Filters
        self.b_source_sorting_filtersEnable.setContextMenuPolicy(Qt.CustomContextMenu)
        self.b_source_sorting_filtersEnable.customContextMenuRequested.connect(lambda: self.filtersRCL("source"))
        #   Destination Filters
        self.b_dest_sorting_filtersEnable.setContextMenuPolicy(Qt.CustomContextMenu)
        self.b_dest_sorting_filtersEnable.customContextMenuRequested.connect(lambda: self.filtersRCL("destination"))

        #   Source Buttons
        self.b_sourcePathUp.clicked.connect(lambda: self.goUpDir("source"))
        self.le_sourcePath.returnPressed.connect(lambda: self.onPasteAddress("source"))
        self.b_browseSource.clicked.connect(lambda: self.explorer("source"))
        self.b_refreshSource.clicked.connect(self.refreshSourceItems)
        self.b_source_sorting_sort.clicked.connect(lambda: self.showSortMenu("source"))
        self.b_source_sorting_duration.clicked.connect(lambda: self.toggleDuration())
        self.b_source_sorting_filtersEnable.toggled.connect(lambda: self.refreshSourceTable(restoreSelection=True))
        self.b_source_sorting_combineSeqs.toggled.connect(lambda: self.refreshSourceItems())
        self.b_tips_source.clicked.connect(lambda: self.getCheatsheet("source", tip=False))
        self.b_source_checkAll.clicked.connect(lambda: self.selectAll(checked=True, mode="source"))
        self.b_source_uncheckAll.clicked.connect(lambda: self.selectAll(checked=False, mode="source"))
        self.b_source_addSel.clicked.connect(self.addSelected)

        #   Destination Buttons
        self.b_destPathUp.clicked.connect(lambda: self.goUpDir("dest"))
        self.le_destPath.returnPressed.connect(lambda: self.onPasteAddress("dest"))
        self.b_browseDest.clicked.connect(lambda: self.chooseDestLoc())
        self.b_refreshDest.clicked.connect(lambda: self.refreshDestItems())
        self.b_dest_sorting_sort.clicked.connect(lambda: self.showSortMenu("destination"))
        self.b_dest_sorting_filtersEnable.toggled.connect(lambda: self.refreshDestTable(restoreSelection=True))
        self.b_dest_sorting_combineSeqs.toggled.connect(lambda: self.refreshDestItems())
        self.b_tips_dest.clicked.connect(lambda: self.getCheatsheet("dest", tip=False))
        self.b_dest_checkAll.clicked.connect(lambda: self.selectAll(checked=True, mode="dest"))
        self.b_dest_uncheckAll.clicked.connect(lambda: self.selectAll(checked=False, mode="dest"))
        self.b_dest_clearSel.clicked.connect(lambda: self.clearTransferList(checked=True))
        self.b_dest_clearAll.clicked.connect(lambda: self.clearTransferList())

        #   Media Player
        self.chb_enablePlayer.toggled.connect(self.togglePreviewPlayer)
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
        # sortTypes = ["Name", "Date", "Size", "Duration"]                      #   TODO ADD DURATION SORTING
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
                self.refreshSourceTable(restoreSelection=True)
            elif table == "destination":
                self.refreshDestTable(restoreSelection=True)

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

            self.refreshSourceTable(restoreSelection=True)

        elif table == "destination":
            for label, cb in checkboxRefs.items():
                self.filterStates_dest[label] = cb.isChecked()

            self.refreshDestTable(restoreSelection=True)

        menu.close()


    #   Toggles Duration Display in Tiles
    @err_catcher(name=__name__)
    def toggleDuration(self):
        for tile in self.getAllSourceTiles():
            tile.setDuration()


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
                    self.refreshDestItems()
            else:
                self.core.popup(f"ERROR: Dropped path is not a directory: {path}")

        # elif e.mimeData().hasFormat("application/x-sourcefileitem"):
        #     ##  This is your custom item!
        #     e.acceptProposedAction()

        #     dataBytes = e.mimeData().data("application/x-sourcefileitem")
        #     dataString = bytes(dataBytes).decode('utf-8')

        #     fileItem = self.createDestFileTile(dataString)

        #     # Insert into QListWidget
        #     listItem = QListWidgetItem()
        #     listItem.setSizeHint(fileItem.sizeHint())  # Optional, if sizing matters

        #     self.lw_destination.addItem(listItem)
        #     self.lw_destination.setItemWidget(listItem, fileItem)

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
            self.useLibImport = settingData ["useLibImport"]

            #   Get OCIO View Presets
            lutPresetData = sData["viewLutPresets"]
            self.configureViewLut(lutPresetData)                 #   TODO - MOVE

            #   Get Tab (UI) Settings
            tabData = sData["tabSettings"]

            #   Sorting Options
            self.sortOptions = sData["sortOptions"]
            self.b_source_sorting_duration.setChecked(tabData["enable_frames"])
            self.b_source_sorting_combineSeqs.setChecked(tabData["source_combineSeq"]) 
            self.b_dest_sorting_combineSeqs.setChecked(tabData["dest_combineSeq"]) 

            #   Media Player Enabled Checkbox
            playerEnabled = tabData["playerEnabled"]
            self.chb_enablePlayer.setChecked(playerEnabled)
            self.togglePreviewPlayer(playerEnabled)
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


    #   Initializes Worker Threadpools and Semaphore Slots
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

            self.cache_threadpool = QThreadPool()
            self.cache_threadpool.setMaxThreadCount(6)

        except Exception as e:
            logger.warning(f"ERROR:  Failed to Set Threadpools:\n{e}")


    @err_catcher(name=__name__)
    def configureViewLut(self, presets=None):
        self.PreviewPlayer.container_viewLut.setVisible(self.useViewLuts)

        if presets:
            self.PreviewPlayer.cb_viewLut.clear()

            for preset in presets:
                self.PreviewPlayer.cb_viewLut.addItem(preset["name"])

    
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
                        self.gb_sourceHeader,
                        self.gb_sourceFooter,
                        self.gb_destHeader,
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
    def getTimeRemaining(self, copiedSize, totalSize):
        try:
            speed_bps = 0
            current_time = time()

            self.speedSamples.append((current_time, copiedSize))

            #   Adaptive maxlen: Increase as Transfer Progresses
            progress_ratio = copiedSize / totalSize if totalSize > 0 else 0
            adapt_start, adapt_end = self.adaptiveProgUpdate
            adaptive_maxlen = int(adapt_start + progress_ratio * adapt_end)
            self.speedSamples = deque(self.speedSamples, maxlen=adaptive_maxlen)

            #   Calculate Rolling Average Speed
            if len(self.speedSamples) >= 2:
                t0, b0 = self.speedSamples[0]
                t1, b1 = self.speedSamples[-1]
                time_span = t1 - t0
                bytes_span = b1 - b0

                if time_span > 0 and bytes_span > 0:
                    speed_bps = bytes_span / time_span
                else:
                    speed_bps = 0

            #   Estimate Remaining Time
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


    @err_catcher(name=__name__)
    def refreshUI(self):
        self.core.media.invalidateOiioCache()                               #   TODO

        if hasattr(self, "sourceDir"):
            self.le_sourcePath.setText(self.sourceDir)
        if hasattr(self, "destDir"):
            self.le_destPath.setText(self.destDir)
        
        self.refreshSourceItems()
        self.refreshDestItems()

        self.refreshStatus = "valid"


    #   Toggles Media Player Visability
    @err_catcher(name=__name__)
    def togglePreviewPlayer(self, checked):
        self.PreviewPlayer.setVisible(checked)
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
    def chooseDestLoc(self):
        self.libPlugin = self.core.getPlugin("Libraries")

        #   If Libraries Plugin is Installed and User Chooses Lib Option
        if self.libPlugin and self.useLibImport:
            #   Open Custom Lib Popup
            self.getPathFromLib()
        else:
            #   Just Open File Explorer
            self.explorer("dest")


    #   Opens Custom Libraries Popup to Choose Dest Dir
    @err_catcher(name=__name__)
    def getPathFromLib(self):

        #   Calls File Explorer Method
        def _onExplorerFromLib():
            self.dlg_lib.reject()
            self.explorer("dest")
            
        #   Sets Dest Dir
        def _onLibAssetSelected(origin, paths=None):
            path = origin.getSelectedPath()
            self.destDir = os.path.normpath(path)
            self.dlg_lib.accept()
            self.refreshDestItems()

        #   Gets Texture Lib from Libraries
        lib = self.libPlugin.getTextureLibrary(initialize=False)       
        lib.showShotLib = False
        lib.entered(navData=None)
        lib.chb_flatten.setChecked(True)

        #   Create Custom Library Popup
        self.dlg_lib = QDialog()
        lib.reject = self.dlg_lib.reject
        self.dlg_lib.libDlg = lib
        self.dlg_lib.setWindowTitle("Choose Destination Folder")
        self.core.parentWindow(self.dlg_lib, parent=self)
        self.lo_dlgLib = QVBoxLayout(self.dlg_lib)
        self.lo_dlgLib.addWidget(lib)
        #   Add Buttons
        bb_main = QDialogButtonBox()
        b_import = bb_main.addButton("Select Library Folder", QDialogButtonBox.AcceptRole)
        b_import.clicked.connect(lambda: _onLibAssetSelected(lib))
        b_productBrowser = bb_main.addButton("Open File Explorer", QDialogButtonBox.AcceptRole)
        b_productBrowser.clicked.connect(_onExplorerFromLib)
        b_cancel = bb_main.addButton("Cancel", QDialogButtonBox.RejectRole)
        b_cancel.clicked.connect(self.dlg_lib.reject)

        self.lo_dlgLib.addWidget(bb_main)
        self.dlg_lib.exec_()


    #   Open File Explorer to Choose Directory
    @err_catcher(name=__name__)
    def explorer(self, mode, dir=None):
        if not dir:
            if mode == "source" and hasattr(self, "sourceDir"):
                dir = self.sourceDir
            elif mode == "dest" and hasattr(self, "destDir"):
                dir = self.destDir

        title = f"Select {mode.capitalize()} Directory"
        selected_path = Utils.explorerDialogue(title=title, dir=dir, selDir=True)

        if not selected_path:
            return
        
        if os.path.isfile(selected_path):
            selected_path = os.path.dirname(selected_path)

        if mode == "source":
            self.sourceDir = os.path.normpath(selected_path)
            self.refreshSourceItems()
        elif mode == "dest":
            self.destDir = os.path.normpath(selected_path)
            self.refreshDestItems()

            return selected_path


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
                refreshFunc = lambda: self.refreshDestItems()
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
    def goUpDir(self, mode):
        if mode == "source":
            attribute = "sourceDir"
            refreshFunc = self.refreshSourceItems

        elif mode == "dest":
            attribute = "destDir"
            refreshFunc = self.refreshDestItems
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
                _, extension = os.path.splitext(Utils.getBasename(path))
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
                _, extension = os.path.splitext(Utils.getBasename(path))
            elif ext:
                extension = ext
            else:
                extension = self.getFileExtension()
            
            return  extension.lower() in self.core.media.videoFormats
        
        except Exception as e:
            logger.warning(f"ERROR:  isVideo() Failed:\n{e}")
    

    #   Returns Bool if File is in Audio Formats
    @err_catcher(name=__name__)
    def isAudio(self, path=None, ext=None):
        if path:
            _, extension = os.path.splitext(Utils.getBasename(path))
        elif ext:
            extension = ext
        else:
            extension = self.getFileExtension()
        
        return extension.lower() in self.audioFormats


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
                filterEnabled = self.b_source_sorting_filtersEnable.isChecked()
                filterStates = self.filterStates_source
            elif table == "destination":
                filterEnabled = self.b_dest_sorting_filtersEnable.isChecked()
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


    #   Group Image Sequences with Seq Number Suffix
    @err_catcher(name=__name__)
    def groupSequences(self, table, sortedList):
        # Helper to Split Filename into Parts
        def _splitFilename(filename):
            name, ext = os.path.splitext(filename)
            match = re.search(r'(\d+)$', name)
            if match:
                frame = match.group(1)
                base = name[:match.start(1)]
            else:
                base = name
                frame = ''
            return base, frame, ext

        filePath_to_item = {}
        seen = set()
        groupedItems = []

        # Collect Files
        ordered_file_paths = []
        for item in sortedList:
            if item["tileType"] == "file":
                path = item["data"]["source_mainFile_path"]
                filePath_to_item[path] = item
                ordered_file_paths.append(path)

        for current in ordered_file_paths:
            if current in seen:
                continue

            base, frame, ext = _splitFilename(current)

            if (
                frame and
                ext.lower() in self.core.media.supportedFormats and
                ext.lower() not in self.core.media.videoFormats
            ):
                # Build regex pattern for matching sequence files
                pattern = re.escape(base) + r'\d+' + re.escape(ext)
                regex = re.compile(pattern)

                matched_dict = OrderedDict()
                for f in ordered_file_paths:
                    if f not in seen and regex.fullmatch(f):
                        matched_dict[f] = None
                matched_dict[current] = None  # ensure current is included

                matched = list(matched_dict.keys())

                if len(matched) > 1:
                    seen.update(matched)
                    padded = "#" * len(frame)
                    display_name = Utils.getBasename(f"{base}{padded}{ext}")

                    matchedItems = [filePath_to_item[f] for f in matched]
                    uuid_list = [item["data"]["uuid"] for item in matchedItems]

                    baseItem = filePath_to_item[current]
                    groupedData = baseItem["data"].copy()

                    # Remove redundant per-frame fields from main dict
                    for key in [
                        "source_mainFile_path",
                        "source_mainFile_duration",
                        "source_mainFile_hash",
                        "hasProxy",
                        "icon",
                        "source_mainFile_date_raw",
                        "source_mainFile_date",
                        "source_mainFile_size_raw",
                        "source_mainFile_size"
                    ]:
                        groupedData.pop(key, None)

                    groupedData["displayName"] = display_name
                    groupedData["fileType"] = "Image Sequence"
                    groupedData["sequenceItems"] = matchedItems
                    groupedData["sequenceUUIDs"] = uuid_list


                    groupedItems.append({
                        "tile": baseItem["tile"],
                        "tileType": "file",
                        "data": groupedData
                    })

                else:
                    seen.add(current)
                    groupedItems.append(filePath_to_item[current])

            else:
                seen.add(current)
                groupedItems.append(filePath_to_item[current])

        # Preserve folder order (if any)
        folders = [item for item in sortedList if item["tileType"] == "folder"]
        return folders + groupedItems


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
                # case "duration":
                #     return data.get("source_mainFile_frames", 0)
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
        if ((table == "source" and self.b_source_sorting_filtersEnable.isChecked()) or
            (table == "destination" and self.b_dest_sorting_filtersEnable.isChecked())):

            sortedList = self.applyTableFilters(table, sortedList)

        #   Combine Image Sequences
        if ((table == "source" and self.b_source_sorting_combineSeqs.isChecked()) or
            (table == "destination" and self.b_dest_sorting_combineSeqs.isChecked())):

            sortedList = self.groupSequences(table, sortedList)

        return sortedList


    #   Build List of Items in Source Directory
    @err_catcher(name=__name__)
    def refreshSourceItems(self):
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
                return
            else:
                self.le_sourcePath.setToolTip(sourceDir)
                self.le_sourcePath.setStyleSheet("")

            #   Capture Scrollbar Position
            scrollPos = self.lw_destination.verticalScrollBar().value()

            #   Get all Items from the Source Dir
            allSourceItems = os.listdir(self.sourceDir)

            self.sourceDataItems = []

            #   Create Data Item for Each Item in Dir
            for file in allSourceItems:
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
    def refreshSourceTable(self, restoreSelection=False):
        WaitPopup.showPopup(parent=self.projectBrowser)

        try:
            #   Save Selection State if Needed
            if restoreSelection:
                self.sourceSelState = {}
                for row in range(self.lw_source.count()):
                    item = self.lw_source.item(row)
                    fileTile = self.lw_source.itemWidget(item)
                    if fileTile and isinstance(fileTile, TileWidget.SourceFileTile):
                        key = fileTile.data["uuid"]
                        self.sourceSelState[key] = fileTile.isChecked()

            #   Sort the Table Items
            sourceDataItems_sorted = self.sortTable("source", self.sourceDataItems)

            # Reset Table
            self.lw_source.clear()
            row = 0

            #   Itterate Sorted Items and Create Tile UI Widgets
            for dataItem in sourceDataItems_sorted:
                data = dataItem.get("data", {})
                tileType = dataItem["tileType"]
                displayName = data["displayName"]
                fileType = data["fileType"]
                uuid = data["uuid"]

                if tileType == "folder":
                    itemTile = TileWidget.FolderItem(self, data)
                    rowHeight = SOURCE_DIR_HEIGHT

                else:
                    #   Get SeqData if Exists
                    if "sequenceItems" in data:
                        uuid = data["uuid"] = Utils.createUUID()
                        fileItem = TileWidget.SourceFileItem(self, passedData=data)

                    else:
                        fileItem = dataItem["tile"]

                    itemTile = TileWidget.SourceFileTile(fileItem, fileType)
                    rowHeight = SOURCE_ITEM_HEIGHT

                #   Set Row Size and Add File Tile widget and Data to Row
                list_item = QListWidgetItem()
                list_item.setSizeHint(QSize(0, rowHeight))
                list_item.setData(Qt.UserRole, {
                    "displayName": displayName,
                    "tileType": tileType,
                    "fileType": fileType,
                    "uuid": uuid
                })

                self.lw_source.addItem(list_item)
                self.lw_source.setItemWidget(list_item, itemTile)

                row += 1

            #   Restore Checked Status
            if restoreSelection:
                for row in range(self.lw_source.count()):
                    item = self.lw_source.item(row)
                    fileTile = self.lw_source.itemWidget(item)
                    if fileTile and isinstance(fileTile, TileWidget.SourceFileTile):
                        uuid = fileTile.data.get("uuid")
                        if uuid in self.sourceSelState:
                            fileTile.setChecked(self.sourceSelState[uuid])

        except Exception as e:
            logger.warning(f"ERROR:  Failed to Refresh Source Table:\n{e}")

        finally:
            WaitPopup.closePopup()


    #   Build List of Items in Destination Directory
    @err_catcher(name=__name__)
    def refreshDestItems(self):
        WaitPopup.showPopup(parent=self.projectBrowser)

        try:
            #   Get Dir and Set Short Name
            destDir = getattr(self, "destDir", "")
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
    def refreshDestTable(self, restoreSelection=False):
        WaitPopup.showPopup(parent=self.projectBrowser)

        try:
            #   Save Selection State if Needed
            if restoreSelection:
                self.destSelState = {}
                for row in range(self.lw_destination.count()):
                    item = self.lw_destination.item(row)
                    fileTile = self.lw_destination.itemWidget(item)
                    if fileTile and isinstance(fileTile, TileWidget.DestFileTile):
                        key = fileTile.data["uuid"]
                        self.destSelState[key] = fileTile.isChecked()

            #   Sort the Table Items
            destDataItems_sorted = self.sortTable("destination", self.destDataItems)

            # Reset Table
            self.lw_destination.clear()
            row = 0

            #   Itterate Sorted Items and Create Tile UI Widgets
            for dataItem in destDataItems_sorted:
                fileItem = dataItem["tile"]
                tileType = dataItem["tileType"]
                data = dataItem["data"]
                displayName = data["displayName"]
                fileType = data["fileType"]
                uuid = data["uuid"]

                if "sequenceItems" in data:
                    uuid = data["uuid"] = Utils.createUUID()
                    data["hasProxy"] = False
                    fileItem = TileWidget.DestFileItem(self, passedData=data)

                else:
                    fileItem = dataItem["tile"]

                itemTile = TileWidget.DestFileTile(fileItem, fileType)
                rowHeight = SOURCE_ITEM_HEIGHT

                #   Set Row Size and Add File Tile widget and Data to Row
                list_item = QListWidgetItem()
                list_item.setSizeHint(QSize(0, rowHeight))
                list_item.setData(Qt.UserRole, {
                    "displayName": displayName,
                    "tileType": tileType,
                    "fileType": fileType,
                    "uuid": uuid
                })

                self.lw_destination.addItem(list_item)
                self.lw_destination.setItemWidget(list_item, itemTile)

                row += 1

            #   Restore Checked Status
            if restoreSelection:
                for row in range(self.lw_destination.count()):
                    item = self.lw_destination.item(row)
                    fileTile = self.lw_destination.itemWidget(item)
                    if fileTile and isinstance(fileTile, TileWidget.DestFileTile):
                        uuid = fileTile.data.get("uuid")
                        if uuid in self.destSelState:
                            fileTile.setChecked(self.destSelState[uuid])

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
            data["uuid"] = Utils.createUUID()

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
            logger.warning(f"ERROR:  Failed to Create Source Data Item for:{file}\n{e}")


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
            copySize_str = Utils.getFileSizeStr(self.total_transferSize)
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


    #   Opens File in External System Default App
    @err_catcher(name=__name__)
    def openInShell(self, filePath, prog=""):
        if prog == "default":
            progPath = ""
        else:
            progPath = self.mediaPlayerPath or ""

        comd = []

        # fileName = Utils.getBasename(filePath)
        # baseName, extension = os.path.splitext(fileName)

        ##   Commented Out to Allow All Files to Open   ##
        # if extension.lower() in self.core.media.supportedFormats:

        logger.debug("Opening File in Shell Application")

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


    #   Adds the Item(s) to the Transfer List (and thus the Destination Table)
    @err_catcher(name=__name__)
    def addToDestList(self, data, refresh=False):
        addList = []

        #   If there is Sequence Data
        if data.get("sequenceItems"):
            #   Itterate Seq Items and Add to List
            for sData in data["sequenceItems"]:
                tile = sData["tile"]
                addList.append(tile.getData())

        else:
            #   Just Add to List
            addList.append(data)

        #   Do Not Add if Already in the Destination List
        for tData in addList:
            if not self.isDuplicate(tData):
                self.transferList.append(tData)
        
        if refresh:
            self.refreshDestItems()


    #   Returns Bool if Display Name Already in Transfer List
    @err_catcher(name=__name__)
    def isDuplicate(self, data):
        displayName = data["displayName"]
        return any(item.get("displayName") == displayName for item in self.transferList)
    

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

            self.refreshDestItems()

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
            #   Get All Checked Tiles
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
        spaceAvail = Utils.getDriveSpace(os.path.normpath(self.destDir))
        transferSize = self.getTotalTransferSize()

        #   Not Enough Space
        if transferSize >= spaceAvail:
            transSize_str = Utils.getFileSizeStr(transferSize)
            spaceAvail_str = Utils.getFileSizeStr(spaceAvail)
            errors["Not Enough Storage Space:"] = f"Transfer: {transSize_str} - Available: {spaceAvail_str}"

        #   Low Space
        elif (spaceAvail - transferSize) < 100 * 1024 * 1024:  # 100 MB
            transSize_str = Utils.getFileSizeStr(transferSize)
            spaceAvail_str = Utils.getFileSizeStr(spaceAvail)
            warnings["Storage Space Low:"] = f"Transfer: {transSize_str} - Available: {spaceAvail_str}"

        ##  File Exists
        for fileTile in self.copyList:
            if fileTile.destFileExists():
                basename = Utils.getBasename(fileTile.getDestMainPath())
                if self.sourceFuncts.chb_overwrite.isChecked():
                    warnings[f"{basename}: "] = "File Exists in Destination"
                else:
                    errors[f"{basename}: "] = "File Exists in Destination"

        ##  CODEC Not Supported and MainFile/Proxy Conflict
        if self.proxyEnabled and self.proxyMode in ["generate", "missing"]:
            for fileTile in (ft for ft in self.copyList if ft.isVideo()):
                basename = Utils.getBasename(fileTile.getDestMainPath())

                ##  UnSupported Format for Proxy Generation
                if not fileTile.isCodecSupported():
                    codec = fileTile.data.get("source_mainFile_codec", "unknown")
                    warnings[f"{basename}: "] = f"Proxy Generation not supported for  '{codec}'  format"

                ##  Proxy Conflict
                elif fileTile.isCodecSupported() and not fileTile.data["hasProxy"]:
                    mainPath = Path(fileTile.getDestMainPath()).resolve()
                    proxyPath = Path(fileTile.getDestProxyFilepath()).resolve()

                    if mainPath == proxyPath:
                        errors[f"{basename}: "] = "Main File and Proxy File have the Same File Path and will Conflict"

        hasErrors = True if len(errors) > 0 else False

        #   Set to Global Vars
        self.transferErrors = errors.copy()
        self.transferWarnings = warnings.copy()

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
            availSpace = Utils.getDriveSpace(os.path.normpath(self.destDir))
            availspace_str = Utils.getFileSizeStr(availSpace)

            header = {
                "Destination Path": self.destDir,
                "Available Drive Space": availspace_str,
                "Number of Files": len(self.copyList),
                "Total Transfer Size": Utils.getFileSizeStr(self.total_transferSize),                #   TODO - Get Actual Size
                "Allow Overwrite": self.sourceFuncts.chb_overwrite.isChecked(),
                "Proxy Mode:": "Disabled" if not self.proxyEnabled else self.proxyMode,
                "": ""
            }

            ##   WARNINGS SECTION
            errors, warnings, hasErrors = self.getTransferErrors()

            ##   FILES SECTION
            file_list = []

            for item in self.copyList:
                filename = Utils.getBasename(item.getDestMainPath())
                
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
                file_list.append(group_box)

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
        self.copyList = self.getCopyList()

        if len(self.copyList) == 0:
            self.core.popup("There are no Items Selected to Transfer")
            return False
        
        if not os.path.isdir(self.destDir):
            self.core.popup("YOU FORGOT TO SELECT DEST DIR")
            return False
        
        WaitPopup.showPopup(parent=self.projectBrowser)

        # Timer for Progress Updates
        self.progressTimer = QTimer(self)
        self.progressTimer.setInterval(self.progUpdateInterval * 1000)
        self.progressTimer.timeout.connect(self.updateTransfer)

        #   Capture Time for Elapsed Calc
        self.totalTransferTimer = ElapsedTimer()

        #   Initialize Time Remaining Calc
        self.speedSamples = deque(maxlen=10)

        self.refreshTotalTransSize()

        #   Reset Calculated Proxy Multipliers
        self.calculated_proxyMults = [] 

        #   If Override is NOT Selected Attempt to Get Resolved Path
        self.resolved_proxyDir = None
        self.getResolvedProxyPaths()

        if self.resolvedProxyPaths:
            self.resolved_proxyDir = next(iter(self.resolvedProxyPaths))

        #   Get Formatted Transfer Details
        popupData, hasErrors = self.generateTransferPopup()

        WaitPopup.closePopup()

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
                    "resolved_proxyDir": self.resolved_proxyDir,
                    "scale"            : self.proxySettings["proxyScale"],
                    "Global_Parameters" : preset["Global_Parameters"],
                    "Video_Parameters" : preset["Video_Parameters"],
                    "Audio_Parameters" : preset["Audio_Parameters"],
                    "Extension"        : preset["Extension"],
                    "Multiplier"        : preset["Multiplier"]
                })

                options["proxySettings"] = proxySettings

            self.progressTimer.start()
            self.totalTransferTimer.start()
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
        self.totalTransferTimer.pause()
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
        self.totalTransferTimer.start()
        self.setTransferStatus("Transferring")
        self.configTransUI("resume")

        logger.status("Resuming Transfer")


    @err_catcher(name=__name__)
    def cancelTransfer(self):
        for item in self.copyList:
            item.cancel_transfer(self)

        self.progressTimer.stop()
        self.totalTransferTimer.stop()
        self.setTransferStatus("Cancelled")
        self.configTransUI("cancel")

        logger.status("Cancelling Transfer")


    @err_catcher(name=__name__)
    def resetTransfer(self):
        self.progressTimer.stop()
        self.totalTransferTimer.stop()
        self.totalTransferTimer.reset()
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
            totalSize_str = Utils.getFileSizeStr(total_copied)
            self.sourceFuncts.l_size_copied.setText(totalSize_str)

            #   Calculate the Time Elapsed
            self.timeElapsed = self.totalTransferTimer.elapsed()
            self.sourceFuncts.l_time_elapsed.setText(Utils.getFormattedTimeStr(self.timeElapsed))

            #   Calculate the Estimated Time Remaining
            timeRemaining = self.getTimeRemaining(total_copied, self.total_transferSize)
            #   Update Time Remaining in the UI
            self.sourceFuncts.l_time_remain.setText(Utils.getFormattedTimeStr(timeRemaining))

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

            #   Call Complete Method if Applicable
            if any(status == "Cancelled" for status in overall_statusList):
                self.completeTranfer("Cancelled")
            elif all(status in {"Complete"} for status in overall_statusList):
                self.completeTranfer("Complete")
            elif all(status in {"Complete", "Warning"} for status in overall_statusList):
                self.completeTranfer("Complete with Warnings")
            elif all(status in {"Complete", "Error"} for status in overall_statusList):
                self.completeTranfer("Complete with Errors")

            logger.debug(f"Updated Overall Status: {overall_status}")

        except Exception as e:
            logger.warning(f"ERROR:  Failed to Update Transfer Progress:\n{e}")


    @err_catcher(name=__name__)
    def completeTranfer(self, transResult):
        self.progressTimer.stop()

        if transResult == "Complete with Warnings":
            status = "Warning"
        elif transResult == "Complete with Errors":
            status = "Error"
        else:
            status = transResult
        self.setTransferStatus(status)

        self.sourceFuncts.progBar_total.setValue(100)
        logger.status(f"Transfer Result: {transResult}")

        self.configTransUI("complete")

        if self.useTransferReport:
            self.createTransferReport(transResult)

        if self.calculated_proxyMults:
            #   Updates Presets Multiplier
            self.updateProxyPresetMultipliers()

        if self.useCompleteSound:
            if transResult == "Complete":
                self.playSound(SOUND_SUCCESS)
            else:
                self.playSound(SOUND_ERROR)

        if self.useCompletePopup:
            text = "Transfer Complete"
            title = "Transfer Complete"

            if self.useTransferReport:
                buttons = ["Open in Explorer", "Open Report", "Close"]
            else:
                buttons = ["Open in Explorer", "Close"]

            result = self.core.popupQuestion(text, title=title, buttons=buttons, doExec=True)

            if result == "Open in Explorer":
                Utils.openInExplorer(self.core, os.path.normpath(self.destDir))

            elif result == "Open Report":
                if not os.path.exists(self.transferReportPath):
                    self.core.popup("Transfer Report Does not Exists")
                else:
                    self.core.openFile(self.transferReportPath)


    #   Creates Transfer Report PDF
    @err_catcher(name=__name__)
    def createTransferReport(self, result):
        try:
            #   Gets Destination Directory for Save Path
            saveDir = self.destDir
            #   Uses CopyList for Report
            reportData = self.copyList

            #   Header Data Items
            report_uuid     = Utils.createUUID()
            timestamp_file  = datetime.now().strftime("%Y-%m-%d_%H%M%S")
            timestamp_text  = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            projectName     = self.core.projectName
            user            = self.core.username
            transferSize    = Utils.getFileSizeStr(self.total_transferSize)
            transferTime    = Utils.getFormattedTimeStr(self.timeElapsed)

            #   Creates Report Filename
            reportFilename = f"TransferReport_{timestamp_file}_{report_uuid}.pdf"
            self.transferReportPath = os.path.join(saveDir, reportFilename)

            #   Creates New PDF Canvas
            c = canvas.Canvas(self.transferReportPath, pagesize=A4)
            width, height = A4

            #   Icon
            icon        = self.getCustomIcon()
            icon_size   = 18
            icon_x      = 50
            icon_y      = height - 48

            #   Margin and Spacing
            left_margin = 50
            col_spacing = 80

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

            #   Make Proxy Mode Text
            if self.proxyEnabled:
                presetName = self.proxySettings.get("proxyPreset", "")
                scale = self.proxySettings.get("proxyScale", "")
                match self.proxyMode:
                    case "copy":
                        proxy_str = "Transfer Proxys"
                    case "generate":
                        proxy_str = f"Generate Proxys ({presetName} {scale})"
                    case "missing":
                        proxy_str = f"Generate Missing Proxys ({presetName} {scale})"
                    case _:
                        proxy_str = "None"
            else:
                proxy_str = "Disabled"

            #   Add Title Line
            c.setFont("Helvetica-Bold", 16)
            c.drawString(icon_x + icon_size + 5, height - 45, "File Transfer Completion Report")

            #   Header Data Spacing
            header_y = height - 70
            header_line_height = 14
            c.setFont("Helvetica", 10)

            #   Add Header Data Items
            header_data = [
                ("Transfer Date:",      timestamp_text),
                ("Report ID:",          report_uuid),
                ("Project:",            projectName),
                ("User:",               user),
                ("Transfer Result:",    result),
                ("Number of Files:",    str(len(reportData))),
                ("Proxy Mode:",         proxy_str),
                ("Transfer Size:",      transferSize),
                ("Transfer Time:",      transferTime)
            ]

            #   Add Each Data Item
            for label, value in header_data:
                c.drawString(left_margin, header_y, label)
                c.drawString(left_margin + col_spacing, header_y, value)
                header_y -= header_line_height

            # leave a bit of extra space after the header block
            header_y -= 20

            # --- Errors Section ---
            c.setFont("Helvetica-Bold", 10)
            c.drawString(left_margin, header_y, "Errors:")
            header_y -= header_line_height

            if self.transferErrors:
                c.setFont("Helvetica", 8)
                for filename, message in self.transferErrors.items():
                    line = f"- {filename}:  {message}"
                    c.drawString(left_margin + 15, header_y, line)
                    header_y -= header_line_height

            # add extra space after section
            header_y -= 20

            # --- Warnings Section ---
            c.setFont("Helvetica-Bold", 10)
            c.drawString(left_margin, header_y, "Warnings:")
            header_y -= header_line_height

            if self.transferWarnings:
                c.setFont("Helvetica", 8)
                for filename, message in self.transferWarnings.items():
                    line = f"- {filename}:  {message}"
                    c.drawString(left_margin + 15, header_y, line)
                    header_y -= header_line_height


            next_page()
            ## --- Page 2 (and on): File info ---    ##

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
                c.setFont("Helvetica", 7)

                #   File Data Items
                for item in reportData:
                    if item.fileType == "Image Sequence":
                        isSeq = True
                        baseName = item.data["displayName"]
                        mainFile_result = item.data["mainFile_result"]
                        seqNumber = len(item.data["sequenceItems"])
                        iData = item.data["sequenceItems"][0]["data"]
                        hasProxy = False

                    else:
                        isSeq = False
                        iData = item.data
                        baseName = iData["displayName"]
                        mainFile_result = iData["mainFile_result"]
                        hasProxy = iData["hasProxy"]

                    proxyAction = item.transferData["proxyAction"]

                    file_lines = [
                        ("File Name:",          baseName),
                        ("File Type:",          item.fileType),
                        ("Transfer Result",     mainFile_result),
                        ("Proxy Action",        str(proxyAction).capitalize()),
                        ("Transfer Time:",      Utils.getFormattedTimeStr(item.data['transferTime'])),
                        ("Date:",               iData['source_mainFile_date']),
                        ("Main File:",          iData['mainFile_result']),
                        ("    Source:",         iData['source_mainFile_path']),
                        ("    Hash:",           iData['source_mainFile_hash']),
                        ("    Destination:",    iData['dest_mainFile_path']),
                        ("    Hash:",           iData['dest_mainFile_hash']),
                        ("    Size:",           iData['source_mainFile_size']),
                        ("    Proxy present:",  str(hasProxy)),
                        *([("Proxy File:",      iData.get('proxyFile_result', ""))] if proxyAction else []),
                        *([("    Source:",      iData.get('source_proxyFile_path', ''))] if (hasProxy and proxyAction) else []),
                        *([("    Hash:",        iData.get('source_proxyFile_hash', ''))] if (hasProxy and proxyAction) else []),
                        *([("    Destination:", iData.get("dest_proxyFile_path", ''))] if proxyAction else []),
                        *([("    Hash:",        iData.get('dest_proxyFile_hash', ''))] if (hasProxy and proxyAction) else []),
                        *([("    Size:",        iData.get('dest_proxyFile_size', ''))] if proxyAction else []),
                        *([("Sequence Files:",  str(seqNumber))] if isSeq else [])
                    ]

                    #   Check if the Current File Block Can Fit on Page
                    block_height = len(file_lines) * line_height + block_spacing
                    if y - block_height < 50:
                        next_page()
                        c.setFont("Helvetica", 7)
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


    # @err_catcher(name=__name__)
    # def getSelectedContexts(self):
    #     contexts = []
    #     if len(self.lw_source.selectedItems()) > 1:
    #         contexts = self.lw_source.selectedItems()
    #     elif len(self.lw_destination.selectedItems()) > 1:
    #         contexts = self.lw_destination.selectedItems()
    #     else:
    #         data = self.getCurrentFilelayer()
    #         if not data:
    #             data = self.getCurrentSource()
    #             if not data:
    #                 data = self.getCurrentAOV()
    #                 if not data:
    #                     items = self.lw_destination.selectedItems()
    #                     if items:
    #                         data = items[0].data(Qt.UserRole)

    #         if data:
    #             contexts = [data]

    #     return contexts
    

    # @err_catcher(name=__name__)
    # def taskClicked(self):
    #     self.updateVersions()


    # @err_catcher(name=__name__)
    # def sourceClicked(self):
    #     self.PreviewPlayer.updateLayers(restoreSelection=True)


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
        pm = self.PreviewPlayer.PreviewPlayer.l_preview.pixmap()
        self.core.entities.setEntityPreview(entity, pm)
        self.core.pb.sceneBrowser.refreshEntityInfo()
        self.w_entities.getCurrentPage().refreshEntities(restoreSelection=True)


