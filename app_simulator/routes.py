import asyncio
import logging
import urllib

from aiohttp_sse import sse_response
from aiohttp.web import Response, FileResponse, HTTPNotFound
from jinja2 import Environment, PackageLoader, select_autoescape
from multidict import MultiDict

from .app_config import SDK_TAG, extract_app_config, render_app_html
from .form import build_form, ALLOWED_FILE_TYPES
from .samples import TWITTER_FEED, INSTAGRAM_FEED
from .storage import get_file, save_file
from .utils import (
    formdata_to_json,
    inject_script_into_html,
)


jinja_env = Environment(
    loader=PackageLoader("app_simulator", "templates"),
    autoescape=select_autoescape(["html", "xml"]),
)

logger = logging.getLogger("onsigntv.routes")


tracked_files = {}


def track_file(x):
    tracked_files[x] = 0


async def list_form_file(request):
    name = request.match_info.get("file_name", "")

    path = request.app["base_path"]
    if name:
        path = path / name

    if path.is_file() and path.name.endswith(".html"):
        logger.debug(f"open a html file: {name}")

        try:
            config = extract_app_config(path.read_text("utf-8"))

            tracked_files.clear()
            logger.debug(f"add {name} to tracked files list")
            track_file(path)

            form = build_form(config)
            form.process()

        except Exception as exp:
            exceptions = [exp]
            logger.info(f"handling exception: {exp}")

            return Response(
                text=jinja_env.get_template("widget_exceptions.html").render(
                    {"exceptions": exceptions}
                ),
                content_type="text/html",
            )

        return Response(
            text=jinja_env.get_template("widget_form.html").render(
                {
                    "form": form,
                    "warnings": config["warnings"],
                    "title": config["title"],
                    "file_name": "/.preview/{}".format(urllib.parse.quote(name)),
                },
            ),
            content_type="text/html",
        )
    elif path.is_file():
        if ".preview/" in request.headers.get("referer", ""):
            return HTTPNotFound()
        elif path.suffix in ALLOWED_FILE_TYPES:
            logger.debug(f"serving file: {name}")
            return FileResponse(path)
        else:
            return HTTPNotFound()
    elif path.is_dir():
        logger.debug("opening directory")

        folder_or_files = []
        if name:
            link = str(path.parent.relative_to(request.app["base_path"]))
            if link == ".":
                link = "/"
            else:
                link = f"/{link}/"

            folder_or_files.append(
                {
                    "name": "Up...",
                    "link": link,
                    "is_up": True,
                }
            )

        for element in sorted(
            path.iterdir(), key=lambda f: (not f.is_dir(), f.name.lower())
        ):
            if element.is_file() and element.suffix not in ALLOWED_FILE_TYPES:
                continue

            if element.name.startswith("."):
                continue

            folder_or_files.append(
                {
                    "name": element.name + ("/" if element.is_dir() else ""),
                    "link": urllib.parse.quote(
                        element.name + ("/" if element.is_dir() else "")
                    ),
                    "is_file": element.is_file(),
                }
            )
        return Response(
            text=jinja_env.get_template("list_files.html").render(
                {
                    "files": folder_or_files,
                    "path": path.absolute(),
                }
            ),
            content_type="text/html",
        )
    else:
        return HTTPNotFound()


