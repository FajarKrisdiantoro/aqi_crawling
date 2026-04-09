import requests
import csv
import time
import datetime
import os
import subprocess

# ==== KONFIGURASI ====
API_KEY = "adf8aa88db75f2b964de54b43cf82875ed02b009"
UIDS = {
    "Jakarta": "A521365",
    "Depok": "A511573",
    "Bogor": "A472486",
    "Tangerang": "A416803",
    "Bekasi": "A416815"
}
SLEEP_PER_CITY = 2  # jeda antar kota (detik)
GITHUB_REPO = "https://github.com/FajarKrisdiantoro/aqi_crawling.git"
GITHUB_LOCAL_PATH = "/root/aqi_collector/aqi_crawling"
TELEGRAM_BOT_TOKEN = "8489899571:AAFk0u6B7JWU2R2t5DQNdgtxnUk5SryY-qw"
TELEGRAM_CHAT_ID = "1300916604"

# Parameter kolom CSV
FIELDNAMES = [
    "city", "station_name", "time", "aqi",
    "pm25", "pm10", "pm1", "no2", "so2", "co", "o3",
    "humidity", "temperature", "pressure", "wind", "rain"
]

# ==== FUNGSI ====
def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        requests.get(url, params={"chat_id": TELEGRAM_CHAT_ID, "text": msg}, timeout=10)
    except:
        pass

def init_repo():
    if not os.path.exists(GITHUB_LOCAL_PATH):
        os.makedirs(os.path.dirname(GITHUB_LOCAL_PATH), exist_ok=True)
        subprocess.run(["git", "clone", GITHUB_REPO, GITHUB_LOCAL_PATH])
    os.chdir(GITHUB_LOCAL_PATH)

def fetch_data(city, uid):
    url = f"https://api.waqi.info/feed/{uid}/?token={API_KEY}"
    try:
        response = requests.get(url, timeout=15)
        res = response.json()
        if res.get("status") == "ok":
            d = res.get("data", {})
            iaqi = d.get("iaqi", {})
            v = lambda k: iaqi.get(k, {}).get("v")
            return {
                "city": city,
                "station_name": d.get("city", {}).get("name"),
                "time": d.get("time", {}).get("s"),
                "aqi": d.get("aqi"),
                "pm25": v("pm25"), "pm10": v("pm10"), "pm1": v("pm1"),
                "no2": v("no2"), "so2": v("so2"), "co": v("co"), "o3": v("o3"),
                "humidity": v("h"), "temperature": v("t"), "pressure": v("p"),
                "wind": v("w"), "rain": v("r")
            }
    except Exception as e:
        print(f"❌ Error Fetch {city}: {e}")
    return None

def save_csv(data_list):
    if not data_list: return None
    now = datetime.datetime.now()
    file_name = f"aqi_{now.strftime('%Y-%m-%d')}.csv"
    file_path = os.path.join(GITHUB_LOCAL_PATH, file_name)
    
    write_header = not os.path.exists(file_path)
    with open(file_path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if write_header:
            writer.writeheader()
        writer.writerows(data_list)
    return file_name

def push_to_github(file_name):
    try:
        # Tambahkan pull dulu agar selalu sinkron sebelum push
        subprocess.run(["git", "pull", "origin", "main", "--rebase"], cwd=GITHUB_LOCAL_PATH)
        
        subprocess.run(["git", "add", "."], cwd=GITHUB_LOCAL_PATH)
        msg = f"Update data harian: {file_name}"
        subprocess.run(["git", "commit", "-m", msg], cwd=GITHUB_LOCAL_PATH)
        
        # Gunakan force push agar tidak tertolak kalau ada perbedaan history
        subprocess.run(["git", "push", "origin", "main", "--force"], cwd=GITHUB_LOCAL_PATH)
        
        print(f"🚀 Berhasil push {file_name} ke GitHub")
    except Exception as e:
        print(f"❌ Gagal push: {e}")

# ==== PROGRAM UTAMA ====
if __name__ == "__main__":
    send_telegram("🚀 AQI collector dimulai (Interval: 1 Menit, Push: 24 Jam)")
    init_repo()

    while True:
        # Ambil tanggal hari ini sebagai patokan satu file CSV
        start_day = datetime.datetime.now().strftime("%Y-%m-%d")
        print(f"📅 Memulai hari baru: {start_day}")

        # Loop pengambilan data selama tanggal masih sama
        while datetime.datetime.now().strftime("%Y-%m-%d") == start_day:
            round_data = []
            
            for city, uid in UIDS.items():
                data = fetch_data(city, uid)
                if data:
                    round_data.append(data)
                    # LOG LENGKAP YANG LU MAU
                    print("-" * 45)
                    print(f"📍 {city} ({data['station_name']})")
                    print(f"📊 AQI: {data['aqi']} | PM2.5: {data['pm25']} | PM10: {data['pm10']}")
                    print(f"🧪 O3: {data['o3']} | NO2: {data['no2']} | SO2: {data['so2']} | CO: {data['co']}")
                    print(f"🌡️ T: {data['temperature']}°C | H: {data['humidity']}% | P: {data['pressure']} hPa")
                time.sleep(SLEEP_PER_CITY)
            
            # Simpan data putaran ini ke file lokal tiap menit
            if round_data:
                save_csv(round_data)
                print(f"\n✅ Putaran {datetime.datetime.now().strftime('%H:%M:%S')} aman disimpan.")
            
            # JEDA 1 MENIT (60 detik)
            print("😴 Menunggu 1 menit...\n")
            time.sleep(60)

        # KODE INI JALAN PAS SUDAH GANTI HARI (TANGGAL BERUBAH)
        yesterday_file = f"aqi_{start_day}.csv"
        print(f"📤 Ganti hari! Push file harian {yesterday_file} ke GitHub...")
        push_to_github(yesterday_file)
        send_telegram(f"✅ Laporan harian {yesterday_file} sukses diunggah ke GitHub.")
