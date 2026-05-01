/* ===== SHARED CLIENT-SIDE UTILITIES ===== */
/* Used across all EchoStack pages to reduce duplication and ensure consistency */

const SIDEBAR_BREAKPOINT = 1024;

/* ── Sidebar State Management ── */
function getSidebarState() {
    return {
        isMobile: window.innerWidth < SIDEBAR_BREAKPOINT,
        sidebar: document.getElementById('sidebar'),
        overlay: document.getElementById('sidebarOverlay') || document.getElementById('sidebar-overlay'),
        main: document.querySelector('.main-wrapper, .app, main, .page-container')
    };
}

if (typeof toggleSidebar === 'undefined') {
    function toggleSidebar() {
        const { sidebar, overlay, isMobile } = getSidebarState();
        if (!sidebar) return;
        
        const isOpen = sidebar.classList.toggle('open');
        
        if (overlay) {
            overlay.classList.toggle('show', isOpen);
        }
        
        document.body.classList.toggle('sidebar-open', isOpen);
        
        // Adjust main content margin on mobile
        if (isMobile && document.body.classList.contains('sidebar-open')) {
            document.body.style.overflow = 'hidden';
        } else {
            document.body.style.overflow = '';
        }
    }
}

if (typeof closeSidebar === 'undefined') {
    function closeSidebar() {
        const { sidebar, overlay, main } = getSidebarState();
        
        if (sidebar) {
            sidebar.classList.remove('open');
        }
        
        if (overlay) {
            overlay.classList.remove('show');
        }
        
        document.body.classList.remove('sidebar-open');
        document.body.style.overflow = '';
    }
}

if (typeof openSidebar === 'undefined') {
    function openSidebar() {
        const { sidebar, overlay, isMobile } = getSidebarState();
        if (!sidebar) return;
        
        sidebar.classList.add('open');
        
        if (overlay) {
            overlay.classList.add('show');
        }
        
        document.body.classList.add('sidebar-open');
        
        if (isMobile) {
            document.body.style.overflow = 'hidden';
        }
    }
}

/* ── Toast Notification ── */
if (typeof showToast === 'undefined') {
    function showToast(msg, type = 'info') {
        const toast = document.getElementById('toast');
        if (!toast) return;
        toast.textContent = msg;
        toast.className = 'toast show ' + type;
        setTimeout(() => { toast.className = 'toast'; }, 2500);
    }
}

/* ── HTML Escape ── */
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

/* ── Time Ago ── */
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

/* ── Logout ── */
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

/* ── Format File Size ── */
if (typeof formatFileSize === 'undefined') {
    function formatFileSize(bytes) {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
        if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
        return (bytes / (1024 * 1024 * 1024)).toFixed(1) + ' GB';
    }
}

/* ── Debounce ── */
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
    
    // Close sidebar when any link inside it is clicked
    sidebar.addEventListener('click', (e) => {
        const link = e.target.closest('a');
        if (link && link.href && !link.href.startsWith('javascript') && !link.href.startsWith('#')) {
            // Small delay to allow navigation to start
            setTimeout(() => closeSidebar(), 100);
        }
    });
    
    // Close sidebar when overlay is clicked
    const overlay = document.getElementById('sidebarOverlay') || document.getElementById('sidebar-overlay');
    if (overlay) {
        overlay.addEventListener('click', closeSidebar);
    }
}

/* ── Handle browser back/forward navigation ── */
window.addEventListener('popstate', () => {
    closeSidebar();
});

/* ── Auto-close on page unload (when navigating away) ── */
window.addEventListener('beforeunload', function() {
    closeSidebar();
});

/* ── Initialize Sidebar State on Page Load ── */
function initSidebar() {
    const { sidebar, isMobile } = getSidebarState();
    
    // Always close sidebar on initial page load
    closeSidebar();
    sessionStorage.removeItem('sidebarClosing');
    
    // On desktop, sidebar should be visible by default
    // On mobile, sidebar should be hidden by default
    if (!isMobile && sidebar) {
        // Desktop: Keep sidebar visible (no 'open' class means visible in desktop CSS)
        // But ensure main content has proper margin
        const main = document.querySelector('.main-wrapper, .app, main');
        if (main) {
            main.style.marginLeft = 'var(--sidebar-width, 280px)';
            main.style.width = 'calc(100% - var(--sidebar-width, 280px))';
        }
    }
    
    // Set active navigation link
    if (typeof setActiveNavLink !== 'undefined') setActiveNavLink();
    
    // Setup auto-close on navigation
    if (typeof setupSidebarAutoClose !== 'undefined') setupSidebarAutoClose();
    
    // Initialize collapse state
    if (typeof initSidebarCollapse !== 'undefined') initSidebarCollapse();
}

/* ── Handle window resize ── */
let resizeTimer;
window.addEventListener('resize', () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => {
        const { isMobile } = getSidebarState();
        
        // On resize to mobile, ensure sidebar is closed
        if (isMobile) {
            closeSidebar();
        } else {
            // On resize to desktop, ensure proper margins
            const main = document.querySelector('.main-wrapper, .app, main');
            if (main) {
                main.style.marginLeft = 'var(--sidebar-width, 280px)';
                main.style.width = 'calc(100% - var(--sidebar-width, 280px))';
            }
        }
    }, 250);
});

/* ── Initialization on DOM Ready ── */
document.addEventListener('DOMContentLoaded', initSidebar);

/* ── PWA Install Prompt ── */
let deferredPrompt = null;

function showInstallBanner() {
    if (document.getElementById('pwa-install-banner')) return;
    const banner = document.createElement('div');
    banner.id = 'pwa-install-banner';
    banner.innerHTML = `
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
    `;
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