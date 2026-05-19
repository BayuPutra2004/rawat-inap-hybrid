<?php

namespace App\Console\Commands;

use Illuminate\Console\Command;

class SyncData extends Command
{
    protected $signature = 'sync:data';
    protected $description = 'Sync data ke server lain';

    public function handle()
    {
        $sync = new \App\Http\Controllers\Api\SyncController();

        $sync->kirimPasien();
        $sync->kirimVisit();
    }
}