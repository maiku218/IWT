document.addEventListener('DOMContentLoaded', function () {
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
