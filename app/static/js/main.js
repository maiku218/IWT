document.addEventListener('DOMContentLoaded', function () {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebarOverlay');
    const toggle = document.getElementById('sidebarToggle');
    const isMobile = window.matchMedia('(max-width: 991.98px)');

    function openSidebar() {
        if (sidebar) sidebar.classList.remove('sidebar-hidden');
        if (overlay) overlay.classList.add('show');
        if (isMobile.matches) {
            document.body.classList.add('sidebar-open');
        }
    }
    function closeSidebar() {
        if (sidebar) sidebar.classList.add('sidebar-hidden');
        if (overlay) overlay.classList.remove('show');
        if (isMobile.matches) {
            document.body.classList.remove('sidebar-open');
        }
    }

    if (toggle) toggle.addEventListener('click', openSidebar);
    if (overlay) overlay.addEventListener('click', closeSidebar);

    // Close sidebar when clicking a nav item (mobile UX)
    document.querySelectorAll('.sidebar-nav .nav-item').forEach(function (item) {
        item.addEventListener('click', function () {
            if (isMobile.matches) {
                closeSidebar();
            }
        });
    });

    // Close sidebar on escape
    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') closeSidebar();
    });

    // Reopen sidebar on desktop when resizing back up
    window.addEventListener('resize', function () {
        if (!isMobile.matches) {
            if (sidebar) sidebar.classList.remove('sidebar-hidden');
            if (overlay) overlay.classList.remove('show');
            document.body.classList.remove('sidebar-open');
        } else {
            if (sidebar) sidebar.classList.add('sidebar-hidden');
            if (overlay) overlay.classList.remove('show');
            document.body.classList.remove('sidebar-open');
        }
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
