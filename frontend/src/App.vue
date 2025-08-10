<template>
    <header>
        <div class="d-flex flex-column flex-md-row align-items-center py-3 mb-3 border-bottom">
            <a href="/" class="d-flex align-items-center link-body-emphasis text-decoration-none">
                <!-- <span class="fs-4 text-uppercase fw-bold">NewFace Recognition</span> -->
                <!-- <span class="fs-4 text-uppercase fw-bold">Saijaan Recognition</span> -->
                <span class="fs-4 fw-bold text-danger">IG : hendri.arifin.skom | WA : 085746080544</span>
            </a>
            <nav class="d-inline-flex mt-2 mt-md-0 ms-md-auto">
                <RouterLink to="/" class="me-3 py-2 link-body-emphasis text-decoration-none" href="#">Home</RouterLink>
                <RouterLink to="/register" class="me-3 py-2 link-body-emphasis text-decoration-none" href="#">Register</RouterLink>
                <RouterLink to="/recognize" class="me-3 py-2 link-body-emphasis text-decoration-none" href="#">Recognition</RouterLink>
                <a class="py-2 link-body-emphasis text-decoration-none" href="#">Pricing</a>
            </nav>
        </div>
        <div class="pb-4 mx-auto text-center">
            <h1 class="display-4 fw-bold text-success mb-0">MANFAAT</h1>
            <p class="fs-1 text-danger fw-bold text-uppercase mb-0">Absen, Monitoring, Antrian, Verifikasi, Menghitung</p>
            <ul class="list-unstyled d-flex justify-content-center flex-wrap">
                <li class="me-3"><span class="badge text-bg-success">Absen Siswa / Pegawai</span></li>
                <li class="me-3"><span class="badge text-bg-success">Monitoring Rapat / Kegiatan / Ruangan</span></li>
                <li class="me-3"><span class="badge text-bg-success">Verifikasi Bandara / DPO / Ruang Tahanan</span></li>
                <li class="me-3"><span class="badge text-bg-success">Rekam Medis</span></li>
                <li class="me-3"><span class="badge text-bg-success">Human Analytics (Usia, Gender, Ekspresi)</span></li>
                <li class="me-3"><span class="badge text-bg-success">Menghitung jumlah pengunjung dan berapa lama</span></li>
            </ul>
        </div>
    </header>
    <RouterView />
</template>
<script setup>
    import { RouterView } from 'vue-router'
</script>