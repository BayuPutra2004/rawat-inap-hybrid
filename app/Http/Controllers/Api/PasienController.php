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
        $pasien = Pasien::with('dokter')->get();

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

        $pasien = Pasien::create([
            'no_rm' => $request->no_rm,
            'nama' => $request->nama,
            'jenis_kelamin' => $request->jenis_kelamin,
            'tanggal_lahir' => $request->tanggal_lahir,
            'dokter_id' => $request->dokter_id,
            'is_active' => 1,
            'status' => 'dirawat',
            'tanggal_keluar' => null,
            'catatan_keluar' => null,
        ]);
        // AUTO SYNC KE SERVER LAIN
        app(\App\Http\Controllers\Api\SyncController::class)
            ->kirimPasien();
        
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
            $pasien->dokter_id =
                $request->has('dokter_id')
                ? $request->dokter_id
                : $pasien->dokter_id;
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

        if (!$pasien) {
            return response()->json([
                'success' => false,
                'message' => 'Pasien tidak ditemukan'
            ], 404);
        }

        $pasien->delete();

        return response()->json([
            'success' => true
        ]);
    }

    // ================= PASIEN BY DOKTER =================
    public function pasienByDokter($id)
    {
        $pasien = Pasien::where('dokter_id', $id)
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
        $pasien = Pasien::with('dokter')->find($id);

        if (!$pasien) {
            return response()->json([
                'message' => 'Pasien tidak ditemukan'
            ], 404);
        }

        return response()->json($pasien);
    }
}