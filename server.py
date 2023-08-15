import argparse
import asyncio
import logging
import os
from asyncio.exceptions import CancelledError
from functools import partial

import aiofiles
from aiohttp import web

server_logger = logging.getLogger(__name__)


async def archive(request: web.Request, photos_path, internal_time):
    response = web.StreamResponse()
    try:
        archive_hash = request.match_info["archive_hash"]
    except KeyError:
        return web.Response(
            text="<h1>404 <br>Archive hash must be exists</h1><a href='/'>main page</a>",
            status=404,
            content_type="text/html"
        )

    if not os.path.isdir(os.path.join(photos_path, archive_hash)) or archive_hash == "." or archive_hash == "..":
        return web.Response(
            text="<h1>404 <br>Archive not exists or has been deleted</h1><a href='/'>main page</a>",
            status=404,
            content_type="text/html"
        )
    response.headers['Content-Disposition'] = f"attachment; filename={archive_hash}.zip"
    response.enable_chunked_encoding()
    await response.prepare(request)
    proc = await asyncio.create_subprocess_exec(
        "zip", "-r", "-", archive_hash,
        cwd=photos_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    try:
        while not proc.stdout.at_eof():
            photos_in_zip = bytes(await proc.stdout.read(10240))
            server_logger.info(f"Sending archive chunk {len(photos_in_zip)}")
            await response.write(photos_in_zip)
            await asyncio.sleep(internal_time)
    except (CancelledError, ConnectionResetError) as ex:
        server_logger.error(f"Dowload was interrupted. Error:\n{str(ex)}")
        raise
    finally:
        server_logger.info(f"process end with code: {proc.returncode}")
        if proc.returncode != 0:
            proc.kill()
        await proc.communicate()
    return response


async def handle_index_page(request: web.Request):
    async with aiofiles.open('index.html', mode='r') as index_file:
        index_contents = await index_file.read()
    return web.Response(text=index_contents, content_type='text/html')


def main():
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
    parser = argparse.ArgumentParser(description="Set settings for run server", allow_abbrev=False)
    parser.add_argument(
        "-d",
        "--disable_log",
        action="store_true",
        help="disable logging"
    )

    parser.add_argument(
        "-r",
        "--response_delay",
        action="store",
        type=int,
        help="enable delay for response user",
        default=0
    )
    parser.add_argument(
        "-p",
        "--photos_path",
        action="store",
        type=str,
        help="set path where store photo",
        default="test_photos"
    )
    args = parser.parse_args()

    app = web.Application()

    if args.disable_log:
        logging.disable()

    internal_time = args.response_delay

    photos_path = args.photos_path

    archive_partial = partial(archive, photos_path=photos_path, internal_time=internal_time)

    app.add_routes([
        web.get('/', handle_index_page),
        web.get('/archive/{archive_hash}/', archive_partial),
    ])
    web.run_app(app)


if __name__ == '__main__':
    main()
