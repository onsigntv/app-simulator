import datetime
import json
import logging
import random
import re
from collections import OrderedDict

import jinja2
import pytz
from wtforms import validators, Field, SelectField, StringField, IntegerField
from wtforms.widgets import Input, FileInput

from . import utils
from .samples import INSTAGRAM_FEED, TWITTER_FEED, VIDEOS
from .storage import get_file


logger = logging.getLogger("onsigntv.fields")


class AdaptableMixin:
    def adapt(self):
        if self.data and not self.errors:
            self.adapt_data()

    def adapt_data(self):
        self.data = self.adapt_class(self.data)


class AirportField(SelectField):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.choices = [
            ("CAN", "Guangzhou Baiyun International Airport"),
            ("ATL", "Hartsfield–Jackson Atlanta International Airport"),
            ("DEN", "Denver International Airport"),
            ("HND", "Tokyo Haneda Airport"),
            ("DEL", "Indira Gandhi International Airport"),
            ("DXB", "Dubai International Airport"),
            ("LHR", "Heathrow Airport"),
            ("MEX", "Mexico City International Airport"),
            ("GRU", "Guarulhos International Airport"),
        ]
        if not self.flags.required:
            self.choices.insert(0, ("", "-----------"))


class ColorInput(Input):
    input_type = "text"

    def __call__(self, field, **kwargs):
        kwargs["data_jscolor"] = "{required:false}"
        return super().__call__(field, **kwargs)


class ColorField(AdaptableMixin, StringField):
    def __init__(self, *args, **kwargs):
        kwargs["validators"].append(
            validators.Regexp(
                r"^#[0-9A-F]{6}(?:[0-9A-F]{2})?$", message="Invalid color"
            )
        )
        kwargs["widget"] = ColorInput()
        super().__init__(*args, **kwargs)

    def adapt_data(self):
        if len(self.data) == 9:
            r, g, b, a = [int(self.data[i : i + 2], 16) for i in range(1, 9, 2)]
            self.data = "rgba(%i,%i,%i,%.3f)" % (r, g, b, float(a) / 255)