async def preview_app(request):
    logger.debug("retrieve data")

    name = request.match_info["file_name"]
    path = request.app["base_path"] / name

    if path not in tracked_files:
        logger.debug(f"add {name} to tracked files list before preview")
        track_file(path)

    formdata = MultiDict()

    request_reader = await request.multipart()

    while True:
        part = await request_reader.next()
        if part is None:
            break

        field_name = part.name
        if part.filename:
            logger.debug(f"field name {field_name} is a file")
            file_byte = await part.read(decode=True)
            formdata.add(field_name, save_file(part.filename, file_byte))
        else:
            metadata = await part.text()
            logger.debug(f"field name {field_name} has value {metadata}")
            formdata.add(field_name, metadata)

    try:
        config = extract_app_config(path.read_text("utf-8"))
    except Exception as exp:
        exceptions = [exp]
        logger.info(f"handling exception: {exp}")

        return Response(
            text=jinja_env.get_template("widget_exceptions.html").render(
                {
                    "exceptions": exceptions,
                    "formdata": formdata_to_json(formdata),
                },
            ),
            content_type="text/html",
        )

    form = build_form(config)
    form.process(formdata=formdata)

    if form.validate():
        logger.debug("form data valid")
        data = {}
        for field in form:
            if callable(getattr(field, "adapt", None)):
                field.adapt()

            data[field.name] = field.data

        html, excep = render_app_html(data, path, track_file)
        if html is None:
            logger.debug("handling rendering exceptions")
            return Response(
                text=jinja_env.get_template("widget_exceptions.html").render(
                    {
                        "exceptions": [str(excep)],
                        "formdata": formdata_to_json(formdata),
                    },
                ),
                content_type="text/html",
            )

        html = inject_script_into_html(html, SDK_TAG, formdata)

        return Response(text=html, content_type="text/html")
    else:
        logger.debug("invalid data")

        for field in form:
            for error in field.errors:
                logger.info(f"{field.name} : {error}")

        return Response(
            text=jinja_env.get_template("widget_form.html").render(
                {
                    "form": form,
                    "title": config["title"],
                    "file_name": "/.preview/{}".format(urllib.parse.quote(name)),
                    "warnings": config["warnings"],
                },
            ),
            content_type="text/html",
        )


async def change_notification_sse(request):
    loop = request.app.loop
    async with sse_response(request) as resp:
        while True:
            if not tracked_files:
                await resp.send("refresh")
                return resp

            for path, last_modification in tracked_files.items():
                if path.is_file():
                    actual_modification = path.stat().st_ctime
                    logger.debug(f"Checking m_time {path}")

                    if last_modification == 0:
                        tracked_files[path] = actual_modification
                    else:
                        if actual_modification > last_modification:
                            logger.info(f"Reloading due to change on {path}")
                            await resp.send("refresh")
                            tracked_files[path] = actual_modification
                else:
                    logger.info(f"File not found: {path}")
            await asyncio.sleep(1, loop=loop)

    return resp


async def proxy_request(request):
    import aiohttp
    from multidict import CIMultiDict

    hop_by_hop_headers = (
        "Accept-Encoding",
        "Connection",
        "Keep-Alive",
        "TE",
        "Trailer",
        "Transfer-Encoding",
        "Upgrade",
    )

    async with aiohttp.ClientSession() as session:
        # Clean hop-by-hop headers
        req_headers = CIMultiDict(request.headers)
        for header_name in hop_by_hop_headers + ("Host",):
            req_headers.pop(header_name, 0)

        req_data = None
        if request.body_exists:
            req_data = await request.read()

        async with session.request(
            request.method, request.query.get("url"), headers=req_headers, data=req_data
        ) as resp:
            # Clean hop-by-hop headers
            resp_headers = CIMultiDict(resp.headers)
            for header_name in hop_by_hop_headers + (
                "Content-Encoding",
                "Content-Length",
            ):
                resp_headers.pop(header_name, 0)

            resp_data = await resp.read()
            return Response(
                body=resp_data,
                status=resp.status,
                headers=resp_headers,
            )


async def serve_preview_asset(request):
    name = request.match_info.get("file_name", "")

    path = request.app["base_path"]
    if name:
        path = path / name

    if (
        path.is_file()
        and path.suffix in ALLOWED_FILE_TYPES
        and request.query.get("tracked")
    ):
        logger.debug(f"serving file: {name}")
        return FileResponse(path)

    return HTTPNotFound()


async def serve_file_from_uploads(request):
    return FileResponse(get_file(request.match_info["file_name"]))


async def serve_twitter_data(request):
    from aiohttp import web
    import json

    return web.json_response(json.loads(TWITTER_FEED))


async def serve_instagram_data(request):
    from aiohttp import web
    import json

    return web.json_response(json.loads(INSTAGRAM_FEED))


async def serve_font(request):
    font_path = request.match_info["blob_path"]

    font_file = get_file(font_path.replace("/", ""))

    if font_file:
        return FileResponse(font_file)
    else:
        import aiohttp

        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://signagewidgets.net/app-media/" + font_path
            ) as resp:
                data = await resp.read()

        filename = save_file(font_path, data)

        return FileResponse(get_file(filename))
