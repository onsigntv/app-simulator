import json
import logging
import pathlib
import re
import subprocess
import time
from urllib import request


logger = logging.getLogger("onsigntv.utils")


def safe_function(
    if_except_return=None, if_except_call=None, except_list=(Exception), log_to=None
):
    """Makes a function exception safe, wrapping it on a try..except block.

    Sometimes exceptions can be caught just to provide a default, and this
    is the use case for this decorator.
    """

    def _inner_decorator(func):
        def wrapped(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except except_list:
                if log_to:
                    log_to.warning("exception on %s", func.__name__, exc_info=True)

                if if_except_call is not None:
                    return if_except_call(*args, **kwargs)

                return if_except_return

        # Make this decorator well behaved.
        wrapped.__name__ = func.__name__
        wrapped.__doc__ = func.__doc__
        wrapped.__dict__.update(func.__dict__)
        return wrapped

    return _inner_decorator


@safe_function(if_except_return={})
def safe_probe_metadata(obj):
    metadata = {}
    ext = pathlib.Path(obj).suffix

    try:
        output = subprocess.run(
            [
                "ffprobe",
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_format",
                "-show_streams",
                obj,
            ],
            capture_output=True,
            timeout=5.0,
            check=True,
            text=True,
        ).stdout
    except subprocess.CalledProcessError:
        metadata["duration"] = 0
        metadata["duration_exact"] = 0
        metadata["height"] = 0
        metadata["width"] = 0

    else:
        output = json.loads(output)
        metadata["duration"] = int(float(output["format"]["duration"]))
        metadata["duration_exact"] = output["format"]["duration"]

        for stream in output["streams"]:
            if stream.get("codec_type") == "video":
                metadata["height"] = stream["height"]
                metadata["width"] = stream["width"]

            elif stream.get("codec_type") == "audio":
                metadata["audio_codec"] = stream["codec_long_name"]

    if ext == ".mp3":
        try:
            from mutagen import id3

            for key, value in id3.ID3(obj).items():
                if key == "TDRC":
                    metadata["id3_year"] = value.text[0]
                elif key == "TIT2":
                    metadata["id3_title"] = value.text[0]
                elif key == "TPE1":
                    metadata["id3_artist"] = value.text[0]
                elif key == "TALB":
                    metadata["id3_album"] = value.text[0]
                elif key == "TCOM":
                    metadata["id3_composer"] = value.text[0]
                elif key == "TCON":
                    metadata["id3_genre"] = value.text[0]

        except ImportError:
            logger.warning("install mutagen if you want have support to audio type")

            metadata["id3_year"] = ""
            metadata["id3_title"] = ""
            metadata["id3_artist"] = ""
            metadata["id3_album"] = ""
            metadata["id3_composer"] = ""
            metadata["id3_genre"] = ""

    return metadata


def formdata_to_json(data):
    _data = dict(data)
    for key, value in data.items():
        if isinstance(value, dict) and "filename" in value:
            _data[key] = value["filename"]

    return json.dumps(_data)


def inject_script_into_html(html, data):
    script = """
<script type="text/javascript">
  (function() {
    var source = null;
    function createSource() {
      if (source) source.close();
      source = new EventSource("/.change_notification");
      source.onmessage = function() {
        var formEl = document.createElement('form');
        formEl.method = 'POST'
        formEl.enctype = 'multipart/form-data';
        for (var [key, val] of Object.entries(%s)) {
          var i = document.createElement('input');
          i.hidden = true;
          i.name = key;
          i.value = val;
          formEl.appendChild(i);
        }
        document.body.appendChild(formEl);
        formEl.requestSubmit();
      };
      source.onerror = function() { window.setTimeout(createSource, 1000); };
    }
    createSource();
  })();
</script>
    """ % formdata_to_json(
        data
    )

    if "<head" in html:
        match_list = re.findall("<head[\\s\\S]*?>", html)
        split_val = match_list[0]
    elif "<style" in html:
        match_list = re.findall("<style[\\s\\S]+?</style>", html)
        split_val = match_list[-1]
    elif "<meta" in html:
        match_list = re.findall("<meta[\\s\\S]+?>", html)
        split_val = match_list[-1]
    else:
        match_list = re.findall("<title[\\s\\S]+?</title>", html)
        split_val = match_list[-1]

    parts = html.split(split_val)
    html_new = parts[0] + split_val + script + parts[1]

    return html_new


class SimpleResponse:
    __slots__ = ("url", "data", "status", "headers")

    def __init__(self, url, data, status, headers):
        self.url = url
        self.data = data
        self.status = status
        self.headers = headers

    def __repr__(self):
        return "<Response {}, data={}>".format(self.url, self.data)

    def json(self):
        return json.loads(self.data)


_url_cache = {}


def get_url(url):
    if url in _url_cache:
        ts, s_resp = _url_cache[url]
        if time.time() - ts < 30 * 60:
            return s_resp

    res = request.urlopen(
        request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4139.2 Safari/537.36"
            },
        )
    )

    if res.code >= 400:
        raise ValueError("Invalid request")

    s_resp = SimpleResponse(
        res.url, res.read(), res.code, {k.lower(): v for k, v in res.getheaders()}
    )

    _url_cache[url] = (time.time(), s_resp)

    return s_resp
