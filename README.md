Alexa
=====

To use Alexe Voice Service with ReSpeaker. It's based on [AlexaPi](https://github.com/sammachin/AlexaPi).

### Requirements
+ CherryPy
+ Requests
+ PyAudio
+ [ReSpeaker python library](https://github.com/respeaker/respeaker_python_library)
+ webrtcvad - for Voice Activity Detection, available on ReSpeaker by default
+ PocketSphinx - for Keyword Spotting, available on ReSpeaker
+ ffplay, part of [ffmpeg](https://ffmpeg.org/download.html)




### On Ubuntu

1. [Register for an Amazon Developer Account](https://github.com/alexa/alexa-avs-raspberry-pi#61---register-your-product-and-create-a-security-profile).
2. Run `git clone https://github.com/respeaker/Alexa.git && cd Alexa`
3. Rename `example_creds.py` to `creds.py` and fill `ProductID`, `Security_Profile_Description`, `Security_Profile_ID`, `Client_ID` and `Client_Secret` with your Alexa device information.
4. Run `sudo pip install cherrypy requests pyaudio webrtcvad pocketsphinx respeaker` to get required python packages.
5. Run `python auth_web.py` and open [http://localhost:3000](http://localhost:3000)

    It will redirect you to Amazon to sign in.

6. Run `python alexa.py` to interact with Alexa.


### On ReSpeaker

The respeaker python library requires 1.2M storage.
If the on-board flash doesn't have enough space,
we can use virtualenv to install python packages on a SD card.
If you get it work on Ubuntu, you can use the previous `creds.py` and skip step 3 and step 5.

1. [Register for an Amazon Developer Account](https://github.com/alexa/alexa-avs-raspberry-pi#61---register-your-product-and-create-a-security-profile). Make sure Web Settings look like the picture:

    ![](doc/alexa_web_settings.png)

2. Run `cd /Media/SD-P1 && git clone https://github.com/respeaker/Alexa.git && cd Alexa`
3. Rename `example_creds.py` to `creds.py` and fill `ProductID`, `Security_Profile_Description`, `Security_Profile_ID`, `Client_ID` and `Client_Secret` with your Alexa device information.
4. Run `pip install cherrypy requests respeaker` to get required python packages.
5. Run `python auth_web.py`, connect to ReSpeaker's AP and open http://192.168.100.1:3000

    It will redirect you to Amazon to sign in.

6. Run `python alexa.py` to interact with Alexa.



