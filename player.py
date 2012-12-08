#!/bin/env python
import time

import msplib

# Launchpad registers
WDTCTL = 0x120
P1DIR = 0x22
P1SEL = 0x26
P1SEL2 = 0x41
P2DIR = 0x2A
P2SEL = 0x2E
P2SEL2 = 0x42

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


import datetime
import sys

from numpy import array_split, short, fromstring
from numpy.random import rand as rand_array

import anfft

import audioread

import pyaudio

#import ansi


# Slow the light state changes down to every 0.05 seconds.
delayBetweenUpdates = 0.05

bytes_per_frame_per_channel = 2


filename = sys.argv[1]

# Warm up ANFFT, allowing it to determine which FFT algorithm will work fastest on this machine.
anfft.fft(rand_array(1024), measure=True)

lastCallTime = datetime.datetime.now()

# Update PORT2 pins _every other_ time we update lights; otherwise, we get really bad stutter because mspdebug
# apparently blocks until the first byte is verified as written before writing the second.
port2 = False

with audioread.audio_open(filename) as inFile:
    print inFile.channels, inFile.samplerate, inFile.duration
    inFileIter = None

    # Instantiate PyAudio.
    audio = pyaudio.PyAudio()

    def callback(in_data, frame_count, time_info, status):
        global inFileIter, lastCallTime, port2

        if not inFileIter:
            inFileIter = inFile.read_data(frame_count * inFile.channels * bytes_per_frame_per_channel)

        data = next(inFileIter)

        thisCallTime = datetime.datetime.now()
        if (thisCallTime - lastCallTime).total_seconds() > delayBetweenUpdates:
            lastCallTime = thisCallTime
            dataArr = fromstring(data, dtype=short)
            normalized = dataArr / float(2 ** (bytes_per_frame_per_channel * 8))

            #spectrum = map((lambda arr: sum(arr) / len(arr)), array_split(abs(anfft.rfft(normalized)), 256))
            spectrum = map(sum, array_split(abs(anfft.rfft(normalized)), 16))  # Cut the spectrum down to 16 channels.

            #ansi.stdout('{cursor.row.0}')
            #for row in range(70 * 4, 0, -4):
            #    print(' '.join('#' if level > row else ' ' for level in spectrum))

            #ansi.stdout('{cursor.row.0}{clear.line.end}{}',
            #ansi.stdout('{cursor.row.0}{clear.screen.end}{}',
            #        '\n'.join('=' * int(level) for level in spectrum)
            #        )
            #ansi.stdout('{cursor.row.0}')
            #for level in spectrum:
            #    ansi.stdout('{clear.line.end}{}', '=' * int(level))
            #ansi.stdout('{cursor.row.0}{clear.screen.end}{}',
            #        '\n'.join('=' * int(level / 3) + ' ' * int(240 - level / 3) for level in spectrum)
            #        )

            lightStates = [
                    1 << channel if level > 40 else 0
                    for channel, level in enumerate(spectrum)
                    ]
            lightStates = sum(lightStates)

            if not port2:
                launchpad.write(0x21, lightStates >> 8 & 0xFF)
            else:
                launchpad.write(0x29, lightStates & 0x1F)

            port2 = not port2

        return (data, pyaudio.paContinue)

    stream = audio.open(
            format=pyaudio.paInt16,
            channels=inFile.channels,
            rate=inFile.samplerate,
            output=True,
            stream_callback=callback
            )

    # Wait for stream to finish.
    while stream.is_active():
        time.sleep(0.1)

    # Stop stream.
    stream.stop_stream()
    stream.close()
    inFile.close()

    # Close PyAudio.
    audio.terminate()
