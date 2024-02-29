import colorsys
import datetime
import decimal
import hashlib
import json
import logging
import re
import threading
import urllib
import uuid
from collections import OrderedDict
from html.parser import HTMLParser

from jinja2 import Markup, StrictUndefined, Undefined, nodes
from jinja2.exceptions import TemplateSyntaxError
from jinja2.ext import GETTEXT_FUNCTIONS, Extension, extract_from_ast
from jinja2.sandbox import ImmutableSandboxedEnvironment

from . import samples, utils
from .fields import AVAILABLE_FONTS

_local = threading.local()

logger = logging.getLogger("onsigntv.app_config")

BANNED_NAMES = {
    "category",
    "id",
    "list",
    "media",
    "name",
    "widget_id",
    "widget_uid",
    "gettext",
    "ngettext",
    "signagewidgets",
}

KNOWN_TYPES = {
    "audio",
    "audiolist",
    "airport",
    "bool",
    "choice",
    "color",
    "currency",
    "date",
    "datetime",
    "float",
    "font",
    "googlesheet",
    "googlevoice",
    "instagram",
    "image",
    "imagelist",
    "location",
    "media",
    "multichoice",
    "multicurrency",
    "number",
    "paragraph",
    "richtext",
    "stock",
    "text",
    "time",
    "twitter",
    "url",
    "video",
    "webfeed",
    "xml",
}

JS_SUPPORTED_TYPES = {
    "bool",
    "choice",
    "color",
    "date",
    "datetime",
    "float",
    "multichoice",
    "number",
    "paragraph",
    "richtext",
    "text",
    "time",
    "url",
}

USER_TYPES = {"audio", "audiolist", "image", "imagelist", "media", "video"}

KNOWN_METAS = {
    "aspectratio",
    "audio",
    "audio-app",
    "caps",
    "compatibility",
    "description",
    "automation",
    "automation-app",
    "plugin",
    "plugin-app",
}

DATA_SOURCE_TYPES = {
    "boolean",
    "date",
    "datetime",
    "image",
    "integer",
    "media",
    "number",
    "text",
    "time",
    "url",
    "video",
}

ATTR_TYPES = {
    "number",
    "string",
    "numberarray",
    "stringarray",
}

ATTR_MODES = {"r", "w", "rw"}

FETCH_TEMPLATE = """
<script type="text/plain" id="%(id)s">%(content)s</script>
<script type="text/javascript">
  window.%(variable)s = document.getElementById('%(id)s').innerHTML.trim().replace(/&(lt|gt|#34|#39|amp);/g, function(match) {
    switch(match) {
      case '&lt;': return '<'; case '&gt;': return '>'; case '&#34;': return '"'; case '&#39;': return "'"; case '&amp;': return '&';
    }
  });
</script>
"""

SDK_TAG = "<!--__loadsdk__-->"
SDK_WARNING_EXPIRY_DATE = "2023-02-01"


class MediaItem:
    def __init__(self, path, name, tracker):
        self._path = path / name
        self._name = name
        self._tracker = tracker

    @property
    def name(self):
        return self._path.name

    @property
    def url(self):
        self._tracker(self._path)
        return urllib.parse.quote(self._name) + "?tracked=1"

    @property
    def width(self):
        from PIL import Image

        image = Image.open(self._path)
        return image.size[0]

    @property
    def height(self):
        from PIL import Image

        image = Image.open(self._path)
        return image.size[1]


class ConfigurableWidgetMedia:
    def __init__(self, path, tracker):
        logger.debug("register widget media: %s", path)
        self._path = path
        self._tracker = tracker
        self._subfiles = {
            re.sub(r"[^\w]", "_", subpath.stem.lower()): MediaItem(
                self._path, subpath.name, self._tracker
            )
            for subpath in self._path.iterdir()
            if subpath.is_file() and not subpath.name.startswith(".")
        }

    def __getitem__(self, name):
        if not (self._path / name).is_file():
            raise ValueError(f"File not found: {name}")

        return MediaItem(self._path, name, self._tracker)

    def __getattr__(self, key):
        if key not in self._subfiles:
            raise ValueError(f"File not found: {key}")

        return self._subfiles[key.lower()]


