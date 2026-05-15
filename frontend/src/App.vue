<template>
    <header>
        <div class="d-flex flex-column flex-md-row align-items-center py-3 mb-3 border-bottom">
            <a href="/" class="d-flex align-items-center link-body-emphasis text-decoration-none">
                <!-- <span class="fs-4 text-uppercase fw-bold">NewFace Recognition</span> -->
                <!-- <span class="fs-4 text-uppercase fw-bold">Saijaan Recognition</span> -->
                <!-- <span class="fs-4 fw-bold text-danger">IG : hendri.arifin.skom | WA : 085746080544</span> -->
                <span class="fs-4 fw-bold text-warning">SMKN 1 KOTABARU | REKAYASA PERANGKAT LUNAK</span>
            </a>
            <nav class="d-inline-flex mt-2 mt-md-0 ms-md-auto">
                <RouterLink to="/" class="me-3 py-2 link-body-emphasis text-decoration-none" href="#">Home</RouterLink>
                <RouterLink to="/register" class="me-3 py-2 link-body-emphasis text-decoration-none" href="#">Register</RouterLink>
                <RouterLink to="/recognize" class="me-3 py-2 link-body-emphasis text-decoration-none" href="#">Recognition</RouterLink>
                <RouterLink to="/violation" class="me-3 py-2 link-body-emphasis text-decoration-none" href="#">Violation</RouterLink>
                <a class="py-2 link-body-emphasis text-decoration-none" href="#">Pricing</a>
            </nav>
        </div>
        <div class="pb-4 mx-auto text-center bg-dark text-white mb-4">
            <h1 class="display-4 fw-bold mb-0">MANFAAT</h1>
            <p class="fs-1 fw-bold text-uppercase mb-0">Absen, Monitoring, Lalulintas, Antrian, Tiket, Verifikasi, Menghitung</p>
        </div>
    </header>
    <RouterView />
    <footer class="mt-5">
        <ul class="list-unstyled d-flex justify-content-center flex-wrap">
            <li class="me-2"><span class="badge p-3 mb-2 rounded-pill fw-lighter text-bg-success">Absen Siswa / Pegawai</span></li>
            <li class="me-2"><span class="badge p-3 mb-2 rounded-pill fw-lighter text-bg-success">Tilang Elektronik</span></li>
            <li class="me-2"><span class="badge p-3 mb-2 rounded-pill fw-lighter text-bg-success">Monitoring Rapat / Kegiatan / Ruangan</span></li>
            <li class="me-2"><span class="badge p-3 mb-2 rounded-pill fw-lighter text-bg-success">Verifikasi Bandara / DPO / Ruang Tahanan</span></li>
            <li class="me-2"><span class="badge p-3 mb-2 rounded-pill fw-lighter text-bg-success">Rekam Medis</span></li>
            <li class="me-2"><span class="badge p-3 mb-2 rounded-pill fw-lighter text-bg-success">Human Analytics (Usia, Gender, Ekspresi)</span></li>
            <li class="me-2"><span class="badge p-3 mb-2 rounded-pill fw-lighter text-bg-success">Menghitung jumlah pengunjung dan berapa lama</span></li>
        </ul>
        <!-- <div class="row">
            <div class="col-12 col-md-6">
                <h5 class="fw-bold">Tentang Kami</h5>
                <p class="small">Kami adalah penyedia solusi pengenalan wajah berbasis AI.</p>
            </div>
            <div class="col-12 col-md-6">
                <h5 class="fw-bold">Kontak</h5>
                <p class="small">Email: info@newface.com</p>
                <p class="small">Telepon: 08123456789</p>
            </div>
        </div> -->
    </footer>
</template>
<script setup>
    import { RouterView } from 'vue-router'
</script>