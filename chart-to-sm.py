# -*- coding: UTF-8 -*-

# chart-to-sm.py converter
# Copyright (C) 2021 shockdude

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
import math
import os
import sys
import traceback
import codecs
# hacked mido 1.2.9 to support sysex data bytes > 127, used for tap notes
import mido_sysexhack as mido

VERSION = "v0.3"

CHART_EXT = ".chart"
MID_EXT = ".mid"
NOTES_NAME = "notes"
SONG_INI = "song.ini"

SUSTAIN_THRESH = 16

NUM_COLUMNS = 6

SONG_FILES = ("song.ogg", "guitar.ogg", "song.mp3", "guitar.mp3")

# mappings for difficulty names from CH to SM
DIFFMAPPINGS = (("[ExpertSingle]", "Challenge"),
				("[HardSingle]", "Hard"),
				("[MediumSingle]", "Medium"),
				("[EasySingle]", "Easy"))
				
# MIDI green notes & open sysex on/off per difficulty
# open sysex off currently unused, but good to document
MIDDIFFMAPPINGS = (("Challenge", 96, (80,83,0,0,3,1,1), (80,83,0,0,3,1,0)),
					("Hard", 84, (80,83,0,0,2,1,1), (80,83,0,0,2,1,0)),
					("Medium", 72, (80,83,0,0,1,1,1), (80,83,0,0,1,1,0)),
					("Easy", 60, (80,83,0,0,0,1,1), (80,83,0,0,0,1,0)))

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

# based on https://stackoverflow.com/a/65841914
def check_encoding(infile):
	with open(infile, "rb") as f:
		beginning = f.read(4)
		# The order of these if-statements is important
		# otherwise UTF32 LE may be detected as UTF16 LE as well
		if beginning == codecs.BOM_UTF32_LE:
			return "utf_32_be"
		elif beginning == codecs.BOM_UTF32_BE:
			return "utf_32_le"
		elif beginning[0:3] == codecs.BOM_UTF8:
			return "utf_8_sig"
		elif beginning[0:2] == codecs.BOM_UTF16_LE:
			return "utf_16_le"
		elif beginning[0:2] == codecs.BOM_UTF16_BE:
			return "utf_16_be"
	# check if utf-8
	try:
		with open(infile, "r", encoding="utf-8") as f:
			f.read()
		return "utf-8"
	except:
		return "cp1252"

def output_sm(notes, last_note, measure_length, sm_diff, diff_value):
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

		# add notes for each measure
		for measure_start in range(0, last_note + measure_length, measure_length):
			measure_end = measure_start + measure_length
			valid_indexes = set()
			for i in range(measure_start, measure_end):
				if i in notes:
					valid_indexes.add(i - measure_start)
			
			# use gcd to minimize number of rows in each measure
			note_step = measure_gcd(valid_indexes, measure_length)
			for i in range(measure_start, measure_end, note_step):
				if i not in notes:
					sm_notes += '0'*NUM_COLUMNS + '\n'
				else:
					for digit in notes[i]:
						sm_notes += str(digit)
					sm_notes += '\n'

			if measure_start + measure_length > last_note:
				sm_notes += ";\n"
			else:
				sm_notes += ',\n'
	return sm_notes

def process_song_ini(bpms):
	# load the song.ini
	songini_encoding = check_encoding(SONG_INI)
	songdata = {}
	try:
		with open(SONG_INI, "r", encoding=songini_encoding) as songini_file:
			for line in songini_file:
				split_line = line.split("=", 1)
				if len(split_line) == 2:
					songdata[split_line[0].strip().lower()] = split_line[1].strip()
	except:
		traceback.print_exc()
		print("Failed to parse song.ini")
		songdata = {}
	
	# look for the song audio file
	song_file = None
	for file in SONG_FILES:
		if os.path.isfile(file):
			if song_file == None:
				song_file = file
			else:
				print("Warning: found song {} & stem {}. Stems currently not supported in SM".format(song_file, file))
	if song_file == None:
		print("Warning: Audio file not found for chart")
		song_file = "song.ogg"

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
	sm_header += "#MUSIC:{};\n".format(song_file)
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
		
	return sm_header, diff_guitar

