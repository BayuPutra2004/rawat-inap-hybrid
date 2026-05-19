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
	    Schema::create('pemeriksaan_visit', function (Blueprint $table) {
	        $table->id();
	        $table->foreignId('rawat_inap_id')->constrained('rawat_inap')->cascadeOnDelete();
	        $table->date('tanggal_visit');
	        $table->text('keluhan')->nullable();
	        $table->text('pemeriksaan_fisik')->nullable();
	        $table->text('diagnosa')->nullable();
	        $table->text('rencana_tindakan')->nullable();
	        $table->timestamps();
	    });
	}

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('pemeriksaan_visit');
    }
};
