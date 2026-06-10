<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\User;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Hash;

class UserController extends Controller
{
    // GET DOKTER
    public function getDokter()
    {
        $dokter = User::where('role', 'dokter')->get();

        return response()->json([
            'data' => $dokter
        ]);
    }

    // TAMBAH DOKTER
    public function storeDokter(Request $request)
    {
        $request->validate([
            'name'     => 'required',
            'email'    => 'required|email|unique:users,email',
            'password' => 'required|min:6',
        ]);

        $user = User::create([
            'name'          => $request->name,
            'email'         => $request->email,
            'password'      => Hash::make($request->password),
            'role'          => 'dokter',

            // HYBRID SYNC — dokter baru harus tersinkron ke VPS
            'status_sync'   => 'pending',
            'source_server' => env('SERVER_ROLE', 'lokal'),
            'action_type'   => 'create',
        ]);

        return response()->json(['data' => $user]);
    }

    // EDIT DOKTER
    public function updateDokter(Request $request, $id)
    {
        $user = User::findOrFail($id);

        $user->update([
            'name'          => $request->input('name'),
            'email'         => $request->input('email'),

            // HYBRID SYNC — perubahan dokter harus tersinkron ke VPS
            'status_sync'   => 'pending',
            'source_server' => env('SERVER_ROLE', 'lokal'),
            'action_type'   => 'update',
        ]);

        return response()->json([
            'data' => $user
        ]);
    }

    // DELETE DOKTER
    public function deleteDokter($id)
    {
        $user = User::findOrFail($id);
        $user->delete();

        return response()->json(['message' => 'Dokter dihapus']);
    }
}