AVAILABLE_CURRENCIES = OrderedDict(
    [
        ("AED", "United Arab Emirates Dirham"),
        ("AFN", "Afghan Afghani"),
        ("ALL", "Albanian Lek"),
        ("AMD", "Armenian Dram"),
        ("ANG", "Netherlands Antillean Guilder"),
        ("AOA", "Angolan Kwanza"),
        ("ARS", "Argentine Peso"),
        ("AUD", "Australian Dollar"),
        ("AWG", "Aruban Florin"),
        ("AZN", "Azerbaijani Manat"),
        ("BAM", "Bosnia-Herzegovina Convertible Mark"),
        ("BBD", "Barbadian Dollar"),
        ("BDT", "Bangladeshi Taka"),
        ("BGN", "Bulgarian Lev"),
        ("BHD", "Bahraini Dinar"),
        ("BIF", "Burundian Franc"),
        ("BMD", "Bermudan Dollar"),
        ("BND", "Brunei Dollar"),
        ("BOB", "Bolivian Boliviano"),
        ("BRL", "Brazilian Real"),
        ("BSD", "Bahamian Dollar"),
        ("BTC", "Bitcoin"),
        ("BTN", "Bhutanese Ngultrum"),
        ("BWP", "Botswanan Pula"),
        ("BYR", "Belarusian Ruble"),
        ("BZD", "Belize Dollar"),
        ("CAD", "Canadian Dollar"),
        ("CDF", "Congolese Franc"),
        ("CHF", "Swiss Franc"),
        ("CLF", "Chilean Unit of Account (UF)"),
        ("CLP", "Chilean Peso"),
        ("CNY", "Chinese Yuan"),
        ("COP", "Colombian Peso"),
        ("CRC", "Costa Rican Colón"),
        ("CUC", "Cuban Convertible Peso"),
        ("CUP", "Cuban Peso"),
        ("CVE", "Cape Verdean Escudo"),
        ("CZK", "Czech Republic Koruna"),
        ("DJF", "Djiboutian Franc"),
        ("DKK", "Danish Krone"),
        ("DOP", "Dominican Peso"),
        ("DZD", "Algerian Dinar"),
        ("EEK", "Estonian Kroon"),
        ("EGP", "Egyptian Pound"),
        ("ERN", "Eritrean Nakfa"),
        ("ETB", "Ethiopian Birr"),
        ("EUR", "Euro"),
        ("FJD", "Fijian Dollar"),
        ("FKP", "Falkland Islands Pound"),
        ("GBP", "British Pound Sterling"),
        ("GEL", "Georgian Lari"),
        ("GGP", "Guernsey Pound"),
        ("GHS", "Ghanaian Cedi"),
        ("GIP", "Gibraltar Pound"),
        ("GMD", "Gambian Dalasi"),
        ("GNF", "Guinean Franc"),
        ("GTQ", "Guatemalan Quetzal"),
        ("GYD", "Guyanaese Dollar"),
        ("HKD", "Hong Kong Dollar"),
        ("HNL", "Honduran Lempira"),
        ("HRK", "Croatian Kuna"),
        ("HTG", "Haitian Gourde"),
        ("HUF", "Hungarian Forint"),
        ("IDR", "Indonesian Rupiah"),
        ("ILS", "Israeli New Sheqel"),
        ("IMP", "Manx pound"),
        ("INR", "Indian Rupee"),
        ("IQD", "Iraqi Dinar"),
        ("IRR", "Iranian Rial"),
        ("ISK", "Icelandic Króna"),
        ("JEP", "Jersey Pound"),
        ("JMD", "Jamaican Dollar"),
        ("JOD", "Jordanian Dinar"),
        ("JPY", "Japanese Yen"),
        ("KES", "Kenyan Shilling"),
        ("KGS", "Kyrgystani Som"),
        ("KHR", "Cambodian Riel"),
        ("KMF", "Comorian Franc"),
        ("KPW", "North Korean Won"),
        ("KRW", "South Korean Won"),
        ("KWD", "Kuwaiti Dinar"),
        ("KYD", "Cayman Islands Dollar"),
        ("KZT", "Kazakhstani Tenge"),
        ("LAK", "Laotian Kip"),
        ("LBP", "Lebanese Pound"),
        ("LKR", "Sri Lankan Rupee"),
        ("LRD", "Liberian Dollar"),
        ("LSL", "Lesotho Loti"),
        ("LTL", "Lithuanian Litas"),
        ("LVL", "Latvian Lats"),
        ("LYD", "Libyan Dinar"),
        ("MAD", "Moroccan Dirham"),
        ("MDL", "Moldovan Leu"),
        ("MGA", "Malagasy Ariary"),
        ("MKD", "Macedonian Denar"),
        ("MMK", "Myanma Kyat"),
        ("MNT", "Mongolian Tugrik"),
        ("MOP", "Macanese Pataca"),
        ("MRO", "Mauritanian Ouguiya"),
        ("MTL", "Maltese Lira"),
        ("MUR", "Mauritian Rupee"),
        ("MVR", "Maldivian Rufiyaa"),
        ("MWK", "Malawian Kwacha"),
        ("MXN", "Mexican Peso"),
        ("MYR", "Malaysian Ringgit"),
        ("MZN", "Mozambican Metical"),
        ("NAD", "Namibian Dollar"),
        ("NGN", "Nigerian Naira"),
        ("NIO", "Nicaraguan Córdoba"),
        ("NOK", "Norwegian Krone"),
        ("NPR", "Nepalese Rupee"),
        ("NZD", "New Zealand Dollar"),
        ("OMR", "Omani Rial"),
        ("PAB", "Panamanian Balboa"),
        ("PEN", "Peruvian Nuevo Sol"),
        ("PGK", "Papua New Guinean Kina"),
        ("PHP", "Philippine Peso"),
        ("PKR", "Pakistani Rupee"),
        ("PLN", "Polish Zloty"),
        ("PYG", "Paraguayan Guarani"),
        ("QAR", "Qatari Rial"),
        ("RON", "Romanian Leu"),
        ("RSD", "Serbian Dinar"),
        ("RUB", "Russian Ruble"),
        ("RWF", "Rwandan Franc"),
        ("SAR", "Saudi Riyal"),
        ("SBD", "Solomon Islands Dollar"),
        ("SCR", "Seychellois Rupee"),
        ("SDG", "Sudanese Pound"),
        ("SEK", "Swedish Krona"),
        ("SGD", "Singapore Dollar"),
        ("SHP", "Saint Helena Pound"),
        ("SLL", "Sierra Leonean Leone"),
        ("SOS", "Somali Shilling"),
        ("SRD", "Surinamese Dollar"),
        ("STD", "São Tomé and Príncipe Dobra"),
        ("SVC", "Salvadoran Colón"),
        ("SYP", "Syrian Pound"),
        ("SZL", "Swazi Lilangeni"),
        ("THB", "Thai Baht"),
        ("TJS", "Tajikistani Somoni"),
        ("TMT", "Turkmenistani Manat"),
        ("TND", "Tunisian Dinar"),
        ("TOP", "Tongan Paʻanga"),
        ("TRY", "Turkish Lira"),
        ("TTD", "Trinidad and Tobago Dollar"),
        ("TWD", "New Taiwan Dollar"),
        ("TZS", "Tanzanian Shilling"),
        ("UAH", "Ukrainian Hryvnia"),
        ("UGX", "Ugandan Shilling"),
        ("USD", "United States Dollar"),
        ("UYU", "Uruguayan Peso"),
        ("UZS", "Uzbekistan Som"),
        ("VEF", "Venezuelan Bolívar Fuerte"),
        ("VND", "Vietnamese Dong"),
        ("VUV", "Vanuatu Vatu"),
        ("WST", "Samoan Tala"),
        ("XAF", "CFA Franc BEAC"),
        ("XAG", "Silver (troy ounce)"),
        ("XAU", "Gold (troy ounce)"),
        ("XCD", "East Caribbean Dollar"),
        ("XDR", "Special Drawing Rights"),
        ("XOF", "CFA Franc BCEAO"),
        ("XPD", "Palladium Ounce"),
        ("XPF", "CFP Franc"),
        ("XPT", "Platinum Ounce"),
        ("YER", "Yemeni Rial"),
        ("ZAR", "South African Rand"),
        ("ZMK", "Zambian Kwacha (pre-2013)"),
        ("ZMW", "Zambian Kwacha"),
        ("ZWL", "Zimbabwean Dollar"),
    ]
)

