# Clone Hero Chart to SM converter
Roughly convert Clone Hero charts to simfiles for Stepmania 5.3 Outfox's Guitar mode \
Supports both .mid and .chart files

Usage: Drag-and-drop the chart file or chart folder onto `chart-to-sm.exe` \
Or use the command line: `python chart-to-sm.py notes.chart`

Extremely hacky with barely any error handling, but should work for most CH chart folders \
containing a `notes.chart`/`notes.mid` and a `song.ini`. \
Can also scan & batch convert multiple charts in a folder.

Written by shockdude in Python 3.7 \
Original chart-to-sm.js by Paturages \
https://github.com/Paturages/

Uses Mido 1.2.9, hacked to support sysex data bytes > 127 \
https://github.com/mido/mido

Stepmania 5.3 Outfox: https://projectmoon.dance/ \
Clone Hero: https://clonehero.net/
