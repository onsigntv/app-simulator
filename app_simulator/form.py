import logging
import re
from collections import OrderedDict

import wtforms
from wtforms.form import BaseForm
from wtforms.meta import DefaultMeta
from wtforms.validators import Regexp
from wtforms.widgets import TextInput, Input, TextArea, Select

from .fields import (
    AirportField,
    ColorField,
    CurrencyField,
    DataSourceField,
    FontField,
    GoogleSheetsURLField,
    InstagramField,
    LocationField,
    StockExchangeField,
    TwitterField,
    UserMediaField,
    WebFeedField,
)


logger = logging.getLogger("onsigntv.form")


ALLOWED_FILE_TYPES = [
    ".png",
    ".jpeg",
    ".jpg",
    ".gif",
    ".webp",
    ".mkv",
    ".avi",
    ".mp4",
    ".mpg",
    ".mpeg",
    ".mov",
    ".mht",
    ".mhtm",
    ".mhtml",
    ".js",
    ".css",
    ".html",
    ".swf",
    ".svg",
    ".glb",
    ".gltf",
    ".hdr",
    ".xml",
    ".ttf",
    ".otf",
    ".woff",
    ".woff2",
    ".mp3",
    ".m3u",
    ".pdf",
]


class BootstrapMeta(DefaultMeta):
    def render_field(self, field, render_kw):
        if getattr(field, "process_errors", None) or getattr(field, "errors", None):
            render_kw["class"] = render_kw.get("class", "") + " is-invalid"

        return super().render_field(field, render_kw)


