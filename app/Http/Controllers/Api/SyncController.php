<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\DB;
use Carbon\Carbon;
use App\Models\Pasien;
use App\Models\Visit;

class SyncController extends Controller
{
    // ================== TERIMA DATA DARI SERVER LAIN ==================

    public function syncPasien(Request $request)
    {
        foreach ($request->all() as $item) {

            // CARI DOKTER BERDASARKAN UUID
            $dokter = \App\Models\User::where('uuid', $item['dokter_uuid'])->first();

            // CEK DATA PASIEN
            $existing = Pasien::where('uuid',$item['uuid'])->first();
            //hendle delete
            if (
                isset($item['is_deleted'])
                && (
                    $item['is_deleted'] == 1 ||
                    $item['is_deleted'] == "1"
                )
            ) {
                if ($existing) {
                    $existing->update([
                        'is_deleted' => true,
                        'status_sync' => 'synced',
                        'action_type' => 'delete',
                        'synced_at' => now()
                    ]);
                }

                continue;
            }

            // DATA BARU
            if (!$existing) {
                Pasien::create([
                    'uuid' => $item['uuid'],
                    'no_rm' => $item['no_rm'],
                    'nama' => $item['nama'],
                    'jenis_kelamin' =>$item['jenis_kelamin'],
                    'tanggal_lahir' =>$item['tanggal_lahir'],
                    // DOKTER VPS
                    'dokter_id' =>$dokter ? $dokter->id : null,
                    'dokter_uuid' => $item['dokter_uuid'],
                    'status' => $item['status'],
                    'tanggal_keluar' => $item['tanggal_keluar'],
                    'catatan_keluar' => $item['catatan_keluar'],
                    'is_active' => $item['is_active'],

                    // HYBRID SYNC
                    'status_sync' => 'synced',
                    'synced_at' => now(),
                    'source_server' => $item['source_server'],
                    'action_type' => $item['action_type'],
                    'is_deleted' => $item['is_deleted'],
                    'created_at' =>  $item['created_at'],
                    'updated_at' => $item['updated_at']
                ]);

            } else {
                // CONFLICT HANDLING
                if (
                    $item['updated_at']
                    > $existing->updated_at
                ) {
                    $existing->update([
                        'no_rm' => $item['no_rm'],
                        'nama' => $item['nama'],
                        'jenis_kelamin' => $item['jenis_kelamin'],
                        'tanggal_lahir' => $item['tanggal_lahir'],

                        // DOKTER VPS
                        'dokter_id' =>  $dokter ? $dokter->id : null,
                        'dokter_uuid' => $item['dokter_uuid'],
                        'status' =>  $item['status'],
                        'tanggal_keluar' =>  $item['tanggal_keluar'],
                        'catatan_keluar' => $item['catatan_keluar'],
                        'is_active' =>  $item['is_active'],

                        // HYBRID SYNC
                        // ====================================
                        'status_sync' => 'synced',
                        'synced_at' => now(),
                        'source_server' => $item['source_server'],
                        'action_type' =>  $item['action_type']
                    ]);

                } else {
                    // DATA CONFLICT
                    $existing->update([
                        'status_sync' => 'conflict'
                    ]);
                }
            }
        }

        return response()->json([
            'success' => true
        ]);
    }

