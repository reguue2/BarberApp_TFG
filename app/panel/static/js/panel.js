// PeluGestor - JS del panel
// Comportamientos genéricos: modales, drawers, cierre con ESC.

(function () {
    'use strict';

    function openModal(id) {
        const modal = document.getElementById(id);
        if (modal) modal.hidden = false;
    }

    function closeModal(modal) {
        if (modal) modal.hidden = true;
    }

    // Botones que abren un modal
    document.querySelectorAll('[data-open-modal]').forEach(function (btn) {
        btn.addEventListener('click', function () {
            openModal(btn.getAttribute('data-open-modal'));
        });
    });

    // Botones que cierran un modal (backdrop, X, cancelar)
    document.addEventListener('click', function (e) {
        const closer = e.target.closest('[data-close-modal]');
        if (closer) {
            const modal = closer.closest('.modal');
            closeModal(modal);
        }
        const drawerCloser = e.target.closest('[data-close-drawer]');
        if (drawerCloser) {
            const drawer = drawerCloser.closest('.drawer');
            if (drawer) drawer.hidden = true;
        }
    });

    // ESC cierra modal/drawer abierto
    document.addEventListener('keydown', function (e) {
        if (e.key !== 'Escape') return;
        document.querySelectorAll('.modal:not([hidden])').forEach(function (m) { m.hidden = true; });
        document.querySelectorAll('.drawer:not([hidden])').forEach(function (d) { d.hidden = true; });
    });


    // Barras de métricas del dashboard.
    document.querySelectorAll('[data-bar-percent]').forEach(function (bar) {
        const raw = bar.getAttribute('data-bar-percent') || '0';
        const percent = Number.parseFloat(raw.replace(',', '.'));
        const safePercent = Number.isFinite(percent) ? Math.min(Math.max(percent, 0), 100) : 0;
        bar.style.width = safePercent + '%';
    });

    // Auto-ocultar flashes tras 5s
    setTimeout(function () {
        document.querySelectorAll('.flash').forEach(function (f) {
            f.style.transition = 'opacity 0.4s';
            f.style.opacity = '0';
            setTimeout(function () { f.remove(); }, 400);
        });
    }, 5000);
})();
