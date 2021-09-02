import asyncio
import logging
import os
from pathlib import Path

from aiohttp_sse import sse_response
from aiohttp.web import Response, FileResponse, HTTPFound, HTTPNotFound
from jinja2 import Environment, PackageLoader, select_autoescape
from multidict import MultiDict

from .app_config import extract_app_config, render_app_html
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
    if "file_name" in request.match_info:
        name = request.match_info["file_name"]

        if name == "..back":
            name = ".."
    else:
        name = ""

    path = Path.cwd() / name

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
                    "title": config["title"],
                    "file_name": "/.preview/{}".format(name),
                },
            ),
            content_type="text/html",
        )
    elif path.is_file():
        if path.suffix in ALLOWED_FILE_TYPES:
            logger.debug(f"serving file: {name}")
            return FileResponse(name)
        else:
            return HTTPNotFound()
    else:
        logger.debug("opening directory")
        if path.is_dir() and name != "":
            logger.debug("back to a parent directory")
            os.chdir(name)
            raise HTTPFound("/")

        folder_or_files = [{"name": "..", "link": "/..back"}]
        for element in sorted(Path.cwd().iterdir(), key=lambda f: f.name.lower()):
            if not element.name.startswith("."):
                folder_or_files.append(
                    {
                        "name": element.name,
                        "link": "/" + element.name,
                        "is_file": Path.is_file(Path.cwd() / element),
                    }
                )

        return Response(
            text=jinja_env.get_template("list_files.html").render(
                {"files": folder_or_files}
            ),
            content_type="text/html",
        )


async def preview_app(request):
    logger.debug("retrieve data")

    name = request.match_info["file_name"]
    path = Path.cwd() / name

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
        logger.debug(f"handling exception: {exp}")
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

        html = inject_script_into_html(html, formdata)

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
                    "file_name": "/.preview/{}".format(request.match_info["file_name"]),
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
