import datetime
import json
import logging
import random
import re
from collections import OrderedDict
from dataclasses import dataclass

import jinja2
import pytz
from wtforms import (
    Field,
    IntegerField,
    SelectField,
    SelectMultipleField,
    StringField,
    validators,
)
from wtforms.widgets import FileInput, Input, Select, TextInput

from . import utils
from .samples import INSTAGRAM_FEED, TWITTER_FEED, VIDEOS
from .storage import create_file_path, get_file, save_file

logger = logging.getLogger("onsigntv.fields")


class AdaptableMixin:
    def adapt(self):
        if self.data and not self.errors:
            self.adapt_data()

    def adapt_data(self):
        self.data = self.adapt_class(self.data)


AIRPORT_CHOICES = {
    "CAN": "Guangzhou Baiyun International Airport",
    "ATL": "Hartsfield–Jackson Atlanta International Airport",
    "DEN": "Denver International Airport",
    "HND": "Tokyo Haneda Airport",
    "DEL": "Indira Gandhi International Airport",
    "DXB": "Dubai International Airport",
    "LHR": "Heathrow Airport",
    "MEX": "Mexico City International Airport",
    "GRU": "Guarulhos International Airport",
}


class Airport:
    def __init__(self, code, name):
        self._code = code
        self._name = name

    def __str__(self):
        return self._code

    def flight_url(self, kinds=["departures", "arrivals"]):
        flight_type = ",".join(kinds)

        return f"/.aviation/mock_data/{self._name}/{flight_type}"


class AirportField(AdaptableMixin, SelectField):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.choices = list(AIRPORT_CHOICES.items())

        if not self.flags.required:
            self.choices.insert(0, ("", "-----------"))

    def adapt_data(self):
        self.data = Airport(self.data, AIRPORT_CHOICES.get(self.data))


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
            r, g, b, a = (int(self.data[i : i + 2], 16) for i in range(1, 9, 2))
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
        self.data = Currency(self.data)


class MultiCurrencyField(CurrencyField, SelectMultipleField):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs, widget=Select(multiple=True))

    def adapt_data(self):
        self.data = [Currency(d) for d in self.data]


class FontWeight:
    LIGHT = 300
    NORMAL = 400
    BOLD = 700
    ULTRA_BOLD = 800


class FontStyle:
    NORMAL = "normal"
    ITALIC = "italic"


@dataclass
class FontDef:
    filename: str
    family: str
    weight: FontWeight
    style: FontStyle
    sha: str
    size: int
    alphabet: str = "latin"

    @property
    def extension(self):
        return self.filename.split(".")[1]

    @property
    def blob_path(self):
        return f"{self.sha[:2]}/{self.sha[2:]}.{self.extension}"


