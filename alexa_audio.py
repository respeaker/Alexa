
import pyaudio
import wave
import time
import os
import platform
import threading
from respeaker import Microphone


__author__ = "NJC"
__license__ = "MIT"


class AlexaAudio:
    """ This object handles all audio playback and recording required by the Alexa enabled device. Audio playback
        and recording both use the PyAudio package.

    """
    def __init__(self):
        """ AlexaAudio initialization function.
        """
        self.quit_event = threading.Event()
        self.mic = Microphone(quit_event=self.quit_event)

        # Initialize pyaudio
        self.pyaudio_instance = self.mic.pyaudio_instance

    def close(self):
        """ Called when the AlexaAudio object is no longer needed. This closes the PyAudio instance.
        """

        self.quit_event.set()
        # Terminate the pyaudio instance
        self.pyaudio_instance.terminate()

    def get_audio(self, timeout=3):
        return self.mic.listen(timeout=timeout)

    def play_mp3(self, raw_audio):
        """ Play an MP3 file. Alexa uses the MP3 format for all audio responses. PyAudio does not support this, so
            the MP3 file must first be converted to a wave file before playing.

            This function assumes ffmpeg is located in the current working directory (ffmpeg/bin/ffmpeg).

        :param raw_audio: the raw audio as a binary string
        """
        # Save MP3 data to a file
        with open("files/response.mp3", 'wb') as f:
            f.write(raw_audio)

            # Convert mp3 response to wave (pyaudio doesn't work with MP3 files)
            # subprocess.call(['ffmpeg/bin/ffmpeg', '-y', '-i', 'files/response.mp3', 'files/response.wav'],
            #                 stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
            #
            # # Play a wave file directly
            # self.play_wav('files/response.wav')

        if platform.machine() == 'mips':
            os.system('madplay ' + 'files/response.mp3')
        else:
            os.system('ffplay -autoexit -nodisp -loglevel quiet ' + 'files/response.mp3')

    def play_wav(self, file, timeout=None, stop_event=None, repeat=False):
        """ Play a wave file using PyAudio. The file must be specified as a path.

        :param file: path to wave file
        """
        # Open wave wave
        with wave.open(file, 'rb') as wf:
            # Create pyaudio stream
            stream = self.pyaudio_instance.open(
                        format=self.pyaudio_instance.get_format_from_width(wf.getsampwidth()),
                        channels=wf.getnchannels(),
                        rate=wf.getframerate(),
                        output=True)

            # Set chunk size for playback
            chunk = 1024

            # Get start time
            start_time = time.mktime(time.gmtime())

            end = False
            while not end:
                # Read first chunk of data
                data = wf.readframes(chunk)
                # Continue until there is no data left
                while len(data) > 0 and not end:
                    if timeout is not None and time.mktime(time.gmtime())-start_time > timeout:
                        end = True
                    if stop_event is not None and stop_event.is_set():
                        end = True
                    stream.write(data)
                    data = wf.readframes(chunk)
                if not repeat:
                    end = True
                else:
                    wf.rewind()

        # When done, stop stream and close
        stream.stop_stream()
        stream.close()
