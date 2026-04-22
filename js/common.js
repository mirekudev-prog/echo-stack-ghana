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
    closeSidebar();
});
