#!/bin/env python
from __future__ import print_function
import time
from multiprocessing import Process, Queue

#import sys
#sys.exit(0)

import msplib

# Launchpad registers
WDTCTL = 0x120
P1DIR = 0x22
P1SEL = 0x26
P1SEL2 = 0x41
P2DIR = 0x2A
P2SEL = 0x2E
P2SEL2 = 0x42

def launchProc(q):
    # Instantiate the launchpad control class.
    launchpad = msplib.MSP430()

    # Initialize the launchpad.
    time.sleep(2)
    launchpad.write(WDTCTL, 0x5A, 0x80)
    launchpad.write(P1DIR, 0xFF)
    launchpad.write(P1SEL, 0x00)
    launchpad.write(P1SEL2, 0x00)
    launchpad.write(P2DIR, 0xFF)
    launchpad.write(P2SEL, 0x00)
    launchpad.write(P2SEL2, 0x00)

    while True :
        msg = q.get(True)

        if msg == 'end':
            break;
        launchpad.write(msg)

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

# Update PORT2 pins _every other_ time we update lights; otherwise, we get really bad stutter because mspdebug
# apparently blocks until the first byte is verified as written before writing the second.
port2 = False

totalFramesRead = 0.0
recentFrameStatuses = collections.deque(' ' * 64, maxlen=64)
lastCallTime = datetime.datetime.now()


def playFile():
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

        # Instantiate PyAudio.
        audio = pyaudio.PyAudio()

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

                lightStates = [
                        1 << channel if level > thresholds[channel] else 0
                        for channel, level in enumerate(spectrum)
                        ]
                lightStates = sum(lightStates)

                if not port2:
                    #q.put(0x21, 0xFF)
                    q.put(0x21, lightStates >> 8 & 0xFF)
                else:
                    #q.put(0x29, 0xFF)
                    q.put(0x29, lightStates & 0x1F)

                port2 = not port2

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
        playFile()
except KeyboardInterrupt:
    print()
    print("User interrupted; outer loop stopping")

    # Close PyAudio.
    #audio.terminate()

    ansi.done()
