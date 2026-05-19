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
            'name' => 'required',
            'email' => 'required|email|unique:users,email',
            'password' => 'required|min:6',
        ]);

        $user = User::create([
            'name' => $request->name,
            'email' => $request->email,
            'password' => Hash::make($request->password),
            'role' => 'dokter',
        ]);

        return response()->json(['data' => $user]);
    }

    // EDIT DOKTER
    public function updateDokter(Request $request, $id)
    {
	\Log::info('UPDATE MASUK', $request->all()); // 🔥 deb

	$user = User::findOrFail($id);

	$user->update([
	      'name' => $request->input('name'),   // 🔥 WAJIB pakai input()
	      'email' => $request->input('email'),
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