class LocalContextManager:
    def __init__(self):
        self.ctx = {}

    def __call__(self, **kwargs):
        self.ctx = dict(kwargs)
        return self

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.ctx = {}

    def do_gettext(self, value):
        return value

    def do_ngettext(self, singular, plural, num):
        return singular if num == 1 else plural

    def do_localize(self, value, format=None):
        return value

    def do_shim(self, name):
        if name == "events":
            return ""

        shims = {
            "i18n": "static/shim/Intl.min.js",
        }

        path = shims.get(name)
        if path is None:
            raise ValueError("Unknown shim")

        return Markup(utils.get_resource_string(path))

    def do_datafeed(
        self, *, name, label, fields, help=None, optional=False, optgroup=None
    ):
        data_source_item = self.ctx["context"].get(name)
        if data_source_item:
            return data_source_item._render(name)
        return ""

    def do_fetch_feed(self, value):
        from .fields import WebFeed, WebFeedEntry
        from .rss import process_feed

        processed_feed = process_feed(value)

        return WebFeed(
            url=value,
            title=processed_feed["title"],
            subtitle=processed_feed["subtitle"],
            entries=[WebFeedEntry(entry) for entry in processed_feed["entries"]],
        )

    def do_fetch_sheet(self, value):
        from .fields import GoogleSheet, GoogleSheetsURLField

        match = GoogleSheetsURLField.RE_SHEET_ID.match(value)
        return GoogleSheet(match.groups(1))

    def do_fetch_text(self, url, refresh=15, variable="FETCH_RESULT"):
        try:
            resp = utils.get_url(url)
            data = resp.data
        except Exception:
            data = ""

        return Markup(FETCH_TEMPLATE) % {
            "id": "v" + hashlib.sha1(data).hexdigest(),
            "content": data.decode("utf-8"),
            "variable": variable,
        }

    def do_signagewidgets(self, *args, **kwargs):
        from urllib.parse import urlencode

        url = "https://signagewidgets.net/" + "/".join(map(str, args))

        if kwargs:
            url = url + "?" + urlencode(kwargs)

        return url


def render_app_html(context, path, tracker, **kwargs):
    context = {**context, "media": ConfigurableWidgetMedia(path.parent, tracker)}

    html = None
    exceptions = None

    env = default_jinja_env()

    try:
        # First we need to convert the data into a template
        template = env.from_string(path.read_text("utf-8"))

        with env.local_ctx(tracker=tracker, context=context):
            html = template.render(context)
    except Exception as exp:
        exceptions = exp

    return html, exceptions


def default_jinja_env():
    if hasattr(_local, "env"):
        return _local.env

    env = ImmutableSandboxedEnvironment(
        autoescape=True,
        keep_trailing_newline=True,
        undefined=StrictUndefined,
        extensions=[
            ErrorExtension,
            "jinja2.ext.autoescape",
            "jinja2.ext.InternationalizationExtension",
        ],
    )
    env.local_ctx = LocalContextManager()
    env.install_gettext_callables(
        env.local_ctx.do_gettext, env.local_ctx.do_ngettext, newstyle=True
    )

    # In the default env __config__ is a no-op.
    env.globals["__config__"] = lambda *args, **kwargs: ""
    env.globals["__meta__"] = lambda *args, **kwargs: ""

    env.globals["contrast"] = do_contrast
    env.globals["darken"] = do_darken
    env.globals["lighten"] = do_lighten
    env.globals["regex_match"] = do_regex_match
    env.globals["shim"] = env.local_ctx.do_shim
    env.globals["fetch_feed"] = env.local_ctx.do_fetch_feed
    env.globals["fetch_text"] = env.local_ctx.do_fetch_text
    env.globals["fetch_sheet"] = env.local_ctx.do_fetch_sheet
    env.globals["localize"] = env.local_ctx.do_localize
    env.globals["signagewidgets"] = env.local_ctx.do_signagewidgets
    env.globals["__datasink__"] = env.local_ctx.do_datafeed
    env.globals["__datafeed__"] = env.local_ctx.do_datafeed
    env.globals["__field__"] = lambda *args, **kwargs: ""
    env.globals["__attr__"] = lambda *args, **kwargs: ""

    env.globals["__loadsdk__"] = Markup(SDK_TAG)

    env.globals["__lang__"] = "en"
    env.globals["__rtl__"] = False
    env.globals["__muted__"] = False
    env.globals["timeline_is_muted"] = False

    env.filters["json"] = do_json
    env.filters["numberfmt"] = do_numberfmt
    env.filters["slugify"] = do_slugify
    env.filters["qrcode"] = do_qrcode

    _local.env = env

    return env