def chart_get_notes(infile, diff_map, diff_value, measure_length, infile_encoding):
	# create a map to access notes by their index (<index> = N 0 0)
	notes = {}
	last_note = 0
	ch_diff, sm_diff = diff_map # e.g. [ExpertSingle], Challenge:
	with open(infile, "r", encoding=infile_encoding) as chartfile:
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
					notes[index] = [0]*NUM_COLUMNS

				# .chart 01234 are from green to orange
				# 1 is "rice" (non-sustained note), 2 is "long note toggle on" (sustain on)
				if length == 0:
					notes[index][note] = 1
				else:
					notes[index][note] = 2
					# 3 is "long note toggle off", so we need to set it after a 2
					sustain_end = index + length
					if sustain_end not in notes:
						notes[sustain_end] = [0]*NUM_COLUMNS
					notes[sustain_end][note] = 3
					if last_note <= sustain_end:
						last_note = sustain_end + 1

				if last_note <= index:
					last_note = index + 1
					
	# output the chart text	
	return output_sm(notes, last_note, measure_length, sm_diff, diff_value)

def chart_to_sm(infile):
	# look for [Song] and chart resolution
	chart_resolution = 0
	measure_length = 0
	infile_encoding = check_encoding(infile)
	with open(infile, "r", encoding=infile_encoding) as chartfile:
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
	with open(infile, "r", encoding=infile_encoding) as chartfile:
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

	# get sm_header metadata & difficulty value out of the song.ini
	sm_header, diff_guitar = process_song_ini(bpms)
	# make sure we didn't return an error
	if type(sm_header) == int:
		return sm_header

	# write simfile
	with open("notes.sm", "w", encoding="utf-8") as outfile:
		outfile.write(sm_header)					
		for diffmap in DIFFMAPPINGS:
			sm_notes = chart_get_notes(infile, diffmap, diff_guitar, measure_length, infile_encoding)
			if len(sm_notes) > 0:
				outfile.write(sm_notes)
				
	return 0

def mid_get_notes(track_notes, diffmap, diff_value, measure_length):
	sm_diff = diffmap[0]
	green_note = diffmap[1]
	diff_notes = (green_note, green_note+1, green_note+2, green_note+3, green_note+4)
	open_sysex = diffmap[2]
	
	notes = {}
	active_notes = {}
	current_tick = 0
	for msg in track_notes:
		current_tick += msg.time
		if msg.type == "note_on" and msg.note in diff_notes:
			if msg.velocity > 0:
				# note on event
				index = current_tick
				note = msg.note - green_note
				active_notes[note] = index

				# Initialize the notes array, each index representing an SM column
				if index not in notes:
					notes[index] = [0]*NUM_COLUMNS

				# .chart 01234 are from green to orange
				# 1 is "rice" (non-sustained note), 2 is "long note toggle on" (sustain on)
				notes[index][note] = 1
			elif msg.velocity == 0:
				index = current_tick
				note = msg.note - green_note
				
				if note not in active_notes:
					print("Warning: note_off not corresponding to a note_on event")
					continue
				
				old_index = active_notes[note]
				if index - old_index >= int(round(measure_length / SUSTAIN_THRESH)):
					# sustain, so convert note to long note
					notes[old_index][note] = 2
					if index not in notes:
						notes[index] = [0]*NUM_COLUMNS
					notes[index][note] = 3
				
				# check if this note is actually an open note
				if 5 in active_notes and active_notes[5] == active_notes[note]:
					note_value = notes[old_index][note]
					notes[old_index][5] = note_value
					notes[old_index][note] = 0
					if note_value == 2:
						notes[index][5] = 3
						notes[index][note] = 0

				del active_notes[note]
		elif msg.type == "sysex":
			# remember that there should be an open note at this index
			if msg.data == open_sysex:
				index = current_tick
				note = 5
				active_notes[note] = index

	last_note = current_tick
	
	# output the chart text
	return output_sm(notes, last_note, measure_length, sm_diff, diff_value)

