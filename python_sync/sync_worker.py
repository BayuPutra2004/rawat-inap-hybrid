import pymysql
import requests
import time

while True:

    db = pymysql.connect(
        host="127.0.0.1",
        user="root",
        password="",
        database="rawat_inap"
    )

    cursor = db.cursor(pymysql.cursors.DictCursor)

    query = "SELECT * FROM pasien WHERE status_sync='pending'"

    cursor.execute(query)

    hasil = cursor.fetchall()

    print("CEK DATA PENDING...")

    for pasien in hasil:

        try:

            response = requests.post(
                "http://IP-VPS:8001/api/sync/pasien",
                json=pasien
            )

            if response.status_code == 200:

                update_query = '''
                UPDATE pasien
                SET status_sync='synced'
                WHERE id=%s
                '''

                cursor.execute(update_query, (pasien['id'],))

                db.commit()

                print("BERHASIL SYNC:", pasien['id'])

        except Exception as e:

            print("SYNC GAGAL:", e)

    db.close()

    time.sleep(5)