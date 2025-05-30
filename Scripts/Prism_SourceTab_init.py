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



#   Make Basic Class Object without Imports
class Prism_SourceTab:
    def __init__(self, core):
        self.core = core

        self.pluginName = "SourceTab"

        #   Abort if not Standalone
        if self.core.appPlugin.pluginName != "Standalone":
            return

        #   Continue Loading SourceTab as Normal
        from Prism_SourceTab_Variables import Prism_SourceTab_Variables
        from Prism_SourceTab_Functions import Prism_SourceTab_Functions

        #   Re-inherit Class
        self.__class__ = type("Prism_SourceTab", (Prism_SourceTab_Variables, Prism_SourceTab_Functions), {})

        Prism_SourceTab_Variables.__init__(self, core, self)
        Prism_SourceTab_Functions.__init__(self, core, self)




