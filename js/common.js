/* ===== SHARED CLIENT-SIDE UTILITIES ===== */
/* Used across all EchoStack pages to reduce duplication and ensure consistency */

/* ── Guard: Prevent redefinition if page already defines these ── */
if (typeof toggleSidebar === 'undefined') {
    function toggleSidebar() {
        const sidebar = document.getElementById('sidebar');
        const overlay = document.getElementById('sidebarOverlay') || document.getElementById('sidebar-overlay');
        if (sidebar) sidebar.classList.toggle('open');
        if (overlay) overlay.classList.toggle('show');
    }
}

if (typeof closeSidebar === 'undefined') {
    function closeSidebar() {
        const sidebar = document.getElementById('sidebar');
        const overlay = document.getElementById('sidebarOverlay') || document.getElementById('sidebar-overlay');
        if (sidebar) sidebar.classList.remove('open');
        if (overlay) overlay.classList.remove('show');
    }
}

if (typeof showToast === 'undefined') {
    function showToast(msg, type = 'info') {
        const toast = document.getElementById('toast');
        if (!toast) return;
        toast.textContent = msg;
        toast.className = 'toast show ' + type;
        setTimeout(() => { toast.className = 'toast'; }, 2500);
    }
}

if (typeof escapeHtml === 'undefined') {
    function escapeHtml(str) {
        if (!str && str !== 0) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }
}

if (typeof timeAgo === 'undefined') {
    function timeAgo(dateStr) {
        if (!dateStr) return '';
        const isoStr = dateStr.replace(' ', 'T');
        const diff = (Date.now() - new Date(isoStr)) / 1000;
        if (isNaN(diff)) return '';
        if (diff < 60) return Math.floor(diff) + 's';
        if (diff < 3600) return Math.floor(diff / 60) + 'm';
        if (diff < 86400) return Math.floor(diff / 3600) + 'h';
        return Math.floor(diff / 86400) + 'd';
    }
}

if (typeof logout === 'undefined') {
    async function logout() {
        try {
            await fetch('/api/users/logout', { method: 'POST', credentials: 'include' });
        } catch (e) { /* ignore */ }
        localStorage.removeItem('es_user');
        localStorage.removeItem('es_admin');
        location.href = '/';
    }
}

if (typeof formatFileSize === 'undefined') {
    function formatFileSize(bytes) {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
        if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
        return (bytes / (1024 * 1024 * 1024)).toFixed(1) + ' GB';
    }
}

if (typeof debounce === 'undefined') {
    function debounce(fn, delay = 300) {
        let timer = null;
        return function (...args) {
            clearTimeout(timer);
            timer = setTimeout(() => fn.apply(this, args), delay);
        };
    }
}

/* ── Active Navigation State (Sidebar) ── */
function setActiveNavLink() {
    const path = window.location.pathname;
    const links = document.querySelectorAll('.sidebar-link, .sb-item');
    links.forEach(link => {
        const href = link.getAttribute('href');
        if (!href) return;
        let match = false;
        if (href === path) match = true;
        else if (href.endsWith('/') && path.startsWith(href)) match = true;
        else if (path.startsWith(href + '/')) match = true;
        if (match) link.classList.add('active');
        else link.classList.remove('active');
    });
}

/* ── Auto-close Sidebar on Navigation (Mobile UX) ── */
function setupSidebarAutoClose() {
    const sidebar = document.getElementById('sidebar');
    if (!sidebar) return;
    // Close sidebar when any link inside it is clicked (event delegation)
    sidebar.addEventListener('click', (e) => {
        const link = e.target.closest('a');
        if (link && link.href) {
            closeSidebar();
        }
    });
}

/* ── Initialization on DOM Ready ── */
document.addEventListener('DOMContentLoaded', () => {
    if (typeof setActiveNavLink !== 'undefined') setActiveNavLink();
    if (typeof setupSidebarAutoClose !== 'undefined') setupSidebarAutoClose();
        if (typeof initSidebarCollapse !== 'undefined') initSidebarCollapse();
    closeSidebar();
    // Ensure desktop layout has proper spacing if CSS didn't load
    if (window.innerWidth >= 1025) {
        const sidebar = document.getElementById('sidebar');
        const main = document.querySelector('.main-wrapper, .app, main');
        if (sidebar && main) {
            sidebar.style.transform = 'translateX(0)';
            main.style.marginLeft = 'var(--sidebar-width, 280px)';
            main.style.width = 'calc(100% - var(--sidebar-width, 280px))';
        }
    }
});

/* ── PWA Install Prompt ── */
let deferredPrompt = null;

function showInstallBanner() {
    if (document.getElementById('pwa-install-banner')) return;
    const banner = document.createElement('div');
    banner.id = 'pwa-install-banner';
    banner.innerHTML = \`
        <div style="
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: var(--surface, #0f1e2d);
            color: white;
            padding: 12px 16px;
            border-radius: 12px;
            display: flex;
            align-items: center;
            gap: 12px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
            z-index: 9999;
            font-family: 'DM Sans', sans-serif;
            border: 1px solid var(--gold, #C8962E);
        ">
            <img src="/echostack-logo.png" alt="EchoStack" style="height: 32px; width: 32px; border-radius: 6px; object-fit: cover;">
            <div style="font-weight: 600; font-size: 0.95rem;">Install EchoStack</div>
            <button id="install-accept" style="
                background: var(--gold, #C8962E); color: #0D1B2A; border: none; padding: 6px 14px; border-radius: 6px; font-weight: 700; cursor: pointer;
            ">Install</button>
            <button id="install-dismiss" style="
                background: transparent; color: rgba(255,255,255,0.6); border: none; padding: 6px 10px; cursor: pointer; font-size: 1.2rem; line-height: 1;
            ">&times;</button>
        </div>
    \`;
    document.body.appendChild(banner);
    document.getElementById('install-accept').addEventListener('click', async () => {
        if (!deferredPrompt) return;
        deferredPrompt.prompt();
        const { outcome } = await deferredPrompt.userChoice;
        if (outcome === 'accepted') console.log('Install accepted');
        deferredPrompt = null;
        banner.remove();
    });
    document.getElementById('install-dismiss').addEventListener('click', () => banner.remove());
}

window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    deferredPrompt = e;
    showInstallBanner();
});


/* ── Sidebar Collapse (icon-only mode) ── */
function toggleSidebarCollapse() {
    const sidebar = document.getElementById('sidebar');
    if (!sidebar) return;
    sidebar.classList.toggle('collapsed');
    const isCollapsed = sidebar.classList.contains('collapsed');
    localStorage.setItem('sidebar_collapsed', isCollapsed ? '1' : '0');
    // Adjust main margin if needed (handled by CSS)
}

function initSidebarCollapse() {
    const sidebar = document.getElementById('sidebar');
    if (!sidebar) return;
    const saved = localStorage.getItem('sidebar_collapsed');
    if (saved === '1') {
        sidebar.classList.add('collapsed');
    } else {
        sidebar.classList.remove('collapsed');
    }
}

// Extend DOMContentLoaded to call initSidebarCollapse
document.addEventListener('DOMContentLoaded', () => {
    if (typeof initSidebarCollapse !== 'undefined') initSidebarCollapse();
});

