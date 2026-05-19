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
            $existing = Pasien::where('uuid', $item['uuid'])->first();

            if (!$existing) {
                Pasien::create(array_merge($item, [
                    'status_sync' => 'synced',
                    'synced_at'   => now(),
                ]));
            } else {
                if ($item['updated_at'] > $existing->updated_at) {
                    $existing->update(array_merge($item, [
                        'status_sync' => 'synced',
                        'synced_at'   => now(),
                    ]));
                } else {
                    // Data konflik — updated_at sama atau lebih lama
                    $existing->update(['status_sync' => 'conflict']);
                }
            }
        }

        return response()->json(['success' => true]);
    }

    public function syncVisit(Request $request)
    {
        foreach ($request->all() as $item) {
            $existing = Visit::where('uuid', $item['uuid'])->first();

            if (!$existing) {
                Visit::create(array_merge($item, [
                    'status_sync' => 'synced',
                    'synced_at'   => now(),
                ]));
            } else {
                if ($item['updated_at'] > $existing->updated_at) {
                    $existing->update(array_merge($item, [
                        'status_sync' => 'synced',
                        'synced_at'   => now(),
                    ]));
                } else {
                    $existing->update(['status_sync' => 'conflict']);
                }
            }
        }

        return response()->json(['success' => true]);
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

                $this->catatLog('pasien', 'lokal_ke_publik', 'berhasil',
                    'Berhasil sync ' . $data->count() . ' pasien',
                    $startedAt, $finishedAt, $durasiMs
                );

                return response()->json([
                    'success'   => true,
                    'jumlah'    => $data->count(),
                    'durasi_ms' => $durasiMs,
                    'pesan'     => "Sync {$data->count()} pasien selesai dalam {$durasiMs}ms",
                ]);
            }

            throw new \Exception('Response gagal: ' . $res->status());

        } catch (\Exception $e) {
            $finishedAt = Carbon::now();
            $durasiMs   = $startedAt->diffInMilliseconds($finishedAt);

            $this->catatLog('pasien', 'lokal_ke_publik', 'gagal',
                $e->getMessage(), $startedAt, $finishedAt, $durasiMs
            );

            return response()->json([
                'success' => false,
                'pesan'   => 'Sync gagal: ' . $e->getMessage(),
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

                $this->catatLog('visit', 'lokal_ke_publik', 'berhasil',
                    'Berhasil sync ' . $data->count() . ' visit',
                    $startedAt, $finishedAt, $durasiMs
                );

                return response()->json([
                    'success'   => true,
                    'jumlah'    => $data->count(),
                    'durasi_ms' => $durasiMs,
                    'pesan'     => "Sync {$data->count()} visit selesai dalam {$durasiMs}ms",
                ]);
            }

            throw new \Exception('Response gagal: ' . $res->status());

        } catch (\Exception $e) {
            $finishedAt = Carbon::now();
            $durasiMs   = $startedAt->diffInMilliseconds($finishedAt);

            $this->catatLog('visit', 'lokal_ke_publik', 'gagal',
                $e->getMessage(), $startedAt, $finishedAt, $durasiMs
            );

            return response()->json([
                'success' => false,
                'pesan'   => 'Sync gagal: ' . $e->getMessage(),
            ], 500);
        }
    }

    // ================== AVG SYNC TIME ==================

    public function avgSyncTime()
    {
        $avg = DB::table('sync_log')
            ->where('status', 'berhasil')
            ->whereNotNull('duration_ms')
            ->avg('duration_ms');

        return response()->json([
            'avg_ms'    => round($avg, 2),
            'avg_detik' => round($avg / 1000, 3),
            'pesan'     => 'Rata-rata waktu sinkronisasi: ' . round($avg, 2) . ' ms',
        ]);
    }

    // ================== HELPER LOG ==================

    private function catatLog($tabel, $arah, $status, $pesan, $startedAt, $finishedAt, $durasiMs)
    {
        DB::table('sync_log')->insert([
            'tabel'         => $tabel,
            'uuid_data'     => '-',
            'arah'          => $arah,
            'status'        => $status,
            'pesan'         => $pesan,
            'source_server' => env('SERVER_ROLE', 'lokal'),
            'started_at'    => $startedAt,
            'finished_at'   => $finishedAt,
            'duration_ms'   => $durasiMs,
            'created_at'    => Carbon::now(),
        ]);
    }
}