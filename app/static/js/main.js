document.addEventListener('DOMContentLoaded', function () {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebarOverlay');
    const toggle = document.getElementById('sidebarToggle');

    function openSidebar() {
        if (sidebar) sidebar.classList.remove('sidebar-hidden');
        if (overlay) overlay.classList.add('show');
    }
    function closeSidebar() {
        if (sidebar) sidebar.classList.add('sidebar-hidden');
        if (overlay) overlay.classList.remove('show');
    }

    if (toggle) toggle.addEventListener('click', openSidebar);
    if (overlay) overlay.addEventListener('click', closeSidebar);

    // Close sidebar on escape
    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') closeSidebar();
    });

    // Global CSRF token for fetch requests
    const meta = document.querySelector('meta[name="csrf-token"]');
    const token = meta ? meta.getAttribute('content') : '';

    const _fetch = window.fetch;
    window.fetch = function (input, init) {
        init = init || {};
        const headers = init.headers || {};
        const isFormData = init.body instanceof FormData;
        if (!isFormData && !(headers instanceof Headers ? headers.get('Content-Type') : headers['Content-Type'])) {
            headers['Content-Type'] = 'application/json';
        }
        if (token) headers['X-CSRFToken'] = token;
        init.headers = headers;
        return _fetch(input, init);
    };
});
