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


# FUNCTION SIMPAN LOG SINKRONISASI
#----------------------------------------------------
# Fungsi ini digunakan untuk menyimpan histori sync
# ke tabel sync_log agar dapat dianalisis pada BAB 4
# seperti:
# - waktu sinkronisasi
# - keberhasilan sync
# - error sync
# - monitoring hybrid network
def save_sync_log(
    cursor,
    table_name,
    data_uuid,
    source_server,
    target_server,
    sync_status,
    duration_ms,
    message
):
    query = """
    INSERT INTO sync_log (
        table_name,
        data_uuid,
        source_server,
        target_server,
        sync_status,
        sync_duration_ms,
        message,
        created_at,
        updated_at
    )
    VALUES (
        %s,%s,%s,%s,%s,%s,%s,NOW(),NOW()
    )
    """

    cursor.execute(query, (
        table_name,
        data_uuid,
        source_server,
        target_server,
        sync_status,
        duration_ms,
        message
    ))

# FUNCTION GENERIC SYNC DATA
#-----------------------------------
# Fungsi ini dibuat generic agar:
# - tidak duplicate code
# - lebih profesional
# - mudah dikembangkan
# - siap two-way synchronization
#
# Parameter:
# table_name = nama tabel database
# endpoint   = endpoint API tujuan
def sync_data(table_name, endpoint):

    # koneksi database
    db = pymysql.connect(**db_config)

    cursor = db.cursor(pymysql.cursors.DictCursor)

    print(f"\n[SYNC {table_name.upper()}]")
    print("CEK DATA PENDING...")

    # AMBIL DATA YANG BELUM TERSINKRON
    #------------------------------------------------
    # source_server='lokal'
    # penting untuk mencegah infinite loop
    # saat nanti two-way sync aktif
    query = f"""
    SELECT * FROM {table_name}
    WHERE status_sync='pending'
    AND source_server='lokal'
    """

    cursor.execute(query)

    hasil = cursor.fetchall()

    # jika tidak ada data
    if not hasil:

        print("TIDAK ADA DATA PENDING")

        db.close()

        return

    # UBAH SEMUA DATA MENJADI STRING
    # agar JSON serializable
    # terutama untuk datetime/date
    for item in hasil:

        for key, value in item.items():

            if value is not None:
                item[key] = str(value)

    try:

        # UPDATE STATUS MENJADI syncing
        # menandakan data sedang diproses sync
        ids = [str(item['id']) for item in hasil]

        update_syncing = f"""
        UPDATE {table_name}
        SET status_sync='syncing'
        WHERE id IN ({','.join(ids)})
        """

        cursor.execute(update_syncing)

        db.commit()

        # HITUNG WAKTU SINKRONISASI
        start_time = time.time()

        # KIRIM DATA KE VPS
        response = requests.post(
            f"{BASE_URL}/{endpoint}",
            json=hasil,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json"
            },

            # timeout agar worker tidak hang
            timeout=10
        )

        end_time = time.time()

        # konversi ke milidetik
        duration_ms = int((end_time - start_time) * 1000)

        print("STATUS :", response.status_code)
        print("RESPON :", response.text)
        print(f"DURATION : {duration_ms} ms")

        # CHECK RESPONSE API
        if (
            response.status_code == 200 and
            response.json().get("success")
        ):

            # UPDATE STATUS MENJADI synced
            update_synced = f"""
            UPDATE {table_name}
            SET
                status_sync='synced',
                synced_at=NOW()
            WHERE id IN ({','.join(ids)})
            """

            cursor.execute(update_synced)

            db.commit()

            # SIMPAN LOG BERHASIL
            for item in hasil:

                save_sync_log(
                    cursor,
                    table_name,
                    item["uuid"],
                    "lokal",
                    "vps",
                    "success",
                    duration_ms,
                    f"Sync {table_name} berhasil"
                )

            db.commit()

            print(f"SYNC {table_name.upper()} BERHASIL")

        else:

            # JIKA RESPONSE GAGAL
            for item in hasil:

                save_sync_log(
                    cursor,
                    table_name,
                    item["uuid"],
                    "lokal",
                    "vps",
                    "failed",
                    duration_ms,
                    response.text
                )

            # kembalikan status menjadi pending
            rollback_query = f"""
            UPDATE {table_name}
            SET status_sync='pending'
            WHERE id IN ({','.join(ids)})
            """

            cursor.execute(rollback_query)

            db.commit()

            print(f"SYNC {table_name.upper()} GAGAL")

    except Exception as e:

        # JIKA TERJADI ERROR
        print(f"SYNC {table_name.upper()} ERROR :", e)

        # simpan log gagal
        for item in hasil:

            save_sync_log(
                cursor,
                table_name,
                item["uuid"],
                "lokal",
                "vps",
                "failed",
                0,
                str(e)
            )

        # KEMBALIKAN STATUS KE pending
        rollback_query = f"""
        UPDATE {table_name}
        SET status_sync='pending'
        WHERE id IN ({','.join(ids)})
        """

        cursor.execute(rollback_query)

        db.commit()

    finally:

        # tutup koneksi database
        db.close()


# MAIN WORKER LOOP
#----------------------
# Worker berjalan terus menerus
# setiap 5 detik untuk:
# - cek data pending
# - sinkronisasi otomatis
# - monitoring hybrid network
while True:

    # sync data pasien
    sync_data(
        "pasien",
        "sync/pasien"
    )

    # sync data visit
    sync_data(
        "visit",
        "sync/visit"
    )

    # delay worker 5 detik
    time.sleep(5)