AVAILABLE_FONTS = {
    f.filename: f
    for f in [
        FontDef(
            "Allan-Regular.ttf",
            "Allan",
            FontWeight.NORMAL,
            FontStyle.NORMAL,
            "8f1651ec01b88145a37f69715af9936fee766e5d",
            44876,
        ),
        FontDef(
            "Allan-Bold.ttf",
            "Allan",
            FontWeight.BOLD,
            FontStyle.NORMAL,
            "e658858648cdd3d69bab08a1ed6e2d54765e0695",
            61500,
        ),
        FontDef(
            "Arvo-Regular.ttf",
            "Arvo",
            FontWeight.NORMAL,
            FontStyle.NORMAL,
            "3857248afcedf01b6e9dc0048f4ca662bc328493",
            38596,
        ),
        FontDef(
            "Arvo-Italic.ttf",
            "Arvo",
            FontWeight.NORMAL,
            FontStyle.ITALIC,
            "a06e1dda1e20a7a289a943ec45db074db1dfacf2",
            34968,
        ),
        FontDef(
            "Arvo-Bold.ttf",
            "Arvo",
            FontWeight.BOLD,
            FontStyle.NORMAL,
            "0f5c7895d87238a42e7e1e15396bb46591063a65",
            37480,
        ),
        FontDef(
            "Arvo-BoldItalic.ttf",
            "Arvo",
            FontWeight.BOLD,
            FontStyle.ITALIC,
            "70c487c81a8cd53165d4d41abdcfa35dbc9eb7cd",
            36692,
        ),
        FontDef(
            "Audiowide-Regular.ttf",
            "Audiowide",
            FontWeight.NORMAL,
            FontStyle.NORMAL,
            "651503b7a0a89f49f78f14d04c62f811853573cd",
            47676,
        ),
        FontDef(
            "Bangers.ttf",
            "Bangers",
            FontWeight.NORMAL,
            FontStyle.NORMAL,
            "9c81590199c778e14e4a7b0e9a7543288779a7ba",
            96116,
        ),
        FontDef(
            "BreeSerif-Regular.ttf",
            "Bree Serif",
            FontWeight.NORMAL,
            FontStyle.NORMAL,
            "f19ca8ca7c6f79883f331cf66f4a7d4bc5651a42",
            43572,
        ),
        FontDef(
            "CabinSketch-Regular.ttf",
            "Cabin Sketch",
            FontWeight.NORMAL,
            FontStyle.NORMAL,
            "c9ba1b52ae2735e7e255c974e16bfe5f354dde60",
            154600,
        ),
        FontDef(
            "CabinSketch-Bold.ttf",
            "Cabin Sketch",
            FontWeight.BOLD,
            FontStyle.NORMAL,
            "ff53f010c8e0abb5252b332069c92cb3e2febd1e",
            269380,
        ),
        FontDef(
            "CaesarDressing-Regular.ttf",
            "Caesar Dressing",
            FontWeight.NORMAL,
            FontStyle.NORMAL,
            "ebc9bc29dfeddf6feb91f78f062157ff33e50298",
            88528,
        ),
        FontDef(
            "Chewy.ttf",
            "Chewy",
            FontWeight.NORMAL,
            FontStyle.NORMAL,
            "a3ad025edbfd8e4c49ca201e2478d51e1027ef1c",
            40212,
        ),
        FontDef(
            "Cinzel-Regular.ttf",
            "Cinzel",
            FontWeight.NORMAL,
            FontStyle.NORMAL,
            "bdf7f3d0c52a1cde0aeccf80a2bc3c314c4ec014",
            76456,
        ),
        FontDef(
            "Cinzel-Bold.ttf",
            "Cinzel",
            FontWeight.BOLD,
            FontStyle.NORMAL,
            "0b077ab2e24751a85d61bd1c14e1b7300c7f56be",
            76848,
        ),
        FontDef(
            "Cinzel-Black.ttf",
            "Cinzel",
            FontWeight.ULTRA_BOLD,
            FontStyle.NORMAL,
            "3a3452e31f7ee5999f6114447478314a3ff989bd",
            76884,
        ),
        FontDef(
            "CinzelDecorative-Regular.ttf",
            "Cinzel Decorative",
            FontWeight.NORMAL,
            FontStyle.NORMAL,
            "c7c4f19fcfb7cc34ded9341ecc6d1c72ee272dbf",
            58828,
        ),
        FontDef(
            "CinzelDecorative-Bold.ttf",
            "Cinzel Decorative",
            FontWeight.BOLD,
            FontStyle.NORMAL,
            "e28e0c1aaab05e33a1b3b4bdf71072e3ab97f839",
            60700,
        ),
        FontDef(
            "CinzelDecorative-Black.ttf",
            "Cinzel Decorative",
            FontWeight.NORMAL,
            FontStyle.NORMAL,
            "2072783fa89c9424f2f52803caa9725b8ebdb05d",
            61120,
        ),
        FontDef(
            "Courgette-Regular.ttf",
            "Courgette",
            FontWeight.NORMAL,
            FontStyle.NORMAL,
            "0e6826b92f8f80fe2eb803bdef7d81355845e283",
            118784,
        ),
        FontDef(
            "Cousine-Regular.ttf",
            "Cousine",
            FontWeight.NORMAL,
            FontStyle.NORMAL,
            "f3ba9f44fc4b356f30be5514b048239af90ef2e7",
            300208,
        ),
        FontDef(
            "Cousine-Italic.ttf",
            "Cousine",
            FontWeight.NORMAL,
            FontStyle.ITALIC,
            "75d590158e5197d86e4eef21f02d62f749aacc57",
            262528,
        ),
        FontDef(
            "Cousine-Bold.ttf",
            "Cousine",
            FontWeight.BOLD,
            FontStyle.NORMAL,
            "ba31c6a1f8ff3ecdb0e324ecb088f282938ec6fb",
            288572,
        ),
        FontDef(
            "Cousine-BoldItalic.ttf",
            "Cousine",
            FontWeight.BOLD,
            FontStyle.ITALIC,
            "47999c6bb1771dfb17cd104ddbdce5c6b29d2776",
            265160,
        ),
        FontDef(
            "CoveredByYourGrace.ttf",
            "Covered by Your Grace",
            FontWeight.NORMAL,
            FontStyle.NORMAL,
            "c2b2ff79a5c488c1afd4a7662559e37394d22d94",
            50072,
        ),
        FontDef(
            "Creepster-Regular.ttf",
            "Creepster",
            FontWeight.NORMAL,
            FontStyle.NORMAL,
            "7d00ea50354f1d3364e6403054254586fbafc533",
            61368,
        ),
        FontDef(
            "Cuprum-Regular.ttf",
            "Cuprum",
            FontWeight.NORMAL,
            FontStyle.NORMAL,
            "b4e965d30c5b1f05ebe60f02147c274f7d50fa38",
            56088,
        ),
        FontDef(
            "Cuprum-Italic.ttf",
            "Cuprum",
            FontWeight.NORMAL,
            FontStyle.ITALIC,
            "1273c1ffa1bbfaeac10577ae44e04c4d184be499",
            56320,
        ),
        FontDef(
            "Cuprum-Bold.ttf",
            "Cuprum",
            FontWeight.BOLD,
            FontStyle.NORMAL,
            "9966a66ede80b3d3430bd3a8a79e371c7d581392",
            56008,
        ),
        FontDef(
            "Cuprum-BoldItalic.ttf",
            "Cuprum",
            FontWeight.BOLD,
            FontStyle.ITALIC,
            "37cb9a961c513f3738f6b972b9f73e4a06cae43a",
            56304,
        ),
        FontDef(
            "Dosis-Regular.ttf",
            "Dosis",
            FontWeight.NORMAL,
            FontStyle.NORMAL,
            "223f2240a8b3da47bb195e560a46f50fcafd43db",
            72744,
        ),
        FontDef(
            "Dosis-Bold.ttf",
            "Dosis",
            FontWeight.BOLD,
            FontStyle.NORMAL,
            "9f646e03f99c47f3a361ce86163485cefe9731f7",
            72580,
        ),
        FontDef(
            "FontdinerSwanky.ttf",
            "Fontdiner Swanky",
            FontWeight.NORMAL,
            FontStyle.NORMAL,
            "a2cc67b3d669317efbcf57436430086daf914427",
            44500,
        ),
        FontDef(
            "FrederickatheGreat-Regular.ttf",
            "Fredericka the Great",
            FontWeight.NORMAL,
            FontStyle.NORMAL,
            "fa23748932f92c01b80d0e1d6090ff9a133662f3",
            484664,
        ),
        FontDef(
            "GloriaHallelujah.ttf",
            "Gloria Hallelujah",
            FontWeight.NORMAL,
            FontStyle.NORMAL,
            "f8daece907bf486d3ccf7138f34027e37583c862",
            54232,
        ),
        FontDef(
            "GreatVibes-Regular.ttf",
            "Great Vibes",
            FontWeight.NORMAL,
            FontStyle.NORMAL,
            "4dd3bad8fb151d31eedee2676488f94f831bf515",
            154020,
        ),
        FontDef(
            "IMFePIrm28P.ttf",
            "IM Fell DW Pica",
            FontWeight.NORMAL,
            FontStyle.NORMAL,
            "fb0dc84d07898b696db3ec1e25c440e0c8e377b0",
            212864,
        ),
        FontDef(
            "IMFePIit28P.ttf",
            "IM Fell DW Pica",
            FontWeight.NORMAL,
            FontStyle.ITALIC,
            "b4b1437660b9125389e0a531b0f3b7f8cda0c13f",
            240468,
        ),
        FontDef(
            "Inconsolata-Regular.ttf",
            "Inconsolata",
            FontWeight.NORMAL,
            FontStyle.NORMAL,
            "5236122ed33eacc57aa314cedbb46ff31b1a52a2",
            97864,
        ),
        FontDef(
            "Inconsolata-Bold.ttf",
            "Inconsolata",
            FontWeight.BOLD,
            FontStyle.NORMAL,
            "82ff0ef4a72d1414995377a3b30af84381d7b85a",
            98260,
        ),
        FontDef(
            "Lato-Regular.ttf",
            "Lato",
            FontWeight.NORMAL,
            FontStyle.NORMAL,
            "e923c72eda5e50a87e18ff5c71e9ef4b3b6455a3",
            75152,
        ),
        FontDef(
            "Lato-Italic.ttf",
            "Lato",
            FontWeight.NORMAL,
            FontStyle.ITALIC,
            "190187b720ec2f2ff2e4281237e301000e09673f",
            75792,
        ),
        FontDef(
            "Lato-Bold.ttf",
            "Lato",
            FontWeight.BOLD,
            FontStyle.NORMAL,
            "542498221d97bee5bdbccf86ee8890bf8e8005c9",
            73332,
        ),
        FontDef(
            "Lato-BoldItalic.ttf",
            "Lato",
            FontWeight.BOLD,
            FontStyle.ITALIC,
            "6bf491e78e16d3b9c8a55752e1bd658e15ed7f19",
            77732,
        ),
        FontDef(
            "Lobster-Regular.ttf",
            "Lobster",
            FontWeight.NORMAL,
            FontStyle.NORMAL,
            "120c751cd7a77174037c2409ab883ef7efc5edbb",
            396740,
        ),
        FontDef(
            "Lora-Regular.ttf",
            "Lora",
            FontWeight.NORMAL,
            FontStyle.NORMAL,
            "85426a2922125a163b2cffa0570c42e000ba09f7",
            136556,
        ),
        FontDef(
            "Lora-Italic.ttf",
            "Lora",
            FontWeight.NORMAL,
            FontStyle.ITALIC,
            "e369d350db1315c9ecd0cd4a0e70c79c8a8cf518",
            143428,
        ),
        FontDef(
            "Lora-Bold.ttf",
            "Lora",
            FontWeight.BOLD,
            FontStyle.NORMAL,
            "73b65a96e525836154dd558c1899ab523aef081a",
            136276,
        ),
        FontDef(
            "Lora-BoldItalic.ttf",
            "Lora",
            FontWeight.BOLD,
            FontStyle.ITALIC,
            "3c357f9e6aa8c09b28f9839cf2a819eaf6c183a7",
            144092,
        ),
        FontDef(
            "LuckiestGuy.ttf",
            "Luckiest Guy",
            FontWeight.NORMAL,
            FontStyle.NORMAL,
            "7701304fb627ae9caa78cd982dce30d99a591296",
            58324,
        ),
        FontDef(
            "Monoton-Regular.ttf",
            "Monoton",
            FontWeight.NORMAL,
            FontStyle.NORMAL,
            "153a328e43fe091266e300116d93536044d74109",
            49908,
        ),
        FontDef(
            "Montserrat-Regular.ttf",
            "Montserrat",
            FontWeight.NORMAL,
            FontStyle.NORMAL,
            "de57aa03e4821fdbe6c34ec2c895e8b5c914e837",
            197976,
        ),
        FontDef(
            "Montserrat-Bold.ttf",
            "Montserrat",
            FontWeight.BOLD,
            FontStyle.NORMAL,
            "04052dc3b846609216de1e0cbcec337c6b6e74f6",
            198072,
        ),
        # FontDef('Montserrat-Bold-Italic.ttf', 'Montserrat', FontWeight.BOLD, FontStyle.ITALIC, 'ed5e533b6571e33adb6d01298cb8d1a5a2466657', 202492),
        # FontDef('Montserrat-Italic.ttf', 'Montserrat', FontWeight.NORMAL, FontStyle.ITALIC, '4ee8f07c7414009645d03d87cd72df15658fe9f4', 202380),
        FontDef(
            "MountainsofChristmas-Regular.ttf",
            "Mountains of Christmas",
            FontWeight.NORMAL,
            FontStyle.NORMAL,
            "52056676e1d162d9d78e0477e4da9eac5e5e2b9e",
            121024,
        ),
        FontDef(
            "MountainsofChristmas-Bold.ttf",
            "Mountains of Christmas",
            FontWeight.BOLD,
            FontStyle.NORMAL,
            "95a9ee76c1d7a149edbae8986e070c3c21b449e4",
            121828,
        ),
        FontDef(
            "OpenSans-Regular.ttf",
            "Open Sans",
            FontWeight.NORMAL,
            FontStyle.NORMAL,
            "73b8e80d4ff1cf32806a12f296754819c17d4eff",
            129796,
        ),
        FontDef(
            "OpenSans-Italic.ttf",
            "Open Sans",
            FontWeight.NORMAL,
            FontStyle.ITALIC,
            "8eeed9e71e4f905f8421455810c8f9cebf96aa61",
            135380,
        ),
        FontDef(
            "OpenSans-Bold.ttf",
            "Open Sans",
            FontWeight.BOLD,
            FontStyle.NORMAL,
            "266b36edacf112b480a28f0f5acbbe0ebc01b18f",
            129784,
        ),
        FontDef(
            "OpenSans-BoldItalic.ttf",
            "Open Sans",
            FontWeight.BOLD,
            FontStyle.ITALIC,
            "1c28f4b03ffb9b570875af6e0ab5cdada653d61b",
            135108,
        ),
        FontDef(
            "Orbitron-Regular.ttf",
            "Orbitron",
            FontWeight.NORMAL,
            FontStyle.NORMAL,
            "da04191947877377e875e24a89c62c271bc7feb3",
            24368,
        ),
        FontDef(
            "Orbitron-Bold.ttf",
            "Orbitron",
            FontWeight.BOLD,
            FontStyle.NORMAL,
            "8459068027fc0e245f40e0681d7058131f9bddbb",
            24308,
        ),
        FontDef(
            "Oswald-Regular.ttf",
            "Oswald",
            FontWeight.NORMAL,
            FontStyle.NORMAL,
            "d16c1dcb19e0e7572d2dea9d7445c0506c20b25d",
            63900,
        ),
        # FontDef('Oswald-Bold.ttf', 'Oswald', FontWeight.BOLD, FontStyle.NORMAL, 'a6d0bf488eefe0dea9d0e433f0bc706514a7f8f6', 64184),
        FontDef(
            "Pacifico.ttf",
            "Pacifico",
            FontWeight.NORMAL,
            FontStyle.NORMAL,
            "baca1fca7fe74b61cb33aa0da48ec1a3a77bcf49",
            315408,
        ),
        FontDef(
            "PinyonScript-Regular.ttf",
            "Pinyon Script",
            FontWeight.NORMAL,
            FontStyle.NORMAL,
            "7bde9de376b1e78220b4d0e3a63ca6e7146c3ed3",
            58936,
        ),
        FontDef(
            "PlayfairDisplay-Regular.ttf",
            "Playfair Display",
            FontWeight.NORMAL,
            FontStyle.NORMAL,
            "b93c059782bd1c16bc0c5c495d245e2147a7c573",
            192812,
        ),
        FontDef(
            "PlayfairDisplay-Italic.ttf",
            "Playfair Display",
            FontWeight.NORMAL,
            FontStyle.ITALIC,
            "1e0084ef41c9f0c72c0447a5bd4f4902fc370702",
            177224,
        ),
        FontDef(
            "PlayfairDisplay-Bold.ttf",
            "Playfair Display",
            FontWeight.BOLD,
            FontStyle.NORMAL,
            "a01693c7d32826d9626013a283d22748314a2157",
            193136,
        ),
        FontDef(
            "PlayfairDisplay-BoldItalic.ttf",
            "Playfair Display",
            FontWeight.BOLD,
            FontStyle.ITALIC,
            "e9258014d6c7a541dce54e2dda072ef7ba279744",
            177660,
        ),
        FontDef(
            "PlayfairDisplay-Black.ttf",
            "Playfair Display",
            FontWeight.ULTRA_BOLD,
            FontStyle.NORMAL,
            "bfccbb9a4c46f3d3c30d245af74442e730d56723",
            193036,
        ),
        FontDef(
            "PlayfairDisplay-BlackItalic.ttf",
            "Playfair Display",
            FontWeight.ULTRA_BOLD,
            FontStyle.ITALIC,
            "fa47f0f9a0be6d7f5b9cd731ae0acc941b86ed4f",
            177144,
        ),
        FontDef(
            "PTM55FT.ttf",
            "PT Mono",
            FontWeight.NORMAL,
            FontStyle.NORMAL,
            "adebfdd491cb3bf2ebb92ea23e9ec1ec1608f9bc",
            169480,
        ),
        FontDef(
            "PT_Serif-Web-Regular.ttf",
            "PT Serif",
            FontWeight.NORMAL,
            FontStyle.NORMAL,
            "9ea0ea4d9ed8fda292db458366dbd9af013eced7",
            215516,
        ),
        FontDef(
            "PT_Serif-Web-Italic.ttf",
            "PT Serif",
            FontWeight.NORMAL,
            FontStyle.ITALIC,
            "ab129b4c762edcc4724d46ee655f461bfc98bdaa",
            232264,
        ),
        FontDef(
            "PT_Serif-Web-Bold.ttf",
            "PT Serif",
            FontWeight.BOLD,
            FontStyle.NORMAL,
            "581675fd5d3734c5ee1506359190ce467c477e18",
            196092,
        ),
        FontDef(
            "PT_Serif-Web-BoldItalic.ttf",
            "PT Serif",
            FontWeight.BOLD,
            FontStyle.ITALIC,
            "f440f00aae9cf53d7f40d4feb41fa380d063d502",
            193752,
        ),
        FontDef(
            "PT_Sans-Web-Regular.ttf",
            "PT Sans",
            FontWeight.NORMAL,
            FontStyle.NORMAL,
            "641626d5d6a625a1e46e09ceb806cf33d1c1867e",
            278612,
        ),
        FontDef(
            "PT_Sans-Web-Italic.ttf",
            "PT Sans",
            FontWeight.NORMAL,
            FontStyle.ITALIC,
            "fb0639634daaf32b25aa4284fc91256fef10855a",
            270920,
        ),
        FontDef(
            "PT_Sans-Web-Bold.ttf",
            "PT Sans",
            FontWeight.BOLD,
            FontStyle.NORMAL,
            "356c8987ef7a8752108cf7b7a86d1f1bf0c60999",
            288340,
        ),
        FontDef(
            "PT_Sans-Web-BoldItalic.ttf",
            "PT Sans",
            FontWeight.BOLD,
            FontStyle.ITALIC,
            "8909d6fd6c65904e10ae48052fb49a29a3294ea3",
            210224,
        ),
        FontDef(
            "Roboto-Regular.ttf",
            "Roboto",
            FontWeight.NORMAL,
            FontStyle.NORMAL,
            "56c5c0d38bde4c1f1549dda43db37b09c608aad3",
            168260,
        ),
        FontDef(
            "Roboto-Italic.ttf",
            "Roboto",
            FontWeight.NORMAL,
            FontStyle.ITALIC,
            "65f3f6a7e1bd2fa6f2df35e4b07775d7f1dde4f0",
            170504,
        ),
        FontDef(
            "Roboto-Bold.ttf",
            "Roboto",
            FontWeight.BOLD,
            FontStyle.NORMAL,
            "62442a18a9fe9457c1afeabf683d263a691b7798",
            167336,
        ),
        FontDef(
            "Roboto-BoldItalic.ttf",
            "Roboto",
            FontWeight.BOLD,
            FontStyle.ITALIC,
            "2f10ad9e8cab0880182705c4e0fbaeabae706e64",
            171508,
        ),
        FontDef(
            "RobotoCondensed-Regular.ttf",
            "Roboto Condensed",
            FontWeight.NORMAL,
            FontStyle.NORMAL,
            "e0d7acf2ca3dd0ff68f533797bb94b0580397e95",
            166836,
        ),
        FontDef(
            "RobotoCondensed-Italic.ttf",
            "Roboto Condensed",
            FontWeight.NORMAL,
            FontStyle.ITALIC,
            "56725c6d7698dcfee226424bb1f21565f23a0573",
            171724,
        ),
        FontDef(
            "RobotoCondensed-Bold.ttf",
            "Roboto Condensed",
            FontWeight.BOLD,
            FontStyle.NORMAL,
            "15e8faa21a00eb5b40d3837e16960a39d78fe45c",
            166340,
        ),
        FontDef(
            "RobotoCondensed-BoldItalic.ttf",
            "Roboto Condensed",
            FontWeight.BOLD,
            FontStyle.ITALIC,
            "2195d05ea6a9338a69929445e4ddf0a9650dfc12",
            172408,
        ),
        FontDef(
            "RobotoMono-Regular.ttf",
            "Roboto Mono",
            FontWeight.NORMAL,
            FontStyle.NORMAL,
            "10459dd11ec5adb59f3775b062dc06c4abe70a3a",
            86908,
        ),
        FontDef(
            "RobotoMono-Italic.ttf",
            "Roboto Mono",
            FontWeight.NORMAL,
            FontStyle.ITALIC,
            "fae9acb23533e32c69da98c3e288d333245b5b4b",
            93904,
        ),
        FontDef(
            "RobotoMono-Bold.ttf",
            "Roboto Mono",
            FontWeight.BOLD,
            FontStyle.NORMAL,
            "0c75d7b11dacfede72053e40b71849c43c22a454",
            87008,
        ),
        FontDef(
            "RobotoMono-BoldItalic.ttf",
            "Roboto Mono",
            FontWeight.BOLD,
            FontStyle.ITALIC,
            "6be5bc60f9bfb14a8f81d56587d7c4eb266f2a54",
            94148,
        ),
        FontDef(
            "RobotoSlab-Regular.ttf",
            "Roboto Slab",
            FontWeight.NORMAL,
            FontStyle.NORMAL,
            "40da9134dfa586bc4b6c62b6540269d3d497f480",
            125936,
        ),
        FontDef(
            "RobotoSlab-Bold.ttf",
            "Roboto Slab",
            FontWeight.BOLD,
            FontStyle.NORMAL,
            "7bfea10c4050e0bce05c56d9d303788773430fa3",
            126676,
        ),
        FontDef(
            "SansitaOne.ttf",
            "Sansita One",
            FontWeight.NORMAL,
            FontStyle.NORMAL,
            "f282ec693340a87e0e0553a0ab12ce7d82b30b64",
            47440,
        ),
        FontDef(
            "ShadowsIntoLight.ttf",
            "Shadows Into Light",
            FontWeight.NORMAL,
            FontStyle.NORMAL,
            "e512d65b44398e83907215402d477643751c1dfa",
            48468,
        ),
        FontDef(
            "SpecialElite.ttf",
            "Special Elite",
            FontWeight.NORMAL,
            FontStyle.NORMAL,
            "dba5375769650ccf8308f24b73c5a1563d8a4731",
            151068,
        ),
        FontDef(
            "Ultra.ttf",
            "Ultra",
            FontWeight.NORMAL,
            FontStyle.NORMAL,
            "50d3f9625efc43d483764172981f95253a7db40d",
            51084,
        ),
        FontDef(
            "UnifrakturMaguntia-Book.ttf",
            "UnifrakturMaguntia",
            FontWeight.NORMAL,
            FontStyle.NORMAL,
            "604584f388c198a68e1e5afa421ae05e6e4c7dac",
            82576,
        ),
        FontDef(
            "YanoneKaffeesatz-Regular.ttf",
            "Yanone Kaffeesatz",
            FontWeight.NORMAL,
            FontStyle.NORMAL,
            "dd197f6de883dc2ad8c573240888628c099afa9b",
            74644,
        ),
        FontDef(
            "YanoneKaffeesatz-Bold.ttf",
            "Yanone Kaffeesatz",
            FontWeight.BOLD,
            FontStyle.NORMAL,
            "2bf8796f36dc5a0b0bedd2ebc6b2cedd44e7c460",
            74464,
        ),
        FontDef(
            "NotoSans-Regular.ttf",
            "Noto Sans",
            FontWeight.NORMAL,
            FontStyle.NORMAL,
            "6af0b309f2f2af25bfd0f901ed24bd0527c2cbf4",
            556216,
        ),
        FontDef(
            "NotoSans-Italic.ttf",
            "Noto Sans",
            FontWeight.NORMAL,
            FontStyle.ITALIC,
            "4fa74443f61703f22d749de24dbfbf1391753e83",
            403724,
        ),
        FontDef(
            "NotoSans-Bold.ttf",
            "Noto Sans",
            FontWeight.BOLD,
            FontStyle.NORMAL,
            "20f80dbd99b857c66796321d3f596400d1334ca7",
            557380,
        ),
        FontDef(
            "NotoSans-BoldItalic.ttf",
            "Noto Sans",
            FontWeight.BOLD,
            FontStyle.ITALIC,
            "e2104bab749433d65a710c2181bb137b65346c17",
            401608,
        ),
        FontDef(
            "NotoSerif-Regular.ttf",
            "Noto Serif",
            FontWeight.NORMAL,
            FontStyle.NORMAL,
            "3f15509c797a957769316e054c4f7f43ef1d9563",
            375804,
        ),
        FontDef(
            "NotoSerif-Italic.ttf",
            "Noto Serif",
            FontWeight.NORMAL,
            FontStyle.ITALIC,
            "43922a075458e4328bf5a72c1da7b2bbb3b2f0e5",
            350192,
        ),
        FontDef(
            "NotoSerif-Bold.ttf",
            "Noto Serif",
            FontWeight.BOLD,
            FontStyle.NORMAL,
            "0ac1af0607337223d4514685289f07815f573564",
            395916,
        ),
        FontDef(
            "NotoSerif-BoldItalic.ttf",
            "Noto Serif",
            FontWeight.BOLD,
            FontStyle.ITALIC,
            "1aa07f8aece2709fc935bec4bb924ebfcaca55d9",
            360440,
        ),
        FontDef(
            "NotoKufiArabic-Regular.ttf",
            "Noto Kufi Arabic",
            FontWeight.NORMAL,
            FontStyle.NORMAL,
            "dbbdd305fcbee3213319bf561569e2ccb0865f68",
            122736,
            alphabet="arabic",
        ),
        FontDef(
            "NotoKufiArabic-Bold.ttf",
            "Noto Kufi Arabic",
            FontWeight.BOLD,
            FontStyle.NORMAL,
            "aa3f1b258180ccb68d54ac9f5618bb3c5c492c78",
            122900,
            alphabet="arabic",
        ),
        FontDef(
            "NotoNaskhArabic-Regular.ttf",
            "Noto Naskh Arabic",
            FontWeight.NORMAL,
            FontStyle.NORMAL,
            "7768f6235454f9e3c8339306d29a3888e4886f1e",
            132340,
            alphabet="arabic",
        ),
        FontDef(
            "NotoNaskhArabic-Bold.ttf",
            "Noto Naskh Arabic",
            FontWeight.BOLD,
            FontStyle.NORMAL,
            "4853190a92c884920d863bfc4a74dbe1ea7189da",
            132536,
            alphabet="arabic",
        ),
        FontDef(
            "NotoNastaliqUrdu-Regular.ttf",
            "Noto Nastaliq Urdu",
            FontWeight.NORMAL,
            FontStyle.NORMAL,
            "66b824a0dd1eb3fe25b3e1b5b72f712fcf265147",
            581240,
            alphabet="urdu",
        ),
        FontDef(
            "NotoSansGurmukhi-Regular.ttf",
            "Noto Sans Gurmukhi",
            FontWeight.NORMAL,
            FontStyle.NORMAL,
            "71fcc79188f6ca2bad652e39d897bdd000fe6b9f",
            37080,
            alphabet="gurmukhi",
        ),
        FontDef(
            "NotoSansGurmukhi-Bold.ttf",
            "Noto Sans Gurmukhi",
            FontWeight.BOLD,
            FontStyle.NORMAL,
            "6ef0fc53205dce96c5b3c38856a71b1dcd025bad",
            37076,
            alphabet="gurmukhi",
        ),
        FontDef(
            "NotoSansDevanagari-Regular.ttf",
            "Noto Sans Devanagari",
            FontWeight.NORMAL,
            FontStyle.NORMAL,
            "a6bc19d46f8f5200534a75c3ef0bcc17ab1d75f6",
            190960,
        ),
        FontDef(
            "NotoSansDevanagari-Bold.ttf",
            "Noto Sans Devanagari",
            FontWeight.BOLD,
            FontStyle.NORMAL,
            "f070a09e7ba7418a3a36cb4f2cd6612f8708fa27",
            191156,
        ),
        FontDef(
            "NotoSansBengali-Regular.ttf",
            "Noto Sans Bengali",
            FontWeight.NORMAL,
            FontStyle.NORMAL,
            "4b049bc8a97071a829b90eb80fb5fea65587ed81",
            167796,
        ),
        FontDef(
            "NotoSansBengali-Bold.ttf",
            "Noto Sans Bengali",
            FontWeight.BOLD,
            FontStyle.NORMAL,
            "9fdf17c7bd7ac80df09c5d56e192ee28b346ccb6",
            167968,
        ),
        FontDef(
            "NotoSansHebrew-Regular.ttf",
            "Noto Sans Hebrew",
            FontWeight.NORMAL,
            FontStyle.NORMAL,
            "385db6166b42efa9ec6ab07a752a6c3ea44c7af6",
            42284,
        ),
        FontDef(
            "NotoSansHebrew-Bold.ttf",
            "Noto Sans Hebrew",
            FontWeight.BOLD,
            FontStyle.NORMAL,
            "f887595b310566de33193d1b24faa3975490cf20",
            42196,
        ),
        FontDef(
            "NotoSansCJKsc-Light.otf",
            "Noto Sans CJK SC",
            FontWeight.LIGHT,
            FontStyle.NORMAL,
            "0223a3518fe52d18993e9dc9854b6882bc781075",
            8434216,
        ),
        FontDef(
            "NotoSansCJKsc-Regular.otf",
            "Noto Sans CJK SC",
            FontWeight.NORMAL,
            FontStyle.NORMAL,
            "7fb779ea2a8d83d7f80d4a2865d1ebb5e3cf1257",
            8482020,
        ),
        FontDef(
            "NotoSansCJKsc-Bold.otf",
            "Noto Sans CJK SC",
            FontWeight.BOLD,
            FontStyle.NORMAL,
            "60a514fd2a07ca63ebd7f5484951e50cb03f4fc2",
            8716392,
        ),
        FontDef(
            "NotoSansCJKtc-Light.otf",
            "Noto Sans CJK TC",
            FontWeight.LIGHT,
            FontStyle.NORMAL,
            "91dc7b49208ac599bf6e431e46bfa3b321355501",
            5733208,
        ),
        FontDef(
            "NotoSansCJKtc-Regular.otf",
            "Noto Sans CJK TC",
            FontWeight.NORMAL,
            FontStyle.NORMAL,
            "e8a5e3f136711dd493da7b61b0cf55596b58029e",
            5766468,
        ),
        FontDef(
            "NotoSansCJKtc-Bold.otf",
            "Noto Sans CJK TC",
            FontWeight.BOLD,
            FontStyle.NORMAL,
            "bf4ddd1eda61428e3086fc4a71e8ec462bd35f3d",
            5942628,
        ),
        FontDef(
            "NotoSansCJKkr-Light.otf",
            "Noto Sans CJK KR",
            FontWeight.LIGHT,
            FontStyle.NORMAL,
            "03bd5bfbc27f2d2b9bdc8854e4174a300e89a007",
            4713928,
        ),
        FontDef(
            "NotoSansCJKkr-Regular.otf",
            "Noto Sans CJK KR",
            FontWeight.NORMAL,
            FontStyle.NORMAL,
            "5f533d0d5caf3847afa2d78301e7b87b3485ecbc",
            4744692,
        ),
        FontDef(
            "NotoSansCJKkr-Bold.otf",
            "Noto Sans CJK KR",
            FontWeight.BOLD,
            FontStyle.NORMAL,
            "49e50de244558c4c21f43d85b7404cabb970b30b",
            4909668,
        ),
        FontDef(
            "NotoSansCJKjp-Light.otf",
            "Noto Sans CJK JP",
            FontWeight.LIGHT,
            FontStyle.NORMAL,
            "953979a92d817471ebdeef476362b2605098139d",
            4513776,
        ),
        FontDef(
            "NotoSansCJKjp-Regular.otf",
            "Noto Sans CJK JP",
            FontWeight.NORMAL,
            FontStyle.NORMAL,
            "7533dabbd7f41ab48213d0b899d715f11f906b57",
            4548208,
        ),
        FontDef(
            "NotoSansCJKjp-Bold.otf",
            "Noto Sans CJK JP",
            FontWeight.BOLD,
            FontStyle.NORMAL,
            "64638dbf1a299124c1e860c62b149ecf35a91304",
            4691408,
        ),
    ]
}


