# chart-to-sm.py converter
# Copyright (C) 2020 shockdude

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# Built from the original chart-to-sm.js by Paturages, released under GPL3 with his permission

import re
import configparser
import math
import os
import sys

VERSION = "v0.1"

CHART_EXT = ".chart"
NOTES_CHART = "notes.chart"
SONG_INI = "song.ini"

# mappings for difficulty names from CH to SM
DIFFMAPPINGS = (("[ExpertSingle]", "Challenge"),
				("[HardSingle]", "Hard"),
				("[MediumSingle]", "Medium"),
				("[EasySingle]", "Easy"))

# valid notes: GRYBO and open
VALID_NOTES = (0, 1, 2, 3, 4, 7)

# compute the maximum note index step per measure
def measure_gcd(num_set, measure_length):
	d = measure_length
	for x in num_set:
		d = math.gcd(d, x)
		if d == 1:
			return d
	return d;

def get_notes(infile, diff_map, diff_value, measure_length):
	# create a map to access notes by their index (<index> = N 0 0)
	notes = {}
	last_note = 0
	ch_diff, sm_diff = diff_map # e.g. [ExpertSingle], Challenge:
	with open(infile, "r") as chartfile:
		line = "\n"
		while len(line) > 0 and line.find(ch_diff) < 0: # e.g. [ExpertSingle]
			line = chartfile.readline()
		while len(line) > 0 and line.find("}") < 0:
			line = chartfile.readline()
			# find note line
			reline = re.search("(\d+) = N (\d) (\d+)", line)
			if reline:
				index = int(reline.group(1))
				note = int(reline.group(2))
				length = int(reline.group(3))

				# ignore forced notes and other special notes
				if note not in VALID_NOTES:
					continue
				
				# convert CH open (7) to sm open (5)
				if note == 7:
					note = 5

				# Initialize the notes array, each index representing an SM column
				if index not in notes:
					notes[index] = [0, 0, 0, 0, 0, 0]

				# .chart 01234 are from green to orange
				# 1 is "rice" (non-sustained note), 2 is "long note toggle on" (sustain on)
				if length == 0:
					notes[index][note] = 1
				else:
					notes[index][note] = 2
					# 3 is "long note toggle off", so we need to set it after a 2
					sustain_end = index + length
					if sustain_end not in notes:
						notes[sustain_end] = [0, 0, 0, 0, 0, 0]
					notes[sustain_end][note] = 3
					if last_note < sustain_end:
						last_note = sustain_end

				if last_note <= index:
					last_note = index + 1
					
	# output the chart text
	sm_notes = ''
	if len(notes) > 0:
		# write chart & difficulty info
		sm_notes += "\n"
		sm_notes += "//---------------bass-six - ----------------\n"
		sm_notes += "#NOTES:\n"
		sm_notes += "     bass-six:\n"
		sm_notes += "     :\n"
		sm_notes += "     {}:\n".format(sm_diff) # e.g. Challenge:
		sm_notes += "     {}:\n".format(diff_value)
		sm_notes += "     0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0:\n" # empty groove radar

		# ensure the last measure has the correct number of lines
		if last_note % measure_length != 0:
			last_note += measure_length - (last_note % measure_length)

		# add notes for each measure
		for measure_start in range(0, last_note, measure_length):
			measure_end = measure_start + measure_length
			valid_indexes = set()
			for i in range(measure_start, measure_end):
				if i in notes:
					valid_indexes.add(i - measure_start)
			
			# use gcd to minimize number of rows in each measure
			note_step = measure_gcd(valid_indexes, measure_length)
			for i in range(measure_start, measure_end, note_step):
				if i not in notes:
					sm_notes += '000000\n'
				else:
					for digit in notes[i]:
						sm_notes += str(digit)
					sm_notes += '\n'

			if measure_start + measure_length == last_note:
				sm_notes += ";\n"
			else:
				sm_notes += ',\n'
					
	return sm_notes

