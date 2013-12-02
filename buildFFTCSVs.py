#!/usr/bin/env python

#-----------------------------------------------------------------------------------------------------------------------
# Iterates over a directory of mp3 files, and generates FFT csv files for all songs.
#
# Usage:
#   $ ./buildFFTCSVs.py ~/music
#-----------------------------------------------------------------------------------------------------------------------

import sys
import os
import fnmatch

import analyzer

#-----------------------------------------------------------------------------------------------------------------------

for root, dir, files in os.walk(sys.argv[1]):
    for item in fnmatch.filter(files, "*.mp3"):
        mp3Path = os.path.join(root, item)
        csvPath = mp3Path.replace('.mp3', '.csv')

        analyzer.AnalyzerProcess(csvPath, mp3Path).loop()

#-----------------------------------------------------------------------------------------------------------------------