class Font:
    __slots__ = ("name",)

    def __init__(self, name):
        self.name = name

    @property
    def _font(self):
        return AVAILABLE_FONTS[self.name]

    @property
    def url(self):
        return f"/.font/{self._font.blob_path}"

    @property
    def family(self):
        return jinja2.Markup(f"'{self._font.family}'")

    @property
    def style(self):
        return jinja2.Markup(
            f"""
            <style>
              @font-face {{
                font-family: '{self._font.family}';
                font-weight: '{self._font.weight}';
                font-style: '{self._font.style}';
                src: url('{self.url}') format('truetype');
              }}
            </style>"""
        )


class FontField(AdaptableMixin, SelectField):
    adapt_class = Font

    def __init__(self, *args, **kwargs):
        kwargs["choices"] = [(f.filename, f.filename) for f in AVAILABLE_FONTS.values()]
        if not kwargs.get("default"):
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
            sum((ord(l) - 96) * (26**i) for i, l in enumerate(reversed(end_col)))
            - sum((ord(l) - 96) * (26**i) for i, l in enumerate(reversed(start_col)))
            + 1,
            int(end_row) - int(start_row) + 1,
        )

    def get_range(self, *ranges):
        ranges = [r.strip() for sublist in ranges for r in sublist.split(",")]

        res = utils.get_url(self.get_range_url(*ranges))
        return res.json()

    def get_range_url(self, *ranges):
        ranges = [r.strip() for sublist in ranges for r in sublist.split(",")]
        return "https://signagewidgets.net/sheet/{}/{}".format(
            self._sheet_id,
            ",".join(ranges),
        )

    def get_range_data(self, *ranges):
        return jinja2.Markup(json.dumps(self.get_range(*ranges)))


