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


PRISMROOT = r"C:\Prism2"                                            ###   TODO
prismRoot = os.getenv("PRISM_ROOT")
if not prismRoot:
    prismRoot = PRISMROOT


from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *




class MetaDataPopup(QDialog):
    def __init__(self, metadata):
        super().__init__()

        self.setWindowTitle("File Metadata")

        # Check the Qt version to handle screen geometry differently for Qt6 and Qt5
        screen = QGuiApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()  # Get the available screen geometry
        screen_width = screen_geometry.width()
        screen_height = screen_geometry.height()

        # Calculate the center position and set window size to half of the screen's width and height
        width = screen_width // 2
        height = screen_height // 2
        x_pos = (screen_width - width) // 2
        y_pos = (screen_height - height) // 2

        # Set the geometry of the window
        self.setGeometry(x_pos, y_pos, width, height)

        # Layout for the metadata display
        layout = QVBoxLayout()

        # Scroll Area to hold all metadata sections
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area_widget = QWidget()
        scroll_area.setWidget(scroll_area_widget)
        scroll_layout = QVBoxLayout(scroll_area_widget)

        # Organize metadata by group
        grouped_metadata = self.group_metadata(metadata)

        # For each group (section), display a QGroupBox with its tags
        for section, tags in grouped_metadata.items():
            group_box = QGroupBox(section)  # Section name as the title of the group box
            form_layout = QFormLayout()  # Layout to hold the key-value pairs
            
            for key, value in tags.items():
                form_layout.addRow(key, QLabel(str(value)))  # Display key-value pairs
                
            group_box.setLayout(form_layout)
            scroll_layout.addWidget(group_box)  # Add the group box to the scrollable layout

        layout.addWidget(scroll_area)  # Add the scroll area to the main layout
        self.setLayout(layout)

    def group_metadata(self, metadata):
        """
        Groups metadata by the section tags (e.g., 'File', 'QuickTime', etc.)
        Returns a dictionary with grouped metadata.
        """
        grouped = {}
        
        for key, value in metadata.items():
            # Extract the section (e.g., 'QuickTime', 'File') from the key
            section = key.split(":")[0]  # Get the part before the colon
            tag = key.split(":")[1] if len(key.split(":")) > 1 else key  # Get the part after the colon
            
            if section not in grouped:
                grouped[section] = {}
            
            grouped[section][tag] = value
        
        return grouped
