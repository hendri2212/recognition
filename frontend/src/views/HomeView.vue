<template>
    <section class="home-hero">
        <img :src="heroImage" alt="Dashboard pengenalan wajah untuk monitoring area institusi" />
        <div class="hero-shade"></div>
        <div class="page-width hero-content">
            <p class="eyebrow">AI Recognition Showcase</p>
            <h1>NewFace Recognition</h1>
            <p class="hero-copy">
                Platform demo computer vision untuk registrasi wajah, pengenalan langsung, dan
                analisis pelanggaran visual yang siap dipresentasikan ke lingkungan sekolah,
                layanan publik, dan operasional lapangan.
            </p>
            <div class="hero-actions">
                <RouterLink to="/recognize" class="btn btn-info">
                    <i class="bi bi-camera-video"></i>
                    Coba recognition
                </RouterLink>
                <RouterLink to="/register" class="btn btn-light">
                    <i class="bi bi-person-plus"></i>
                    Registrasi wajah
                </RouterLink>
            </div>
        </div>
    </section>

    <section class="page-width feature-strip" aria-label="Nilai utama">
        <article>
            <strong>Realtime workflow</strong>
            <p>Kamera, capture, recognition otomatis, dan hasil deteksi berada dalam satu alur demo.</p>
        </article>
        <article>
            <strong>Use case luas</strong>
            <p>Absensi, monitoring, verifikasi, antrian, traffic, dan analitik pengunjung.</p>
        </article>
        <article>
            <strong>Presentasi jelas</strong>
            <p>Fitur inti tetap terlihat, sementara narasi manfaat produk lebih terarah.</p>
        </article>
    </section>

    <section class="page-width solution-grid">
        <div class="section-copy">
            <p class="eyebrow">Demo modules</p>
            <h2>Satu tampilan produk, tiga modul yang bisa langsung diuji.</h2>
            <p>
                Halaman ini tetap berfungsi sebagai promosi, tetapi arah utamanya adalah membuktikan
                kemampuan sistem lewat modul yang dapat dibuka saat presentasi.
            </p>
        </div>

        <div class="module-list">
            <RouterLink to="/register" class="module-row">
                <span class="module-icon"><i class="bi bi-person-vcard"></i></span>
                <span>
                    <strong>Face Registry</strong>
                    <small>Daftarkan identitas lewat upload gambar atau capture kamera.</small>
                </span>
                <i class="bi bi-arrow-right"></i>
            </RouterLink>
            <RouterLink to="/recognize" class="module-row">
                <span class="module-icon"><i class="bi bi-bounding-box-circles"></i></span>
                <span>
                    <strong>Live Recognition</strong>
                    <small>Uji deteksi wajah, nama, umur, gender, dan voice feedback.</small>
                </span>
                <i class="bi bi-arrow-right"></i>
            </RouterLink>
            <RouterLink to="/violation" class="module-row">
                <span class="module-icon"><i class="bi bi-sign-stop"></i></span>
                <span>
                    <strong>Violation Analysis</strong>
                    <small>Analisis traffic, video traffic, dan indikasi overload kendaraan.</small>
                </span>
                <i class="bi bi-arrow-right"></i>
            </RouterLink>
        </div>
    </section>

    <section class="page-width use-case-band">
        <div>
            <p class="eyebrow">Promotion scope</p>
            <h2>Manfaat yang tetap mudah dibawa ke percakapan bisnis.</h2>
        </div>
        <div class="use-case-grid">
            <span>Absen siswa dan pegawai</span>
            <span>Monitoring kegiatan dan ruangan</span>
            <span>Verifikasi tiket dan akses</span>
            <span>Traffic dan tilang elektronik</span>
            <span>Human analytics</span>
            <span>Hitung pengunjung dan durasi</span>
        </div>
    </section>
</template>

<script setup>
import { RouterLink } from 'vue-router'
import heroImage from '../assets/recognition-hero.jpg'
</script>

<style scoped>
.home-hero {
    position: relative;
    display: grid;
    min-height: min(760px, calc(100vh - 84px));
    align-items: center;
    overflow: hidden;
}

.home-hero img,
.hero-shade {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
}

.home-hero img {
    object-fit: cover;
}

.hero-shade {
    background:
        linear-gradient(90deg, rgba(8, 18, 29, 0.92) 0%, rgba(8, 18, 29, 0.74) 36%, rgba(8, 18, 29, 0.18) 72%),
        linear-gradient(180deg, rgba(8, 18, 29, 0.18), rgba(8, 18, 29, 0.44));
}

.hero-content {
    position: relative;
    z-index: 1;
    padding: 92px 0 126px;
    color: #fff;
}

.hero-content .eyebrow {
    color: #75d7e1;
}

h1 {
    max-width: 640px;
    margin: 0;
    font-size: 92px;
    line-height: 0.98;
}

