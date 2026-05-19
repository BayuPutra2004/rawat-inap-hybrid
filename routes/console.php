<?php

use Illuminate\Foundation\Inspiring;
use Illuminate\Support\Facades\Artisan;
use Illuminate\Support\Facades\Schedule;

// ================= TEST COMMAND =================
Artisan::command('inspire', function () {
    $this->comment(Inspiring::quote());
})->purpose('Display an inspiring quote');


// ================= AUTO SYNC HYBRID =================
// Schedule::call(function () {
//     app(\App\Http\Controllers\Api\SyncController::class)
//         ->kirimPasien();
//     app(\App\Http\Controllers\Api\SyncController::class)
//         ->kirimVisit();
// })->everyMinute();