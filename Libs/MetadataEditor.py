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
import json
import csv

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *


pluginPath = os.path.dirname(os.path.dirname(__file__))
uiPath = os.path.join(pluginPath, "Libs", "UserInterfaces")
iconDir = os.path.join(uiPath, "Icons")
sys.path.append(uiPath)


from PrismUtils.Decorators import err_catcher

from SourceTab_Models import (MetaFileItems,
                              MetadataModel,
                              MetadataField,
                              MetadataFieldCollection,
                              MetadataTableModel,
                              SectionHeaderDelegate,
                              MetadataComboBoxDelegate,
                              CheckboxDelegate)

import SourceTab_Utils as Utils
from PopupWindows import DisplayPopup, MetaPresetsPopup, WaitPopup

from MetadataEditor_ui import Ui_w_metadataEditor


logger = logging.getLogger(__name__)



class MetadataEditor(QWidget, Ui_w_metadataEditor):
    def __init__(self, core, origin, parent=None):
        super(MetadataEditor, self).__init__(parent)


        self.core = core
        self.sourceBrowser = origin
        self.projectBrowser = origin.projectBrowser

        self.metaMapPath = os.path.join(self.sourceBrowser.pluginPath,
                                        "Libs",
                                        "UserInterfaces",
                                        "MetaMap.json")
        
        self.sourceOptions = []

        #   Instantiate Metafiles
        self.MetaFileItems = MetaFileItems()

        self.filterStates = {
            "Hide Disabled": False,
            "Hide Empty": False,
            "----1": False,
            "Crew/Production": True,
            "Shot/Scene": True,
            "Camera": True,
            "Audio": True,
            "----2": False
        }

        self.loadMetamap()

        #   Setup UI from Ui_w_metadataEditor
        self.setupUi(self)

        self.configureUI()
        self.refresh()
        self.connectEvents()

        logger.debug("Loaded Metadata Editor")


    @err_catcher(name=__name__)
    def refresh(self, loadFilepath=None):
        WaitPopup.showPopup(parent=self.projectBrowser)

        self.loadFiles(loadFilepath)
        self.populateEditor()
        self.populatePresets()

        WaitPopup.closePopup()


    @err_catcher(name=__name__)
    def configureUI(self):
        #   Set up Sizing and Position
        screen = QGuiApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        calc_width = screen_geometry.width() // 1.5
        width = max(1000, min(2000, calc_width))
        calc_height = screen_geometry.height() // 1.2
        height = max(900, min(2500, calc_height))
        x_pos = (screen_geometry.width() - width) // 2
        y_pos = (screen_geometry.height() - height) // 2
        self.setGeometry(x_pos, y_pos, width, height)

        #   Color MetadataEditor Background
        self.setStyleSheet("""
            #w_metadataEditor {
                background-color: #323537;
                color: #ccc;
            }
        """)

        #   Icons
        icon_filters = QIcon(os.path.join(iconDir, "sort.png"))
        icon_reset = QIcon(os.path.join(iconDir, "reset.png"))
        self.b_filters.setIcon(icon_filters)
        self.b_reset.setIcon(icon_reset)

        #   Build Custom Table Model
        self.MetadataTableModel = MetadataTableModel(
            self.MetadataFieldCollection,
            self.sourceOptions,
            parent=self
        )

        self.tw_metaEditor.setModel(self.MetadataTableModel)

        # Set Section Headers Delegate
        sectionHeaderDelegate = SectionHeaderDelegate(self.tw_metaEditor)
        self.tw_metaEditor.setItemDelegate(sectionHeaderDelegate)

        #   Configure Table
        self.tw_metaEditor.verticalHeader().setVisible(False)
        self.tw_metaEditor.setShowGrid(True)
        self.tw_metaEditor.setGridStyle(Qt.SolidLine)
        self.tw_metaEditor.setAlternatingRowColors(True)
        self.tw_metaEditor.horizontalHeader().setHighlightSections(False)
        self.tw_metaEditor.setSelectionBehavior(QAbstractItemView.SelectItems)
        self.tw_metaEditor.setAutoFillBackground(True)

        #   Makes It so Single-click Will Edit a Cell
        self.tw_metaEditor.setEditTriggers(QAbstractItemView.SelectedClicked)

        self.tw_metaEditor.setStyleSheet("""
            QTableView {
                background-color: #2f3136;
                color: #ccc;
                gridline-color: #555;
                alternate-background-color: #313335;
            }
            QHeaderView::section {
                background-color: #444;
                color: #eee;
                padding: 4px;
                border: 1px solid #555;
            }
        """)

        QTimer.singleShot(.1, self.setInitialColumnWidths)
        self.setToolTips()


    #   Set Column Widths After Launch
    def setInitialColumnWidths(self):
        try:
            table_width = self.tw_metaEditor.viewport().width()
            self.tw_metaEditor.setColumnWidth(0, int(table_width * 0.05))
            self.tw_metaEditor.setColumnWidth(1, int(table_width * 0.20))
            self.tw_metaEditor.setColumnWidth(2, int(table_width * 0.30))
            self.tw_metaEditor.horizontalHeader().setStretchLastSection(True)
        except Exception as e:
            logger.warning(f"ERROR: Unable to resize Table Columns:{e}")


    @err_catcher(name=__name__)
    def setToolTips(self):
        tip = ("File Listing\n\n"
               "Select File to View Metadata")
        self.cb_fileList.setToolTip(tip)

        tip = "Opens Metadata Display Window"
        self.b_showMetadataPopup.setToolTip(tip)

        tip = ("Table Display Filters (will  not affect Saved Metadata\n\n"
               "    - Click to Enable/Disable Filters\n"
               "    - Right-click to Configure Filters")
        self.b_filters.setToolTip(tip)

        tip = ("Reset Editor\n\n"
               "This will clear all existing data or changes loaded into the Editor.\n"
               "This will not alter any metadata in the file itself.")
        self.b_reset.setToolTip(tip)

        tip = "Select Metadata Configuration Preset"
        self.cb_presets.setToolTip(tip)

        tip = "Opens Metadata Presets Editor"
        self.b_presets.setToolTip(tip)

        tip = ("Saves the Current Configuration and\n"
               "closes the Editor")
        self.b_save.setToolTip(tip)

        tip = "Closes the Editor without Saving"
        self.b_close.setToolTip(tip)


    @err_catcher(name=__name__)
    def connectEvents(self):
        self.cb_fileList.currentIndexChanged.connect(lambda: self.onFileChanged())
        self.b_showMetadataPopup.clicked.connect(lambda: self.showMetaDataPopup())
        self.b_filters.clicked.connect(self.populateEditor)
        self.b_filters.setContextMenuPolicy(Qt.CustomContextMenu)
        self.b_filters.customContextMenuRequested.connect(lambda: self.filtersRCL())
        self.b_reset.clicked.connect(self.resetTable)
        self.cb_presets.currentIndexChanged.connect(lambda: self.loadPreset())
        self.b_presets.clicked.connect(self.showPresetsMenu)
        self.b_sidecar_save.clicked.connect(self.saveSidecar)
        self.b_save.clicked.connect(self._onSave)
        self.b_close.clicked.connect(self._onClose)
        

    #   Right Click List for Filters
    @err_catcher(name=__name__)
    def filtersRCL(self):
        cpos = QCursor.pos()
        rcmenu = QMenu(self)

        def _wrapWidget(widget):
            action = QWidgetAction(self)
            action.setDefaultWidget(widget)
            return action
        
        def _separator():
            gb = QGroupBox()
            gb.setFixedHeight(15)
            return _wrapWidget(gb)

        def _applyFilterStates(checkboxRefs, menu):
            for label, cb in checkboxRefs.items():
                self.filterStates[label] = cb.isChecked()
            self.populateEditor()
            menu.close()

        checkboxRefs = {}

        #   Add Filter Checkboxes
        for label, checked in self.filterStates.items():
            if label.startswith("----"):
                rcmenu.addAction(_separator())
                continue

            cb = QCheckBox(label)
            cb.setChecked(checked)
            checkboxRefs[label] = cb
            rcmenu.addAction(_wrapWidget(cb))

        #   Apply Button
        b_apply = QPushButton("Apply")
        b_apply.setFixedWidth(80)
        b_apply.setStyleSheet("font-weight: bold;")
        b_apply.clicked.connect(lambda: _applyFilterStates(checkboxRefs, rcmenu))
        rcmenu.addAction(_wrapWidget(b_apply))

        if rcmenu.isEmpty():
            return False

        rcmenu.exec_(cpos)


    #   Builds MetadataFieldCollection from MetaMap.json
    @err_catcher(name=__name__)
    def loadMetamap(self):
        try:
            with open(self.metaMapPath, "r", encoding="utf-8") as f:
                mData = json.load(f)

            self.metaMap = mData["metaMap"]

        except FileNotFoundError:
            logger.warning("ERROR: MetaMap.json is not found")
            return
        
        try:
            #   Build MetadataFieldCollection
            metadata_fields = []
            for item in self.metaMap:
                field = MetadataField(
                    name=item.get("MetaName", ""),
                    category=item.get("category", "Shot/Scene"),
                    enabled=item.get("enabled", True)
                )
                metadata_fields.append(field)

            self.MetadataFieldCollection = MetadataFieldCollection(metadata_fields)

            logger.debug("Built MetadataFieldCollection from 'MetaMap.json'")

        except Exception as e:
            logger.warning(f"ERROR: Unable to Build MetadataFieldCollection: {e}")


    #   Loads Preset Data and Loads Presets into Combo
    @err_catcher(name=__name__)
    def populatePresets(self):
        self.cb_presets.clear()
        self.cb_presets.addItem("PRESETS")

        orderedPresetNames = self.sourceBrowser.metaPresets.getOrderedPresetNames()

        #   Populate combo box
        for name in orderedPresetNames:
            self.cb_presets.addItem(name)

        idx = self.cb_presets.findText(self.sourceBrowser.metaPresets.currentPreset)
        if idx != -1:
            self.cb_presets.setCurrentIndex(idx)

        self.cb_presets.setSizeAdjustPolicy(QComboBox.AdjustToContents)


    #   Loads Files into MetaFileItems an Combo
    @err_catcher(name=__name__)
    def loadFiles(self, loadFilepath=None):
        #   Get All Checked FileTiles in Dest List
        try:
            fileTiles = self.sourceBrowser.getAllDestTiles(onlyChecked=True)

        except Exception as e:
            logger.warning(f"ERROR: Unable to get Destination FileTiles")
            return

        activeFiles = []

        #   Itterate through Files
        for fileTile in fileTiles:
            try:
                #   Get File Name and Check if it Exists in the MetaFileItems
                filePath = fileTile.data.get("source_mainFile_path", "")
                fileName_orig = Utils.getBasename(filePath)
                fileName_mod = fileTile.getModifiedName(fileName_orig)
                activeFiles.append(fileName_orig)
                existing_item = self.MetaFileItems.getByName(fileName_orig)

                #   If it Exists, Refresh the fileTile Reference
                if existing_item:
                    existing_item.fileName=fileName_orig
                    existing_item.fileName_mod = fileName_mod
                    existing_item.fileTile = fileTile

                #   Or Add New MetaFileItem
                else:
                    if not existing_item:
                        metadata_raw = Utils.getFFprobeMetadata(filePath)
                        metadata = MetadataModel(metadata_raw)

                        self.MetaFileItems.addItem(
                            filePath=filePath,
                            fileName=fileName_orig,
                            fileName_mod = fileName_mod,
                            fileTile=fileTile,
                            metadata=metadata,
                        )

            except Exception as e:
                logger.warning(f"ERROR: Unable to add FileTile '{fileTile}': {e}")

        #   Update Active Files List
        self.MetaFileItems.activeFiles = activeFiles

        #   Update the File List Combobox
        self.cb_fileList.blockSignals(True)
        self.cb_fileList.clear()
        try:
            self.cb_fileList.addItems(activeFiles)

            #   Select Passed File
            if loadFilepath:
                fileName = Utils.getBasename(loadFilepath)
                idx = self.cb_fileList.findText(fileName)
                if idx != -1:
                    self.cb_fileList.setCurrentIndex(idx)

        except Exception as e:
            logger.warning(f"ERROR: Unable to Populate Files Combobox")

        finally:
            self.cb_fileList.setSizeAdjustPolicy(QComboBox.AdjustToContents)
            self.cb_fileList.blockSignals(False)

        self.onFileChanged()


    @err_catcher(name=__name__)
    def onFileChanged(self, filePath=None):
        if filePath:
            path = filePath
        else:
            if self.cb_fileList.count() < 1:
                return
            
            try:
                fileName = self.cb_fileList.currentText()
                fileItem = self.MetaFileItems.getByName(fileName)
                path = fileItem.filePath

            except Exception as e:
                logger.warning(f"ERROR: Unable to get FilePath from Selected File: {e}")
                return
            
        #   Bold Current Viewed File in Combo
        current_idx = self.cb_fileList.currentIndex()
        for i in range(self.cb_fileList.count()):
            font = self.cb_fileList.font()
            font.setBold(i == current_idx)
            self.cb_fileList.setItemData(i, font, Qt.FontRole)

        #   Extract Metadata and add to Model Class
        metadata_raw = Utils.getFFprobeMetadata(path)
        metadata = MetadataModel(metadata_raw)

        #   Update Table Model
        self.MetadataTableModel.sourceOptions = self.sourceOptions

        #   Create Combox Delegate
        self.ComobDelegate = MetadataComboBoxDelegate(metadata, parent=self)
        self.MetadataTableModel.combo_delegate = self.ComobDelegate
        self.tw_metaEditor.setItemDelegateForColumn(MetadataTableModel.COL_SOURCE, self.ComobDelegate)

        #   Create Checkbox Delegate
        self.CheckboxDelegate = CheckboxDelegate()
        self.MetadataTableModel.checkbox_delegate = self.CheckboxDelegate
        self.tw_metaEditor.setItemDelegateForColumn(MetadataTableModel.COL_ENABLED, self.CheckboxDelegate)
        
        #   Add File Names to Fixed Rows
        for field in self.MetadataTableModel.collection.fields_all:
            if field.name == "File Name":
                field.currentValue = fileItem.fileName_mod
            elif field.name == "Original File Name":
                field.currentValue = fileItem.fileName

        #   Refresh Table
        self.MetadataTableModel.layoutChanged.emit()


    #   Loads MetaFieldItems into the Table
    @err_catcher(name=__name__)
    def populateEditor(self):
        useFilters = self.b_filters.isChecked()
        self.MetadataFieldCollection.applyFilters(self.filterStates, useFilters, self.metaMap)
        self.MetadataTableModel.layoutChanged.emit()


    #   Displays Popup with Selected File's Metadata
    @err_catcher(name=__name__)
    def showMetaDataPopup(self, filePath=None):
        #   If passed
        if filePath:
            path = filePath
            fileName = Utils.getBasenamefilePath()

        #   Get Selected File from Combo
        else:
            fileName = self.cb_fileList.currentText()
            fileItem = self.MetaFileItems.getByName(fileName)
            path = fileItem.filePath
            fileName = fileItem.fileName

        #   Get and Format Metadata
        try:
            metadata_raw = Utils.getFFprobeMetadata(path)
            metadata = Utils.groupFFprobeMetadata(metadata_raw)

        except Exception as e:
            logger.warning(f"ERROR: Unable to get Grouped Metadata: {e}")
            return

        DisplayPopup.display(metadata, title=f"Metadata: {fileName}", modal=False)


    #   Saves Presets to Config
    @err_catcher(name=__name__)
    def savePresets(self):
        mData = {
            "currMetaPreset": self.sourceBrowser.metaPresets.currentPreset,
            "metaPresetOrder": self.sourceBrowser.metaPresets.presetOrder
            }

        #   Save to Project Config
        self.sourceBrowser.plugin.saveSettings(key="metadataSettings", data=mData)


    #   Displays Preset Popup
    @err_catcher(name=__name__)
    def showPresetsMenu(self):
        #   Display Meta Presets Popup
        presetPopup = MetaPresetsPopup(self.core, self)

        #   If Saved Button Pressed
        if presetPopup.exec() == QDialog.Accepted:
           self.savePresets()
           self.populatePresets()


    #   Loads Preset into the Table
    @err_catcher(name=__name__)
    def loadPreset(self, presetName=None, onlyExisting=True):
        if not presetName:
            presetName = self.cb_presets.currentText()

        try:
            pData = self.sourceBrowser.metaPresets.getPresetData(presetName)
            if not pData:
                logger.debug(f"Preset Not Found: {presetName}")
                return
        
        except Exception as e:
            logger.warning(f"ERROR: Unable to get Preset from Preset Name: {e}")
            return
        
        #   Build Lookup from List
        presetFields = {row["field"]: row for row in pData}

        if len(self.MetaFileItems.allItems()) < 1:
            return
        
        for row, field in enumerate(self.MetadataFieldCollection.fields):
            #   Skip UNIQUE Rows
            if field.sourceField == "- UNIQUE -":
                continue

            if field.name in presetFields:
                info = presetFields[field.name]

                field.enabled = info.get("enabled", False)
                field.sourceField = info.get("sourceField", "")

                #   Preset field is NONE
                if field.sourceField == "- NONE -":
                    field.currentValue = ""

                #   Preset Field is GLOBAL
                elif field.sourceField == "- GLOBAL -":
                    globalValue = info.get("currentData", "")
                    if globalValue:
                        field.currentValue = globalValue

                else:
                    #   Check sourceField Exists in Metadata
                    if field.sourceField not in self.ComobDelegate.display_strings:
                        #   Not present Fallback to NONE
                        field.sourceField = "- NONE -"
                        field.currentValue = ""
                    else:
                        #   Exists Use Metadata
                        field.currentValue = self.ComobDelegate.getValueForField(field.sourceField)
            else:
                if not onlyExisting:
                    field.enabled = False
                    field.sourceField = "- NONE -"
                    field.currentValue = ""

        #   Update Table
        self.MetadataTableModel.layoutChanged.emit()


    #   Resets Table to Default None's
    @err_catcher(name=__name__)
    def resetTable(self):
        title = "Reset Metadata Table"
        text = (
            "Would you like to clear all existing data or changes loaded into the Editor?\n\n"
            "This will not alter any metadata in the file itself."
        )
        buttons = ["Reset", "Cancel"]
        result = self.core.popupQuestion(text=text, title=title, buttons=buttons)

        if result == "Reset":
            self.cb_presets.setCurrentIndex(0)

            fieldNames = self.MetadataFieldCollection.get_allFieldNames()
            for fieldName in fieldNames:
                if fieldName in ["File Name", "Original File Name"]:
                    continue

                field = self.MetadataFieldCollection.get_fieldByName(fieldName)
                field.enabled = False
                field.sourceField = "- NONE -"
                field.currentValue = ""

            self.MetadataTableModel.layoutChanged.emit()
            logger.debug("Reset Metadata Editor")


    #   Returns Current Data from Editor
    @err_catcher(name=__name__)
    def getCurrentData(self, filterNone=True):
        currentData = []

        fieldNames = self.MetadataFieldCollection.get_allFieldNames()
        for fieldName in fieldNames:
            field = self.MetadataFieldCollection.get_fieldByName(fieldName)
            sourceField = field.sourceField

            if filterNone and (not sourceField or sourceField == "- NONE -"):
                continue

            fieldData = {
                "field": field.name,
                "enabled": field.enabled,
                "sourceField": field.sourceField,
                "currentData": field.currentValue
                }

            currentData.append(fieldData)

        return currentData


    @err_catcher(name=__name__)
    def saveSidecar(self, filePath=None):               #   TODO - Implement UI for Selecting Sidecar type
        if filePath:
            sidecarPath = filePath

        else:
            ####   TEMP TESTING BUTTON     ####                         #   TODO
            testFileName = self.cb_fileList.currentText()
            fileItem = self.MetaFileItems.getByName(testFileName)
            testPath = fileItem.filePath
            savedir = os.path.dirname(testPath)
            sideCarFilename = "TEST_Sidecar.csv"
            sidecarPath = os.path.join(savedir, sideCarFilename)
            
        #   Create .CSV
        self.saveSidecarCSV(sidecarPath)


    #   Create Resolve Type .CSV
    @err_catcher(name=__name__)
    def saveSidecarCSV(self, sidecarPath):
        #   Get All Field Names
        fieldNames = self.MetadataFieldCollection.get_allFieldNames()

        #   Open CSV file to Write To
        with open(sidecarPath, mode="w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)

            #   Write Header
            writer.writerow(fieldNames)

            #   Iterate Over each File
            for fileItem in self.MetaFileItems.allItems(active=True):
                row = []
                metadata = fileItem.metadata

                for fieldName in fieldNames:
                    field = self.MetadataFieldCollection.get_fieldByName(fieldName)

                    #   Skip if the Field Doesn't Exist
                    if not field:
                        row.append("")
                        continue

                    #   Add File Name Fixed Cells
                    if field.name == "File Name":
                        row.append(fileItem.fileName_mod)
                        continue
                    if field.name == "Original File Name":
                        row.append(fileItem.fileName)
                        continue

                    #   Get Currently Selected Source
                    sourceField = field.sourceField

                    #   Handle Each Type of Source
                    if not sourceField or sourceField == "- NONE -":
                        row.append("")

                    elif sourceField == "- GLOBAL -":
                        row.append(field.currentValue)

                    elif sourceField == "- UNIQUE -":
                        value = self.MetaFileItems.get_uniqueValue(fileItem, field.name)
                        row.append(value)

                    #   Normal Metadata Field
                    else:
                        row.append(metadata.get_valueFromSourcefield(sourceField))

                writer.writerow(row)

        logger.status(f"Saved sidecar to: {sidecarPath}")


    #   Saves and Closes the MetaEditor
    @err_catcher(name=__name__)
    def _onSave(self):
        preset = self.cb_presets.currentText()
        if preset == "PRESETS":
            preset = ""
            
        self.sourceBrowser.metaPresets.currentPreset = preset

        self.savePresets()
        self.sourceBrowser.sourceFuncts.updateUI()
        self.close()


    #   Closes the MetaEditor
    @err_catcher(name=__name__)
    def _onClose(self):
        self.close()