def s_rgba(value):
    match = re.match(r"\s*#([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})\s*", value, re.I)
    if match:
        return tuple(int(i, 16) / 255 for i in match.groups()) + (1.0,)

    match = re.match(
        r"\s*#([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})\s*", value, re.I
    )
    if match:
        return tuple(int(i, 16) / 255 for i in match.groups())

    match = re.match(
        r"""
        rgba\(\s*
            ([01]?[0-9]?[0-9]|2[0-4][0-9]|25[0-5])\s*,\s*
            ([01]?[0-9]?[0-9]|2[0-4][0-9]|25[0-5])\s*,\s*
            ([01]?[0-9]?[0-9]|2[0-4][0-9]|25[0-5])\s*,\s*
            (\d*\.\d+)
        \s*\)
    """,
        value,
        re.X | re.I,
    )
    if match:
        return tuple(int(i) / 255 for i in match.groups()[:3]) + (
            float(match.groups()[-1]),
        )

    raise ValueError("invalid color")


def rgb_s(r, g, b, a=1.0):
    if a == 1.0:
        return "#{:02x}{:02x}{:02x}".format(*tuple(round(c * 255) for c in (r, g, b)))
    else:
        return "rgba(%i,%i,%i,%.3f)" % tuple([round(c * 255) for c in (r, g, b)] + [a])


def s_amount(amount):
    if isinstance(amount, str):
        return float(amount.strip(" %")) / 100

    return amount


def do_lighten(value, amount=0.1):
    r, g, b, a = s_rgba(value)

    h, l, s = colorsys.rgb_to_hls(r, g, b)
    l = min(1, max(0, l + s_amount(amount)))

    return rgb_s(*colorsys.hls_to_rgb(h, l, s), a=a)


def do_darken(value, amount=0.1):
    r, g, b, a = s_rgba(value)

    h, l, s = colorsys.rgb_to_hls(r, g, b)
    l = min(1, max(0, l - s_amount(amount)))

    return rgb_s(*colorsys.hls_to_rgb(h, l, s), a=a)


def do_contrast(value, light, dark, threshold=0.43):
    r, g, b, a = s_rgba(value)

    # Gama correct the values
    r = r / 12.92 if r <= 0.03928 else ((r + 0.055) / 1.055) ** 2.4
    g = g / 12.92 if g <= 0.03928 else ((g + 0.055) / 1.055) ** 2.4
    b = b / 12.92 if b <= 0.03928 else ((b + 0.055) / 1.055) ** 2.4

    luma = 0.2126 * r + 0.7152 * g + 0.0722 * b

    if luma < threshold:
        return light
    else:
        return dark


def do_regex_match(pattern, string, case_insensitive=False):
    flags = 0
    if case_insensitive:
        flags = flags | re.I

    try:
        match = re.match(pattern, string, flags)
    except re.error:
        raise ValueError("Invalid regular expression")
    else:
        results = {}
        if match:
            results.update(
                dict(list(zip(list(range(len(match.groups()))), match.groups())))
            )
            results.update(match.groupdict())

        return results


