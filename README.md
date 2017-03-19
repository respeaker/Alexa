# Alexa II

>Note: It is at very early stage and is not ready for respeaker core, but you can test it on Windows or Ubuntu.

This branch based on [python-alexa-voice-service](https://github.com/nicholasjconn/python-alexa-voice-service) is a Python implementation of Amazon's Alexa Voice Service (AVS). The goal of this project is to create cross-platform example Alexa device that is completely compatible with the current AVS API (v20160207). This is a work in progress.

## Requirements
- [Python 2.7](https://www.python.org/)
	- [cherrypy](http://www.cherrypy.org/)
    - [requests](http://docs.python-requests.org/en/master/)
    - [hyper](https://github.com/xiongyihui/hyper) (a forked version)
	- [pyaudio](https://people.csail.mit.edu/hubert/pyaudio/)
	- [respeaker](https://github.com/respeaker/respeaker_python_library)
- [ffmpeg](https://ffmpeg.org/)

## Getting Started

Install the necessary requirements and clone the repository.

``
pip install https://github.com/xiongyihui/hyper/archive/development.zip
git clone https://github.com/reapeaker/alexa.git
git checkout v2
cd python-alexa-voice-service
``

Follow the directions from Amazon on how to get your Client ID, Client Secret, and ProductID (parts of Chapter 3 and Chapter 6).

[https://github.com/amzn/alexa-avs-raspberry-pi](https://github.com/amzn/alexa-avs-raspberry-pi)

Rename config_example.dict to config.dict. Then open the file and update the Client ID, Client Secret, and ProductID values to your own values

Run the main.py script. If you run into any errors, chances are that you have missed one of the requirements.

``
python main.py
``

## Using the Code

This is a command line based program. You will be receive notices and prompts via the command line. Start a voice command by pressing enter. The software is not always listening (I am waiting on a response from Amazon before enabling this), so a button press is required to active the microphone.

When you would like to close the program, press 'q' and then enter.

Errors and other text may be printed out if anything goes wrong. This is a work in progress.

#### Example Alexa Commands
* "What time is it?"
* "Set an alarm."
* "Where am I?"
* "What is the weather tomorrow?"
* "Are you a robot?"

If you have the Wink hub or any other supported home automation devices, you can connect them via the [Android Alexa App](https://play.google.com/store/apps/details?id=com.amazon.dee.app&hl=en). Once connected, you can say things like "turn on bedroom lights" or "set bedroom lights to 50%".

Have fun!

## Cross-Platform

This code has only been tested on Windows. This project will eventually support Linux and hopefully OS X. The final goal is for this project to work out of the box on a Raspberry Pi.

## Alexa Voice Service

The following link has all of the information needed to understand the Alexa Voice Service API:

[https://developer.amazon.com/public/solutions/alexa/alexa-voice-service/content/avs-api-overview](https://developer.amazon.com/public/solutions/alexa/alexa-voice-service/content/avs-api-overview)

## Bugs

If you run into any bugs, please create an issue on GitHub. Don't hesitate to submit bugs for the README.md as well!

## Contributing

Feel free contribute to the code!

## License
MIT - [See LICENSE](./license.txt)


## Future Work
Please feel free to add functionality or fix any bugs that you find.
Currently, only the SpeechRecognizer and SpeechSynthesizer interfaces are supported. More will be added in the near future.

## Credits
+ https://github.com/nicholasjconn/python-alexa-voice-service