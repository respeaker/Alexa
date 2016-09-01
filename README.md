Alexa
=====

Run Alexe Voice Service on ReSpeaker (OpenWrt), other Linux, Windows and Mac. It's based on [AlexaPi](https://github.com/sammachin/AlexaPi).

### Getting Started

1. [Register for an Amazon Developer Account](https://github.com/alexa/alexa-avs-raspberry-pi#31---register-for-a-free-amazon-developer-account).
2. Rename `example_creds.py` to `creds.py` and fill `ProductID`, `Security_Profile_Description`, `Security_Profile_ID`, `Client_ID` and `Client_Secret` with your Alexa device information.
3. Run `setup.sh` (or `setup_on_openwrt.sh` when using ReSpeaker) to get [ReSpeaker Python Library]() and other python libraries.
4. Run `python auth_web.py` and open http://127.0.0.1:5000 (replace 127.0.0.1 with ReSpeker's IP when using ReSpeaker).
5. Run `python alexa.py` to interact with Alexa.