CURRENCY_SYMBOLS = {
    "ALL": "Lek",
    "AFN": "؋",
    "ARS": "$",
    "AWG": "ƒ",
    "AUD": "$",
    "AZN": "ман",
    "BSD": "$",
    "BBD": "$",
    "BYR": "p.",
    "BZD": "BZ$",
    "BMD": "$",
    "BOB": "$b",
    "BAM": "KM",
    "BWP": "P",
    "BGN": "лв",
    "BRL": "R$",
    "BND": "$",
    "KHR": "៛",
    "CAD": "$",
    "KYD": "$",
    "CLP": "$",
    "CNY": "¥",
    "COP": "$",
    "CRC": "₡",
    "HRK": "kn",
    "CUP": "₱",
    "CZK": "Kč",
    "DKK": "kr",
    "DOP": "RD$",
    "XCD": "$",
    "EGP": "£",
    "SVC": "$",
    "EEK": "kr",
    "EUR": "€",
    "FKP": "£",
    "FJD": "$",
    "GHC": "¢",
    "GIP": "£",
    "GTQ": "Q",
    "GGP": "£",
    "GYD": "$",
    "HNL": "L",
    "HKD": "$",
    "HUF": "Ft",
    "ISK": "kr",
    "INR": "₹",
    "IDR": "Rp",
    "IRR": "﷼",
    "IMP": "£",
    "ILS": "₪",
    "JMD": "J$",
    "JPY": "¥",
    "JEP": "£",
    "KZT": "лв",
    "KPW": "₩",
    "KRW": "₩",
    "KGS": "лв",
    "LAK": "₭",
    "LVL": "Ls",
    "LBP": "£",
    "LRD": "$",
    "LTL": "Lt",
    "MKD": "ден",
    "MYR": "RM",
    "MUR": "₨",
    "MXN": "$",
    "MNT": "₮",
    "MZN": "MT",
    "NAD": "$",
    "NPR": "₨",
    "ANG": "ƒ",
    "NZD": "$",
    "NIO": "C$",
    "NGN": "₦",
    "NOK": "kr",
    "OMR": "﷼",
    "PKR": "₨",
    "PAB": "B/.",
    "PYG": "Gs",
    "PEN": "S/.",
    "PHP": "₱",
    "PLN": "zł",
    "QAR": "﷼",
    "RON": "lei",
    "RUB": "руб",
    "SHP": "£",
    "SAR": "﷼",
    "RSD": "Дин.",
    "SCR": "₨",
    "SGD": "$",
    "SBD": "$",
    "SOS": "S",
    "ZAR": "S",
    "LKR": "₨",
    "SEK": "kr",
    "CHF": "CHF",
    "SRD": "$",
    "SYP": "£",
    "TWD": "NT$",
    "THB": "฿",
    "TTD": "TT$",
    "TRL": "₤",
    "TVD": "$",
    "UAH": "₴",
    "GBP": "£",
    "USD": "$",
    "UYU": "$U",
    "UZS": "лв",
    "VEF": "Bs",
    "VND": "₫",
    "YER": "﷼",
    "ZWD": "Z$",
}