def build_form(config):
    fields = OrderedDict()

    for name, field in config["fields"]:
        kind = field["type"]

        label = field["label"]
        help_text = field["help_text"]

        logger.debug(f"registering field '{name}' of type '{kind}'")

        if "required" in field and field["required"]:
            validators = [wtforms.validators.InputRequired()]
        else:
            validators = [wtforms.validators.Optional()]

        if kind == "audio":
            fields[name] = UserMediaField(
                label=label,
                description=help_text,
                default=field["value"],
                validators=validators,
                render_kw={
                    "class": "form-control-file",
                    "accept": "audio/mp3",
                },
            )

        elif kind == "audiolist":
            fields[name] = UserMediaField(
                label=label,
                description=help_text,
                multiple=True,
                default=field["value"],
                validators=validators,
                render_kw={
                    "class": "form-control-file",
                    "accept": "audio/mp3",
                },
            )

        elif kind == "airport":
            fields[name] = AirportField(
                label=label,
                description=help_text,
                choices=[],
                validators=validators,
                render_kw={"class": "form-control"},
            )

        elif kind == "bool":
            initial = True
            if not field["value"] or field["value"].lower() in ("no", "false", "0"):
                initial = False

            validators = []
            fields[name] = wtforms.BooleanField(
                label=label,
                description=help_text,
                default=initial,
                validators=validators,
                render_kw={
                    "class": "form-check-input",
                },
            )

        elif kind == "choice":
            choices = [(c[0], c[1]) for c in field["choices"]]
            initial = field["value"]
            if not initial:
                initial = choices[0][0]

            fields[name] = wtforms.SelectField(
                label=label,
                default=initial,
                description=help_text,
                choices=choices,
                validators=validators,
                render_kw={"class": "form-control"},
            )

        elif kind == "color":
            fields[name] = ColorField(
                label=label,
                description=help_text,
                default=field["value"],
                validators=validators,
                render_kw={"class": "form-control", "style": "height: 38px;"},
            )

        elif kind == "currency":
            fields[name] = CurrencyField(
                label=label,
                description=help_text,
                default=field["value"],
                validators=validators,
                render_kw={"class": "form-control"},
            )

        elif kind == "date":
            fields[name] = wtforms.DateField(
                label=label,
                description=help_text,
                format="%Y-%m-%d",
                default=field["value"],
                validators=validators,
                render_kw={
                    "class": "form-control",
                    "type": "date",
                },
                widget=TextInput(),
            )

        elif kind == "datetime":
            fields[name] = wtforms.DateTimeField(
                label=label,
                description=help_text,
                format="%Y-%m-%dT%H:%M:%S",
                default=field["value"],
                validators=validators,
                render_kw={
                    "class": "form-control",
                    "type": "datetime-local",
                    "step": "1",
                },
                widget=TextInput(),
            )

        elif kind == "float":
            fields[name] = wtforms.FloatField(
                label=label,
                description=help_text,
                default=field["value"],
                validators=validators,
                render_kw={"class": "form-control", "step": 0.1},
                widget=Input(input_type="number"),
            )

        elif kind == "font":
            fields[name] = FontField(
                label=label,
                description=help_text,
                validators=validators,
                render_kw={"class": "form-control"},
            )

        elif kind == "googlesheet":
            fields[name] = GoogleSheetsURLField(
                label=label,
                description=help_text,
                default=field["value"],
                validators=validators,
                render_kw={"class": "form-control"},
            )

        elif kind == "instagram":
            fields[name] = InstagramField(
                label=label,
                description=help_text,
                default=field["value"],
                validators=validators,
                render_kw={"class": "form-control"},
            )

        elif kind == "image":
            fields[name] = UserMediaField(
                label=label,
                description=help_text,
                default=field["value"],
                validators=validators,
                render_kw={
                    "class": "form-control-file",
                    "accept": "image/*",
                },
            )

        elif kind == "imagelist":
            fields[name] = UserMediaField(
                label=label,
                description=help_text,
                multiple=True,
                default=field["value"],
                validators=validators,
                render_kw={
                    "class": "form-control-file",
                    "accept": "image/*",
                },
            )

        elif kind == "location":
            fields[name] = LocationField(
                label=label,
                description=help_text,
                default=field["value"],
                validators=validators,
                render_kw={"class": "form-control"},
            )

        elif kind == "number":
            fields[name] = wtforms.IntegerField(
                label=label,
                description=help_text,
                default=field["value"],
                validators=validators,
                render_kw={"class": "form-control", "step": 1},
                widget=Input(input_type="number"),
            )

        elif kind == "media":
            fields[name] = UserMediaField(
                label=label,
                description=help_text,
                multiple=True,
                default=field["value"],
                validators=validators,
                render_kw={
                    "class": "form-control-file",
                    "accept": "image/*, video/*",
                },
            )

        elif kind == "multichoice":
            choices = [(c[0], c[1]) for c in field["choices"]]
            initial = field["value"]
            if not initial:
                initial = choices[0][0]

            fields[name] = wtforms.SelectMultipleField(
                label=label,
                description=help_text,
                default=initial,
                choices=choices,
                validators=validators,
                widget=Select(multiple=True),
                render_kw={"class": "form-control"},
            )

        elif kind == "multicurrency":
            fields[name] = CurrencyField(
                label=label,
                description=help_text,
                validators=validators,
                widget=Select(multiple=True),
                render_kw={"class": "form-control"},
            )

        elif kind == "paragraph":
            fields[name] = wtforms.StringField(
                label=label,
                description=help_text,
                default=field["value"],
                validators=validators,
                render_kw={"class": "form-control", "rows": 10, "cols": 40},
                widget=TextArea(),
            )

        elif kind == "richtext":
            fields[name] = wtforms.StringField(
                label=label,
                description=help_text,
                default=field["value"],
                validators=validators,
                render_kw={"class": "form-control", "rows": 10, "cols": 40},
                widget=TextArea(),
            )

        elif kind == "stock":
            fields[name] = StockExchangeField(
                label=label,
                description=help_text,
                default=field["value"],
                validators=validators,
                render_kw={"class": "form-control"},
            )

        elif kind == "text":
            fields[name] = wtforms.StringField(
                label=label,
                description=help_text,
                default=field["value"],
                validators=validators,
                render_kw={"class": "form-control"},
                widget=TextInput(),
            )

        elif kind == "time":
            fields[name] = wtforms.TimeField(
                label=label,
                description=help_text,
                format="%H:%M:%S",
                default=field["value"],
                validators=validators,
                render_kw={
                    "class": "form-control",
                    "type": "time",
                    "step": "1",
                },
                widget=TextInput(),
            )

        elif kind == "twitter":
            fields[name] = TwitterField(
                label=label,
                description=help_text,
                default=field["value"],
                validators=validators,
                render_kw={"class": "form-control"},
            )

        elif kind == "video":
            fields[name] = UserMediaField(
                label=label,
                description=help_text,
                default=field["value"],
                validators=validators,
                render_kw={
                    "class": "form-control-file",
                    "accept": "video/*",
                },
            )

        elif kind == "url":
            URL_RE = re.compile(
                r"""^
                   (?:(?:udp|rtp)://@(?::\d+)?) # Special case for VLC udp URLs
                   |
                   (?:
                     (?:[a-z0-9\.\-]*)://  # scheme is validated separately
                     (?:[-_@\.\+\w]+:[^@]+@)? # user:password
                     (?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}(?<!-)\.?)|  # domain...
                     [A-Z0-9][A-Z0-9-]{1,61}| # localhost and other locally defined domains...
                     \d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}|  # ...or ipv4
                     \[?[A-F0-9]*:[A-F0-9:]+\]?)  # ...or ipv6
                     (?::\d+)?  # optional port
                     (?:/?|[/?]\S+)
                   )
               $""",
                re.IGNORECASE | re.X,
            )

            validators += [Regexp(URL_RE, message="This string is not in url pattern")]

            fields[name] = wtforms.StringField(
                label=label,
                description=help_text,
                default=field["value"],
                validators=validators,
                render_kw={"class": "form-control"},
                widget=TextInput(),
            )

        elif kind == "webfeed":
            fields[name] = WebFeedField(
                label=label,
                description=help_text,
                default=field["value"],
                validators=validators,
                render_kw={
                    "class": "form-control",
                    "placeholder": 'Use "sample" for a sample RSS feed...',
                },
            )

        elif kind == "xml":
            fields[name] = UserMediaField(
                label=label,
                description=help_text,
                default=field["value"],
                validators=validators,
                render_kw={
                    "class": "form-control-file",
                    "accept": "text/xml",
                },
            )

        elif kind == "datasink":
            fields[name] = DataSourceField(
                fields=field["datasource_fields"],
                label=label + " | number of entries",
                description=help_text,
                default=field["value"],
                render_kw={
                    "class": "form-control",
                },
                widget=Input(input_type="number"),
                validators=validators,
            )

    return BaseForm(fields)
