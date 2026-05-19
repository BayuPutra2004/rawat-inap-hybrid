<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    /**
     * Run the migrations.
     */
    public function up(): void
    {
        Schema::create('visit', function (Blueprint $table) {
	   $table->id();
	   $table->foreignId('pasien_id')->constrained('pasien')->onDelete('cascade');
	   $table->text('keluhan')->nullable();
	   $table->text('diagnosa')->nullable();
	   $table->text('tindakan')->nullable();
	   $table->timestamps();
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('visit');
    }
};
