
import helper
import time
import threading
import traceback

import logging

import alexa_audio
import alexa_communication

__author__ = "NJC"
__license__ = "MIT"
__version__ = "0.2"


logger = logging.getLogger(__file__)


class AlarmManager:
    """ This object manages all alarms and timers sent via the Alerts interface.
    """
    def __init__(self, audio):
        """ Initializes the AlarmManager object. Requires an AlexaAudio object to sound alarms. The
            AlexaCommunication object must be specified in a separate function call.

        :param audio: AlexaAudio object instance
        """
        self.alexa_device = None
        self.audio = audio
        self.alerts = {}

    def set_alexa_device(self, alexa_device):
        """ Set's the current AlexaDevice object.

        :param alexa_device: AlexaDevice object
        """
        self.alexa_device = alexa_device

    def set_alert(self, token, alert_type, scheduled_time):
        """ Called when a new alarm is to be added (from SetAlert directive).

        :param token: token for the alarm
        :param alert_type: alert type from the API
        :param scheduled_time: scheduled time (UTC time as ISO string)
        :return: boolean indicating success or failure
        """
        try:
            s_time = helper.get_timestamp_from_iso(scheduled_time)
            time_difference = s_time-time.time()
            print(time_difference)
            timer_thread = threading.Timer(time_difference, self.start_alert, args=(token,))
            timer_thread.start()
            stop_event = threading.Event()
            self.alerts[token] = {
                'type': alert_type,
                'scheduled_time': scheduled_time,
                'timer_thread': timer_thread,
                'stop_event': stop_event,
                'is_active': False
            }
            logger.info("Alarm set successfully.")
        except:
            logger.warning("Error setting alarm")
            return False
        return True

    def delete_alert(self, token):
        """ Called when an alarm is to be deleted (from DeleteAlert directive).

        :param token: token for the alarm
        :param alert_type: alert type from the API
        :param scheduled_time: scheduled time (UTC time as ISO string)
        :return: boolean indicating success or failure
        """
        try:
            self.alerts[token]['timer_thread'].cancel()
            if self.alerts[token]['is_active']:
                print("Stopping alarm")
                self.alerts[token]['stop_event'].set()

                stream_id = self.alexa_device.alexa.send_event_alert_name('AlertStopped', token)
                # TODO combine get_and_process_reponse with alexa_send_event
                self.alexa_device.alexa.get_and_process_response(stream_id)
            del self.alerts[token]
            print("Alarm deleted")
            return True
        except:
            traceback.print_exc()
            print("Error deleting alarm")
            return False

    def get_alarm_context(self):
        """ Get the alert context dictionary.

        :return: dictionary containing alert context
        """
        tokens = self.alerts.keys()
        all_alerts = []
        active_alerts = []
        for token in tokens:
            alert = {
                'token': token,
                'type': self.alerts[token]['type'],
                'scheduledTime': self.alerts[token]['scheduled_time']
            }
            all_alerts.append(alert)
            if self.alerts[token]['is_active']:
                active_alerts.append(alert)

        context_alerts = {
            "header": {
                "namespace": "Alerts",
                "name": "AlertsState"
            },
            "payload": {
                "allAlerts": all_alerts,
                "activeAlerts": active_alerts
            }
        }
        return context_alerts

    def start_alert(self, token):
        """ Called as a thread when the alarm is started.

        :param token: token for active alarm
        """
        logger.info("Alarm started!")
        # This function is called by the scheduler
        # Be sure to delete the alert dictionary when done

        self.alerts[token]['is_active'] = True

        # Send alert started to alexa
        stream_id = self.alexa_device.alexa.send_event_alert_name('AlertStarted', token)
        self.alexa_device.alexa.get_and_process_response(stream_id)
        # If foreground
        if True:
            # Play in foreground for 30 seconds, unless stopped
            self.audio.play_wav('files/alarm.wav',
                                timeout=30, stop_event=self.alerts[token]['stop_event'], repeat=True)
            # Send status to alexa
            stream_id = self.alexa_device.alexa.send_event_alert_name('AlertEnteredForeground', token)
            self.alexa_device.alexa.get_and_process_response(stream_id)
        else:
            # Play quietly in background (or not at all
            # Send status to alexa
            stream_id = self.alexa_device.alexa.send_event_alert_name('AlertEnteredBackground', token)
            self.alexa_device.alexa.get_and_process_response(stream_id)

        # If alert still exists (would exist if alarm is not cancelled)
        if token in self.alerts:
            self.delete_alert(token)


