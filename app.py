from flask import Flask, render_template, jsonify, request, send_from_directory # send_from_directory eklendi
import pandas as pd
import os
import requests 
from datetime import datetime

# --- AYARLAR ---
# Dosya yollarını otomatik bulur
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'static')
EXCEL_FILE = os.path.join(BASE_DIR, 'sorular.xlsx')

# Firebase Veritabanı URL (Skorları buraya kaydeder)
FIREBASE_DB_URL = "https://map-9488e-default-rtdb.firebaseio.com/metro_scores.json"
app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)

# --- GOOGLE ADSENSE İZNİ (ADS.TXT) ---
@app.route('/ads.txt')
def ads_txt():
    # static klasörü içindeki ads.txt dosyasını dış dünyaya açar
    return send_from_directory('static', 'ads.txt')

# --- SAYFA ROTALARI (MENÜLER) ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/hakkimizda')
def hakkimizda():
    return render_template('hakkimizda.html')

@app.route('/gizlilik')
def gizlilik():
    return render_template('gizlilik.html')

@app.route('/iletisim')
def iletisim():
    return render_template('iletisim.html')

# --- API: SORULARI GETİR (ŞEHİR BAZLI) ---
@app.route('/api/sorular')
def get_sorular():
    sehir_secimi = request.args.get('bolge', 'Istanbul')

    try:
        if not os.path.exists(EXCEL_FILE):
            print(f"HATA: Excel dosyası bulunamadı! Yol: {EXCEL_FILE}")
            return jsonify([])
        
        df = pd.read_excel(EXCEL_FILE, engine='openpyxl').fillna('')
        df.columns = df.columns.str.strip()
        
        hedef_kolon = 'Sehir' if 'Sehir' in df.columns else 'Bolge'
        
        if hedef_kolon in df.columns:
            df = df[df[hedef_kolon].astype(str).str.lower() == sehir_secimi.lower()]
        
        soru_sayisi = min(20, len(df))
        if soru_sayisi == 0:
            return jsonify([])
            
        final_df = df.sample(n=soru_sayisi).reset_index(drop=True)
        
        quiz_data = []
        for index, row in final_df.iterrows():
            if not str(row['Soru']).strip() or not str(row['Dogru_Cevap']).strip():
                continue

            soru_objesi = {
                "id": index + 1,
                "soru": str(row['Soru']),
                "secenekler": [str(row['A']), str(row['B']), str(row['C']), str(row['D'])],
                "dogru_cevap": str(row['Dogru_Cevap'])
            }
            quiz_data.append(soru_objesi)
            
        return jsonify(quiz_data)
        
    except Exception as e:
        print(f"Sistem Hatası: {e}")
        return jsonify([])

# --- API: SKOR KAYDET ---
@app.route('/api/skor-kaydet', methods=['POST'])
def skor_kaydet():
    try:
        data = request.json
        isim = data.get('isim', 'Anonim').strip()[:15]
        puan = data.get('puan', 0)
        sehir = data.get('bolge', 'Istanbul') 
        
        if not isim: isim = "Anonim"
        bugun = datetime.now().strftime("%Y-%m-%d %H:%M")

        yeni_skor = {
            "isim": isim,
            "puan": puan,
            "bolge": sehir,
            "tarih": bugun
        }
        
        requests.post(FIREBASE_DB_URL, json=yeni_skor)

        return jsonify({"mesaj": "Kaydedildi!"})
    except Exception as e:
        print(f"Skor Kayıt Hatası: {e}")
        return jsonify({"hata": str(e)})

# --- API: LİDERLİK TABLOSU ---
@app.route('/api/liderlik')
def liderlik_tablosu():
    try:
        response = requests.get(FIREBASE_DB_URL)
        if response.status_code != 200 or not response.json():
            return jsonify([])

        veriler = response.json()
        skor_listesi = []
        
        if isinstance(veriler, dict):
            for key, value in veriler.items():
                skor_listesi.append(value)
        elif isinstance(veriler, list):
             skor_listesi = [v for v in veriler if v]

        skor_listesi = sorted(skor_listesi, key=lambda x: x.get('puan', 0), reverse=True)
        
        return jsonify(skor_listesi[:15])

    except Exception as e:
        print(f"Liderlik Hatası: {e}")
        return jsonify([])

if __name__ == '__main__':
    app.run(debug=True, port=5000)
