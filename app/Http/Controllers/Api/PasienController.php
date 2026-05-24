<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use Illuminate\Http\Request;
use App\Models\Pasien;

class PasienController extends Controller
{
    // ================= GET ALL PASIEN =================
    public function index()
    {
        $pasien = Pasien::with('dokter')
            ->where('is_deleted', false)
            ->get();
        
        return response()->json([
            'success' => true,
            'data' => $pasien
        ]);
    }

    // ================= TAMBAH PASIEN =================
    public function store(Request $request)
    {
        $request->validate([
            'no_rm' => 'required',
            'nama' => 'required',
            'jenis_kelamin' => 'required',
            'tanggal_lahir' => 'required',
        ]);

        // AMBIL DATA DOKTER
        $dokter = \App\Models\User::find($request->dokter_id);

        // SIMPAN PASIEN
        $pasien = Pasien::create([
            'no_rm' => $request->no_rm,
            'nama' => $request->nama,
            'jenis_kelamin' => $request->jenis_kelamin,
            'tanggal_lahir' => $request->tanggal_lahir,
            'dokter_id' => $request->dokter_id,

            // UUID DOKTER
            'dokter_uuid' => $dokter ? $dokter->uuid : null,
            'is_active' => 1,
            'status' => 'dirawat',
            'tanggal_keluar' => null,
            'catatan_keluar' => null,

            // HYBRID SYNC
            'status_sync' => 'pending',
            'source_server' => 'lokal',
            'action_type' => 'create',
            'synced_at' => null
        ]);

        return response()->json([
            'success' => true,
            'data' => $pasien
        ]);
    }

    // ================= UPDATE PASIEN =================
    public function update(Request $request, $id)
    {
        try {
            $pasien = Pasien::find($id);
            if (!$pasien) {
                return response()->json([
                    'success' => false,
                    'message' => 'Pasien tidak ditemukan'
                ], 404);
            }

            // UPDATE DATA PASIEN
            $pasien->nama = $request->nama ?? $pasien->nama;
            $pasien->jenis_kelamin = $request->jenis_kelamin ?? $pasien->jenis_kelamin;
            $pasien->tanggal_lahir = $request->tanggal_lahir ?? $pasien->tanggal_lahir;
            
            // UPDATE DOKTER
            $pasien->dokter_id =
                $request->has('dokter_id')
                ? $request->dokter_id
                : $pasien->dokter_id;

            // AMBIL UUID DOKTER BARU
            $dokter = \App\Models\User::find($pasien->dokter_id);

            $pasien->dokter_uuid =
                $dokter ? $dokter->uuid : null;

            $pasien->status = $request->status ?? $pasien->status;
            $pasien->catatan_keluar = $request->catatan_keluar ?? $pasien->catatan_keluar;

            // STATUS PASIEN
            if (
                $pasien->status == 'pulang' ||
                $pasien->status == 'meninggal'
            ) {
                $pasien->tanggal_keluar =
                    now()->toDateString();
            } else {
                $pasien->tanggal_keluar = null;
            }

            // TANDAI PERLU SYNC ULANG
            $pasien->status_sync = 'pending';
            $pasien->source_server = 'lokal';
            $pasien->synced_at = null;

            // for sync log
            $pasien->action_type = 'update';
            
            // simpan perubahan
            $pasien->save();

            // reload relasi dokter
            $pasien->load('dokter');

            // RESPONSE SUCCESS
            return response()->json([
                'success' => true,
                'message' => 'Data pasien berhasil diupdate',
                'data' => $pasien
            ], 200);
        } catch (\Exception $e) {
            return response()->json([
                'success' => false,
                'message' => $e->getMessage()
            ], 500);
        }
    }

    // ================= DELETE PASIEN =================
    public function destroy($id)
    {
        $pasien = Pasien::find($id);

        // CEK PASIEN
        if (!$pasien) {
            return response()->json([
                'success' => false,
                'message' => 'Pasien tidak ditemukan'
            ], 404);
        }

        // SOFT DELETE HYBRID SYNC
        $pasien->is_deleted = true;

        // TANDAI PERLU SYNC
        $pasien->status_sync = 'pending';
        $pasien->source_server = 'lokal';
        $pasien->synced_at = null;

        // ACTION DELETE
        $pasien->action_type = 'delete';

        // SIMPAN
        $pasien->save();
        return response()->json([
            'success' => true,
            'message' => 'Pasien berhasil dihapus'
        ]);
    }

    // ================= PASIEN BY DOKTER =================
    public function pasienByDokter($id)
    {
        $pasien = 
        Pasien::where('dokter_id', $id)
        ->where('is_deleted', false)
            ->with('dokter')
            ->get();

        return response()->json([
            'success' => true,
            'data' => $pasien
        ]);
    }

    // ================= DETAIL PASIEN =================
    public function show($id)
    {
        $pasien = 
        Pasien::with('dokter')
        ->where('is_deleted', false)
        ->find($id);

        if (!$pasien) {
            return response()->json([
                'message' => 'Pasien tidak ditemukan'
            ], 404);
        }

        return response()->json($pasien);
    }
}