class GoogleSheetsURLField(AdaptableMixin, StringField):
    RE_SHEET_ID = re.compile(r".*\/spreadsheets\/d\/([a-zA-Z0-9-_]+)\/.*$")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def adapt_data(self):
        match = self.RE_SHEET_ID.match(self.data)
        if match:
            self.data = GoogleSheet(match.groups(1)[0])
        else:
            raise ValueError(f'Invalid sheet URL: "{self.data}"')


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
    Location("London", 51.5074, -0.1278, pytz.timezone("Europe/London")),
    Location("New York", 40.7128, -74.0060, pytz.timezone("America/New_York")),
    Location("Paris", 48.8566, 2.3522, pytz.timezone("Europe/Paris")),
    Location("Shanghai", 31.2304, 121.4737, pytz.timezone("Asia/Shanghai")),
    Location("São Paulo", -23.5558, -46.6396, pytz.timezone("America/Sao_Paulo")),
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
        return f"https://signagewidgets.net/stockexchange/{self._stock_name}"

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
        return f"https://signagewidgets.net/alphavantage/{self._stock_name}"

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
                title=self.title,
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


class ContentList(list):
    pass


class ContentFile:
    __slots__ = ("_path", "_name", "_metadata_cache", "_type")

    def __init__(self, path, name):
        import mimetypes

        self._path = path
        self._name = name
        self._metadata_cache = None

        mimetypes.init()
        file_type = mimetypes.guess_type(self.url)[0]
        if file_type.startswith("application"):
            self._type = file_type.split("/")[1]
        else:
            self._type = file_type.split("/")[0]

    @property
    def id(self):
        return self._name[:6]

    @property
    def name(self):
        return self._name

    @property
    def type(self):
        return self._type

    @property
    def url(self):
        return "/.uploads/" + self._name

    def _serialize(self):
        serialized_content = {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "url": self.url,
        }

        if self.type in ("audio", "video"):
            serialized_content["duration"] = self.duration

        if self.type in ("image", "video"):
            serialized_content["width"] = self.width
            serialized_content["height"] = self.height

        return serialized_content


