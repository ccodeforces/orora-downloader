import yt_dlp


def get_download_link(url):
    ydl_opts = {
        'format': 'best',
        'quiet': True,
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
        'cookiefile': 'path/to/cookies.txt',  # Use cookies if necessary
        'http_headers': {
            'Referer': 'https://www.pornhub.com/',
            'Origin': 'https://www.pornhub.com/',
        },
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        if 'entries' in info:
            # If it's a playlist or a multi-video link, extract the first entry
            info = info['entries'][0]

        # Extracting the download URL from the info dictionary
        download_url = info.get('url')
        return download_url


if __name__ == '__main__':
    input_url = input("Enter the URL of the video: ")
    download_link = get_download_link(input_url)
    if download_link:
        print(f"Download link: {download_link}")
    else:
        print("Could not extract download link.")