class Currency:
    __slots__ = ("code",)

    def __init__(self, code):
        self.code = code

    @property
    def name(self):
        return AVAILABLE_CURRENCIES.get(self.code, "")

    @property
    def symbol(self):
        return CURRENCY_SYMBOLS.get(self.code, "")

    def __str__(self):
        return self.code


class CurrencyField(AdaptableMixin, SelectField):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.choices = sorted(AVAILABLE_CURRENCIES.items(), key=lambda x: x[1])
        if not self.flags.required:
            self.choices.insert(0, ("", "-----------"))

    def adapt_data(self):
        if isinstance(self.data, str):
            self.data = Currency(self.data)
        else:
            self.data = [Currency(d) for d in self.data]


class FontDef:
    def __init__(self, filename, family, sha, size):
        self.filename = filename
        self.family = family
        self.sha = sha
        self.size = size

    @property
    def blob_path(self):
        return f"{self.sha[:2]}/{self.sha[2:]}.ttf"


AVAILABLE_FONTS = {
    f.filename: f
    for f in [
        FontDef(
            "Allan-Regular.ttf",
            "Allan Normal",
            "7149dbb8c888c7fea06553d0c7a6d4190318bfa8",
            56460,
        ),
        FontDef(
            "Allan-Bold.ttf",
            "Allan Bold",
            "a452d8e0fcfa1a29aed2034988f6b2f8395a5477",
            115328,
        ),
        FontDef(
            "Arvo-Regular.ttf",
            "Arvo Normal",
            "9d5d3fca52ada72c3885b3df7bd77edc3a9a31a5",
            40340,
        ),
        FontDef(
            "OpenSans-Regular.ttf",
            "Open Sans Normal",
            "3564ed0b5363df5cf277c16e0c6bedc5a682217f",
            217360,
        ),
        FontDef(
            "OpenSans-Italic.ttf",
            "Open Sans Italic",
            "f1692eac564e95023e4da341a1b89baae7a65155",
            212896,
        ),
        FontDef(
            "OpenSans-Bold.ttf",
            "Open Sans Bold",
            "c1691e8168b2596af8a00162bac60dbe605e9e36",
            224592,
        ),
        FontDef(
            "OpenSans-BoldItalic.ttf",
            "Open Sans Bold Italic",
            "cea7b25e625f8f42d09c3034aad8afd826e9941a",
            213292,
        ),
    ]
}


