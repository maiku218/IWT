function initCalendar() {
    const calendarEl = document.getElementById('calendar');
    if (!calendarEl) return;

    const todayBtn = document.getElementById('btnToday');
    const recordsCard = document.getElementById('recordsCard');
    const recordsDate = document.getElementById('recordsDate');
    const recordsBody = document.getElementById('recordsBody');
    const addBtn = document.getElementById('btnAddFromDate');

    let selectedDate = null;

    const calendar = new FullCalendar.Calendar(calendarEl, {
        initialView: 'dayGridMonth',
        height: 'auto',
        fixedWeekCount: false,
        headerToolbar: {
            left: 'prev,next today',
            center: 'title',
            right: ''
        },
        buttonText: { today: 'Today' },
        events: function (fetchInfo, successCallback, failureCallback) {
            fetch('/dashboard/api/calendar-events?start=' + encodeURIComponent(fetchInfo.startStr) + '&end=' + encodeURIComponent(fetchInfo.endStr))
                .then(r => r.json())
                .then(events => successCallback(events))
                .catch(failureCallback);
        },
        eventClick: function (info) {
            selectedDate = info.event.startStr;
            loadRecords(selectedDate);
        },
        dateClick: function (info) {
            selectedDate = info.dateStr;
            loadRecords(selectedDate);
        },
        eventDidMount: function (info) {
            const props = info.event.extendedProps || {};
            if (props.status === 'Completed') {
                info.el.style.opacity = '0.6';
            }
        }
    });
    calendar.render();

    if (todayBtn) {
        todayBtn.addEventListener('click', function () {
            calendar.today();
            selectedDate = null;
            if (recordsCard) recordsCard.style.display = 'none';
        });
    }

    window.calendarInstance = calendar;
}

function loadRecords(dateStr) {
    const recordsCard = document.getElementById('recordsCard');
    const recordsDate = document.getElementById('recordsDate');
    const recordsBody = document.getElementById('recordsBody');
    const addBtn = document.getElementById('btnAddFromDate');
    const wlWorkDate = document.getElementById('wlWorkDate');

    if (!dateStr) return;

    recordsDate.textContent = formatDate(dateStr);
    recordsBody.innerHTML = '<div class="text-muted text-center py-3">Loading...</div>';
    recordsCard.style.display = '';

    if (wlWorkDate) wlWorkDate.value = dateStr;
    if (addBtn) {
        addBtn.onclick = function () { openModalForDate(dateStr); };
    }

    fetch('/dashboard/api/records?date=' + encodeURIComponent(dateStr))
        .then(r => r.json())
        .then(data => {
            recordsBody.innerHTML = '';
            if (!data.records || data.records.length === 0) {
                recordsBody.innerHTML = '<div class="text-center py-3"><div class="text-muted">No records for this date.</div><button class="btn btn-sm btn-primary mt-2" onclick="openModalForDate(\'' + dateStr + '\')">+ Add Work Log</button></div>';
                return;
            }
            const table = document.createElement('table');
            table.className = 'table table-sm align-middle';
            table.innerHTML = '<thead><tr><th>Task</th><th>Category</th><th>Status</th><th>Actions</th></tr></thead><tbody></tbody>';
            const tbody = table.querySelector('tbody');
            data.records.forEach(rec => {
                const tr = document.createElement('tr');
                tr.innerHTML =
                    '<td>' + escapeHtml(rec.task_title) + '</td>' +
                    '<td><span class="badge category-badge">' + escapeHtml(rec.category) + '</span></td>' +
                    '<td><span class="badge status-badge status-' + (rec.status || '').toLowerCase() + '">' + escapeHtml(rec.status) + '</span></td>' +
                    '<td><div class="d-flex gap-1">' +
                    '<button class="btn btn-sm btn-outline-secondary view-log" data-id="' + rec.id + '">View</button>' +
                    '<button class="btn btn-sm btn-outline-primary edit-log" data-id="' + rec.id + '">Edit</button>' +
                    '<button class="btn btn-sm btn-outline-danger delete-log" data-id="' + rec.id + '" data-title="' + escapeHtml(rec.task_title) + '">Delete</button>' +
                    '</div></td>';
                tbody.appendChild(tr);
            });
            recordsBody.appendChild(table);

            tbody.querySelectorAll('.view-log').forEach(b => {
                b.addEventListener('click', function () { viewLog(this.dataset.id); });
            });
            tbody.querySelectorAll('.edit-log').forEach(b => {
                b.addEventListener('click', function () { editLog(this.dataset.id); });
            });
            tbody.querySelectorAll('.delete-log').forEach(b => {
                b.addEventListener('click', function () {
                    if (!confirm('Delete "' + this.dataset.title + '"?')) return;
                    deleteLog(this.dataset.id);
                });
            });
        })
        .catch(() => {
            recordsBody.innerHTML = '<div class="text-danger text-center py-3">Failed to load records.</div>';
        });
}

function formatDate(iso) {
    const d = new Date(iso + 'T00:00:00');
    return d.toLocaleDateString(undefined, { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
}
