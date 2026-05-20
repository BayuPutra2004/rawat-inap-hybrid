<?php

use Illuminate\Http\Request;
use Illuminate\Support\Facades\Route;
use Illuminate\Support\Facades\Auth;

use App\Http\Controllers\Api\PasienController;
use App\Http\Controllers\Api\VisitController;
use App\Http\Controllers\Api\UserController;
use App\Http\Controllers\Api\SyncController;

// ================= PUBLIK (Tanpa login) =================
Route::post('/login', function (Request $request) {
    $request->validate([
        'email' => 'required|email',
        'password' => 'required'
    ]);

    if (!Auth::attempt($request->only('email', 'password'))) {
        return response()->json([
            'success' => false,
            'message' => 'Email atau password salah'
        ], 401);
    }

    $user = Auth::user();
    $token = $user->createToken('mobile-token')->plainTextToken;

    return response()->json([
        'success' => true,
        'token' => $token,
        'message' => 'Login berhasil',
        'role' => $user->role,
        'name' => $user->name,
        'user'    => $user 
    ]);
});

Route::get('/ping', function () {
    return response()->json([
        'status' => 'API hidup',
        'time' => now()
    ]);
});

// ================= SYNC (TANPA LOGIN) =================
Route::post('/sync/pasien', [SyncController::class, 'syncPasien']);
Route::post('/sync/visit', [SyncController::class, 'syncVisit']);
Route::post('/sync/users', [SyncController::class, 'syncUsers']);

Route::post('/sync/kirim-pasien', [SyncController::class, 'kirimPasien']);
Route::post('/sync/kirim-visit',  [SyncController::class, 'kirimVisit']);
   

// ================= WAJIB LOGIN =================
Route::middleware('auth:sanctum')->group(function () {

    // ================= PASIEN =================
    Route::get('/pasien/{id}', [PasienController::class, 'show']);
    Route::get('/pasien', [PasienController::class, 'index']);
    Route::post('/pasien', [PasienController::class, 'store']);
    Route::put('/pasien/{id}', [PasienController::class, 'update']);
    Route::delete('/pasien/{id}', [PasienController::class, 'destroy']);
    Route::get('/pasien-by-dokter/{id}', [PasienController::class, 'pasienByDokter']);
    Route::get('/pasien-by-visit/{dokterId}', [VisitController::class, 'pasienByDokterVisit']);

    // ================= DOKTER =================
    Route::post('/dokter', [UserController::class, 'storeDokter']);
    Route::get('/dokter', [UserController::class, 'getDokter']);
    Route::put('/dokter/{id}', [UserController::class, 'updateDokter']);
    Route::delete('/dokter/{id}', [UserController::class, 'deleteDokter']);

    // ================= VISIT =================
    Route::get('/visit', [VisitController::class, 'index']);
    Route::post('/visit', [VisitController::class, 'store']);
    Route::get('/visit/pasien/{id}', [VisitController::class, 'byPasien']);
    Route::get('/visit/pasien/{pasienId}/dokter/{dokterId}', [VisitController::class, 'byPasienDokter']);

    // ================= PASIEN PULANG =================
    Route::put('/pasien/{id}/pulang', function ($id) {
        $pasien = \App\Models\Pasien::find($id);

        if (!$pasien) {
            return response()->json([
                'success' => false,
                'message' => 'Pasien tidak ditemukan'
            ], 404);
        }

        $pasien->update(['is_active' => false]);
        return response()->json(['success' => true]);
    });

    // ================= SYNC =================
    Route::get('/sync/avg',           [SyncController::class, 'avgSyncTime']);

    // ================= LOGOUT =================
    Route::post('/logout', function (Request $request) {
        $request->user()->currentAccessToken()->delete();
        return response()->json(['message' => 'Logout berhasil']);
    });
});