class Font:
    __slots__ = ("name",)

    def __init__(self, name):
        self.name = name

    @property
    def url(self):
        font = AVAILABLE_FONTS[self.name]
        return "https://signagewidgets.net/app-media/" + font.blob_path

    @property
    def family(self):
        return AVAILABLE_FONTS[self.name].family

    @property
    def style(self):
        return jinja2.Markup(
            """
            <style>
              @font-face {
                font-family: '%s';
                src: url('%s') format('truetype');
              }
            </style>"""
            % (self.family, self.url)
        )


class FontField(AdaptableMixin, SelectField):
    adapt_class = Font

    def __init__(self, *args, **kwargs):
        kwargs["choices"] = [(f.filename, f.filename) for f in AVAILABLE_FONTS.values()]
        kwargs["default"] = kwargs["choices"][0][0]
        super().__init__(*args, **kwargs)


class GoogleSheet:
    __slots__ = ("_sheet_id",)

    def __init__(self, sheet_id):
        self._sheet_id = sheet_id

    def range_size(self, range):
        match = re.match(
            r"(?:(?:\w*|\'[^\']*\'|\"[^\"]*\")!)?\$?([a-z]+)\$?(\d+)(?::\$?([a-z]+)\$?(\d+))?",
            range.lower(),
        )
        if not match:
            raise ValueError('Invalid range, must be in the format "A1:C2"')

        start_col, start_row, end_col, end_row = match.groups()

        if end_col is None and end_row is None:
            return (1, 1)

        return (
            sum((ord(l) - 96) * (26 ** i) for i, l in enumerate(reversed(end_col)))
            - sum((ord(l) - 96) * (26 ** i) for i, l in enumerate(reversed(start_col)))
            + 1,
            int(end_row) - int(start_row) + 1,
        )

    def get_range(self, *ranges):
        ranges = [r.strip() for sublist in ranges for r in sublist.split(",")]

        res = utils.get_url(self.get_range_url(*ranges))
        return res.json()

    def get_range_url(self, *ranges):
        ranges = [r.strip() for sublist in ranges for r in sublist.split(",")]
        return "https://signagewidgets.net/sheet/%s/%s" % (
            self._sheet_id,
            ",".join(ranges),
        )

    def get_range_data(self, *ranges):
        return jinja2.Markup(json.dumps(self.get_range(*ranges)))


class GoogleSheetsURLField(StringField):
    RE_SHEET_ID = re.compile(r".*\/spreadsheets\/d\/([a-zA-Z0-9-_]+)\/.*$")

    def __init__(self, *args, **kwargs):
        kwargs["validators"].append(validators.Regexp(self.RE_SHEET_ID))
        super().__init__(*args, **kwargs)

    def adapt_data(self):
        match = self.RE_SHEET_ID.match(self.data)
        self.data = GoogleSheet(match.groups(1))


class Instagram:
    __slots__ = ("input_value",)

    def __init__(self, input_value):
        self.input_value = input_value

    @property
    def embeds(self):
        logger.debug("returning instagram mocked embeds")
        return "/.instagram/mock_data"

    @property
    def feed_url(self):
        logger.debug("returning instagram mocked url")
        return "/.instagram/mock_data"

    @property
    def feed_data(self):
        logger.debug("returning instagram mocked data")
        return jinja2.Markup(INSTAGRAM_FEED)


class InstagramField(AdaptableMixin, StringField):
    adapt_class = Instagram


class Location:
    __slots__ = (
        "city",
        "latitude",
        "longitude",
        "_tz",
        "_cached_forecast",
        "_cached_forecast_ext",
    )

    def __init__(self, name, lat, lng, tz):
        self.city = name
        self.latitude = lat
        self.longitude = lng
        self._tz = tz
        self._cached_forecast = None
        self._cached_forecast_ext = None

    @property
    def forecast_url(self):
        return f"https://signagewidgets.net/weather/forecast/{self.latitude:.3f},{self.longitude:.3f}"

    @property
    def extended_forecast_url(self):
        return f"https://signagewidgets.net/weather/forecast/{self.latitude:.3f},{self.longitude:.3f}?extended=1"

    def get_forecast_data(self, extended=False):
        response = utils.get_url(
            self.extended_forecast_url if extended else self.forecast_url
        )
        return jinja2.Markup(response.data.decode("utf-8"))

    @property
    def forecast_data(self):
        if not self._cached_forecast:
            self._cached_forecast = self.get_forecast_data()

        return self._cached_forecast

    @property
    def extended_forecast_data(self):
        if not self._cached_forecast_ext:
            self._cached_forecast_ext = self.get_forecast_data(extended=True)

        return self._cached_forecast_ext

    @property
    def timezone(self):
        return self._tz.zone

    @property
    def timezone_offset(self):
        now = datetime.datetime.now()
        return self._tz.utcoffset(now)

    @property
    def timezone_dst(self):
        now = datetime.datetime.now()
        return bool(self._tz.dst(now))


