import asyncio
import json
import logging
from aiohttp import web, WSMsgType
from config.config import config
from app.downloader import download_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('main')

async def add_download(request):
    try:
        data = await request.json()
        url = data.get('url')
        format = data.get('format')
        quality = data.get('quality')
        folder = data.get('folder', 'default')
        user_id = data.get('user_id')
        if not url or not format or not quality or not user_id:
            raise web.HTTPBadRequest(reason='Missing required fields')
        logger.info(f"Received download request: {url} for user {user_id}")
        download_info = await download_manager.add_download(url, format, quality, folder, user_id)
        return web.json_response(download_info)
    except Exception as e:
        logger.error(f"Error in add_download: {e}")
        return web.HTTPInternalServerError(reason=str(e))

async def get_status(request):
    logger.info("Fetching current status of downloads")
    try:
        status = await download_manager.get_status()
        logger.info(f"Current status: {status}")
        return web.json_response(status)
    except Exception as e:
        logger.error(f"Error in get_status: {e}")
        return web.HTTPInternalServerError(reason=str(e))

async def websocket_handler(request):
    user_id = request.query.get('user_id')
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    try:
        while True:
            download_status = await download_manager.get_status(user_id)
            data = json.dumps(download_status)
            await ws.send_str(data)
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        logger.info("WebSocket connection closed by client")
    except Exception as e:
        logger.error(f"Error in WebSocket handler: {e}")
    finally:
        await ws.close()

    return ws

async def delete_download(request):
    try:
        data = await request.json()
        download_id = data.get('id')
        user_id = data.get('user_id')
        if not download_id or not user_id:
            raise web.HTTPBadRequest(reason='Missing required fields')
        logger.info(f"Received delete request for download {download_id} from user {user_id}")
        delete_result = await download_manager.delete_download(download_id, user_id)
        return web.json_response(delete_result)
    except Exception as e:
        logger.error(f"Error in delete_download: {e}")
        return web.HTTPInternalServerError(reason=str(e))

# CORS handling function
async def cors_options_handler(request):
    return web.Response(headers={
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    })

# Adding CORS headers to each response
async def on_prepare(request, response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'

app = web.Application()
app.add_routes([
    web.post('/api/add', add_download),  # Note the /api prefix
    web.options('/api/add', cors_options_handler),  # Handle preflight OPTIONS request for /add
    web.get('/api/status', get_status),
    web.get('/api/ws', websocket_handler),  # WebSocket endpoint
    web.post('/api/delete', delete_download),  # Add delete endpoint
    web.options('/api/delete', cors_options_handler),  # Handle preflight OPTIONS request for /delete
    web.static('/downloads', config.DOWNLOAD_DIR),  # Serve files from DOWNLOAD_DIR
])

app.on_response_prepare.append(on_prepare)  # Attach the CORS handler to all responses

if __name__ == '__main__':
    web.run_app(app, host=config.HOST, port=int(config.PORT))
