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


import time



class ElapsedTimer:
    '''
    Simple Elapsed Timer with Pause Functions
    '''
    def __init__(self):
        self._start_time = None
        self._elapsed = 0.0
        self._running = False

    def start(self) -> None:
        '''
        Starts Timer
        '''

        if not self._running:
            self._start_time = time.time()
            self._running = True

    def pause(self) -> None:
        '''
        Pauses Timer and keeps Time Elapsed
        '''

        if self._running:
            self._elapsed += time.time() - self._start_time
            self._start_time = None
            self._running = False

    def stop(self) -> None:
        '''
        Alias of .pause() Method\n
        Stops Timer and keeps Time Elapsed
        '''
        self.pause()

    def reset(self) -> None:
        '''
        Resets Timer to 0.0
        '''

        self._start_time = None
        self._elapsed = 0.0
        self._running = False

    def isRunning(self) -> bool:
        '''
        Returns Bool of Timer Running
        '''
        return self._running

    def elapsed(self) -> float:
        '''
        Returns the Elapsed Time
        '''

        if self._running:
            return self._elapsed + (time.time() - self._start_time)
        else:
            return self._elapsed