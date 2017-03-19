
import helper
import authorization
import alexa_device
from threading import Thread, Event
import time
import logging
import signal

logging.basicConfig(level=logging.INFO)


def main():
    # Load configuration file (contains the authorization for the user and device information)
    config = helper.read_dict('config.dict')
    # Check for authorization, if none, initialize and ask user to go to a website for authorization.
    if 'refresh_token' not in config:
        print("Please go to http://localhost:5000")
        authorization.get_authorization()
        config = helper.read_dict('config.dict')

    # Create alexa device
    alexa = alexa_device.AlexaDevice(config)
    quit_event = Event()

    def signal_handler(signum, frame):
        quit_event.set()
        alexa.close()

    signal.signal(signal.SIGINT, signal_handler)

    while not quit_event.is_set():
        if alexa.alexa_audio_instance.mic.wakeup(keyword='alexa'):
            print('Wake up')
            try:
                alexa.user_initiate_audio()
            except Exception as e:
                logging.warning(e.message)


if __name__ == '__main__':
    main()