AVAILABLE_LOCATIONS = [
    Location("Barcelona", 41.3851, 2.1734, pytz.timezone("Europe/Madrid")),
    Location("Delhi", 28.7041, 77.1025, pytz.timezone("Asia/Kolkata")),
    Location("Dubai", 25.2048, 55.2708, pytz.timezone("Asia/Dubai")),
    Location("London", 51.5074, 0.1278, pytz.timezone("Europe/London")),
    Location("New York", 40.7128, 74.0060, pytz.timezone("America/New_York")),
    Location("Paris", 48.8566, 2.3522, pytz.timezone("Europe/Paris")),
    Location("Shanghai", 31.2304, 121.4737, pytz.timezone("Asia/Shanghai")),
    Location("São Paulo", 23.5558, 46.6396, pytz.timezone("America/Sao_Paulo")),
    Location("Tokyo", 35.6762, 139.6503, pytz.timezone("Asia/Tokyo")),
]
AVAILABLE_LOCATIONS_DICT = {l.city: l for l in AVAILABLE_LOCATIONS}


class LocationField(AdaptableMixin, SelectField):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.choices = [(l.city, l.city) for l in AVAILABLE_LOCATIONS]
        if not self.flags.required:
            self.choices.insert(0, ("", "-----------"))

    def adapt_data(self):
        self.data = AVAILABLE_LOCATIONS_DICT[self.data]


class StockExchange:
    __slots__ = ("_stock_name",)

    def __init__(self, stock_name):
        self._stock_name = stock_name

    @property
    def stock_url(self):
        return "https://signagewidgets.net/stockexchange/%s" % (self._stock_name,)

    @property
    def stock_data(self):
        try:
            res = utils.get_url(self.stock_url)
        except Exception:
            stocks = {
                "stocks": [
                    {
                        "symbol": symbol,
                        "stock_exchange": None,
                        "change_in_percent": None,
                        "last_trade_price_only": None,
                        "open": None,
                        "previous_close": None,
                        "average_daily_volume": None,
                    }
                    for symbol in self._stock_name.split(",")
                ]
            }
            return jinja2.Markup(json.dumps(stocks))

        return jinja2.Markup(res.data.decode("utf-8"))

    @property
    def high_freq_url(self):
        return "https://signagewidgets.net/alphavantage/%s" % (self._stock_name,)

    @property
    def high_freq_data(self):
        try:
            res = utils.get_url(self.high_freq_url)
        except Exception:
            stocks = {
                "stocks": [
                    {
                        "symbol": symbol,
                        "stock_exchange": None,
                        "change_in_percent": None,
                        "last_trade_price_only": None,
                        "open": None,
                        "previous_close": None,
                        "average_daily_volume": None,
                    }
                    for symbol in self._stock_name.split(",")
                ]
            }
            return jinja2.Markup(json.dumps(stocks))

        return jinja2.Markup(res.data.decode("utf-8"))


class StockExchangeField(AdaptableMixin, StringField):
    adapt_class = StockExchange


class Twitter:
    __slots__ = ("input_value",)

    def __init__(self, input_value):
        self.input_value = input_value

    @property
    def feed_url(self):
        logger.debug("returning twitter mocked data")
        return "/.twitter/mock_data"

    @property
    def feed_data(self):
        logger.debug("returning twitter mocked data")
        return jinja2.Markup(TWITTER_FEED)


class TwitterField(AdaptableMixin, StringField):
    adapt_class = Twitter


