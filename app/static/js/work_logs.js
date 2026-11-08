function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function openModalForDate(dateStr) {
    const modal = new bootstrap.Modal(document.getElementById('workLogModal'));
    document.getElementById('modalTitle').textContent = 'Add Work Log';
    document.getElementById('logId').value = '';
    document.getElementById('workLogForm').reset();
    document.getElementById('wlWorkDate').value = dateStr;
    document.getElementById('formErrors').classList.add('d-none');
    modal.show();
}

function showInfoModal(title, html) {
    let el = document.getElementById('infoModal');
    if (!el) {
        el = document.createElement('div');
        el.id = 'infoModal';
        el.className = 'modal fade';
        el.innerHTML = '<div class="modal-dialog modal-dialog-centered"><div class="modal-content"><div class="modal-header"><h5 class="modal-title"></h5><button type="button" class="btn-close" data-bs-dismiss="modal"></button></div><div class="modal-body"></div><div class="modal-footer"><button type="button" class="btn btn-outline-secondary" data-bs-dismiss="modal">Close</button></div></div></div>';
        document.body.appendChild(el);
    }
    el.querySelector('.modal-title').textContent = title;
    el.querySelector('.modal-body').innerHTML = html;
    new bootstrap.Modal(el).show();
}

function viewLog(id) {
    fetch('/work-logs/' + id)
        .then(r => r.json())
        .then(data => {
            const log = data.log;
            const html =
                '<div class="text-start"><div class="mb-2"><strong class="text-dark">' + escapeHtml(log.task_title) + '</strong></div>' +
                '<div class="row g-2 small"><div class="col-6"><strong>Date:</strong> ' + log.work_date + '</div>' +
                '<div class="col-6"><strong>Category:</strong> ' + escapeHtml(log.category) + '</div>' +
                '<div class="col-6"><strong>Status:</strong> <span class="badge status-badge status-' + (log.status || '').toLowerCase() + '">' + escapeHtml(log.status) + '</span></div>' +
                '<div class="col-6"><strong>Time Spent:</strong> ' + escapeHtml(log.time_spent) + '</div>' +
                '<div class="col-12"><strong>Description:</strong> ' + escapeHtml(log.description) + '</div>' +
                '</div></div>';
            showInfoModal('Work Log Details', html);
        })
        .catch(() => alert('Failed to load record.'));
}

function editLog(id) {
    fetch('/work-logs/' + id + '/edit')
        .then(r => r.json())
        .then(data => {
            const log = data.log;
            document.getElementById('modalTitle').textContent = 'Edit Work Log';
            document.getElementById('logId').value = log.id;
            document.getElementById('wlWorkDate').value = log.work_date;
            document.getElementById('wlTaskTitle').value = log.task_title;
            document.getElementById('wlCategory').value = log.category;
            document.getElementById('wlStatus').value = log.status;
            document.getElementById('wlStartTime').value = log.start_time || '';
            document.getElementById('wlEndTime').value = log.end_time || '';
            document.getElementById('wlDescription').value = log.description;
            document.getElementById('formErrors').classList.add('d-none');
            new bootstrap.Modal(document.getElementById('workLogModal')).show();
        })
        .catch(() => alert('Failed to load record.'));
}

function deleteLog(id) {
    if (!confirm('Delete this work log?')) return;
    fetch('/work-logs/' + id + '/delete', { method: 'POST' })
        .then(r => r.json())
        .then(() => {
            if (window.calendarInstance) window.calendarInstance.refetchEvents();
            bootstrap.Modal.getInstance(document.getElementById('workLogModal'))?.hide();
            location.reload();
        })
        .catch(() => alert('Failed to delete.'));
}

function initWorkLogForm() {
    const form = document.getElementById('workLogForm');
    if (!form) return;
    form.addEventListener('submit', function (e) {
        e.preventDefault();
        const btn = document.getElementById('wlSaveBtn');
        const errBox = document.getElementById('formErrors');
        errBox.classList.add('d-none');
        errBox.textContent = '';
        const fd = new FormData(this);
        const isEdit = !!document.getElementById('logId').value;
        const url = isEdit ? '/work-logs/' + document.getElementById('logId').value + '/edit' : '/work-logs/';
        btn.disabled = true;
        btn.textContent = 'Saving...';
        fetch(url, { method: 'POST', body: fd, headers: { 'X-Requested-With': 'XMLHttpRequest' } })
            .then(async r => {
                const res = await r.json().catch(() => ({}));
                if (!r.ok) {
                    if (res.errors) {
                        const msgs = Object.values(res.errors).flat().join(' ');
                        errBox.textContent = msgs;
                        errBox.classList.remove('d-none');
                    } else {
                        errBox.textContent = res.error || 'Failed to save.';
                        errBox.classList.remove('d-none');
                    }
                    btn.disabled = false;
                    btn.textContent = isEdit ? 'Save Changes' : 'Save Record';
                    return;
                }
                bootstrap.Modal.getInstance(document.getElementById('workLogModal')).hide();
                if (window.calendarInstance) window.calendarInstance.refetchEvents();
                location.reload();
            })
            .catch(() => {
                errBox.textContent = 'An error occurred.';
                errBox.classList.remove('d-none');
                btn.disabled = false;
                btn.textContent = isEdit ? 'Save Changes' : 'Save Record';
            });
    });
}

function initWorkLogList() {
    document.querySelectorAll('.view-log').forEach(b => {
        b.addEventListener('click', function () { viewLog(this.dataset.id); });
    });
    document.querySelectorAll('.edit-log').forEach(b => {
        b.addEventListener('click', function () { editLog(this.dataset.id); });
    });
    document.querySelectorAll('.delete-log').forEach(b => {
        b.addEventListener('click', function () {
            if (!confirm('Delete "' + this.dataset.title + '"?')) return;
            deleteLog(this.dataset.id);
        });
    });
}

function loadStats() {
    fetch('/dashboard/api/stats')
        .then(r => r.json())
        .then(data => {
            const el = id => document.getElementById(id);
            if (el('stat-total')) el('stat-total').textContent = data.total_tasks;
            if (el('stat-completed')) el('stat-completed').textContent = data.completed_tasks;
            if (el('stat-month')) el('stat-month').textContent = data.tasks_this_month;
        });
}
