import logging
import os
import re
import socket
import time
from datetime import datetime
from html.parser import HTMLParser
from io import BytesIO, StringIO
from urllib.parse import urlparse, urljoin

import feedparser

from . import samples
from . import utils


logger = logging.getLogger("onsigntv.rss")


class HtmlScrubber(HTMLParser):
    def __init__(self):
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs = True
        self.text = StringIO()

    def handle_data(self, d):
        self.text.write(d)

    def get_data(self):
        return self.text.getvalue()


def force_text(text):
    try:
        s = HtmlScrubber()
        s.feed(text)
        return re.sub(r"<(?!\s)", "< ", s.get_data().strip())
    except Exception:
        return ""


class AtomRSSParser:
    def __init__(self):
        self.start_time = datetime.now()

    def process_feed(self, feed_body, max_entries=20, feed_headers=None):
        feed = feedparser.parse(BytesIO(feed_body), response_headers=feed_headers)

        processed_entries = []
        for i, entry in enumerate(feed.entries, start=1):
            if len(processed_entries) >= max_entries:
                break

            processed_entry = self.process_entry(entry)
            if processed_entry:
                processed_entry["position"] = i
                processed_entries.append(processed_entry)

        if processed_entries:
            return {
                "title": feed.feed.get("title", ""),
                "subtitle": feed.feed.get("subtitle", ""),
                "entries": processed_entries,
            }

    def process_entry(self, entry):
        guid = self.get_entry_guid(entry)
        guid = guid.replace('"', "").replace("\\", "").strip()

        if not guid:
            return

        return {
            "guid": guid,
            "title": self.parse_entry_title(entry),
            "content": self.parse_entry_content(entry),
            "published_at": self.parse_entry_publish_time(entry),
            "entry_url": self.parse_entry_url(entry),
            "media_url": self.guess_media_url(entry),
            "metadata": self.parse_metadata(entry),
        }

    def get_entry_guid(self, entry):
        return (
            entry.get("guid")
            or entry.get("link")
            or entry.get("linkfoto")
            or entry.get("title")
        )

    def parse_entry_title(self, entry):
        return force_text(entry.get("title"))

    def parse_entry_content(self, entry):
        return force_text(entry.get("description", ""))

    def parse_entry_publish_time(self, entry):
        try:
            if entry.get("published_parsed"):
                return datetime(*entry.get("published_parsed")[:6])
        except Exception:
            return self.start_time

    def parse_entry_url(self, entry):
        return entry.get("link", entry.get("linkfoto"))

    def parse_metadata(self, entry):
        if isinstance(entry, list):
            return [self.parse_metadata(v) for v in entry]
        elif isinstance(entry, dict):
            return {k: self.parse_metadata(v) for k, v in entry.items()}
        elif isinstance(entry, time.struct_time):
            try:
                return datetime(*entry[:6]).strftime("%Y-%m-%dT%H:%M:%SZ")
            except Exception:
                return None
        elif isinstance(entry, datetime):
            return entry.strftime("%Y-%m-%dT%H:%M:%SZ")

        return entry

    def guess_media_url(self, entry):
        # UOL puts their image in a completely different location
        if "linkfoto" in entry:
            return entry.get("linkfoto")

        # Try to see if the feed explicitly listed a media.
        for media in entry.get("media_content", []):
            if not media.get("url"):
                continue

            checks = [
                media.get("type", "").startswith("image/"),
                media.get("medium") == "image",
                media.get("media") == "image",
                re.match(r"^.*\.(jpe?g|png)$", media["url"], re.I),
                media.get("type", "").startswith("video/"),
                media.get("medium") == "video",
                media.get("media") == "video",
                re.match(r"^.*\.(avi|mp4)$", media["url"], re.I),
            ]

            if any(checks):
                # Circumvent thumbnail generators, like Yahoo or Estadao.
                prefix = "https://"
                if prefix not in media["url"]:
                    prefix = "http://"

                return prefix + media["url"].rsplit(prefix, 1)[-1]

        # Flickr uses an image link
        for link in entry.get("links", []):
            if link.get("href", "") and (
                link.get("type", "").startswith("image/")
                or link.get("type", "").startswith("video/")
            ):
                return link["href"]

        # Let's use the image referenced in the description.
        match = re.search(
            r'<\s*?img.+?src\s*?=\s*(?:"(.+?)"|\'(.+?)\').*?>',
            entry.get("description", ""),
        )
        if match:
            image = match.groups()[0] or match.groups()[1]
            # Try to get the full size images from Facebook
            if "fbcdn" in image and image.endswith("_s.jpg"):
                return image[:-6] + "_n.jpg"

            if "tumblr.com" in image:
                return image

            match = re.search(r"glbimg\.com.*?=/\d+x\d+/(?:\w+?/)?(.+)", image)
            if match:
                return "http://" + match.groups()[0]


def get_opengraph_url(base_url, entry):
    # By now we know the feed isn't going to help us by providing an image.
    # Let's download the linked HTML and try to find an image from Open Graph.
    url = urljoin(base_url, entry["entry_url"])
    try:
        res = utils.get_url(url)
        match = re.search(
            r"(<\s*?meta[^<>]+?og:image[^<>]+?>)",
            res.data.decode("ascii", errors="ignore"),
        )
        if match:
            match = re.search(
                r'content\s*?=\s*(?:"(.+?)"|\'(.+?)\')', match.groups()[0]
            )
            if match:
                entry["media_url"] = urljoin(
                    entry["entry_url"], match.groups()[0] or match.groups()[1]
                )
    except Exception as e:
        logger.info(f"error: {url} - {e} ")


def get_metadata(url):
    metadata = {}

    if not url:
        return metadata

    parsed = urlparse(url, scheme="http")
    i, ext = os.path.splitext(parsed.path)
    ext = ext.lower()
    if ext in [".mp3", ".aac", ".ac3"]:
        media_kind = None
    elif ext in [".mkv", ".avi", ".mp4", ".mpg", ".mpeg"]:
        media_kind = "video"
    else:
        media_kind = "image"

    if media_kind:
        metadata["url"] = url
        metadata["kind"] = media_kind

    return metadata


def process_feed(url, max_entries=6, force=False):
    is_sample = url.lower().strip(" '\"") == "sample"
    if is_sample:
        res = utils.SimpleResponse(
            "https://signagewidgets.net/samples/rss.xml",
            samples.RSS,
            200,
            {
                "Content-Type": "text/xml",
                "Date": "Mon, 30 Aug 2021 17:23:39 GMT",
                "Last-Modified": "Tue, 26 Apr 2016 19:17:31 GMT",
            },
        )
    else:
        parsed_url = urlparse(url, scheme="http")

        if parsed_url.scheme not in ("http", "https"):
            raise ValueError("invalid feed protocol")

        if socket.gethostbyname(parsed_url.netloc) == "127.0.0.1":
            raise ValueError("invalid feed host")

        if parsed_url.netloc.endswith("facebook.com") and len(parsed_url.path) > 1:
            raise ValueError("facebook pages are not available on simulator")

        res = utils.get_url(url)

    parser = AtomRSSParser()

    processed_feed = parser.process_feed(
        res.data, max_entries=max_entries, feed_headers=res.headers
    )

    if not processed_feed:
        raise ValueError("feed is empty")

    for entry in processed_feed["entries"]:
        if entry.get("entry_url") and not entry.get("media_url") and not is_sample:
            get_opengraph_url(res.url, entry)

        if entry.get("media_url"):
            entry["media_metadata"] = get_metadata(entry["media_url"])

    return processed_feed