    public function syncVisit(Request $request)
    {
        foreach ($request->all() as $item) {

            // CARI PASIEN BERDASARKAN UUID
            $pasien = Pasien::where('uuid',$item['pasien_uuid'])->first();

            // CARI DOKTER BERDASARKAN UUID
            $dokter = \App\Models\User::where('uuid',$item['dokter_uuid'])->first();

            // CEK DATA VISIT SUDAH ADA ATAU BELUM
            $existing = Visit::where('uuid',$item['uuid'])->first();

            // DATA BARU
            if (!$existing) {
                Visit::create([
                    'pasien_id' => $pasien?->id,
                    'dokter_id' => $dokter?->id,
                    'pasien_uuid' => $item['pasien_uuid'],
                    'dokter_uuid' => $item['dokter_uuid'],
                    'keluhan' => $item['keluhan'],
                    'diagnosa' => $item['diagnosa'],
                    'tindakan' => $item['tindakan'],
                    'uuid' => $item['uuid'],
                    'status_sync' => 'synced',
                    'synced_at' => now(),
                    'source_server' => 'source_server',
                    'created_at' => $item['created_at'],
                    'updated_at' => $item['updated_at'],
                    'action_type' => $item['action_type'],
                    'is_deleted' => $item['is_deleted'],
                ]);

            } else {

                // CONFLICT HANDLING
                if ($item['updated_at'] > $existing->updated_at) {
                    $existing->update([
                        'pasien_id' => $pasien?->id,
                        'dokter_id' => $dokter?->id,
                        'keluhan' => $item['keluhan'],
                        'diagnosa' => $item['diagnosa'],
                        'tindakan' => $item['tindakan'],
                        'status_sync' => 'synced',
                        'action_type' => $item['action_type'],
                        'synced_at' => now(),
                    ]);
                } else {
                    $existing->update([
                        'status_sync' => 'conflict'
                    ]);
                }
            }
        }
        return response()->json([
            'success' => true
        ]);
    }

    // sync user
    public function syncUsers(Request $request)
    {
        try {
            // AMBIL DATA USER
            $data = $request->all();

            foreach ($data as $item) {                
                // UPDATE ATAU CREATE USER
                $existing = \App\Models\User::where(
                    'uuid',
                    $item['uuid']
                )->orWhere(
                    'email',
                    $item['email']
                )->first();

                if ($existing) {

                    // UPDATE USER
                    $existing->update([

                        'uuid' => $item['uuid'],
                        'name' => $item['name'],
                        'email' => $item['email'],
                        'password' => $item['password'],
                        'role' => $item['role'],
                        'status_sync' => 'synced',
                        'synced_at' => now(),
                        'source_server' =>
                            $item['source_server'],
                        'action_type' =>
                            $item['action_type']
                    ]);

                } else {
                    // CREATE USER BARU
                    \App\Models\User::create([
                        'uuid' => $item['uuid'],
                        'name' => $item['name'],
                        'email' => $item['email'],
                        'password' => $item['password'],
                        'role' => $item['role'],
                        'status_sync' => 'synced',
                        'synced_at' => now(),
                        'source_server' =>
                            $item['source_server'],
                        'action_type' =>
                            $item['action_type']
                    ]);
                }
            }

            // RESPONSE SUCCESS
            return response()->json([
                'success' => true,
                'message' => 'Sync users success'
            ], 200);
        } catch (\Exception $e) {
            return response()->json([
                'success' => false,
                'message' => $e->getMessage()
            ], 500);
        }
    }

    // ================== KIRIM DATA KE SERVER LAIN ==================
    public function kirimPasien()
    {
        $startedAt = Carbon::now();
        $data = Pasien::where('status_sync', 'pending')
        ->where('source_server', 'lokal')
        ->get();

        if ($data->isEmpty()) {
            return response()->json([
                'success' => true,
                'pesan'   => 'Tidak ada data pasien yang perlu disync',
            ]);
        }

        try {
            $res = Http::timeout(10)
            ->post(env('SYNC_URL') . '/sync/pasien', $data->toArray());
            $finishedAt = Carbon::now();
            $durasiMs   = $startedAt->diffInMilliseconds($finishedAt);

            if ($res->successful()) {
                foreach ($data as $item) {
                    $item->update([
                        'status_sync' => 'synced',
                        'synced_at'   => now(),
                    ]);
                }

                $this->catatLog('pasien', 'lokal_ke_publik', 'success',
                    'success sync ' . $data->count() . ' pasien',
                    $startedAt, $finishedAt, $durasiMs
                );

                return response()->json([
                    'success'   => true,
                    'jumlah'    => $data->count(),
                    'durasi_ms' => $durasiMs,
                    'pesan'     => "Sync {$data->count()} pasien selesai dalam {$durasiMs}ms",
                ]);
            }

            throw new \Exception('Response failed: ' . $res->status());

        } catch (\Exception $e) {
            $finishedAt = Carbon::now();
            $durasiMs   = $startedAt->diffInMilliseconds($finishedAt);

            $this->catatLog('pasien', 'lokal_ke_publik', 'failed',
                $e->getMessage(), $startedAt, $finishedAt, $durasiMs
            );

            return response()->json([
                'success' => false,
                'pesan'   => 'Sync failed: ' . $e->getMessage(),
            ], 500);
        }
    }

