<?php

namespace App\Http\Middleware;

use Closure;
use Illuminate\Http\Request;
use Symfony\Component\HttpFoundation\Response;

class VerifySyncToken
{
    /**
     * Handle an incoming request.
     *
     * @param  \Closure(\Illuminate\Http\Request): (\Symfony\Component\HttpFoundation\Response)  $next
     */
    public function handle(Request $request, Closure $next): Response
    {
        $token = $request->header('X-Sync-Token');
        $expectedToken = env('SYNC_SECRET_KEY');

        if (!$expectedToken || $token !== $expectedToken) {
            return response()->json([
                'success' => false,
                'message' => 'Unauthorized: Invalid Sync Token'
            ], 401);
        }

        return $next($request);
    }
}
