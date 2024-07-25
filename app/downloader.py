import asyncio
import concurrent.futures
import os
import yt_dlp
from app.dl_formats import get_format
import logging

from config.config import config

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('downloader')

class DownloadManager:
    def __init__(self, config):
        self.config = config
        self.downloads = {}
        self.executor = concurrent.futures.ThreadPoolExecutor()

    async def add_download(self, url, format, quality, folder):
        download_id = str(len(self.downloads) + 1)
        download_info = {
            'id': download_id,
            'url': url,
            'format': format,
            'quality': quality,
            'folder': folder,
            'status': 'pending'
        }
        self.downloads[download_id] = download_info
        logger.debug(f"Adding download {download_id} with status {download_info['status']}")
        asyncio.create_task(self.start_download(download_info))
        return download_info

    async def start_download(self, download_info):
        url = download_info['url']
        format = download_info['format']
        quality = download_info['quality']
        folder = download_info['folder']

        # Update status to downloading
        download_info['status'] = 'downloading'
        logger.debug(f"Download {download_info['id']} status updated to downloading")

        output_dir = os.path.join(self.config.DOWNLOAD_DIR, folder)
        os.makedirs(output_dir, exist_ok=True)

        output_path = os.path.join(output_dir, '%(title)s.%(ext)s')
        ytdl_opts = {
            'format': get_format(format, quality),
            'outtmpl': output_path,
            'noplaylist': True,
        }

        # Run the download in a separate thread to avoid blocking the event loop
        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(self.executor, self.download_video, ytdl_opts, url, download_info)
        except Exception as e:
            logger.error(f"Error downloading {url}: {e}")
            download_info['status'] = 'error'
            download_info['error_message'] = str(e)

    def download_video(self, ytdl_opts, url, download_info):
        with yt_dlp.YoutubeDL(ytdl_opts) as ytdl:
            result = ytdl.download([url])
            download_info['status'] = 'completed' if result == 0 else 'failed'
            logger.debug(f"Download {download_info['id']} completed with status {download_info['status']}")

    async def get_status(self):
        # Return a copy to avoid concurrency issues
        return {k: v.copy() for k, v in self.downloads.items()}

download_manager = DownloadManager(config)