    public function kirimVisit()
    {
        $startedAt = Carbon::now();
        $data = Visit::where('status_sync', 'pending')
            ->where('source_server', 'lokal')
            ->get();
        if ($data->isEmpty()) {
            return response()->json([
                'success' => true,
                'pesan'   => 'Tidak ada data visit yang perlu disync',
            ]);
        }

        try {
            $res = Http::timeout(10)
                ->post(env('SYNC_URL') . '/sync/visit', $data->toArray());

            $finishedAt = Carbon::now();
            $durasiMs   = $startedAt->diffInMilliseconds($finishedAt);

            if ($res->successful()) {
                foreach ($data as $item) {
                    $item->update([
                        'status_sync' => 'synced',
                        'synced_at'   => now(),
                    ]);
                }

                $this->catatLog('visit', 'lokal_ke_publik', 'success',
                    'success sync ' . $data->count() . ' visit',
                    $startedAt, $finishedAt, $durasiMs
                );

                return response()->json([
                    'success'   => true,
                    'jumlah'    => $data->count(),
                    'durasi_ms' => $durasiMs,
                    'pesan'     => "Sync {$data->count()} visit selesai dalam {$durasiMs}ms",
                ]);
            }

            throw new \Exception('Response failed: ' . $res->status());

        } catch (\Exception $e) {
            $finishedAt = Carbon::now();
            $durasiMs   = $startedAt->diffInMilliseconds($finishedAt);

            $this->catatLog('visit', 'lokal_ke_publik', 'failed',
                $e->getMessage(), $startedAt, $finishedAt, $durasiMs
            );

            return response()->json([
                'success' => false,
                'pesan'   => 'Sync failed: ' . $e->getMessage(),
            ], 500);
        }
    }

    // ================== AVG SYNC TIME ==================

    public function avgSyncTime()
    {
        $avg = DB::table('sync_log')
            ->where('sync_status', 'success')
            ->whereNotNull('sync_duration_ms')
            ->avg('sync_duration_ms');

        return response()->json([
            'avg_ms'    => round($avg, 2),
            'avg_detik' => round($avg / 1000, 3),
            'pesan'     => 'Rata-rata waktu sinkronisasi: ' 
                . round($avg, 2) 
                . ' ms',
        ]);
    }

    // ================== HELPER LOG ==================

    private function catatLog(
        $tableName,
        $targetServer,
        $syncStatus,
        $message,
        $startedAt,
        $finishedAt,
        $durationMs
    )
    {
        DB::table('sync_log')->insert([

            // NAMA TABEL YANG DISYNC
            'table_name' => $tableName,

            // UUID DATA
            'data_uuid' => '-',

            // SERVER ASAL
            // 
            'source_server' =>
                env('SERVER_ROLE', 'lokal'),

            // SERVER TUJUAN
            'target_server' =>
                $targetServer,

            // STATUS SYNC
            // success / failed
            'sync_status' =>
                $syncStatus,

            // WAKTU SYNC (MS)
            'sync_duration_ms' =>
                $durationMs,

            // PESAN LOG
            'message' =>
                $message,

            // TIMESTAMP
            'created_at' => Carbon::now(),
            'updated_at' => Carbon::now()
        ]);
    }
}