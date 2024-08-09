# OnSign TV App Simulator

This simulator makes it easier to develop [OnSign TV Apps][1] by testing your configuration locally, without having to upload your HTML to OnSign TV every time you make a change while developing your app.


##  Installing

This simulator requires Python 3.8 and up. You can optionally install [ffmpeg][2] to determine the duration of video and audio files, but that is not needed unless you plan on using those attributes on your app. If you want ID3 information for audio files, you'll also need to install [mutagen][3].


### Installing from [PyPI](https://pypi.org/)

You can easily install it from PyPI:

```
pip install onsigntv-app-simulator
```


### Installing from this repo

You can also install it from this repo.

After cloning or downloading this repo, just enter the folder, create a new environment and install it.

```
python3 -m venv env
. env/bin/activate

python setup.py install
```


## Using the Simulator

After installing, running the simulator is very simple. The following command should be in your path:

```
onsigntv-app-simulator path/to/apps
```

If you don't specify a path, the app simulator will use your current working directory.

After running, open your browser and navigate to <http://127.0.01:8080/>. Click on your template file, fill in the options and start developing.

The app simulator will automatically track files – like images, CSS or Javascript - used by your app. If any file used changes the app will be automatically reloaded.

> **Heads Up!** If you installed the simulator in a `virtualenv` the command should be running with the `virtualenv` activated!

Report any issues you find [here][4] and keep on working on your apps!


[1]: https://github.com/onsigntv/apps
[2]: https://ffmpeg.org/download.html
[3]: https://mutagen.readthedocs.org
[4]: https://github.com/onsigntv/app-simulator/issues
