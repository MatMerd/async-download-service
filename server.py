import argparse
import asyncio
from asyncio.exceptions import CancelledError
import datetime
import logging
import os

from aiohttp import web
import aiofiles


internal_time = 0
photos_path = "test_photos"

server_logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG, 
format='%(asctime)s - %(levelname)s - %(message)s')


async def archivate(request: web.Request):
    response = web.StreamResponse()
    archive_hash = request.match_info.get("archive_hash", "archive.zip")
    if not os.path.isdir(os.path.join(photos_path, archive_hash)) \
    or archive_hash == "." or archive_hash == "..":
        return web.Response(
            text="<h1>404 <br>Archive not exists or has been deleted</h1><a href='/'>main page</a>",
            status=404,
            content_type="text/html"
            )
    response.headers['Content-Disposition'] = f"attachment; filename={archive_hash}.zip"
    response.enable_chunked_encoding()
    await response.prepare(request)
    proc = await asyncio.create_subprocess_exec(
            "zip", "-r",  "-", archive_hash,
            cwd=photos_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
            )
    try:
        while not proc.stdout.at_eof():
            data = bytes(await proc.stdout.read(10240))
            server_logger.info(f"Sending archive chunk {len(data)}")
            await response.write(data)
            await asyncio.sleep(internal_time)
    except CancelledError as e:
        server_logger.error("Dowload was interrupted")
    finally:
        out, err = await proc.communicate()
    return response


async def stream_handler(request):
   response = web.StreamResponse()
   response.headers['Content-Type'] = 'text/html'

   await response.prepare(request)

   for _ in range(10):
       formatted_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
       message = f"{formatted_date}<br>"
       await response.write(message.encode("utf-8"))

       await asyncio.sleep(internal_time)


async def handle_index_page(request):
    async with aiofiles.open('index.html', mode='r') as index_file:
        index_contents = await index_file.read()
    return web.Response(text=index_contents, content_type='text/html')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Set settings for run server", 
                                     allow_abbrev=False)
    parser.add_argument("-d",
                        "--disable_log",
                        action="store_true",
                        help="disable logging")

    parser.add_argument("-r",
                        "--response_delay",
                        action="store",
                        type=int,
                        help="enable delay for response user"
                        )
    parser.add_argument("-p",
                        "--photos_path",
                        action="store",
                        type=str,
                        help="set path where store photo")
    args = parser.parse_args()

    app = web.Application()

    if args.disable_log:
        logging.disable()
    if args.response_delay:
        internal_time = args.response_delay
    if args.photos_path:
        photos_path = args.photos_path
    
    app.add_routes([
        web.get('/', handle_index_page),
        web.get('/archive/{archive_hash}/', archivate),
    ])
    web.run_app(app)
