Alexa
=====

To use Alexe Voice Service with ReSpeaker.


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
Alexa will be installed at the lasest firmware of ReSpeaker. If the command `alexa` is available, skip step 1.

1. Download alexa ipk and install it.

  ```
  cd /tmp
  wget https://github.com/respeaker/get_started_with_respeaker/raw/master/files/alexa_2016-12-16_ramips_24kec.ipk
  opkg install alexa_2016-12-16_ramips_24kec.ipk
  ```

2. Run `alexa` or `/etc/init.d/alexa start` to start Alexa Voice Service

  If got an error "IOError: [Errno -9996] Invalid input device (no default output device)", it may be alexa already runs in the background (`/etc/init.d/alexa stop` will stop it)

3. At the first time, you need to autherize the application.

  Connect ReSpeaker's Access Point, go to [http://192.168.100.1:3000]([http://192.168.100.1:3000) and tt will redirect you to Amazon to sign up or login in.

4. Run `python alexa.py` to interact with Alexa.


### Credits
+ [AlexaPi](https://github.com/sammachin/AlexaPi).
