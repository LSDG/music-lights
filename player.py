#!/bin/env python
from __future__ import print_function
import time
from multiprocessing import Process, Queue

pins = [0, 1, 4, 7, 8, 9, 10, 11, 14, 15, 17, 18, 21, 22, 23, 24, 25]

def launchProc(q):
    import RPi.GPIO as GPIO

    GPIO.setmode(GPIO.BCM)
    for pin in pins:
        GPIO.setup(pin, GPIO.OUT)

    while True :
        msg = q.get(True)

        if msg == 'end':
            break

        for channel, value in enumerate(msg):
            GPIO.output(pins[channel], value)

q = Queue()
p = Process(target=launchProc, args=(q,))
p.start()

import ConfigParser
import collections
import datetime
import os
import sys

from itertools import cycle

from numpy import array_split, short, fromstring
from numpy.random import rand as rand_array

import anfft

import audioread

import pyaudio

import ansi


gcp = ConfigParser.SafeConfigParser()
gcp.read('config.ini')


# The number of spectrum analyzer bands (also light output channels) to use.
frequencyBands = int(gcp.get('main', 'frequencyBands', 16))

# Slow the light state changes down to every 0.05 seconds.
delayBetweenUpdates = float(gcp.get('main', 'delayBetweenUpdates', 0.05))

bytes_per_frame_per_channel = int(gcp.get('main', 'bytes_per_frame_per_channel', 2))

defaultThresholds = map(float, gcp.get('spectrum', 'thresholds').split(','))
defaultOrder = map(int, gcp.get('spectrum', 'channelOrder').split(','))

def statusChar(status):
    if status == pyaudio.paOutputOverflow:
        return "\033[1;33mO\033[m"
    elif status == pyaudio.paOutputUnderflow:
        return "\033[1;31mU\033[m"
    else:
        return "."


files = sys.argv[1:]

# Warm up ANFFT, allowing it to determine which FFT algorithm will work fastest on this machine.
anfft.fft(rand_array(1024), measure=True)

totalFramesRead = 0.0
recentFrameStatuses = collections.deque(' ' * 64, maxlen=64)
lastCallTime = datetime.datetime.now()

# Instantiate PyAudio.
audio = pyaudio.PyAudio()

def playFile(filename):
    with audioread.audio_open(filename) as inFile:
        thresholds = defaultThresholds
        order = defaultOrder
        if os.path.exists(filename + '.ini'):
            cp = ConfigParser.SafeConfigParser()
            cp.read([filename + '.ini'])
            thresholds = map(float, cp.get('spectrum', 'thresholds').split(','))
            order = map(int, cp.get('spectrum', 'channelOrder').split(','))

        global inFileIter, abort
        inFileIter = None
        abort = False

        def callback(in_data, frame_count, time_info, status):
            global inFileIter, lastCallTime, port2, totalFramesRead, recentFrameStatuses, abort

            if abort:
                return (None, pyaudio.paAbort)

            if not inFileIter:
                inFileIter = inFile.read_data(frame_count * inFile.channels * bytes_per_frame_per_channel)

            data = next(inFileIter)

            totalFramesRead += frame_count

            recentFrameStatuses.appendleft(statusChar(status))

            ansi.stdout("{cursor.col.0}{clear.line.all}Current time:"
                        " {style.bold}{elapsedTime: >7.2f}{style.none} / {totalTime: <7.2f}"
                        " {style.bold.fg.black}[{style.none}{status}{style.bold.fg.black}]{style.none}",
                    elapsedTime=totalFramesRead / inFile.samplerate, totalTime=inFile.duration,
                    status=''.join(recentFrameStatuses), suppressNewline=True)

            thisCallTime = datetime.datetime.now()
            if (thisCallTime - lastCallTime).total_seconds() > delayBetweenUpdates:
                lastCallTime = thisCallTime
                dataArr = fromstring(data, dtype=short)
                normalized = dataArr / float(2 ** (bytes_per_frame_per_channel * 8))

                # Cut the spectrum down to the appropriate number of bands.
                bands = array_split(abs(anfft.rfft(normalized)), frequencyBands)
                bands = [bands[i] for i in order]

                spectrum = map((lambda arr: sum(arr) / len(arr)), bands)

                lightStates = [ level > thresholds[channel] for channel, level in enumerate(spectrum) ]

                q.put(lightStates)

            return (data, pyaudio.paContinue)

        print()
        ansi.stdout("Playing audio file: {style.fg.blue}{}{style.none}", filename)
        ansi.stdout("{style.bold.fg.black}channels:{style.none} {inFile.channels}"
                    "   {style.bold.fg.black}sample rate:{style.none} {inFile.samplerate}"
                    "   {style.bold.fg.black}duration:{style.none} {inFile.duration}",
                inFile=inFile)
        #print("Playing audio file: \033[34m{}\033[m".format(filename))
        #print("\033[1;30mchannels:\033[m {}   \033[1;30msample rate:\033[m {}   \033[1;30mduration:\033[m {}".format(
                #inFile.channels, inFile.samplerate, inFile.duration))

        stream = audio.open(
                format=pyaudio.paInt16,
                channels=inFile.channels,
                rate=inFile.samplerate,
                output=True,
                stream_callback=callback
                )

        # Wait for stream to finish.
        try:
            while stream.is_active():
                time.sleep(0.01)
        except KeyboardInterrupt:
            print()
            print("User interrupted; stopping.")
            abort = True
            time.sleep(0.2)

        print()
        print("Stopping audio...")

        # Stop stream.
        stream.stop_stream()
        stream.close()
        inFile.close()

try:
    for filename in cycle(files):
        playFile(filename)
except KeyboardInterrupt:
    print()
    print("User interrupted; outer loop stopping")

    q.put('end')

    # Close PyAudio.
    audio.terminate()

    ansi.done()