class ImageFile(ContentFile):
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


class VideoFile(ContentFile):
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


class AudioFile(ContentFile):
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

        if not self.multiple or isinstance(self.data, str):
            self.data = [self.data]

        files = []

        for file_name in self.data:
            file_path = get_file(file_name)
            if not file_path:
                file_path = create_file_path(file_name)
                try:
                    with open(file_path, "rb") as file:
                        save_file(file_path, file.read())
                except Exception:
                    raise ValueError("Received invalid media form data")

            file_type = mimetypes.guess_type(file_path)[0].split("/")[0]
            if file_type == "image":
                files.append(ImageFile(file_path, file_name))
            elif file_type == "video":
                files.append(VideoFile(file_path, file_name))
            elif file_type == "audio":
                files.append(AudioFile(file_path, file_name))
            else:
                files.append(ContentFile(file_path, file_name))

        if self.multiple:
            self.data = ContentList(files)
        elif len(files) > 0:
            self.data = files[0]
        else:
            self.data = None


DATAFEED_TEMPLATE = """
<script type="text/javascript">
  window.%(variable)s = new Promise(function (resolve) {
    var source = '%(data_source)s';
    var fields = '%(fields)s';
    var updateSource = '%(update_source)s';

    function createUpdatePromise(currSource) {
      return new Promise(function (resolve) {
        setTimeout(function () {
          var nextSource = (currSource === source) ? updateSource : source;
          var updatePromise = createUpdatePromise(nextSource);

          resolve({
            fields: JSON.parse(fields),
            source: JSON.parse(nextSource),
            update: updatePromise
          });
        }, 10 * 1000);
      });
    }

    var updatePromise = new Promise(function (resolve) {
      if (%(simulate_updates)s) {
        resolve(createUpdatePromise(source));
      }
    });

    window.signageLoaded.then(function () {
      resolve({
        fields: JSON.parse(fields),
        source: JSON.parse(source),
        update: updatePromise
      });
    });
  });
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
        for i in range(self._entry_count):
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

    def _render(self, data_source, simulate_updates=False):
        from jinja2 import Markup

        data_fields = {}
        for field in self._fields:
            data_fields[field["name"]] = True

        if not self._cache.get((data_source, self._entry_count)):
            self._cache[(data_source, self._entry_count)] = self._generate_rows()

        update_source = None
        if simulate_updates:
            if not self._cache.get((f"_update_{data_source}", self._entry_count)):
                self._cache[(f"_update_{data_source}", self._entry_count)] = (
                    self._generate_rows()
                )

            update_source = self._cache[(f"_update_{data_source}", self._entry_count)]

        return Markup(
            DATAFEED_TEMPLATE
            % {
                "variable": data_source,
                "fields": utils.safe_json(data_fields),
                "data_source": utils.safe_json(
                    self._cache[(data_source, self._entry_count)]
                ),
                "update_source": utils.safe_json(update_source),
                "simulate_updates": json.dumps(simulate_updates),
            }
        )


class AppAttributeField(StringField):
    def __init__(self, attr, **kwargs):
        self.required = attr["required"]
        self.mode = attr["mode"]
        self.attr_type = attr["type"]
        self.player_name = kwargs["label"] = attr["label"]
        self.is_attribute = True

        if self.attr_type == "number":
            kwargs["widget"] = Input(input_type="number")
        else:
            kwargs["widget"] = TextInput()

        super().__init__(**kwargs)

    def __call__(self):
        if self.mode in {"rw", "r"}:
            return super().__call__()

        return ""


class DataSourceField(AdaptableMixin, IntegerField):
    def __init__(self, fields, *args, **kwargs):
        self.fields = fields
        super().__init__(*args, **kwargs)

    def adapt_data(self):
        self.data = DataSourceItem(self.data, self.fields)
