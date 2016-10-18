import os
import re
import time
import json
import platform
from threading import Event, Thread
import requests

from creds import Client_ID, Client_Secret, refresh_token
from respeaker import Microphone


response_mp3 = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'response.mp3')
token = None


# Get Alexa Token
def get_token():
    global token

    if token:
        return token
    else:
        payload = {
            "client_id": Client_ID,
            "client_secret": Client_Secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
        url = "https://api.amazon.com/auth/o2/token"
        r = requests.post(url, data=payload)
        resp = json.loads(r.text)
        token = resp['access_token']

        # line = '\ntoken = "{}"\n'.format(token)
        # with open("creds.py", 'a') as f:
        #     f.write(line)

        return token


def generate(audio, boundary):
    print('sending data')
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
    print('done')


def alexa(audio):
    global response_mp3

    url = 'https://access-alexa-na.amazon.com/v1/avs/speechrecognizer/recognize'
    # headers = {'Authorization': 'Bearer %s' % gettoken()}

    boundary = 'this-is-a-boundary'
    headers = {
        'Authorization': 'Bearer %s' % get_token(),
        'Content-Type': 'multipart/form-data; boundary=%s' % boundary,
        'Transfer-Encoding': 'chunked'
    }

    print('Post')
    r = requests.post(url, headers=headers, data=generate(audio, boundary), timeout=60)
    print 'Reading response'

    if r.status_code == 200:
        print "Debug: Alexa provided a response"
        for v in r.headers['content-type'].split(";"):
            if re.match('.*boundary.*', v):
                boundary = v.split("=")[1]
        data = r.content.split(boundary)
        for d in data:
            if len(d) >= 1024:
                audio = d.split('\r\n\r\n')[1].rstrip('--')

                # Write response audio to response.mp3 may or may not be played later
                with open(response_mp3, 'wb') as f:
                    print('Save response audio to %s' % response_mp3)
                    f.write(audio)
                    f.close()
                    if platform.machine() == 'mips':
                        os.system('madplay -o wave:- ' + response_mp3 + ' | aplay -M')
                    else:
                        os.system('mpg123 ' + response_mp3)
    else:
        print "Debug: Alexa threw an error with code: ", r.status_code


def task(quit_event):
    mic = Microphone(quit_event=quit_event)

    while not quit_event.is_set():
        if mic.wakeup(keyword='alexa'):
            print('wakeup')
            data = mic.listen()
            try:
                alexa(data)
            except Exception as e:
                print('Something wrong when connecting to Alexa Voice Service: %s' % e.message)
                pass

    mic.close()


def main():
    quit_event = Event()
    thread = Thread(target=task, args=(quit_event,))
    thread.start()
    while True:
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            print('Quit')
            quit_event.set()
            break

    thread.join()

if __name__ == '__main__':
    main()