.hero-copy {
    max-width: 610px;
    margin: 24px 0 0;
    color: rgba(255, 255, 255, 0.84);
    font-size: 18px;
    line-height: 1.6;
}

.hero-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    margin-top: 30px;
}

.hero-actions .btn {
    display: inline-flex;
    min-height: 52px;
    align-items: center;
    gap: 10px;
    border-radius: 8px;
    padding-inline: 18px;
    font-weight: 700;
}

.hero-actions .btn-info {
    border-color: #0ea5b7;
    background: #0ea5b7;
    color: #06151f;
}

.feature-strip {
    position: relative;
    z-index: 2;
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    margin-top: -74px;
    overflow: hidden;
    border: 1px solid rgba(217, 226, 234, 0.96);
    border-radius: 8px;
    background: rgba(255, 255, 255, 0.96);
    box-shadow: 0 24px 70px rgba(19, 33, 47, 0.16);
}

.feature-strip article {
    min-height: 176px;
    padding: 30px;
}

.feature-strip article + article {
    border-left: 1px solid var(--line);
}

.feature-strip strong,
.module-row strong {
    display: block;
    font-size: 20px;
}

.feature-strip p,
.section-copy p {
    color: var(--muted);
    line-height: 1.65;
}

.solution-grid {
    display: grid;
    grid-template-columns: minmax(320px, 0.9fr) minmax(420px, 1fr);
    gap: 44px;
    align-items: start;
    padding-top: 92px;
}

.section-copy h2,
.use-case-band h2 {
    margin: 0;
    font-size: 48px;
    line-height: 1.12;
}

.section-copy p:last-child {
    max-width: 520px;
    margin-top: 18px;
}

.module-list {
    overflow: hidden;
    border: 1px solid var(--line);
    border-radius: 8px;
    background: var(--surface);
    box-shadow: 0 20px 52px rgba(19, 33, 47, 0.08);
}

.module-row {
    display: grid;
    grid-template-columns: 58px minmax(0, 1fr) 24px;
    align-items: center;
    gap: 18px;
    min-height: 138px;
    padding: 24px;
    color: var(--ink);
    text-decoration: none;
    transition: background 160ms ease, transform 160ms ease;
}

.module-row + .module-row {
    border-top: 1px solid var(--line);
}

.module-row:hover {
    background: var(--surface-soft);
    transform: translateX(3px);
}

.module-row small {
    display: block;
    margin-top: 7px;
    color: var(--muted);
    font-size: 15px;
    line-height: 1.5;
}

.module-icon {
    display: grid;
    width: 58px;
    height: 58px;
    place-items: center;
    border-radius: 8px;
    background: #dff3f5;
    color: var(--cyan);
    font-size: 26px;
}

.use-case-band {
    display: grid;
    grid-template-columns: minmax(300px, 0.82fr) minmax(460px, 1fr);
    gap: 42px;
    align-items: center;
    margin-top: 92px;
    padding: 42px;
    border: 1px solid var(--line);
    border-radius: 8px;
    background: var(--navy);
    color: #fff;
}

.use-case-band .eyebrow {
    color: #75d7e1;
}

.use-case-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
}

.use-case-grid span {
    min-height: 76px;
    border: 1px solid rgba(255, 255, 255, 0.16);
    border-radius: 8px;
    background: rgba(255, 255, 255, 0.1);
    padding: 18px;
}

@media (max-width: 900px) {
    .home-hero {
        min-height: 700px;
    }

    .hero-content {
        padding-bottom: 150px;
    }

    .feature-strip,
    .solution-grid,
    .use-case-band {
        grid-template-columns: 1fr;
    }

    h1 {
        font-size: 68px;
    }

    .section-copy h2,
    .use-case-band h2 {
        font-size: 40px;
    }

    .feature-strip article + article {
        border-top: 1px solid var(--line);
        border-left: 0;
    }
}

@media (max-width: 620px) {
    .home-hero {
        min-height: 760px;
    }

    .hero-shade {
        background:
            linear-gradient(180deg, rgba(8, 18, 29, 0.88), rgba(8, 18, 29, 0.66)),
            linear-gradient(90deg, rgba(8, 18, 29, 0.8), rgba(8, 18, 29, 0.28));
    }

    .feature-strip {
        margin-top: -88px;
    }

    .feature-strip article,
    .use-case-band {
        padding: 24px;
    }

    h1 {
        font-size: 48px;
    }

    .section-copy h2,
    .use-case-band h2 {
        font-size: 32px;
    }

    .solution-grid {
        padding-top: 64px;
    }

    .module-row {
        grid-template-columns: 48px minmax(0, 1fr);
        min-height: 124px;
        padding: 20px;
    }

    .module-row > i {
        display: none;
    }

    .module-icon {
        width: 48px;
        height: 48px;
        font-size: 22px;
    }

    .use-case-grid {
        grid-template-columns: 1fr;
    }
}
</style>
