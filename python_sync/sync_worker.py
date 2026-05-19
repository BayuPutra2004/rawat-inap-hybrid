import pymysql
import requests
import time


# KONFIGURASI DATABASE LOKAL
db_config = {
    "host": "127.0.0.1",
    "user": "root",
    "password": "",
    "database": "rawat_inap"
}


# URL SERVER VPS / PUBLIK
BASE_URL = "http://103.87.67.113:8001/api"


# FUNCTION SYNC PASIEN
def sync_pasien():

    db = pymysql.connect(**db_config)

    cursor = db.cursor(pymysql.cursors.DictCursor)

    # ambil data pasien pending
    query = """
    SELECT * FROM pasien
    WHERE status_sync='pending'
    """

    cursor.execute(query)

    hasil = cursor.fetchall()

    print("\n[SYNC PASIEN]")
    print("CEK DATA PASIEN PENDING...")

    if hasil:

        # ubah semua data menjadi string
        for pasien in hasil:

            for key, value in pasien.items():

                if value is not None:
                    pasien[key] = str(value)

        try:

            # kirim ke VPS
            response = requests.post(
                f"{BASE_URL}/sync/pasien",
                json=hasil,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                }
            )

            print("STATUS:", response.status_code)
            print("RESPON:", response.text)

            # jika berhasil
            if response.status_code == 200:

                ids = [str(item['id']) for item in hasil]

                update_query = f"""
                UPDATE pasien
                SET status_sync='synced'
                WHERE id IN ({','.join(ids)})
                """

                cursor.execute(update_query)

                db.commit()

                print("SYNC PASIEN BERHASIL")

        except Exception as e:

            print("SYNC PASIEN GAGAL:", e)

    db.close()


# FUNCTION SYNC VISIT
def sync_visit():

    db = pymysql.connect(**db_config)

    cursor = db.cursor(pymysql.cursors.DictCursor)

    # ambil data visit pending
    query = """
    SELECT * FROM visit
    WHERE status_sync='pending'
    """

    cursor.execute(query)

    hasil = cursor.fetchall()

    print("\n[SYNC VISIT]")
    print("CEK DATA VISIT PENDING...")

    if hasil:

        # ubah semua data menjadi string
        for visit in hasil:

            for key, value in visit.items():

                if value is not None:
                    visit[key] = str(value)

        try:

            # kirim ke VPS
            response = requests.post(
                f"{BASE_URL}/sync/visit",
                json=hasil,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                }
            )

            print("STATUS:", response.status_code)
            print("RESPON:", response.text)

            # jika berhasil
            if response.status_code == 200:

                ids = [str(item['id']) for item in hasil]

                update_query = f"""
                UPDATE visit
                SET status_sync='synced'
                WHERE id IN ({','.join(ids)})
                """

                cursor.execute(update_query)

                db.commit()

                print("SYNC VISIT BERHASIL")

        except Exception as e:

            print("SYNC VISIT GAGAL:", e)

    db.close()


# =========================
# MAIN WORKER LOOP
# =========================
while True:

    # jalankan sync pasien
    sync_pasien()

    # jalankan sync visit
    sync_visit()

    # delay 5 detik
    time.sleep(5)