class WebFeedImage:
    __slots__ = ("url", "width", "height")

    def __init__(self, url):
        self.url = url
        self.width = 0
        self.height = 0


class WebFeedMedia:
    __slots__ = ("url", "width", "height")

    def __init__(self, url):
        self.url = url
        self.width = 0
        self.height = 0
        self.duration = 0


class WebFeedEntry:
    __slots__ = (
        "is_current",
        "title",
        "content",
        "publish_date",
        "image",
        "video",
        "author_image",
        "like_count",
        "comment_count",
        "data",
    )

    def __init__(self, entry):
        self.is_current = True

        self.title = entry["title"]
        self.content = entry["content"]
        self.publish_date = entry["published_at"]

        self.image = None
        if (
            entry.get("media_metadata", {}).get("url")
            and entry.get("media_metadata", {}).get("kind") == "image"
        ):
            self.image = WebFeedImage(entry["media_metadata"]["url"])

        self.video = None
        if (
            entry.get("media_metadata", {}).get("url")
            and entry.get("media_metadata", {}).get("kind") == "video"
        ):
            self.video = WebFeedMedia(entry["media_metadata"])

        self.author_image = None

        try:
            self.like_count = entry["metadata"]["likes"]["summary"]["total_count"]
        except Exception:
            self.like_count = 0

        try:
            self.comment_count = entry.metadata["comments"]["summary"]["total_count"]
        except Exception:
            self.comment_count = 0

        self.data = entry["metadata"] or {}


class WebFeed:
    __slots__ = ("url", "title", "subtitle", "_entries")

    def __init__(self, url, title, subtitle, entries):
        self.url = url
        self.title = title
        self.subtitle = subtitle
        self._entries = entries

    def with_attrs(self, *attrs):
        return self

    @property
    def current(self):
        return self

    @property
    def image(self):
        return None

    def __len__(self):
        return len(self._entries)

    def __iter__(self):
        return iter(self._entries)

    def __getitem__(self, key):
        if isinstance(key, slice):
            return self.__class__(
                url=self.url,
                title=self.tile,
                subtitle=self.subtitle,
                entries=self._entries[key],
            )

        return self._entries[key]


class WebFeedField(AdaptableMixin, StringField):
    def pre_validate(self, form):
        from .rss import process_feed

        if self.data:
            try:
                self.processed_feed = process_feed(self.data)
            except Exception as e:
                raise ValueError(f"Invalid webfeed. Error: {e}")

    def adapt_data(self):
        self.data = WebFeed(
            url=self.data,
            title=self.processed_feed["title"],
            subtitle=self.processed_feed["subtitle"],
            entries=[WebFeedEntry(entry) for entry in self.processed_feed["entries"]],
        )


class DataFile:
    __slots__ = ("_path", "_name", "_metadata_cache")

    def __init__(self, path, name):
        self._path = path
        self._name = name
        self._metadata_cache = None

    @property
    def name(self):
        return self._name

    @property
    def url(self):
        return "/.uploads/" + self._name


class ImageFile(DataFile):
    def _metadata(self):
        if not self._metadata_cache:
            from PIL import Image

            with Image.open(self._path) as img:
                self._metadata_cache = img.size

        return self._metadata_cache

    @property
    def width(self):
        return self._metadata()[0]

    @property
    def height(self):
        return self._metadata()[1]


class VideoFile(DataFile):
    def _metadata(self):
        if not self._metadata_cache:
            self._metadata_cache = utils.safe_probe_metadata(self._path)

        return self._metadata_cache

    @property
    def duration(self):
        return self._metadata()["duration"]

    @property
    def width(self):
        return self._metadata()["width"]

    @property
    def height(self):
        return self._metadata()["height"]


class AudioFile(DataFile):
    def _metadata(self):
        if not self._metadata_cache:
            self._metadata_cache = utils.safe_probe_metadata(self._path)

        return self._metadata_cache

    @property
    def duration(self):
        return self._metadata()["duration"]

    def id3(self, safe=False):
        if safe:
            return jinja2.Markup(json.dumps(self._metadata()))

        return self._metadata()


