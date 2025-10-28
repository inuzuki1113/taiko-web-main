import os

# 基本 URL 設定
BASEDIR = '/'
ASSETS_BASEURL = '/assets/'
SONGS_BASEURL = '/songs/'
MULTIPLAYER_URL = ''
ERROR_PAGES = {404: ''}
EMAIL = None
ACCOUNTS = True
CUSTOM_JS = ''
PLUGINS = [{'url': '', 'start': False, 'hide': False}]
PREVIEW_TYPE = 'mp3'

# MongoDB 設定（環境変数から取得）
MONGO = {
    'host': [os.environ.get('MONGODB_URI')],
    'database': 'taiko'
}

# Redis 設定（環境変数から取得）
REDIS = {
    'CACHE_TYPE': 'redis',
    'CACHE_REDIS_HOST': os.environ.get('REDIS_URL').split('@')[-1].split(':')[0],
    'CACHE_REDIS_PORT': int(os.environ.get('REDIS_URL').split(':')[-1].split('/')[0]),
    'CACHE_REDIS_PASSWORD': os.environ.get('REDIS_URL').split(':')[2].split('@')[0],
    'CACHE_REDIS_DB': 0
}

# Secret key（環境変数から取得）
SECRET_KEY = os.environ.get('SECRET_KEY', 'change-me')

# Git repository URL
URL = 'https://github.com/inuzuki1113/taiko-web-main/'

# Google Drive API
GOOGLE_CREDENTIALS = {
    'gdrive_enabled': False,
    'api_key': '',
    'oauth_client_id': '',
    'project_number': '',
    'min_level': None
}
