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

        if key == "_playback_info":
            try:
                value = json.loads(value)
            except Exception:
                value = {}

            _data[key] = json.dumps(value)

    return json.dumps(_data)


def inject_script_into_html(html, sdk_tag, form_data, attrs, js_app_config):
    attrs_info = {}
    for name, attr in attrs:
        attr_info = {
            "type": attr["type"],
            "mode": attr["mode"],
        }
        if form_data.get("_attr_" + name):
            attr_info["playerName"] = attr["label"]

        attrs_info[name] = attr_info

    app_config = ""
    if js_app_config:
        app_config = f"window.appConfig = {json.dumps(js_app_config)};"

    script = """
<script type="text/javascript">
  window.__appFormData = {form_data};
  window.__appAttrs = {attrs_info};
  {app_config}
  {script}
</script>
    """.format(
        form_data=formdata_to_json(form_data),
        attrs_info=json.dumps(attrs_info or None),
        app_config=app_config,
        script=re.sub(
            r"\s+", " ", get_resource_string("static/shim/signage.js").replace("\n", "")
        ),
    )

    if sdk_tag in html:
        html = html.replace(sdk_tag, script, 1)
    elif re.search(r"<\s*script", html, re.I):
        match = re.search(r"<\s*script", html, re.I)
        html = html[: match.start()] + script + html[match.start() :]

    return html


_resource_manager = None
_resource_provider = None


def get_resource_string(path):
    global _resource_manager
    global _resource_provider

    if _resource_manager is None or _resource_provider is None:
        from pkg_resources import ResourceManager, get_provider

        _resource_manager = ResourceManager()
        _resource_provider = get_provider("app_simulator")

    return _resource_provider.get_resource_string(_resource_manager, path).decode(
        "utf-8"
    )


class SimpleResponse:
    __slots__ = ("url", "data", "status", "headers")

    def __init__(self, url, data, status, headers):
        self.url = url
        self.data = data
        self.status = status
        self.headers = headers

    def __repr__(self):
        return f"<Response {self.url}, data={self.data}>"

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
