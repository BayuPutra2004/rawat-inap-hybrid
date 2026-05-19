<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use Illuminate\Http\Request;
use App\Models\Visit;

class VisitController extends Controller
{
    // 🔥 AMBIL SEMUA VISIT (WAJIB untuk performa)
    public function index()
    {
        return response()->json([
            'success' => true,
            'data' => Visit::with('dokter')->latest()->get()
        ]);
    }

    // 🔥 VISIT BY PASIEN
    public function byPasien($pasienId)
    {
        $visit = Visit::with('dokter')
            ->where('pasien_id', $pasienId)
            ->latest()
            ->get();

        return response()->json([
            'success' => true,
            'data' => $visit
        ]);
    }

    // 🔥 VISIT BY PASIEN + DOKTER
    public function byPasienDokter($pasienId, $dokterId)
    {
        $visit = Visit::with('dokter')
            ->where('pasien_id', $pasienId)
            ->where('dokter_id', $dokterId)
            ->latest()
            ->get();

        return response()->json([
            'success' => true,
            'data' => $visit
        ]);
    }

    // 🔥 INPUT VISIT
    public function store(Request $request)
    {
        try {
            $request->validate([
                'pasien_id' => 'required|exists:pasien,id',
                'dokter_id' => 'required|exists:users,id',
                'keluhan' => 'required',
                'diagnosa' => 'required',
                'tindakan' => 'required',
            ]);

            $pasien = \App\Models\Pasien::find($request->pasien_id);
            $dokter = \App\Models\User::find($request->dokter_id);
            $visit = Visit::create([
                'pasien_id' => $request->pasien_id,
                'dokter_id' => $request->dokter_id,

                // UUID RELATION
                'pasien_uuid' => $pasien?->uuid,
                'dokter_uuid' => $dokter?->uuid,

                // DATA VISIT
                'keluhan' => $request->keluhan,
                'diagnosa' => $request->diagnosa,
                'tindakan' => $request->tindakan,
            ]);

            return response()->json([
                'success' => true,
                'message' => 'Visit berhasil',
                'data' => $visit
            ]);

        } catch (\Exception $e) {
            return response()->json([
                'error' => $e->getMessage()
            ], 500);
        }
    }

    public function pasienByDokterVisit($dokterId)
    {
        // ambil semua pasien_id yang pernah di-visit dokter ini
        $pasienIds = Visit::where('dokter_id', $dokterId)
            ->pluck('pasien_id')
            ->unique();

        // ambil data pasiennya
        $pasien = \App\Models\Pasien::with('dokter')
            ->whereIn('id', $pasienIds)
            ->get();

        return response()->json([
            'success' => true,
            'data' => $pasien
        ]);
    }
}