def chart_to_sm(infile):
	# look for [Song] and chart resolution
	chart_resolution = 0
	measure_length = 0
	with open(infile, "r") as chartfile:
		line = "\n"
		while len(line) > 0 and line.find("[Song]") < 0:
			line = chartfile.readline()
		reline = None
		while len(line) > 0 and not reline:
			line = chartfile.readline()
			reline = re.search("Resolution = (\d+)", line)
		chart_resolution = int(reline.group(1))
		measure_length = chart_resolution * 4
	
	# look for [SyncTrack] and BPMs
	bpms = "#BPMS:"
	with open(NOTES_CHART, "r") as chartfile:
		line = "\n"
		while len(line) > 0 and line.find("[SyncTrack]") < 0:
			line = chartfile.readline()
		while len(line) > 0 and line.find("}") < 0:
			line = chartfile.readline()
			# find BPM line
			reline = re.search("(\d+) = B (\d+)", line)
			if reline:
				index = float(reline.group(1)) / chart_resolution
				bpm = float(reline.group(2)) / 1000
				bpms += "{}={},".format(index, bpm)
	# add semicolon to end of BPM header entry
	bpms = bpms[:-1] + ";\n"

	# load the song.ini
	songini = configparser.ConfigParser()
	try:
		songini.read(SONG_INI)
	except:
		print("Failed to parse chart song.ini")
		usage()
		
	sections = songini.sections()
	if len(sections) != 1:
		print("Malformed song.ini - unexpected number of sections")
		usage()
	songdata = songini[sections[0]]

	# string to contain the .sm header
	sm_header = ''

	# mappings from CH song.ini to .sm header
	inimappings = (("name", "#TITLE"),
					("artist", "#ARTIST"),
					("genre", "#GENRE"),
					("charter", "#CREDIT"))

	# write .sm header
	for mapping in inimappings:
		if mapping[0] in songdata:
			sm_header += "{}:{};\n".format(mapping[1], songdata[mapping[0]])
	sm_header += "#BACKGROUND:background.png;\n"
	sm_header += "#CDTITLE:album.png;\n"
	sm_header += "#MUSIC:song.ogg;\n"
	if "preview_start_time" in songdata:
		sm_header += "#SAMPLESTART:{};\n".format(float(songdata["preview_start_time"])/1000)
	sm_header += bpms

	# get guitar difficulty
	if "diff_guitar" in songdata:
		diff_guitar = int(songdata["diff_guitar"])
		if diff_guitar < 1:
			diff_guitar = 1
	else:
		diff_guitar = 1

	# write simfile
	with open("notes.sm", "w") as outfile:
		outfile.write(sm_header)					
		for diffmap in DIFFMAPPINGS:
			sm_notes = get_notes(infile, diffmap, diff_guitar, measure_length)
			if len(sm_notes) > 0:
				outfile.write(sm_notes)

def usage():
	print("Chart to SM converter")
	print("Usage: {} [chart]".format(sys.argv[0]))
	print("where [chart] is a notes.chart file, or a folder containing a .chart + song.ini")
	print("Outputs a \"notes.sm\" file in the same folder as the chart")
	sys.exit(1)

def main():
	if len(sys.argv) < 2:
		print("Error: not enough arguments")
		usage()
	
	infile = sys.argv[1]
	infile_name, infile_ext = os.path.splitext(os.path.basename(infile))
	if infile_ext == "": # no extension, probably a folder
		infile = os.path.join(sys.argv[1], NOTES_CHART)
		infile_ext = CHART_EXT
	indir = os.path.dirname(infile)
	if not os.path.isdir(indir):
		print("Error parsing chart folder for {}".format(sys.argv[1]))
		usage()
	if os.path.isfile(infile) and infile_ext == CHART_EXT:
		os.chdir(os.path.dirname(infile))
		chart_to_sm(infile)
	else:
		print("Error: unsupported chart {}".format(sys.argv[1]))
		usage()

if __name__ == "__main__":
	main()

