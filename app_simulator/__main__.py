import argparse
import logging
import os
import pathlib

from aiohttp import web

from .routes import (
    list_form_file,
    preview_app,
    change_notification_sse,
    serve_file_from_uploads,
    serve_twitter_data,
    serve_instagram_data,
)
from .storage import clean_storage


WORKING_DIR = pathlib.Path.cwd()


def parse_args():
    parser = argparse.ArgumentParser(
        description="Simulate running OnSign TV apps locally to speed up development."
    )
    parser.add_argument(
        "path",
        nargs="?",
        metavar="path",
        type=str,
        default=".",
        help="path to folder containing your app templates - defaults to current directory",
    )
    parser.add_argument(
        "--host",
        nargs="?",
        default="127.0.0.1",
        type=str,
        help="host the simulator will bind to - defaults to 127.0.0.1",
    )
    parser.add_argument(
        "--port",
        nargs="?",
        default=8080,
        type=int,
        help="port the simulator will use - defaults to 8080",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        dest="is_verbose",
        action="store_const",
        const=True,
        default=False,
        help="enable verbose logging",
    )

    parser.add_argument(
        "-c",
        "--clean",
        dest="clean",
        action="store_const",
        const=True,
        default=False,
        help="clean uploaded files directory, stored at ~/.app-simulator",
    )

    return parser.parse_args()


@web.middleware
async def middleware(request, handler):
    resp = await handler(request)
    resp.headers["Cache-Control"] = "no-store, max-age=0"
    return resp


def main():
    args = parse_args()

    os.chdir(args.path)
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.DEBUG if args.is_verbose else logging.INFO,
    )

    if args.clean:
        clean_storage()

    app = web.Application(middlewares=[middleware])

    app.router.add_get("/", list_form_file)
    app.router.add_get("/.change_notification", change_notification_sse)
    app.router.add_get("/.uploads/{file_name}", serve_file_from_uploads)
    app.router.add_post("/.preview/{file_name}", preview_app)
    app.router.add_post(r"/.preview/{file_name:[^{}/]+}.*", preview_app)
    app.router.add_get("/.twitter/mock_data", serve_twitter_data)
    app.router.add_get("/.instagram/mock_data", serve_instagram_data)
    app.router.add_get(r"/{file_name:[^{}]+}", list_form_file)

    web.run_app(app, port=args.port, host=args.host)


if __name__ == "__main__":
    main()