class AlexaDevice:
    """ This object is the AlexaDevice. It uses the AlexaCommunication and AlexaAudio object. The goal is to provide a
        highly abstract yet simple interface for Amazon's Alexa Voice Service (AVS).

    """
    def __init__(self, alexa_config):
        """ Initialize the AlexaDevice using the config dictionary. The config dictionary must containing the
            Client_ID, Client_Secret, and refresh_token.

        :param alexa_config: config dictionary specific to the device
        """
        self.alexa_audio_instance = alexa_audio.AlexaAudio()
        self.alarm_manager = AlarmManager(self.alexa_audio_instance)
        self.config = alexa_config
        self.alexa = None

        self.device_stop_event = threading.Event()
        self.device_thread = threading.Thread(target=self.device_thread_function)
        self.device_thread.start()

    def device_thread_function(self):
        """ The main thread that waits until the the device is closed. It contains the AlexaConnection object and
            starts any necessary threads for user input.

            Eventually this function will incorporate any device specific functionality.
        """
        # TODO make sure this function can be called again, not during instantiation

        # Start connection and save
        self.alexa = alexa_communication.AlexaConnection(self.config, context_handle=self.get_context,
                                                         process_response_handle=self.process_response)
        self.alarm_manager.set_alexa_device(self)

        # Connection loop
        while not self.device_stop_event.is_set():
            # Do any device related things here
            time.sleep(0.1)
            pass

        # When complete (stop event is same as user_input_thread
        # Close the alexa connection and set stop event
        self.alexa.close()
        self.device_stop_event.set()
        print("Closing Thread")
        # TODO If anything went wrong, and stop event is not set, start new thread automatically

    def user_initiate_audio(self):
        audio = self.alexa_audio_instance.get_audio()
        if audio is None:
            return

        # TODO make it so the response can be interrupted by user if desired (maybe start a thread)
        stream_id = self.alexa.start_recognize_event(audio)
        self.alexa.get_and_process_response(stream_id)

    def get_context(self):
        """ Returns the current context of the AlexaDevice.

        See https://developer.amazon.com/public/solutions/alexa/alexa-voice-service/reference/context for more
        information.

        :return: context dictionary
        """
        # TODO eventually make this dynamic and actually reflect the device's state
        # Get context for the device (basically a status)
        context = []
        playback_state = {
            "header": {
                "namespace": "AudioPlayer",
                "name": "PlaybackState"
            },
            "payload": {
                "token": "audio_token",
                "offsetInMilliseconds": 0,
                "playerActivity": "IDLE"
            }
        }

        alerts_state = self.alarm_manager.get_alarm_context()

        volume_state = {
            "header": {
                "namespace": "Speaker",
                "name": "VolumeState"
            },
            "payload": {
                "volume": 100,
                "muted": False
            }
        }

        speech_state = {
                            "header": {
                                "namespace": "SpeechSynthesizer",
                                "name": "SpeechState"
                            },
                            "payload": {
                                "token": "{{STRING}}",
                                "offsetInMilliseconds": 0,
                                "playerActivity": "{{STRING}}"
                            }
                        }

        context.append(volume_state)
        context.append(alerts_state)
        return context

    def process_response(self, message):
        """ Called when a message is received from Alexa (either on the downchannel or as a response). This
            function will take actions based on the message recieved.

        :param message: message received from Alexa
        """
        # Loop through each message
        logger.info("%d messages received" % len(message['content']))

        # If there is no content in the message, throw error (nothing to parse)
        if 'content' not in message:
            raise KeyError("Content is not available.")
        # If there are more than one attachments, throw error (code currently can't handle this.
        # Not sure if this is even possible based on the AVS API.
        if len(message['attachment']) > 1:
            raise IndexError("Too many attachments (%d)" % len(message['attachment']))

        if message['attachment']:
            attachment = message['attachment'][0]
        else:
            attachment = None

        # print("%d messages received" % len(message['content']))
        # Loop through all content received
        for content in message['content']:
            header = content['directive']['header']

            logger.info('header: {}'.format(header))

            # Get the namespace from the header and call the correct process directive function
            namespace = header['namespace']
            if namespace == 'SpeechSynthesizer':
                self.process_directive_speech_synthesizer(content, attachment)
            elif namespace == 'SpeechRecognizer':
                self.process_directive_speech_recognizer(content, attachment)
            elif namespace == 'Alerts':
                self.process_directive_alerts(content, attachment)
            # Throw an error in case the namespace is not recognized.
            # This indicates new a process directive function needs to be added
            else:
                raise NameError("Namespace not recognized (%s)." % namespace)

    def process_directive_speech_synthesizer(self, content, attachment):
        """ Process a directive that belongs to the SpeechSynthesizer namespace.

        :param content: content dictionary (contains header and payload)
        :param attachment: attachment included with the content
        """
        header = content['directive']['header']
        payload = content['directive']['payload']

        # Get the name from the header
        name = header['name']

        # Process the SpeechSynthesizer.Speak directive
        if name == 'Speak':
            # Get token for current TTS object
            token = payload['token']
            audio_response = attachment

            # Set SpeechSynthesizer context state to "playing"
            # TODO capture state so that it can be used in context
            # Send SpeechStarted Event (with token)
            stream_id = self.alexa.send_event_speech_started(token)
            self.alexa.get_and_process_response(stream_id)
            # Play the mp3 file
            self.alexa_audio_instance.play_mp3(audio_response)
            # Send SpeechFinished Event (with token)
            stream_id = self.alexa.send_event_speech_finished(token)
            self.alexa.get_and_process_response(stream_id)
            # Set SpeechSynthesizer context state to "finished"
            # TODO capture state so that it can be used in context
        # Throw an error if the name is not recognized.
        # This indicates new a case needs to be added
        else:
            raise NameError("Name not recognized (%s)." % name)

    def process_directive_speech_recognizer(self, content, attachment):
        """ Process a directive that belongs to the SpeechRecognizer namespace. Attachment not used, but included
            to keep the same arguments as other process_directive functions.

        :param content: content dictionary (contains header and payload)
        :param attachment: attachment included with the content
        """
        header = content['directive']['header']
        payload = content['directive']['payload']

        # Get the name from the header
        name = header['name']

        # Process the SpeechRecognizer.ExpectSpeech directive
        if name == 'ExpectSpeech':
            # Get specific fields for expect speech
            dialog_request_id = header['dialogRequestId']
            timeout = payload['timeoutInMilliseconds']/1000

            # Get audio, as requested by Alexa (using the specified timeout)
            raw_audio = self.alexa_audio_instance.get_audio(timeout)
            # If raw_audio is none, the user did not respond or speak
            if raw_audio is None:
                # TODO add sounds to prompt the user to do something, rather than text
                print("Speech timeout.")
                # Send an event to let Alexa know that the user did not respond
                stream_id = self.alexa.send_event_expect_speech_timed_out()
                self.alexa.get_and_process_response(stream_id)
                return

            # Send audio captured (start_recognize_event) using old dialog_request_id and then process reponse
            stream_id = self.alexa.start_recognize_event(raw_audio, dialog_request_id=dialog_request_id)
            self.alexa.get_and_process_response(stream_id)
        elif name == 'StopCapture':
            # TODO find out what this means, it is not in the API.
            pass
        # Throw an error if the name is not recognized.
        # This indicates new a case needs to be added
        else:
            raise NameError("Name not recognized (%s)." % name)

    def process_directive_alerts(self, content, attachment):
        """ Process a directive that belongs to the Alert namespace. Attachment not used, but included
            to keep the same arguments as other process_directive functions.

        :param content: content dictionary (contains header and payload)
        :param attachment: attachment included with the content
        """
        header = content['directive']['header']
        payload = content['directive']['payload']

        # Get the name from the header
        name = header['name']
        token = payload['token']

        if name == 'SetAlert':
            is_set = self.alarm_manager.set_alert(
                token,
                payload['type'],
                payload['scheduledTime']
            )
            # TODO move event sending to Alert object
            if is_set:
                stream_id = self.alexa.send_event_alert_name('SetAlertSucceeded', token)
            else:
                stream_id = self.alexa.send_event_alert_name('SetAlertFailed', token)
            self.alexa.get_and_process_response(stream_id)
        elif name == 'DeleteAlert':
            is_deleted = self.alarm_manager.delete_alert(token)
            if is_deleted:
                stream_id = self.alexa.send_event_alert_name('DeleteAlertSucceeded', token)
            else:
                stream_id = self.alexa.send_event_alert_name('DeleteAlertFailed', token)
            self.alexa.get_and_process_response(stream_id)

    def close(self):
        """ Closes the AlexaDevice. Should be called before the program terminates.
        """
        self.device_stop_event.set()
        self.alexa_audio_instance.close()

    def wait_until_close(self):
        """ Waits until the user stops the AlexaDevice threads. This uses thread.join() to wait until the thread is
            terminated.
        """
        self.device_thread.join()