def do_numberfmt(number, decimal_sep=".", thousand_sep=".", decimal_pos=2, grouping=3):
    """
    Adapted from https://github.com/django/django/blob/main/django/utils/numberformat.py
    Get a number (as a number or string), and return it as a string,
    using formats defined as arguments:

    * decimal_sep: Decimal separator symbol (for example ".")
    * thousand_sep: Thousand separator symbol (for example ",")
    * decimal_pos: Number of decimal positions
    * grouping: Number of digits in every group limited by thousand separator.
        For non-uniform digit grouping, it can be a sequence with the number
        of digit group sizes following the format used by the Python locale
        module in locale.localeconv() LC_NUMERIC grouping (e.g. (3, 2, 0)).
    """
    from decimal import Decimal

    # sign
    sign = ""
    if isinstance(number, Decimal):
        # Format values with more than 200 digits (an arbitrary cutoff) using
        # scientific notation to avoid high memory usage in {:f}'.format().
        _, digits, exponent = number.as_tuple()
        if abs(exponent) + len(digits) > 200:
            number = f"{number:e}"
            coefficient, exponent = number.split("e")
            # Format the coefficient.
            coefficient = do_numberfmt(
                coefficient,
                decimal_sep,
                thousand_sep,
                decimal_pos,
                grouping,
            )
            return f"{coefficient}e{exponent}"
        else:
            str_number = f"{number:f}"
    else:
        str_number = str(number)
    if str_number[0] == "-":
        sign = "-"
        str_number = str_number[1:]

    # decimal part
    if "." in str_number:
        int_part, dec_part = str_number.split(".")
        if decimal_pos is not None:
            dec_part = dec_part[:decimal_pos]
    else:
        int_part, dec_part = str_number, ""
    if decimal_pos is not None:
        dec_part = dec_part + ("0" * (decimal_pos - len(dec_part)))
    dec_part = dec_part and decimal_sep + dec_part

    # grouping
    try:
        # if grouping is a sequence
        intervals = list(grouping)
    except TypeError:
        # grouping is a single value
        intervals = [grouping, 0]
    active_interval = intervals.pop(0)
    int_part_gd = ""
    cnt = 0
    for digit in int_part[::-1]:
        if cnt and cnt == active_interval:
            if intervals:
                active_interval = intervals.pop(0) or active_interval
            int_part_gd += thousand_sep[::-1]
            cnt = 0
        int_part_gd += digit
        cnt += 1
    int_part = int_part_gd[::-1]

    return sign + int_part + dec_part


def do_slugify(value):
    import unicodedata

    value = str(value)
    value = (
        unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    )
    value = re.sub(r"[^\w\s-]", "", value).strip().lower()
    return re.sub(r"[-\s]+", "-", value)


def do_qrcode(value):
    from io import BytesIO

    import qrcode
    import qrcode.image.svg

    qr_svg = qrcode.make(value, image_factory=qrcode.image.svg.SvgPathImage)

    svg_stream = BytesIO()
    qr_svg.save(svg_stream)

    svg_value = svg_stream.getvalue().decode("utf-8")

    return Markup(svg_value[svg_value.find("<svg") :])


class LenientJSONEncoder(json.JSONEncoder):
    """
    JSONEncoder subclass that knows how to encode date/time, decimal types, and
    UUIDs.
    """

    def default(self, o):
        # See "Date Time String Format" in the ECMA-262 specification.
        if isinstance(o, datetime.datetime):
            r = o.isoformat()
            if o.microsecond:
                r = r[:23] + r[26:]
            if r.endswith("+00:00"):
                r = r[:-6] + "Z"
            return r
        elif isinstance(o, datetime.date):
            return o.isoformat()
        elif isinstance(o, datetime.time):
            if o.utcoffset() is not None:
                raise ValueError("JSON can't represent timezone-aware times.")
            r = o.isoformat()
            if o.microsecond:
                r = r[:12]
            return r
        elif isinstance(o, datetime.timedelta):
            if o < datetime.timedelta(0):
                sign = "-"
                o *= -1
            else:
                sign = ""

            days = o.days
            seconds = o.seconds
            microseconds = o.microseconds

            minutes = seconds // 60
            seconds = seconds % 60

            hours = minutes // 60
            minutes = minutes % 60
            ms = f".{microseconds:06d}" if microseconds else ""
            return f"{sign}P{days}DT{hours:02d}H{minutes:02d}M{seconds:02d}{ms}S"
        elif isinstance(o, (decimal.Decimal, uuid.UUID)):
            return str(o)
        else:
            return super().default(o)


def do_json(value):
    return Markup(
        json.dumps(value, cls=LenientJSONEncoder)
        .replace("'", r"\u0027")
        .replace("&", r"\u0026")
    )


class LenientUndefined(Undefined):
    """Allows the user to do pretty much anything with undefined values."""

    def _dont_give_up(self, *args, **kwargs):
        return LenientUndefined()

    def __getattr__(self, name):
        if name[:2] == "__":
            raise AttributeError(name)
        return self._dont_give_up()

    def __int__(self):
        return 0

    def __float__(self):
        return 0.0

    __add__ = __radd__ = __mul__ = __rmul__ = __div__ = __rdiv__ = __truediv__ = (
        __rtruediv__
    ) = __floordiv__ = __rfloordiv__ = __mod__ = __rmod__ = __pos__ = __neg__ = (
        __call__
    ) = __getitem__ = __lt__ = __le__ = __gt__ = __ge__ = __complex__ = __pow__ = (
        __rpow__
    ) = _dont_give_up


