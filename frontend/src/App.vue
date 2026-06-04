<template>
    <div class="app-shell">
        <header class="topbar">
            <div class="shell-width topbar-inner">
                <RouterLink to="/" class="brand">
                    <span class="brand-mark" aria-hidden="true">
                        <i class="bi bi-person-bounding-box"></i>
                    </span>
                    <span>
                        <strong>NewFace Recognition</strong>
                        <small>SMKN 1 Kotabaru | Rekayasa Perangkat Lunak</small>
                    </span>
                </RouterLink>

                <nav class="primary-nav" aria-label="Navigasi utama">
                    <RouterLink to="/">Overview</RouterLink>
                    <RouterLink to="/register">Register</RouterLink>
                    <RouterLink to="/recognize">Recognition</RouterLink>
                    <RouterLink to="/violation">Violation</RouterLink>
                </nav>
            </div>
        </header>

        <main>
            <RouterView />
        </main>

        <footer class="app-footer">
            <div class="shell-width footer-grid">
                <div>
                    <p class="footer-kicker">Computer Vision Platform</p>
                    <h2>Pengenalan wajah dan analisis visual untuk demo layanan nyata.</h2>
                </div>
                <div class="capability-list" aria-label="Cakupan solusi">
                    <span>Absensi</span>
                    <span>Monitoring</span>
                    <span>Tilang elektronik</span>
                    <span>Verifikasi</span>
                    <span>Analitik pengunjung</span>
                </div>
            </div>
        </footer>
    </div>
</template>

<script setup>
import { RouterLink, RouterView } from 'vue-router'
</script>

<style>
:root {
    --ink: #13212f;
    --muted: #526474;
    --line: #d9e2ea;
    --surface: #ffffff;
    --surface-soft: #f3f7fa;
    --navy: #12314b;
    --cyan: #087e8b;
    --amber: #db8f25;
    --danger: #b94141;
    color-scheme: light;
}

* {
    box-sizing: border-box;
}

body {
    margin: 0;
    background: #eef4f7;
    color: var(--ink);
    font-family: Inter, "Segoe UI", Arial, sans-serif;
    letter-spacing: 0;
}

button,
input,
select,
textarea {
    font: inherit;
}

#app {
    min-height: 100vh;
}

.app-shell {
    min-height: 100vh;
    background:
        linear-gradient(180deg, rgba(8, 126, 139, 0.08), transparent 360px),
        #eef4f7;
}

.shell-width {
    width: min(1240px, calc(100% - 48px));
    margin: 0 auto;
}

.topbar {
    position: sticky;
    top: 0;
    z-index: 20;
    border-bottom: 1px solid rgba(217, 226, 234, 0.92);
    background: rgba(238, 244, 247, 0.9);
    backdrop-filter: blur(16px);
}

.topbar-inner {
    display: flex;
    min-height: 84px;
    align-items: center;
    justify-content: space-between;
    gap: 28px;
}

.brand {
    display: inline-flex;
    align-items: center;
    gap: 14px;
    color: var(--ink);
    text-decoration: none;
}

.brand-mark {
    display: grid;
    width: 48px;
    height: 48px;
    place-items: center;
    border-radius: 8px;
    background: var(--navy);
    color: #fff;
    font-size: 24px;
    box-shadow: 0 14px 34px rgba(18, 49, 75, 0.2);
}

.brand strong,
.brand small {
    display: block;
}

.brand strong {
    font-size: 18px;
    line-height: 1.2;
}

.brand small {
    margin-top: 3px;
    color: var(--muted);
    font-size: 12px;
    text-transform: uppercase;
}

.primary-nav {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px;
    border: 1px solid rgba(217, 226, 234, 0.95);
    border-radius: 8px;
    background: rgba(255, 255, 255, 0.76);
}

.primary-nav a {
    border-radius: 6px;
    color: var(--muted);
    padding: 10px 14px;
    text-decoration: none;
    transition: background 160ms ease, color 160ms ease;
}

.primary-nav a:hover,
.primary-nav a.router-link-exact-active {
    background: var(--navy);
    color: #fff;
}

main {
    min-height: calc(100vh - 260px);
}

.app-footer {
    margin-top: 56px;
    border-top: 1px solid rgba(217, 226, 234, 0.95);
    background: #f8fbfd;
}

.footer-grid {
    display: grid;
    grid-template-columns: minmax(0, 1.25fr) minmax(320px, 1fr);
    align-items: center;
    gap: 32px;
    padding: 42px 0;
}

.footer-kicker {
    margin: 0 0 10px;
    color: var(--cyan);
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
}

.app-footer h2 {
    max-width: 620px;
    margin: 0;
    font-size: 38px;
    line-height: 1.12;
}

.capability-list {
    display: flex;
    flex-wrap: wrap;
    justify-content: flex-end;
    gap: 10px;
}

.capability-list span {
    border: 1px solid var(--line);
    border-radius: 8px;
    background: var(--surface);
    color: var(--muted);
    padding: 11px 14px;
}

.page-width {
    width: min(1240px, calc(100% - 48px));
    margin: 0 auto;
}

.workflow-page {
    padding-top: 38px;
}

.workflow-panel {
    border: 1px solid var(--line);
    border-radius: 8px;
    background: rgba(255, 255, 255, 0.94);
    box-shadow: 0 24px 60px rgba(19, 33, 47, 0.08);
}

.eyebrow {
    margin: 0 0 10px;
    color: var(--cyan);
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
}

@media (max-width: 820px) {
    .shell-width,
    .page-width {
        width: min(100% - 28px, 1240px);
    }

    .topbar-inner,
    .footer-grid {
        grid-template-columns: 1fr;
        flex-direction: column;
        align-items: stretch;
    }

    .topbar-inner {
        padding: 16px 0;
    }

    .primary-nav {
        overflow-x: auto;
    }

    .primary-nav a {
        flex: 1 0 auto;
        text-align: center;
    }

    .footer-grid {
        display: grid;
        padding: 32px 0;
    }

    .capability-list {
        justify-content: flex-start;
    }

    .app-footer h2 {
        font-size: 30px;
    }
}
</style>
