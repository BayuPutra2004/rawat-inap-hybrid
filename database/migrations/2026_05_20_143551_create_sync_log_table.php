<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('sync_log', function (Blueprint $table) {
            $table->id();
            $table->string('table_name');
            $table->uuid('data_uuid');
            $table->string('source_server');
            $table->string('target_server') ->nullable();
            $table->string('sync_status');
            $table->bigInteger('sync_duration_ms')->nullable();
            $table->text('message')->nullable();
            $table->timestamps();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('sync_log');
    }
};