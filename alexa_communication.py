
import types
import time
import calendar
import json
import requests
import threading
from hyper import HTTP20Connection
import logging

logger = logging.getLogger(__file__)

__author__ = "NJC"
__license__ = "MIT"


def read_from_downstream(boundary, data):
    """ This functions reads data from the raw downstream channel, and pulls out messages based on
        the specified boundary.

    :param boundary: boundary used in message
    :param data: current data in the  downchannel stream
    :return: (new_data, data) new_data contains a complete message, data contains any remaining data
    """
    # Find the last index that ends with boundary
    matching_indices = [n for n, chunk in enumerate(data) if chunk.endswith(boundary)]
    # If there are no matching indices, no new data
    if not matching_indices:
        return b'', data
    # Get last boundary location
    boundary_index = matching_indices[-1]

    # Get parse-able data and remove from data (not including boundary)
    new_data = data[:boundary_index+1]
    data = data[boundary_index+1:]
    return b''.join(new_data), data


def get_boundary_from_response(response):
    """ Parses the response header and returns the boundary.

    :param response: response containing the header that contains the boundary
    :return: a binary string of the boundary
    """
    # Read only the first value with key 'content-type' (duplicate keys are allowed)
    content = response.headers.pop('content-type')[0]
    # Find the start and end index of the boundary
    b_start = content.find(b'boundary=')
    b_end = content[b_start:].find(b';')
    # Separate out boundary
    if b_end == -1:
        # If the end point is not found, just go to the end of the content string
        boundary = content[b_start+9:]
    else:
        boundary = content[b_start+9:b_start+b_end]
    return boundary


def parse_response(response):
    """ This function parses the http/2 response into multiple parts before it
        is processed. The response is returned directly from the http2.request
        function. The stream should not be closed until this function call is
        completed.

    :param response: the hyper.HTTP20Response object
    :return: message dictionary, which contains 'content' and 'attachment' lists
    """
    boundary = get_boundary_from_response(response)

    # Read the data from the response
    data = response.read()

    # Returned the resulting message after parsing data
    return parse_data(data, boundary)

def split_message(data, boundary):
    """ Split the message into it separate parts based on the boundary.

    :param data: raw message data
    :param boundary: boundary used in message
    :return: message parts, that were separated by boundary
    """
    # Split the data into message parts using the boundary
    message_parts = data.split(b'--' + boundary)
    # Remove empty messages (that contain only '--' or '--\r\n'
    message_parts = [p for p in message_parts
                     if p != b'--' and p != b'--\r\n' and len(p) != 0 and p != b'\r\n' and p != '\r\n--']
    return message_parts


def parse_data(data, boundary):
    """ The function parses tha actual data that was read form the response. All
        that is needed in addition to the data, is the boundary specified in the
        response header.

    :param data:
    :param boundary:
    :return: message dictionary, which contains 'content' and 'attachment' lists
    """
    # Split up data using the boundary into message parts
    message_parts = split_message(data, boundary)

    # Initialize message dictionary
    message = dict()
    # Set content and attachment keys to empty lists
    message['content'] = []
    message['attachment'] = []
    # For each message part
    for part in message_parts:
        # Split based on blank line, this separates header and content
        blank_line_start = part.find(b'\r\n\r\n')
        # If there are more than 2 chunks, throw an error (not sure if this is 100% correct)
        if blank_line_start < 0:
            raise NameError("Not find blank line! ({})".format(part))
        # The first part is the header, the second is content. Strip both of white spaces.
        message_header = part[:blank_line_start].strip()
        message_content = part[(blank_line_start + 4):].strip()

        # Find start and stop of content-type
        content_type_start = message_header.find(b'Content-Type: ')+14
        content_type_end = message_header[content_type_start:].find(b'\r\n')
        # If no end index was found, just go to the end
        if content_type_end == -1:
            content_type = message_header[content_type_start:]
        else:
            content_type = message_header[content_type_start:content_type_start+content_type_end]

        # Check the content type, should be json or octet
        if content_type == b'application/json; charset=UTF-8' or content_type == b'application/json':
            # If JSON, add to content
            message['content'].append(json.loads(message_content.decode()))
        elif content_type == b'application/octet-stream':
            # If octet stream, add to attachment
            message['attachment'].append(message_content)
        else:
            raise NameError("Content type not recognized (%s)" % content_type.decode())

    return message


