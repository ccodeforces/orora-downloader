import asyncio
import concurrent.futures
import os
import yt_dlp
import sqlite3
import logging
from app.dl_formats import get_format
from config.config import config

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('downloader')

class DownloadManager:
    def __init__(self, config):
        self.config = config
        self.downloads = {}
        self.executor = concurrent.futures.ThreadPoolExecutor()
        self.init_db()

    def init_db(self):
        self.conn = sqlite3.connect(self.config.DATABASE, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS downloads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT,
                format TEXT,
                quality TEXT,
                folder TEXT,
                user_id TEXT,
                status TEXT,
                download_url TEXT,
                title TEXT,
                size INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                error_message TEXT
            )
        ''')
        self.conn.commit()

    async def add_download(self, url, format, quality, folder, user_id):
        self.cursor.execute('''
            INSERT INTO downloads (url, format, quality, folder, user_id, status)
            VALUES (?, ?, ?, ?, ?, 'pending')
        ''', (url, format, quality, folder, user_id))
        download_id = self.cursor.lastrowid
        self.conn.commit()

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
        self.update_download_status(download_info['id'], 'downloading')

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
            self.update_download_status(download_info['id'], 'error', str(e))
            await notify_sse(user_id)  # Notify on error as well

    def download_video(self, ytdl_opts, url, download_info, user_folder):
        try:
            with yt_dlp.YoutubeDL(ytdl_opts) as ytdl:
                info_dict = ytdl.extract_info(url, download=True)
                output_path = ytdl.prepare_filename(info_dict)
                download_info['status'] = 'completed'
                download_info['title'] = info_dict.get('title', 'video')
                download_info['size'] = info_dict.get('filesize') or info_dict.get('filesize_approx')

                relative_path = os.path.relpath(output_path, self.config.DOWNLOAD_DIR)
                download_info[
                    'download_url'] = f"https://{self.config.HOST}/downloads/{relative_path.replace(os.sep, '/')}"

                self.update_download_info(download_info)
                logger.debug(f"Download {download_info['id']} completed: {output_path}")
        except Exception as e:
            logger.error(f"Error in download_video: {e}")
            download_info['status'] = 'failed'
            self.update_download_status(download_info['id'], 'failed', str(e))

    def update_download_status(self, download_id, status, error_message=None):
        self.cursor.execute('''
            UPDATE downloads
            SET status = ?, error_message = ?
            WHERE id = ?
        ''', (status, error_message, download_id))
        self.conn.commit()

    def update_download_info(self, download_info):
        self.cursor.execute('''
            UPDATE downloads
            SET status = ?, download_url = ?, title = ?, size = ?
            WHERE id = ?
        ''', (
            download_info['status'],
            download_info['download_url'],
            download_info['title'],
            download_info['size'],
            download_info['id']
        ))
        self.conn.commit()

    async def get_status(self, user_id=None):
        if user_id:
            self.cursor.execute('''
                SELECT * FROM downloads WHERE user_id = ? ORDER BY id DESC
            ''', (user_id,))
        else:
            self.cursor.execute('''
                SELECT * FROM downloads ORDER BY id DESC
            ''')
        rows = self.cursor.fetchall()
        return {row[0]: {
            'id': row[0],
            'url': row[1],
            'format': row[2],
            'quality': row[3],
            'folder': row[4],
            'user_id': row[5],
            'status': row[6],
            'download_url': row[7],
            'title': row[8],
            'size': row[9],
            'created_at': row[10],
            'error_message': row[11]
        } for row in rows}

    async def delete_old_downloads(self):
        while True:
            logger.debug("Deleting downloads older than 3 hours")
            self.cursor.execute('''
                DELETE FROM downloads WHERE created_at < datetime('now', '-3 hours')
            ''')
            self.conn.commit()
            await asyncio.sleep(3600)


download_manager = DownloadManager(config)
