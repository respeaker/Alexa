Alexa
=====

Run Alexe Voice Service on ReSpeaker (OpenWrt), other Linux, Windows and Mac. It's based on [AlexaPi](https://github.com/sammachin/AlexaPi).

### Requirements
+ cherrypy
+ Requests
+ webrtcvad - for Voice Activity Detection, available on ReSpeaker by default
+ pocketsphinx - for Keyword Spotting, available on ReSpeaker

### Getting Started on ReSpeaker

1. [Register for an Amazon Developer Account](https://github.com/alexa/alexa-avs-raspberry-pi#61---register-your-product-and-create-a-security-profile). Make sure Web Settings look like the picture:

    ![](doc/alexa_web_settings.png)
  
2. Rename `example_creds.py` to `creds.py` and fill `ProductID`, `Security_Profile_Description`, `Security_Profile_ID`, `Client_ID` and `Client_Secret` with your Alexa device information.
3. Run `setup_on_openwrt.sh` to get required python libraries.

    The script will download ReSpeaker python library, Requests library and CherryPy library

4. Run `python auth_web.py`, connect to ReSpeaker's AP and open http://192.168.100.1:3000

    It will redirect you to Amazon to sign in.

5. Run `python alexa.py` to interact with Alexa.

### On  desktop Linux, Windows or Mac

1. [Register for an Amazon Developer Account](https://github.com/alexa/alexa-avs-raspberry-pi#61---register-your-product-and-create-a-security-profile).
2. Rename `example_creds.py` to `creds.py` and fill `ProductID`, `Security_Profile_Description`, `Security_Profile_ID`, `Client_ID` and `Client_Secret` with your Alexa device information.
3. Run `setup.sh` to get required python libraries.

    The script will download [ReSpeaker python library](https://github.com/respeaker/respeaker_python_library), [pocketsphinx](https://github.com/bambocher/pocketsphinx-python), [webrtcvad python library](https://github.com/wiseman/py-webrtcvad), Requests library and CherryPy library.
    Note: Swig and compile toolchain is required to build pocketsphinx and webrtcvad.

4. Run `python auth_web.py`, connect to ReSpeaker's AP and open http://localhost:3000

    It will redirect you to Amazon to sign in.

5. Run `python alexa.py` to interact with Alexa.