class AlexaConnection:
    """ This object manages the connection to the alexa voice services. Any communication
        related functions should be added to this object.
    """
    def __init__(self, config, context_handle, process_response_handle, boundary='this-is-my-boundary'):
        """ Initialize the AlexaConnection. Requires configuration values and a context
            function handle. Boundary is an optional argument.

        :param config: a configuration dictionary containing the Client_ID, Client_Secret,
                       and refresh_token.
        :param context_handle: this is a pointer to the function that can supply the
                               device's context. See AVS context docs for more info.
        :param boundary: (optional) the boundary used to separate header and context in
                         each message

            Related links:
                https://developer.amazon.com/public/solutions/alexa/alexa-voice-service/reference/context

        """
        # Authentication and device identification configuration variables
        self.latest_token = None
        self.latest_token_time = None
        self.client_id = config['Client_ID']
        self.client_secret = config['Client_Secret']
        self.refresh_token = config['refresh_token']

        # Fields used to generate the actual request
        self.url = 'avs-alexa-na.amazon.com'
        self.boundary = boundary
        self.context_handle = context_handle
        # Seconds since epoch time when connection was created (used for message and dialog ID)
        self.start_time = calendar.timegm(time.gmtime())
        self.message_counter = 0
        self.dialog_counter = 0

        # Thread related variables
        self.lock = threading.Lock()
        self.thread_stop_event = threading.Event()
        self.process_response_handle = process_response_handle

        # Calls the function to initialize the alexa connection
        self.init_connection()

    def init_connection(self):
        """ Opens and maintains the connection with AVS. This starts the thread that runs
            for the duration of the object's life. Sends required requests to initialize
            connection correctly. This should be called anytime the connection needs to be
            reestablished.

        """
        # Open connection
        self.connection = HTTP20Connection(self.url, port=443, secure=True, force_proto="h2", enable_push=True)

        # First start downstream
        self.start_downstream()

        # Send sync state message (required)
        header = {'namespace': "System", 'name': "SynchronizeState"}
        stream_id = self.send_event(header)
        # Manually handle this response for now
        data = self.get_response(stream_id)
        # Should be 204 response (no content)
        if data.status != 204:
            print("PUSH" + str(data.read()))
            raise NameError("Bad status (%s)" % data.status)

        # Start ping thread
        ping_thread = threading.Thread(target=self.ping_thread)
        ping_thread.start()

    def start_downstream(self, lock=False):
        """ Starts the downstream channel thread. Lock should only be True if this function is
            called from a thread object.

        :param lock: boolean indicating if locking should be used
        """
        # Start by sending a "GET" /directives to open downchannel stream
        self.downstream_id = self.send_request('GET', '/directives')
        self.downstream_response = self.get_response(self.downstream_id)
        if self.downstream_response.status != 200:
            logger.warning(self.downstream_response.read())
            raise NameError("Bad status (%s)" % self.downstream_response.status)
        self.downstream_boundary = get_boundary_from_response(self.downstream_response)

        downstream_thread = threading.Thread(target=self.downstream_thread)
        downstream_thread.daemon = True
        downstream_thread.start()

    def downstream_thread(self):
        """ Downstream channel thread, which continuously monitors the stream for new data. Data
            is automatically parsed when an entire message is recieved.
        """

        logger.info('downstream boundary:{}'.format(self.downstream_boundary))

        down_stream = self.connection.streams[self.downstream_id]
        data = b''
        # Loop continuously waiting for stop event to be set
        while not self.thread_stop_event.is_set():
            if down_stream.data:
                data += b''.join(down_stream.data)
                down_stream.data = []
                logger.info('received data from downstream')
                logger.info(data)

                while True:
                    frame_end_position = data.find(b'--' + self.downstream_boundary)
                    if frame_end_position < 0:
                        break

                    frame = data[:frame_end_position - 4]
                    data = data[frame_end_position + len(self.downstream_boundary):]
                    if frame and frame != b'\r\n':
                        logger.info('downstream message: {} bytes'.format(len(frame)))
                        logger.info(frame)

                        try:
                            message = parse_data(frame, self.downstream_boundary)
                            # TODO somehow message ends up being empty
                            self.process_response_handle(message)
                        except Exception as e:
                            logger.warn(e.message)
            else:
                time.sleep(1)
                with self.lock:
                    self.connection._recv_cb()

            # frame = down_stream._read_one_frame()
            # logger.info('downstream:{}'.format(frame))


    def ping_thread(self):
        """ This functions runs as a thread, and will send a ping request every 4 minutes. This ping
            request is required to maintain a connection when the system is idle. If ping fails, the
            connection is reestablished using self.init_connection().
        """
        # Run and wait until ping thread is stopped
        while not self.thread_stop_event.is_set():
            # Try to send ping request, and get the response
            try:
                stream_id = self.send_request('GET', '/ping', path_version=False)
                data = self.get_response(stream_id)
            # If anything goes wrong, reset the connection
            except:
                print("Ping not successful.")
                self.connection.close()
                # Reinitialize the connection
                self.init_connection()
                break
            # If ping failed and did not result in correct response
            if data.status != 204:
                # Print data for debugging
                print(data.read())
                print("Ping not successful.")
                # Close connection
                self.connection.close()
                # Reinitialize the connection
                self.init_connection()
                break

            # Captures the current time before sleeping
            start_sleep_time = time.mktime(time.gmtime())
            # Loops every 1 second, to see if correct time has passed (4 minutes) or the stop event is set
            while not self.thread_stop_event.is_set() \
                    and (time.mktime(time.gmtime()) - start_sleep_time) < 4*60:
                time.sleep(1)
        print("Closing ping thread.")

    def close(self):
        """ Closes the connection and stops the ping thread.
        """
        self.thread_stop_event.set()
        with self.lock:
            self.connection.close()

    def get_unique_message_id(self):
        """ Gets a unique message_id for each message sent to the server. This is built from the connection's
            start time and the current message count. The format is as follows:

                njc_message_id-{start_time}-{message_count}

            where start_time is when the connection was opened (seconds since epoch) and message_count is the
            current message count for the instance.

        :return: a unique message_id
        """
        message_id = "njc_message_id-%d-%d" % (
            self.start_time, self.message_counter)
        # Increment message counter, to keep track of number of message_ids requested
        self.message_counter += 1
        return message_id

    def get_unique_dialog_id(self):
        """ Gets a unique dialog_id for each message sent to the server. This is built from the connection's
            start time and the current dialog count. The format is as follows:

                njc_dialog_id-{start_time}-{message_count}

            where start_time is when the connection was opened (seconds since epoch) and dialog_count is the
            current message count for the instance.

        :return: a unique dialog_id
        """
        message_id = "njc_dialog_id-%d-%d" % (
            self.start_time, self.dialog_counter)
        self.dialog_counter += 1
        return message_id

    def get_current_token(self):
        """ A token is required for authentication purposes on any request send to the AVS. This function uses the
            refresh_token provided by the configuration file to get an up to date communication token. This is
            necessary since the token expires every 3600 seconds. A new token is requested every 3570 seconds.

        :return: a valid token
        """
        # Get current time
        current_time = time.mktime(time.gmtime())
        # If there is no latest token, or the latest token is more than 3570 seconds old
        if (self.latest_token is None) or (current_time - self.latest_token_time) > 3570:
            payload = {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": self.refresh_token,
                "grant_type": "refresh_token",
            }
            # Request new token
            url = "https://api.amazon.com/auth/o2/token"
            r = requests.post(url, data=payload)
            resp = json.loads(r.text)
            token = resp['access_token']
            # Set new latest token and latest token time
            self.latest_token = token
            self.latest_token_time = current_time
        # Otherwise, just use latest token
        else:
            token = self.latest_token
        return token

    def send_request(self, method, path, body=None, path_version=True):
        """ Makes sending a request easy for the end-user. Most of the deails are hidden away inside of this function.
            All that is required is the method (e.g. 'GET') and the path. Optional arguments include the body and
            a flag path_version. The flag path_version allows a request to be sent to a pth that doesn't automatically
            include the current AVS version (e.g. when sending a ping request).

        :param method: string HTTP/2 method (e.g. 'GET')
        :param path: string of the desired path, by default is added to /v20160207 to get the full path
        :param body: (optional) message content to send
        :param path_version: (optional, default=True) flag that indicates if the version should be added to the full
                             path.
        :return: stream_id for the request
        """
        # Get headers
        headers = {
            'authorization': 'Bearer %s' % self.get_current_token(),
            'content-type': 'multipart/form-data; boundary=%s' % self.boundary
        }
        # If path_version is true, add version to path
        if path_version:
            path = '/v20160207' + path

        with self.lock:
            # Send actual request
            if body is not None:
                stream_id = self.connection.request(method, path, headers=headers, body=body)
            else:
                stream_id = self.connection.request(method, path, headers=headers)

        return stream_id

    def send_event(self, header, payload=None, audio=None):
        """ Send an event allows for a higher level of abstraction compared to send_request. The AVS message header
            (different from the HTTP/2 header) is the only required argument. Payload and audio (attachment) are both
            optional. This is used to easily sent events to the AVS.

        :param header: message header dictionary
        :param payload: message payload dictionary
        :param audio: raw binary string attachment
        :return: stream_id associated with the request
        """
        if payload is None:
            payload = {}
        # Add message ID to header
        header['messageId'] = self.get_unique_message_id()
        body_dict = {
            "context": self.context_handle(),
            "event": {
                "header": header,
                "payload": payload
            }
        }

        # Headers used to indicate if the content is JSON or audio
        start_json = '--%s\nContent-Disposition: form-data; name="metadata"\n' \
                     'Content-Type: application/json; charset=UTF-8\n\n' % self.boundary
        start_audio = '--%s\nContent-Disposition: form-data; name="audio"\n' \
                      'Content-Type: application/octet-stream\n\n' % self.boundary

        # Create body, and add json data
        body = (start_json + json.dumps(body_dict) + "--" + self.boundary).encode()

        if isinstance(audio, types.GeneratorType):
            def gen(prefix, audio_iterator, suffix):
                yield prefix
                for d in audio_iterator:
                    yield d
                yield suffix

            body += ("\n" + start_audio).encode()
            body = gen(body, audio, ("--" + self.boundary + "--").encode())

        else:
            # If raw audio exists, add that as well to the body strring
            if audio is not None:
                body += ("\n" + start_audio).encode() + audio
            # Add final boundary
            body += ("--" + self.boundary + "--").encode()

        # Send request and return stream_id
        return self.send_request('GET', '/events', body=body)

    def get_response(self, stream_id):
        """ Get a response from the HTTP/2 connection. Current version of hyper requires locking if threads are used.
            Otherwise, this function would not be needed.

        :param stream_id: stream_id used to get the response
        :return: the resulting response object (hyper.HTTP20Response)
        """
        with self.lock:
            result = self.connection.get_response(stream_id)
        return result

    def start_recognize_event(self, raw_audio, dialog_request_id=None):
        """ Starts a SpeechRecognizer.Recognize event. Requires a raw_audio argument. The optional dialog_request_id
            can be used to indicate that the recognize event is related to a previous one.The response is not read in
            this function.

        :param raw_audio: raw binary string audio attachment
        :param dialog_request_id: (optional) previously used dialog_request_id
        :return: the stream_id associated with the request
        """
        # If dialog_request_id is not specified, generate a new unique one
        if dialog_request_id is None:
            dialog_request_id = self.get_unique_dialog_id()

        # Set required payload and header
        payload = {
            "profile": "CLOSE_TALK",
            "format": "AUDIO_L16_RATE_16000_CHANNELS_1"
        }
        header = {
            'namespace': 'SpeechRecognizer',
            'name': 'Recognize',
            'dialogRequestId': dialog_request_id
        }
        # Send the event to alexa
        stream_id = self.send_event(header, payload=payload, audio=raw_audio)
        # Return
        return stream_id

    def get_and_process_response(self, stream_id):
        """ For a specified stream_id, get AVS's response and process it. The request must have been sent before calling
            this function.

        :param stream_id: stream_id used for the request
        """
        # Get the response
        response = self.get_response(stream_id)

        # If no content response, but things are OK, just return
        if response.status == 204:
            return

        # If not OK response status, throw error
        if response.status != 200:
            print(response.read())
            raise NameError("Bad status (%s)" % response.status)

        # Take the response, and parse it
        message = parse_response(response)
        self.process_response_handle(message)

    def send_event_speech_started(self, token):
        """ API specific function that sends the SpeechSynthesizer.SpeechStarted event. The response is not read
        in this function.

        :param token: token for the current Speak directive
        :return: the stream_id associated with the request
        """
        header = {
            'namespace': "SpeechSynthesizer",
            'name': "SpeechStarted"
        }
        payload = {'token': token}
        stream_id = self.send_event(header, payload=payload)
        return stream_id

    def send_event_speech_finished(self, token):
        """ API specific function that sends the SpeechSynthesizer.SpeechFinished event. The response is not read
        in this function.

        :param token: token for the current Speak directive
        :return: the stream_id associated with the request
        """
        header = {
            'namespace': "SpeechSynthesizer",
            'name': "SpeechFinished"
        }
        payload = {'token': token}
        stream_id = self.send_event(header, payload=payload)
        return stream_id

    def send_event_expect_speech_timed_out(self):
        """ API specific function that sends the SpeechRecognizer.ExpectSpeechTimedOut event. The response is not
            read in this function.

        :return: the stream_id associated with the request
        """
        header = {
            'namespace': 'SpeechRecognizer',
            'name': 'ExpectSpeechTimedOut'
        }
        stream_id = self.send_event(header)
        return stream_id

    def send_event_alert_name(self, name, token):
        """ API specific function that sends a event within the Alerts namespace. The response is not read in
            this function.

        :param name: name of event within the Alerts namesapce
        :param token: token for alert
        :return: the stream_id associated with the request
        """
        header = {
            'namespace': 'Alerts',
            'name': name
        }
        payload = {'token': token}
        stream_id = self.send_event(header, payload=payload)
        return stream_id
