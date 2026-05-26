// Flask CMS Admin JS
document.addEventListener('DOMContentLoaded', function() {
    // Auto-dismiss flash messages
    var flashes = document.querySelectorAll('.flash');
    flashes.forEach(function(flash) {
        setTimeout(function() {
            flash.style.opacity = '0';
            flash.style.transition = 'opacity 0.5s';
            setTimeout(function() { flash.remove(); }, 500);
        }, 5000);
    });

    // Confirm delete dialogs
    document.querySelectorAll('[data-confirm]').forEach(function(el) {
        el.addEventListener('click', function(e) {
            if (!confirm(el.dataset.confirm || '确认此操作?')) {
                e.preventDefault();
            }
        });
    });
});