class UserMediaField(AdaptableMixin, Field):
    def __init__(self, multiple=False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.multiple = multiple
        self.widget = FileInput(multiple=multiple)

    def adapt_data(self):
        import mimetypes

        mimetypes.init()

        if not self.multiple:
            self.data = [self.data]

        files = []

        for file_name in self.data:
            file_path = get_file(file_name)
            if not file_path:
                raise ValueError("received invalid form data")

            file_type = mimetypes.guess_type(file_path)[0].split("/")[0]
            if file_type == "image":
                files.append(ImageFile(file_path, file_name))
            elif file_type == "video":
                files.append(VideoFile(file_path, file_name))
            elif file_type == "audio":
                files.append(AudioFile(file_path, file_name))
            else:
                files.append(DataFile(file_path, file_name))

        if self.multiple:
            self.data = files
        elif len(files) > 0:
            self.data = files[0]
        else:
            self.data = None


DATASINK_TEMPLATE = """
<script type="text/javascript">
    (function() {
      window.%(variable)s = new Promise(function(resolve, reject) {
        window.addEventListener('DOMContentLoaded', function() {
          resolve({
            fields: %(fields)s,
            source: %(data_source)s,
            update: new Promise(function() {})
          });
        }, false);
      });
    })();
</script>
"""


class DataSourceItem:
    _cache = {}

    def __init__(self, entry_count, fields):
        self._entry_count = entry_count
        self._fields = fields

    def _generate_text(self):
        import lorem

        return lorem.paragraph()

    def _generate_image(self):
        width = random.randint(100, 2000)

        vary = 100
        if width > 600:
            vary = 400

        height = random.randint(width - vary, width + vary)

        return {
            "type": "image",
            "url": f"https://picsum.photos/{width}/{height}",
            "width": width,
            "height": height,
        }

    def _generate_video(self):
        return random.choice(VIDEOS)

    def _generate_url(self):
        import uuid

        u = uuid.uuid4()
        return f"http://{u.hex}.com"

    def _generate_datetime(self):
        return datetime.datetime.now() - datetime.timedelta(
            hours=random.randint(-20000, 20000)
        )

    def _generate_rows(self):
        rows = []
        for i in range(0, self._entry_count):
            row = {}
            for field in self._fields:
                if field["type"] == "text":
                    data = self._generate_text()
                elif field["type"] == "url":
                    data = self._generate_url()
                elif field["type"] == "image":
                    data = self._generate_image()
                elif field["type"] == "date":
                    date = self._generate_datetime()
                    data = date.strftime("%Y-%m-%d")
                elif field["type"] == "time":
                    date = self._generate_datetime()
                    data = date.strftime("%H:%M:%S")
                elif field["type"] == "datetime":
                    date = self._generate_datetime()
                    data = date.strftime("%Y-%m-%dT%H:%M:%SZ")
                elif field["type"] == "boolean":
                    data = random.choice([True, False])
                elif field["type"] == "number":
                    num_decimals = random.randint(1, 3)
                    data = round(random.uniform(1, 500), num_decimals)
                elif field["type"] == "integer":
                    data = random.randint(1, 500)
                elif field["type"] == "video":
                    data = self._generate_video()
                elif field["type"] == "media":
                    if random.choice([True, True, False]):
                        data = self._generate_image()
                    else:
                        data = self._generate_video()

                row[field["name"]] = data

            rows.append(row)

        return rows

    def _render(self, data_source):
        from jinja2 import Markup

        data_fields = {}
        for field in self._fields:
            data_fields[field["name"]] = True

        if not self._cache.get((data_source, self._entry_count)):
            self._cache[(data_source, self._entry_count)] = self._generate_rows()

        return Markup(
            DATASINK_TEMPLATE
            % {
                "variable": data_source,
                "fields": json.dumps(data_fields),
                "data_source": json.dumps(
                    self._cache[(data_source, self._entry_count)]
                ),
            }
        )


class DataSourceField(AdaptableMixin, IntegerField):
    def __init__(self, fields, *args, **kwargs):
        self.fields = fields
        super().__init__(*args, **kwargs)

    def adapt_data(self):
        self.data = DataSourceItem(self.data, self.fields)