class ErrorExtension(Extension):
    tags = {"error"}

    def parse(self, parser):
        lineno = next(parser.stream).lineno

        return nodes.Output(
            [self.call_method("_raise", [parser.parse_expression()])]
        ).set_lineno(lineno)

    def _raise(self, message):
        if self.environment.undefined is LenientUndefined:
            return ""

        raise ValueError(message)


def lenient_jinja_env():
    if hasattr(_local, "lenient"):
        return _local.lenient

    lenient = ImmutableSandboxedEnvironment(
        autoescape=True,
        keep_trailing_newline=True,
        undefined=LenientUndefined,
        extensions=[
            ErrorExtension,
            "jinja2.ext.autoescape",
            "jinja2.ext.InternationalizationExtension",
        ],
    )
    lenient.filters = LenientUndefined()
    lenient.install_null_translations(newstyle=True)

    _local.lenient = lenient

    return lenient


class HTMLTemplateParser(HTMLParser):
    def __init__(self):
        self.convert_charrefs = True
        self.reset()
        self._in_title = False
        self.title = None
        self.variables = []
        self.metas = {}
        self.loadsdk_error = False
        self.has_script = False

    def handle_comment(self, data):
        if data == "__loadsdk__" and self.variables:
            self.loadsdk_error = True

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self._in_title = tag == "title"

        if tag == "meta" and all(attrs.get(a) for a in ("label", "name", "type")):
            self.variables.append((self.getpos(), attrs))
        elif (
            tag == "meta" and attrs.get("content") and attrs.get("name") in KNOWN_METAS
        ):
            self.metas[attrs["name"]] = attrs["content"]
        elif tag == "script":
            self.has_script = True

    def handle_endtag(self, tag):
        self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title = data.strip()