def mid_to_sm(infile):
	try:
		mid = mido.MidiFile(infile)
	except:
		traceback.print_exc()
		print("Failed to process {}".format(infile))
		return 1
	track_tempomap = None
	track_guitar = None
	track_t1gems = None
	track_rhythm = None
	track_bass = None
	track_notes = None
	
	chart_resolution = mid.ticks_per_beat
	measure_length = chart_resolution * 4
	
	for i, track in enumerate(mid.tracks):
		# midi spec says tempomap must be first track
		if i == 0:
			track_tempomap = track
		else:
			if track.name == "PART GUITAR":
				track_guitar = track
			elif track.name == "T1 GEMS":
				track_t1gems = track
			elif track.name == "PART RHYTHM":
				track_rhythm = track
			elif track.name == "PART BASS":
				track_bass = track
			
	# stepmania outfox 4.9.6 currently only supports 1 open-note instrument: bass-six
	# so pick 1 guitar track in the midi to use
	if track_guitar != None:
		track_notes = track_guitar
	elif track_t1gems != None:
		track_notes = track_t1gems
	elif track_rhythm != None:
		track_notes = track_rhythm
	elif track_bass != None:
		track_notes = track_bass
	else:
		print("Error: no valid notes track found in MIDI")
		return 1
		
	# parse tempomap
	bpms = "#BPMS:"
	current_tick = 0
	for msg in track_tempomap:
		current_tick += msg.time
		if msg.type == "set_tempo":
			index = current_tick / chart_resolution
			bpm = mido.tempo2bpm(msg.tempo)
			bpms += "{}={},".format(index, bpm)
	# add semicolon to end of BPM header entry
	bpms = bpms[:-1] + ";\n"
	
	# get sm_header metadata & difficulty value out of the song.ini
	sm_header, diff_guitar = process_song_ini(bpms)
	# make sure we didn't return an error
	if type(sm_header) == int:
		return sm_header

	with open("notes.sm", "w", encoding="utf-8") as outfile:
		outfile.write(sm_header)					
		for diffmap in MIDDIFFMAPPINGS:
			sm_notes = mid_get_notes(track_notes, diffmap, diff_guitar, measure_length)
			if len(sm_notes) > 0:
				outfile.write(sm_notes)
				
	return 0

def usage():
	print("Clone Hero Chart to SM converter")
	print("Usage: {} [chart]".format(sys.argv[0]))
	print("where [chart] is a .chart or .mid file, or a folder containing CH charts")
	print("Outputs a \"notes.sm\" file in the same folder as the chart")
	sys.exit(1)

def handle_file(infile):
	infile_name, infile_ext = os.path.splitext(os.path.basename(infile))
	if os.path.isfile(infile):
		parent_name = os.path.dirname(os.path.realpath(infile))
		if infile_ext.lower() == MID_EXT:
			print("Converting .mid for {}".format(parent_name))
			return mid_to_sm(infile)
		elif infile_ext.lower() == CHART_EXT:
			print("Converting .chart for {}".format(parent_name))
			return chart_to_sm(infile)
	return 1

def scan_folder(in_folder):
	# scan subdirectories
	for f in os.listdir("."):
		if os.path.isdir(f):
			os.chdir(f)
			scan_folder(f)
			os.chdir("..")
	try:
		if os.path.isfile(NOTES_NAME+MID_EXT):
			handle_file(NOTES_NAME+MID_EXT)
		elif os.path.isfile(NOTES_NAME+CHART_EXT):
			handle_file(NOTES_NAME+CHART_EXT)
	except:
		traceback.print_exc()
		print("Failed to process chart in {}".format(in_folder))

def main():
	# force utf-8 in stdout
	if not sys.stdout.isatty():
		sys.stdout.reconfigure(encoding='utf-8')
		sys.stderr.reconfigure(encoding='utf-8')

	if len(sys.argv) < 2:
		print("Error: not enough arguments")
		usage()
	
	infile = sys.argv[1]
	if os.path.isdir(infile):
		# scan folder for charts
		print("Scanning for charts to convert...")
		os.chdir(infile)
		scan_folder(infile)
		sys.exit(0)
	elif os.path.isfile(infile):
		os.chdir(os.path.dirname(infile))
		if handle_file(infile):
			print("Error: unsupported chart {}".format(sys.argv[1]))
			usage()
	else:
		print("Error: invalid chart path {}".format(sys.argv[1]))
		usage()

if __name__ == "__main__":
	main()

