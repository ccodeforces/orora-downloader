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

    async def add_download(self, url, format, quality, folder, user_id):
        download_id = str(len(self.downloads) + 1)
        download_info = {
            'id': download_id,
            'url': url,
            'format': format,
            'quality': quality,
            'folder': folder,
            'user_id': user_id,
            'status': 'pending',
            'download_url': None,
            'title': None,
            'size': None
        }
        self.downloads[download_id] = download_info
        logger.debug(f"Adding download {download_id} for user {user_id} with status {download_info['status']}")
        asyncio.create_task(self.start_download(download_info))
        return download_info

    async def start_download(self, download_info):
        url = download_info['url']
        format = download_info['format']
        quality = download_info['quality']
        folder = download_info['folder']
        user_id = download_info['user_id']

        download_info['status'] = 'downloading'
        logger.debug(f"Download {download_info['id']} status updated to downloading")

        user_folder = os.path.join(self.config.DOWNLOAD_DIR, user_id)
        output_dir = os.path.join(user_folder, folder)
        os.makedirs(output_dir, exist_ok=True)

        output_path = os.path.join(output_dir, '%(title)s.%(ext)s')
        ytdl_opts = {
            'format': get_format(format, quality),
            'outtmpl': output_path,
            'noplaylist': True,
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36',
        }

        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(self.executor, self.download_video, ytdl_opts, url, download_info, user_folder)
        except Exception as e:
            logger.error(f"Error downloading {url}: {e}")
            download_info['status'] = 'error'
            download_info['error_message'] = str(e)

    def download_video(self, ytdl_opts, url, download_info, user_folder):
        try:
            with yt_dlp.YoutubeDL(ytdl_opts) as ytdl:
                info_dict = ytdl.extract_info(url, download=True)
                output_path = ytdl.prepare_filename(info_dict)
                download_info['status'] = 'completed'
                download_info['title'] = info_dict.get('title', 'video')
                # Calculate size if 'filesize' is not available, use 'filesize_approx'
                download_info['size'] = info_dict.get('filesize') or info_dict.get('filesize_approx')

                relative_path = os.path.relpath(output_path, self.config.DOWNLOAD_DIR)
                download_info['download_url'] = f"https://tokyo.ororabrowser.com/downloads/{relative_path.replace(os.sep, '/')}"

                logger.debug(f"Download {download_info['id']} completed: {output_path}")
        except Exception as e:
            logger.error(f"Error in download_video: {e}")
            download_info['status'] = 'failed'
            download_info['error_message'] = str(e)

    async def get_status(self, user_id=None):
        if user_id:
            # Ensure the downloads are sorted by the latest first
            return dict(sorted({k: v.copy() for k, v in self.downloads.items() if v['user_id'] == user_id}.items(), key=lambda item: int(item[0]), reverse=True))
        else:
            return dict(sorted(self.downloads.items(), key=lambda item: int(item[0]), reverse=True))


download_manager = DownloadManager(config)