def extract_app_config(template_text):
    config = {}
    env = lenient_jinja_env()

    template = env.from_string(template_text)

    app_fields = OrderedDict()
    app_attrs = OrderedDict()
    exceptions = []

    def detect_config(
        name,
        type,
        label,
        value=None,
        help=None,
        optional=False,
        *,
        js=False,
        optgroup=None,
        **kwargs,
    ):
        field = {
            "type": type,
            "label": label,
            "value": value,
            "help_text": help,
            "required": not bool(optional),
            "js": js,
            "optgroup": optgroup,
        }

        if js:
            if type not in JS_SUPPORTED_TYPES:
                raise ValueError(
                    f"""
                    "{type}" type of configuration option "{name}" does not support the <code>js</code> parameter.<br>
                    Check the <a href="https://github.com/onsigntv/apps/blob/master/docs/JSBRIDGE.md#app-configuration-object-api">appConfig object documentation</a> to see which types are supported.
                    """
                )

            config.setdefault("js_app_config", []).append(name)

        if type in ("choice", "multichoice"):
            if not isinstance(kwargs.get("choices"), (list, tuple)):
                raise ValueError(
                    f'A "choices" argument is required and must be a list: {name}'
                )

            for choice in kwargs["choices"]:
                if not isinstance(choice, (list, tuple)):
                    raise ValueError(f'Each item in "choices" must be a list: {name}')

                if len(choice) != 2:
                    raise ValueError(
                        f'Each item in "choices" must have two strings (name, label): {name}'
                    )

                if not (isinstance(choice[0], str) and isinstance(choice[1], str)):
                    raise ValueError(
                        f'Each item in "choices" must have two strings (name, label): {name}'
                    )

            if value:
                if value not in [choice[0] for choice in kwargs["choices"]]:
                    raise ValueError(
                        f'Default value must be present in "choices" argument: {name}'
                    )
            else:
                field["value"] = kwargs["choices"][0][0]

            field["choices"] = kwargs["choices"]
        elif type == "font":
            if value and value not in AVAILABLE_FONTS:
                raise ValueError(f"Default font should be a valid system font: {name}")

        app_fields[name] = field

    class DataSinkField:
        def __init__(self, *, name, type, label, help=None, optional=False):
            if not re.match("^[a-zA-Z][a-zA-Z0-9_]*$", name):
                raise ValueError(f"Invalid field name: {name}")

            if type not in DATA_SOURCE_TYPES:
                raise ValueError(f"Data source type invalid: {type}")

            self.name = name
            self.type = type
            self.label = label
            self.help_text = help
            self.required = not bool(optional)

        def __repr__(self):
            return f"<DataSinkField {self.as_dict()}>"

        def as_dict(self):
            return self.__dict__

    def detect_datafeed(
        *, name, label, fields, help=None, optional=False, optgroup=None
    ):
        if not re.match("^[a-zA-Z][a-zA-Z0-9_]*$", name):
            raise ValueError(f"Invalid data feed name: {name}")

        if not isinstance(fields, list):
            raise ValueError("Data feed fields must be a list")

        if not fields:
            raise ValueError("Data feed fields must not be empty")

        if not all(isinstance(f, DataSinkField) for f in fields):
            raise ValueError("Data feed fields must use __field__ constructor")

        field_datafeed = {
            "type": "datafeed",
            "label": label,
            "value": None,
            "help_text": help,
            "required": not bool(optional),
            "datasource_fields": [f.as_dict() for f in fields],
            "optgroup": optgroup,
        }

        app_fields[name] = field_datafeed

    def detect_meta(name, value):
        if name in KNOWN_METAS:
            if name in (
                "audio",
                "audio-app",
                "automation",
                "automation-app",
                "plugin",
                "plugin-app",
            ):
                if value:
                    config[name.split("-")[0]] = True
            else:
                config[name] = value

    def detect_attr(*, name, type, label, mode, help=None, optional=False):
        if not re.match("^[a-zA-Z][a-zA-Z0-9_]*$", name):
            raise ValueError(f"Invalid App Attribute name: {name}")

        if type not in ATTR_TYPES:
            raise ValueError(f"App Attribute type invalid: {type}")

        if mode not in ATTR_MODES:
            raise ValueError(f"App Attribute access mode invalid: {mode}")

        if optional not in {True, False}:
            raise ValueError(
                f'App Attribute optional parameter requires a Boolean value, got: "{optional}"'
            )

        app_attrs[name] = {
            "type": type,
            "label": label,
            "value": True,
            "mode": mode,
            "help_text": help,
            "required": not optional,
        }

    class DetectLoadSDK:
        def __str__(self):
            if app_fields:
                raise ValueError(
                    "{{ __loadsdk__ }} must be added before __config__ or __datafeed__"
                )

            config["sdk"] = True
            return Markup(SDK_TAG)

    # Then we render the template to remove all Jinja2 tags
    html = template.render(
        {
            "__loadsdk__": DetectLoadSDK(),
            "__config__": detect_config,
            "__meta__": detect_meta,
            "__datasink__": detect_datafeed,
            "__datafeed__": detect_datafeed,
            "__field__": DataSinkField,
            "__attr__": detect_attr,
        }
    )

    # Now we use a lenient parser to try not to gobble up on invalid markup
    parser = HTMLTemplateParser()
    parser.feed(html)

    if parser.title:
        config["title"] = parser.title
    else:
        raise ValueError("A title tag is required for this app")

    if parser.loadsdk_error:
        raise ValueError("__loadsdk__ must be added before <meta> configurations")

    config["warnings"] = {}

    # After SDK_WARNING_EXPIRY_DATE, not loading sdk will be considered an error.
    if parser.has_script and not config.get("sdk"):
        if datetime.datetime.now().strftime("%Y-%m-%d") >= SDK_WARNING_EXPIRY_DATE:
            raise ValueError("Missing {{ __loadsdk__ }} tag in app.")
        else:
            config["warnings"]["missing_loadsdk"] = True

    config.update(parser.metas)

    if parser.variables:
        if app_fields:
            raise ValueError("Unable to mix __config__ and <meta> variables together.")

        for pos, attrs in parser.variables:
            name = attrs["name"]
            field = {
                "type": attrs["type"],
                "label": attrs["label"],
                "value": attrs.get("value"),
                "help_text": attrs.get("help"),
                "required": "optional" not in attrs,
                "optgroup": attrs.get("optgroup") or None,
            }
            if field["value"] == "":
                field["value"] = None

            if field["type"] in ("choice", "multichoice"):
                if not field.get("value"):
                    raise ValueError(f"Choice variable requires a value: {name}")

                if name not in app_fields:
                    app_fields[name] = field
                    app_fields[name]["choices"] = [[field["value"], field["label"]]]
                elif app_fields[name]["type"] not in ("choice", "multichoice"):
                    raise ValueError(f"Choice variable configured wrong: {name}")
                else:
                    app_fields[name]["choices"].append([field["value"], field["label"]])
            else:
                if field["type"] == "font":
                    if attrs.get("value") and attrs["value"] not in AVAILABLE_FONTS:
                        raise ValueError(
                            f"Default font should be a valid system font: {name}"
                        )
                app_fields[name] = field

        for field in [
            f[1]
            for f in app_fields.items()
            if f[1]["type"] in ("choice", "multichoice")
        ]:
            choices = field["choices"]

            field["label"] = ""
            if all(re.match(r".*\S.*:.*\S.*", choice[1]) for choice in choices):
                field["label"] = choices[0][1].split(":", 1)[0].strip()

                for choice in choices:
                    choice[1] = choice[1].split(":", 1)[1].strip()

    for name, field in app_fields.items():
        if not re.match("^[a-zA-Z][a-zA-Z0-9_]*$", name):
            raise ValueError({"error": f"Invalid variable name: {name}"})

        if name in env.globals or name in BANNED_NAMES:
            raise ValueError({"error": f"Invalid variable name: {name}"})

        if field["type"] not in KNOWN_TYPES | {"datafeed"}:
            raise ValueError({"error": f"Invalid variable type: {name}"})

        if field["type"] in USER_TYPES and field.get("value"):
            raise ValueError(f"User variables cannot contain default values: {name}")

    app_fields["_delay_show"] = {
        "type": "bool",
        "label": "Delay Show Event By 3 Seconds",
        "value": False,
        "help_text": Markup(
            """
            Use this to simulate
            <a href="https://github.com/onsigntv/apps/blob/master/docs/JSBRIDGE.md#show-event" target="_blank">
                app preloading
            </a> done by a real OnSign TV Player.
            """
        ),
        "required": None,
        "optgroup": None,
    }

    app_fields["_proxy_requests"] = {
        "type": "bool",
        "label": "Proxy Javascript Requests",
        "value": False,
        "help_text": Markup(
            """
            Workaround <a href="https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS" target="_blank">
                Cross-Origin Resource Sharing (CORS)
            </a> issues by proxying uses of <code>fetch</code> or <code>XMLHttpRequest</code>
            """
        ),
        "required": None,
        "optgroup": None,
    }

    app_fields["_toast_attr_change"] = {
        "type": "bool",
        "label": "Show Notification on App Attribute Change",
        "value": False,
        "help_text": "Display a toast on the bottom of the screen whenever an app attributes value has changed",
        "required": None,
        "optgroup": None,
    }

    app_fields["_serial_port_config"] = {
        "type": "text",
        "label": "Serial Port Configuration",
        "value": "",
        "help_text": "",
        "required": None,
        "optgroup": None,
    }

    app_fields["_toast_serial_port_data"] = {
        "type": "bool",
        "label": "Show Notification When Serial Port Data is Read",
        "value": False,
        "help_text": Markup(
            """
            Display a toast on the bottom of the screen whenever the
            <a href="https://github.com/onsigntv/apps/blob/master/docs/JSBRIDGE.md#signage-serialportdata-event">
            <code>serialportdata</code> event</a> is fired
            """
        ),
        "required": None,
        "optgroup": None,
    }

    app_fields["_playback_info"] = {
        "type": "paragraph",
        "label": "Javascript Playback Info Data",
        "value": samples.PLAYBACK_INFO,
        "help_text": Markup(
            """
            Check the
            <a href="https://github.com/onsigntv/apps/blob/master/docs/JSBRIDGE.md" target="_blank">
              Javascript API documentation
            </a>
            to know what information will be available through
            <a href="https://github.com/onsigntv/apps/blob/master/docs/JSBRIDGE.md#playbackInfo" target="_blank">
              <code>signage.playbackInfo()</code>
            </a>
            """
        ),
        "required": None,
        "optgroup": None,
    }

    config["fields"] = list(map(list, app_fields.items()))
    config["attrs"] = list(map(list, app_attrs.items()))
    config["exceptions"] = exceptions

    try:
        node = env.parse(template_text)
        list(env.lex(env.preprocess(template_text)))
    except TemplateSyntaxError:
        pass
    else:
        catalog = OrderedDict()

        for lineno, func, message in extract_from_ast(
            node, GETTEXT_FUNCTIONS, babel_style=False
        ):
            if message not in catalog:
                catalog[message] = {"msgid": message}

        if catalog:
            config["i18n"] = True
            config["catalog"] = list(catalog.values())

    return config
