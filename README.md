# Clone Hero Chart to SM converter
Roughly convert Clone Hero charts to simfiles for Stepmania 5.3 Outfox's WIP Guitar mode. \
Supports both .mid and .chart files

Usage: Drag-and-drop the chart file or chart folder onto `chart-to-sm.exe` \
Or use the command line: `python chart-to-sm.py notes.chart` or `python chart-to-sm.py chart_folder`

A bit hacky, but should work for most CH chart folders containing a `notes.chart`/`notes.mid` and a `song.ini`. \
Can also scan & batch convert whole folders of charts. \

Note: For charts with multiple audio stems, e.g. song.ogg & guitar.ogg, currently you have to mix the stems into a single song.ogg manually.

Written by shockdude in Python 3.7 \
Original chart-to-sm.js by Paturages \
https://github.com/Paturages/

Many thanks to GenericMadScientist for help & testing. \
https://github.com/genericmadscientist

Uses Mido 1.2.9, hacked to support out-of-spec sysex behavior for some .mid charts \
https://github.com/mido/mido

Stepmania 5.3 Outfox: https://projectmoon.dance/ \
Clone Hero: https://clonehero.net/
