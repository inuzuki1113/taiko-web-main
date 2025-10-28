#!/usr/bin/env python3

import base64
import bcrypt
import hashlib
import json
import os
import re
import requests
import uuid
import zipfile
from datetime import datetime
from functools import wraps

from flask import Flask, g, jsonify, render_template, request, abort, redirect, session, flash, make_response
from flask_caching import Cache
from flask_session import Session
from flask_wtf.csrf import CSRFProtect, generate_csrf, CSRFError
from werkzeug.utils import secure_filename
from pymongo import MongoClient
from redis import Redis
from ffmpy import FFmpeg

# ---- 既存の config 読み込み部分 ----
try:
    import config
except ModuleNotFoundError:
    raise FileNotFoundError('No such file or directory: \'config.py\'. Copy the example config file config.example.py to config.py')

# ---- Flask 初期化 ----
app = Flask(__name__)
basedir = getattr(config, 'BASEDIR', '/')
app.secret_key = getattr(config, 'SECRET_KEY', 'change-me')

# Redis / Session 設定
redis_config = getattr(config, 'REDIS', {})
redis_config['CACHE_REDIS_HOST'] = os.environ.get("TAIKO_WEB_REDIS_HOST") or redis_config.get('CACHE_REDIS_HOST', 'localhost')
app.config['SESSION_TYPE'] = 'redis'
app.config['SESSION_REDIS'] = Redis(
    host=redis_config['CACHE_REDIS_HOST'],
    port=redis_config.get('CACHE_REDIS_PORT', 6379),
    password=redis_config.get('CACHE_REDIS_PASSWORD', None),
    db=redis_config.get('CACHE_REDIS_DB', 0)
)
app.cache = Cache(app, config=redis_config)
sess = Session()
sess.init_app(app)
#csrf = CSRFProtect(app)  # 必要なら有効化

# MongoDB 設定
mongo_config = getattr(config, 'MONGO', {})
client = MongoClient(host=os.environ.get("TAIKO_WEB_MONGO_HOST") or mongo_config.get('host'))
db = client[mongo_config.get('database')]

# インデックス作成
db.users.create_index('username', unique=True)
db.songs.create_index('id', unique=True)
db.scores.create_index('username')

# ---- アップロード用設定 ----
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'zip'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ---- 管理者権限デコレータ ----
def admin_required(level):
    def decorated_function(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not session.get('username'):
                return abort(403)
            user = db.users.find_one({'username': session.get('username')})
            if user['user_level'] < level:
                return abort(403)
            return f(*args, **kwargs)
        return wrapper
    return decorated_function

# ---- 曲アップロード機能 ----
@app.route(basedir + 'admin/songs/upload', methods=['GET', 'POST'])
@admin_required(level=50)
def upload_song():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part', 'error')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No selected file', 'error')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            temp_zip_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            file.save(temp_zip_path)

            # 曲ごとのフォルダ名をUUIDで生成
            song_id = str(uuid.uuid4())
            song_folder = os.path.join(app.config['UPLOAD_FOLDER'], song_id)
            os.makedirs(song_folder, exist_ok=True)

            # ZIP を解凍
            with zipfile.ZipFile(temp_zip_path, 'r') as zip_ref:
                zip_ref.extractall(song_folder)

            # ZIP 内に tja と ogg があるか確認
            tja_files = [f for f in os.listdir(song_folder) if f.endswith('.tja')]
            if not tja_files:
                flash('ZIPに譜面（.tja）が見つかりません', 'error')
                return redirect(request.url)
            ogg_files = [f for f in os.listdir(song_folder) if f.endswith('.ogg')]
            if not ogg_files:
                flash('ZIPに音源（.ogg）が見つかりません', 'error')
                return redirect(request.url)

            # DB に曲情報を追加
            db.songs.insert_one({
                'id': song_id,
                'title': tja_files[0].rsplit('.',1)[0],
                'type': 'tja',
                'music_type': 'ogg',
                'enabled': True,
                'path': song_folder
            })

            flash('曲をアップロードしました', 'success')
            return redirect(basedir + 'admin/songs')

    return render_template('upload_song.html', config={})

# ---- 以下、既存の app.py のルートや関数に追記していく ----
# 既存の index, api ルート, admin ルートなどはそのまま維持

# ---- アプリ実行 ----
if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Run the taiko-web development server.')
    parser.add_argument('port', type=int, metavar='PORT', nargs='?', default=34801, help='Port to listen on.')
    parser.add_argument('-b', '--bind-address', default='localhost', help='Bind server to address.')
    parser.add_argument('-d', '--debug', action='store_true', help='Enable debug mode.')
    args = parser.parse_args()

    app.run(host=args.bind_address, port=args.port, debug=args.debug)
