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

    query = """
    SELECT * FROM pasien
    WHERE status_sync='pending'
    """

    cursor.execute(query)

    hasil = cursor.fetchall()

    print("CEK DATA PENDING...")

    if hasil:

        # UBAH SEMUA DATE/DATETIME KE STRING
        for pasien in hasil:

            for key, value in pasien.items():

                if value is not None:
                    pasien[key] = str(value)

        try:

            response = requests.post(
                "http://103.87.67.113:8001/api/sync/pasien",
                json=hasil,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                }
            )

            print("STATUS:", response.status_code)
            print("RESPON:", response.text)

            if response.status_code == 200:

                ids = [str(item['id']) for item in hasil]

                update_query = f"""
                UPDATE pasien
                SET status_sync='synced'
                WHERE id IN ({','.join(ids)})
                """

                cursor.execute(update_query)

                db.commit()

                print("SYNC BERHASIL")

        except Exception as e:

            print("SYNC GAGAL:", e)

    db.close()

    time.sleep(5)