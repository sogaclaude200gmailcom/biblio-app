// Bibliothèque en ligne — interactions front-end (aucun appel réseau supplémentaire,
// tout tourne côté navigateur : pas d'impact sur les services ni sur leur surface
// d'attaque mesurée par Trivy / Docker Bench).

document.addEventListener("DOMContentLoaded", function () {
    initToasts();
    initSearch();
    initCounters();
    initReturnConfirm();
});

// ---------- Messages flash -> toasts animés ----------
function initToasts() {
    var source = document.getElementById("flash-source");
    var container = document.getElementById("toast-container");
    if (!source || !container) return;

    var messages = source.querySelectorAll("li");
    messages.forEach(function (li, i) {
        var toast = document.createElement("div");
        toast.className = "toast";
        toast.textContent = li.textContent;
        toast.style.animationDelay = (i * 0.08) + "s";
        container.appendChild(toast);

        setTimeout(function () {
            toast.classList.add("toast-hide");
            setTimeout(function () { toast.remove(); }, 300);
        }, 4500 + i * 300);
    });
}

// ---------- Recherche live dans le catalogue ----------
function initSearch() {
    var input = document.getElementById("book-search");
    var grid = document.getElementById("book-grid");
    var noResults = document.getElementById("no-results");
    if (!input || !grid) return;

    var cards = Array.prototype.slice.call(grid.querySelectorAll(".book-card"));

    input.addEventListener("input", function () {
        var term = input.value.trim().toLowerCase();
        var visibleCount = 0;

        cards.forEach(function (card) {
            var haystack = card.getAttribute("data-search") || "";
            var match = haystack.indexOf(term) !== -1;
            card.classList.toggle("search-hidden", !match);
            if (match) visibleCount++;
        });

        if (noResults) noResults.hidden = visibleCount !== 0;
    });
}

// ---------- Confirmation animée avant de rendre un livre ----------
function initReturnConfirm() {
    var modal = document.getElementById("confirm-modal");
    var text = document.getElementById("confirm-modal-text");
    var btnCancel = document.getElementById("confirm-modal-cancel");
    var btnConfirm = document.getElementById("confirm-modal-confirm");
    var forms = document.querySelectorAll(".return-form");
    if (!modal || !forms.length) return;

    var pendingForm = null;

    function openModal(form) {
        pendingForm = form;
        var title = form.getAttribute("data-book-title") || "ce livre";
        text.textContent = 'Confirmer le retour de « ' + title + ' » ?';
        modal.hidden = false;
        requestAnimationFrame(function () { modal.classList.add("modal-visible"); });
    }

    function closeModal() {
        modal.classList.remove("modal-visible");
        pendingForm = null;
        setTimeout(function () { modal.hidden = true; }, 200);
    }

    forms.forEach(function (form) {
        form.addEventListener("submit", function (e) {
            e.preventDefault();
            openModal(form);
        });
    });

    btnCancel.addEventListener("click", closeModal);
    modal.addEventListener("click", function (e) {
        if (e.target === modal) closeModal();
    });
    document.addEventListener("keydown", function (e) {
        if (e.key === "Escape" && !modal.hidden) closeModal();
    });
    btnConfirm.addEventListener("click", function () {
        if (!pendingForm) return;
        var form = pendingForm;
        pendingForm = null;
        modal.classList.remove("modal-visible");
        modal.hidden = true;
        form.submit();
    });
}

// ---------- Compteurs animés (page profil) ----------
function initCounters() {
    var counters = document.querySelectorAll(".stat-number[data-count]");
    counters.forEach(function (el) {
        var target = parseInt(el.getAttribute("data-count"), 10) || 0;
        var duration = 700;
        var start = null;

        function step(timestamp) {
            if (!start) start = timestamp;
            var progress = Math.min((timestamp - start) / duration, 1);
            el.textContent = Math.round(progress * target);
            if (progress < 1) requestAnimationFrame(step);
        }
        requestAnimationFrame(step);
    });
}
