import os
import re
import time
from monotonic import monotonic
import json
import platform
from threading import Event, Thread
import subprocess
import tempfile
import logging
from contextlib import closing

import requests

from creds import Client_ID, Client_Secret, refresh_token
from respeaker import Microphone


logging.basicConfig(level=logging.DEBUG)


def generate(audio, boundary):
    """
    Generate a iterator for chunked transfer-encoding request of Alexa Voice Service
    Args:
        audio: raw 16 bit LSB audio data
        boundary: boundary of multipart content

    Returns:

    """
    logging.debug('Start sending speech to Alexa Voice Service')
    chunk = '--%s\r\n' % boundary
    chunk += (
        'Content-Disposition: form-data; name="request"\r\n'
        'Content-Type: application/json; charset=UTF-8\r\n\r\n'
    )

    d = {
        "messageHeader": {
            "deviceContext": [{
                "name": "playbackState",
                "namespace": "AudioPlayer",
                "payload": {
                    "streamId": "",
                    "offsetInMilliseconds": "0",
                    "playerActivity": "IDLE"
                }
            }]
        },
        "messageBody": {
            "profile": "alexa-close-talk",
            "locale": "en-us",
            "format": "audio/L16; rate=16000; channels=1"
        }
    }

    yield chunk + json.dumps(d) + '\r\n'

    chunk = '--%s\r\n' % boundary
    chunk += (
        'Content-Disposition: form-data; name="audio"\r\n'
        'Content-Type: audio/L16; rate=16000; channels=1\r\n\r\n'
    )

    yield chunk

    for a in audio:
        yield a

    yield '--%s--\r\n' % boundary
    logging.debug('Finished sending speech to Alexa Voice Service')


class Alexa:
    """
    Provide Alexa Voice Service based on API v1
    """
    def __init__(self):
        self.access_token = None
        self.expire_time = None
        self.session = requests.Session()

    def get_token(self):
        if self.expire_time is None or monotonic() > self.expire_time:
            # get an access token using OAuth
            credential_url = "https://api.amazon.com/auth/o2/token"
            data = {
                "client_id": Client_ID,
                "client_secret": Client_Secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            }
            start_time = monotonic()
            r = self.session.post(credential_url, data=data)

            if r.status_code != 200:
                raise Exception("Failed to get token. HTTP status code {}".format(r.status_code))

            credentials = r.json()
            self.access_token = credentials["access_token"]
            self.expire_time = start_time + float(credentials["expires_in"])

        return self.access_token

    def recognize(self, audio):
        url = 'https://access-alexa-na.amazon.com/v1/avs/speechrecognizer/recognize'
        boundary = 'this-is-a-boundary'
        headers = {
            'Authorization': 'Bearer %s' % self.get_token(),
            'Content-Type': 'multipart/form-data; boundary=%s' % boundary,
            'Transfer-Encoding': 'chunked',
        }
        data = generate(audio, boundary)
        with closing(self.session.post(url, headers=headers, data=data, timeout=60, stream=True)) as r:
            if r.status_code != 200:
                raise Exception("Failed to recognize. HTTP status code {}".format(r.status_code))

            for v in r.headers['content-type'].split(";"):
                if re.match('.*boundary.*', v):
                    boundary = v.split("=")[1]

            if not boundary:
                logging.warn('No boundary is found in headers')
                return

            content = r.iter_content(chunk_size=4096)
            prefix = next(content)
            position = prefix.find(boundary, len(boundary))   # skip first boundary
            if position < 0:
                logging.warn('No boundary is found. Invalid format')
                return

            start = position + len(boundary) + 2              # boundary + cr + lf
            speech = prefix[start:]

            if platform.machine() == 'mips':
                command = 'madplay -o wave:- - | aplay -M'
            else:
                command = 'ffplay -autoexit -nodisp -'

            if 1:
                p = subprocess.Popen(command, stdin=subprocess.PIPE, shell=True)
                p.stdin.write(speech)
                for speech in content:
                    p.stdin.write(speech)

                p.stdin.close()
                p.wait()

            else:
                audio = prefix[start:]
                for c in content:
                    audio += c

                print(len(audio))
                with tempfile.SpooledTemporaryFile() as f:
                    f.write(audio)
                    f.seek(0)
                    p = subprocess.Popen(command, stdin=f, shell=True)
                    p.wait()


def task(quit_event):
    mic = Microphone(quit_event=quit_event)
    alexa = Alexa()

    while not quit_event.is_set():
        if mic.wakeup(keyword='alexa'):
            logging.debug('wakeup')
            data = mic.listen()
            try:
                alexa.recognize(data)
            except Exception as e:
                logging.warn(e.message)

    mic.close()


def main():
    quit_event = Event()
    thread = Thread(target=task, args=(quit_event,))
    thread.start()
    while True:
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            break

    quit_event.set()
    thread.join()
    logging.debug('Mission completed')


if __name__ == '__main__':
    main()
