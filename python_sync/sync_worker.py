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

# MENYIMPAN ERROR TERAKHIR
last_errors = {}

# URL SERVER VPS / PUBLIK
BASE_URL = "http://103.87.67.113:8001/api"

# TOKEN PENGAMAN SINKRONISASI (Harus sama dengan SYNC_SECRET_KEY di .env Laravel)
SYNC_TOKEN = "SyncSecretToken2026Secure"


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
    action_type,
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
        action_type,
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
        %s,%s,%s,%s,%s,%s,%s,%s,
        NOW(),NOW()
    )
    """
    
    cursor.execute(query, (
        table_name,
        action_type,
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
                "Accept": "application/json",
                "X-Sync-Token": SYNC_TOKEN
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
                    item["action_type"],
                    item["uuid"],
                    "lokal",
                    "vps",
                    "success",
                    duration_ms,
                    f"Sync {table_name} berhasil"
                )
                
            db.commit()
            print(f"SYNC {table_name.upper()} BERHASIL")
            
            # RESET ERROR JIKA SUDAH BERHASIL
            last_errors[table_name] = None
            
        else:
            # JIKA RESPONSE GAGAL
            for item in hasil:

                save_sync_log(
                    cursor,
                    table_name,
                    item["action_type"],
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
        error_message = str(e)

        # PESAN ERROR LEBIH RAPI
        if "Failed to establish a new connection" in error_message:
            clean_message = "SERVER VPS OFFLINE / TIDAK TERHUBUNG"
        else:
            clean_message = error_message
        print(f"SYNC {table_name.upper()} GAGAL")
        print("ERROR :", clean_message)

        # CEK AGAR TIDAK SPAM LOG ERROR SAMA
        if last_errors.get(table_name) != clean_message:

            # SIMPAN LOG SEKALI SAJA
            for item in hasil:
                save_sync_log(
                    cursor,
                    table_name,
                    item["action_type"],
                    item["uuid"],
                    "lokal",
                    "vps",
                    "failed",
                    0,
                    clean_message
                )

            db.commit()
            
            # SIMPAN ERROR TERAKHIR
            last_errors[table_name] = clean_message

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

# FUNCTION PULL & SYNC DATA DARI VPS KE LOKAL
#----------------------------------------------------
def pull_and_sync_data(table_name, pull_endpoint, ack_endpoint):
    # Koneksi ke database lokal
    db = pymysql.connect(**db_config)
    cursor = db.cursor(pymysql.cursors.DictCursor)

    print(f"\n[PULL {table_name.upper()}]")
    print("MENGAMBIL DATA DARI VPS...")

    try:
        # Kirim request GET ke VPS untuk mengambil data pending
        response = requests.get(
            f"{BASE_URL}/{pull_endpoint}",
            headers={
                "Accept": "application/json",
                "X-Sync-Token": SYNC_TOKEN
            },
            timeout=10
        )

        if response.status_code != 200:
            print(f"PULL {table_name.upper()} GAGAL - Status: {response.status_code}")
            return

        hasil = response.json()
        if not hasil:
            print("TIDAK ADA DATA PENDING DI VPS")
            return

        print(f"MENERIMA {len(hasil)} DATA PENDING DARI VPS")

        synced_uuids = []
        start_time = time.time()

        # Tentukan kolom yang valid untuk masing-masing tabel
        if table_name == 'pasien':
            allowed_columns = [
                'uuid', 'no_rm', 'nama', 'jenis_kelamin', 'tanggal_lahir',
                'dokter_id', 'dokter_uuid', 'status', 'tanggal_keluar',
                'catatan_keluar', 'is_active', 'status_sync', 'source_server',
                'action_type', 'is_deleted', 'created_at', 'updated_at'
            ]
        elif table_name == 'visit':
            allowed_columns = [
                'uuid', 'pasien_id', 'dokter_id', 'pasien_uuid', 'dokter_uuid',
                'keluhan', 'diagnosa', 'tindakan', 'status_sync', 'source_server',
                'action_type', 'created_at', 'updated_at'
            ]
        elif table_name == 'users':
            allowed_columns = [
                'uuid', 'name', 'email', 'password', 'role', 'status_sync',
                'source_server', 'action_type', 'created_at', 'updated_at'
            ]
        else:
            allowed_columns = []

        for item in hasil:
            uuid_val = item.get('uuid')
            if not uuid_val:
                continue

            # Bersihkan dan sanitisasi nilai-nilai JSON
            for k, v in item.items():
                if v == 'None' or v == 'null' or v == '' or v is None:
                    item[k] = None
                elif k in ['is_active', 'is_deleted']:
                    if v is not None:
                        item[k] = 1 if str(v).lower() in ['true', '1'] else 0
                elif k in ['created_at', 'updated_at', 'synced_at']:
                    if v is not None:
                        # Konversi format datetime ISO ke standar MySQL YYYY-MM-DD HH:MM:SS
                        val_str = str(v).replace('T', ' ')
                        if '.' in val_str:
                            val_str = val_str.split('.')[0]
                        elif val_str.endswith('Z'):
                            val_str = val_str[:-1]
                        item[k] = val_str
                elif k in ['tanggal_lahir', 'tanggal_keluar']:
                    if v is not None:
                        # Ambil tanggal saja (YYYY-MM-DD)
                        item[k] = str(v).split('T')[0]

            # Resolusi relasi foreign key ke ID lokal berdasarkan UUID
            if table_name == 'pasien':
                dokter_uuid = item.get('dokter_uuid')
                if dokter_uuid:
                    cursor.execute("SELECT id FROM users WHERE uuid = %s", (dokter_uuid,))
                    res = cursor.fetchone()
                    item['dokter_id'] = res['id'] if res else None
                else:
                    item['dokter_id'] = None

            elif table_name == 'visit':
                pasien_uuid = item.get('pasien_uuid')
                if pasien_uuid:
                    cursor.execute("SELECT id FROM pasien WHERE uuid = %s", (pasien_uuid,))
                    res = cursor.fetchone()
                    item['pasien_id'] = res['id'] if res else None
                else:
                    item['pasien_id'] = None

                dokter_uuid = item.get('dokter_uuid')
                if dokter_uuid:
                    cursor.execute("SELECT id FROM users WHERE uuid = %s", (dokter_uuid,))
                    res = cursor.fetchone()
                    item['dokter_id'] = res['id'] if res else None
                else:
                    item['dokter_id'] = None

            # Pastikan semua key valid ada di item (isi dengan None jika absen)
            for col in allowed_columns:
                if col not in item:
                    item[col] = None

            # Cek apakah data sudah ada di database lokal
            cursor.execute(f"SELECT * FROM {table_name} WHERE uuid = %s", (uuid_val,))
            existing = cursor.fetchone()

            if not existing:
                # INSERT DATA BARU
                item['status_sync'] = 'synced'
                columns = allowed_columns + ['synced_at']
                placeholders = [f"%({col})s" for col in allowed_columns] + ['NOW()']

                insert_query = f"""
                INSERT INTO {table_name} ({', '.join(columns)})
                VALUES ({', '.join(placeholders)})
                """
                cursor.execute(insert_query, item)
                print(f"INSERT LOKAL BERHASIL: {uuid_val}")
            else:
                # UPDATE DATA JIKA DATA VPS LEBIH BARU
                vps_updated_at = item.get('updated_at')
                local_updated_at = existing.get('updated_at')

                is_newer = False
                if vps_updated_at:
                    if not local_updated_at:
                        is_newer = True
                    else:
                        is_newer = str(vps_updated_at) > str(local_updated_at)

                if is_newer:
                    item['status_sync'] = 'synced'
                    update_parts = [f"{col} = %({col})s" for col in allowed_columns if col not in ['uuid', 'created_at']]
                    update_parts.append("synced_at = NOW()")

                    update_query = f"""
                    UPDATE {table_name}
                    SET {', '.join(update_parts)}
                    WHERE uuid = %(uuid)s
                    """
                    cursor.execute(update_query, item)
                    print(f"UPDATE LOKAL BERHASIL: {uuid_val}")
                else:
                    print(f"SKIP UPDATE (LOKAL LEBIH BARU/SAMA): {uuid_val}")

            synced_uuids.append(uuid_val)

        db.commit()

        # Kirim konfirmasi Acknowledgment ke VPS
        if synced_uuids:
            end_time = time.time()
            duration_ms = int((end_time - start_time) * 1000)

            ack_res = requests.post(
                f"{BASE_URL}/{ack_endpoint}",
                json={"uuids": synced_uuids},
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "X-Sync-Token": SYNC_TOKEN
                },
                timeout=10
            )

            if ack_res.status_code == 200 and ack_res.json().get("success"):
                print(f"ACK PULL {table_name.upper()} SUKSES DI VPS")
                for uuid_val in synced_uuids:
                    save_sync_log(
                        cursor,
                        table_name,
                        "pull_insert",
                        uuid_val,
                        "vps",
                        "lokal",
                        "success",
                        duration_ms,
                        f"Pull sync {table_name} berhasil"
                    )
                db.commit()
            else:
                print(f"ACK PULL {table_name.upper()} GAGAL DI VPS: {ack_res.text}")

    except Exception as e:
        print(f"PULL {table_name.upper()} ERROR:", str(e))
        db.rollback()
    finally:
        db.close()
# FUNCTION RECOVERY / SELF-HEALING (VPS -> LOKAL)
#----------------------------------------------------
def recover_lost_data(table_name, endpoint):
    # Koneksi ke database lokal
    db = pymysql.connect(**db_config)
    cursor = db.cursor(pymysql.cursors.DictCursor)

    print(f"\n[RECOVERY {table_name.upper()}]")
    print("MENGAMBIL DATA RECOVERY DARI VPS...")

    try:
        # Kirim request GET ke VPS untuk mengambil semua data
        response = requests.get(
            f"{BASE_URL}/{endpoint}",
            headers={
                "Accept": "application/json",
                "X-Sync-Token": SYNC_TOKEN
            },
            timeout=15
        )

        if response.status_code != 200:
            print(f"RECOVERY {table_name.upper()} GAGAL - Status: {response.status_code}")
            return

        hasil = response.json()
        if not hasil:
            print("TIDAK ADA DATA RECOVERY DI VPS")
            return

        print(f"MENERIMA {len(hasil)} DATA RECOVERY DARI VPS")

        recovered_count = 0
        updated_count = 0
        start_time = time.time()

        # Tentukan kolom yang valid untuk masing-masing tabel
        if table_name == 'pasien':
            allowed_columns = [
                'uuid', 'no_rm', 'nama', 'jenis_kelamin', 'tanggal_lahir',
                'dokter_id', 'dokter_uuid', 'status', 'tanggal_keluar',
                'catatan_keluar', 'is_active', 'status_sync', 'source_server',
                'action_type', 'is_deleted', 'created_at', 'updated_at'
            ]
        elif table_name == 'visit':
            allowed_columns = [
                'uuid', 'pasien_id', 'dokter_id', 'pasien_uuid', 'dokter_uuid',
                'keluhan', 'diagnosa', 'tindakan', 'status_sync', 'source_server',
                'action_type', 'created_at', 'updated_at'
            ]
        elif table_name == 'users':
            allowed_columns = [
                'uuid', 'name', 'email', 'password', 'role', 'status_sync',
                'source_server', 'action_type', 'created_at', 'updated_at'
            ]
        else:
            allowed_columns = []

        for item in hasil:
            uuid_val = item.get('uuid')
            if not uuid_val:
                continue

            # Bersihkan dan sanitisasi nilai-nilai JSON
            for k, v in item.items():
                if v == 'None' or v == 'null' or v == '' or v is None:
                    item[k] = None
                elif k in ['is_active', 'is_deleted']:
                    if v is not None:
                        item[k] = 1 if str(v).lower() in ['true', '1'] else 0
                elif k in ['created_at', 'updated_at', 'synced_at']:
                    if v is not None:
                        val_str = str(v).replace('T', ' ')
                        if '.' in val_str:
                            val_str = val_str.split('.')[0]
                        elif val_str.endswith('Z'):
                            val_str = val_str[:-1]
                        item[k] = val_str
                elif k in ['tanggal_lahir', 'tanggal_keluar']:
                    if v is not None:
                        item[k] = str(v).split('T')[0]

            # Resolusi relasi foreign key ke ID lokal berdasarkan UUID
            if table_name == 'pasien':
                dokter_uuid = item.get('dokter_uuid')
                if dokter_uuid:
                    cursor.execute("SELECT id FROM users WHERE uuid = %s", (dokter_uuid,))
                    res = cursor.fetchone()
                    item['dokter_id'] = res['id'] if res else None
                else:
                    item['dokter_id'] = None

            elif table_name == 'visit':
                pasien_uuid = item.get('pasien_uuid')
                if pasien_uuid:
                    cursor.execute("SELECT id FROM pasien WHERE uuid = %s", (pasien_uuid,))
                    res = cursor.fetchone()
                    item['pasien_id'] = res['id'] if res else None
                else:
                    item['pasien_id'] = None

                dokter_uuid = item.get('dokter_uuid')
                if dokter_uuid:
                    cursor.execute("SELECT id FROM users WHERE uuid = %s", (dokter_uuid,))
                    res = cursor.fetchone()
                    item['dokter_id'] = res['id'] if res else None
                else:
                    item['dokter_id'] = None

            # Pastikan semua key valid ada di item (isi dengan None jika absen)
            for col in allowed_columns:
                if col not in item:
                    item[col] = None

            # Cek apakah data sudah ada di database lokal
            cursor.execute(f"SELECT * FROM {table_name} WHERE uuid = %s", (uuid_val,))
            existing = cursor.fetchone()

            if not existing:
                # INSERT DATA HILANG / BARU
                item['status_sync'] = 'synced'
                columns = allowed_columns + ['synced_at']
                placeholders = [f"%({col})s" for col in allowed_columns] + ['NOW()']

                insert_query = f"""
                INSERT INTO {table_name} ({', '.join(columns)})
                VALUES ({', '.join(placeholders)})
                """
                cursor.execute(insert_query, item)
                print(f"PEMULIHAN INSERT BERHASIL: {uuid_val}")
                recovered_count += 1
            else:
                # UPDATE DATA JIKA DATA VPS LEBIH BARU
                vps_updated_at = item.get('updated_at')
                local_updated_at = existing.get('updated_at')

                is_newer = False
                if vps_updated_at:
                    if not local_updated_at:
                        is_newer = True
                    else:
                        is_newer = str(vps_updated_at) > str(local_updated_at)

                if is_newer:
                    item['status_sync'] = 'synced'
                    update_parts = [f"{col} = %({col})s" for col in allowed_columns if col not in ['uuid', 'created_at']]
                    update_parts.append("synced_at = NOW()")

                    update_query = f"""
                    UPDATE {table_name}
                    SET {', '.join(update_parts)}
                    WHERE uuid = %(uuid)s
                    """
                    cursor.execute(update_query, item)
                    print(f"PEMULIHAN UPDATE BERHASIL: {uuid_val}")
                    updated_count += 1

        db.commit()
        end_time = time.time()
        duration_ms = int((end_time - start_time) * 1000)

        # Simpan log recovery berhasil jika ada data yang dipulihkan/diupdate
        if recovered_count > 0 or updated_count > 0:
            print(f"RECOVERY {table_name.upper()} SELESAI: {recovered_count} DATA DIPULIHKAN, {updated_count} DATA DIUPDATE")
            save_sync_log(
                cursor,
                table_name,
                "recovery",
                "-",
                "vps",
                "lokal",
                "success",
                duration_ms,
                f"Recovery selesai. {recovered_count} dipulihkan, {updated_count} diupdate."
            )
            db.commit()
        else:
            print(f"RECOVERY {table_name.upper()} SELESAI: TIDAK ADA DATA LOKAL YANG HILANG/TERTANDINGI")

    except Exception as e:
        print(f"RECOVERY {table_name.upper()} ERROR:", str(e))
        db.rollback()
    finally:
        db.close()


# MAIN WORKER LOOP
#----------------------
# Worker berjalan terus menerus
# setiap 5 detik untuk:
# - PUSH: cek data pending lokal -> kirim ke VPS
# - PULL: cek data pending VPS -> tarik ke lokal
# - monitoring hybrid network

print("\n=== MENJALANKAN DISASTER RECOVERY (SELF-HEALING) ===")
recover_lost_data("users", "sync/all-users")
recover_lost_data("pasien", "sync/all-pasien")
recover_lost_data("visit", "sync/all-visit")
print("=== DISASTER RECOVERY SELESAI. MASUK KE LOOP SINKRONISASI ===\n")

while True:

    # 1. PUSH SINKRONISASI (Lokal -> VPS)
    # --------------------------------------------
    sync_data("pasien", "sync/pasien")
    sync_data("visit", "sync/visit")
    sync_data("users", "sync/users")

    # 2. PULL SINKRONISASI (VPS -> Lokal)
    # --------------------------------------------
    pull_and_sync_data("pasien", "sync/pull-pasien", "sync/acknowledge-pasien")
    pull_and_sync_data("visit", "sync/pull-visit", "sync/acknowledge-visit")
    pull_and_sync_data("users", "sync/pull-users", "sync/acknowledge-users")
    
    # delay worker 5 detik
    time.sleep(5)