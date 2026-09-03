/* Nova shell helpers — profile menu + tray aria */
(function () {
  function bindProfile() {
    var btn = document.getElementById('profileButton');
    var dd = document.getElementById('profileDropdown');
    if (!btn || !dd || btn.dataset.novaBound) return;
    btn.dataset.novaBound = '1';
    btn.addEventListener('click', function (e) {
      e.stopPropagation();
      var open = dd.hasAttribute('hidden');
      if (open) {
        dd.removeAttribute('hidden');
        btn.setAttribute('aria-expanded', 'true');
      } else {
        dd.setAttribute('hidden', '');
        btn.setAttribute('aria-expanded', 'false');
      }
    });
    document.addEventListener('click', function () {
      dd.setAttribute('hidden', '');
      btn.setAttribute('aria-expanded', 'false');
    });
  }
  function syncTrayAria() {
    var tray = document.getElementById('collapsedToolbar');
    if (!tray) return;
    tray.setAttribute('aria-hidden', tray.classList.contains('active') ? 'false' : 'true');
  }
  var obs = new MutationObserver(syncTrayAria);
  document.addEventListener('DOMContentLoaded', function () {
    bindProfile();
    var tray = document.getElementById('collapsedToolbar');
    if (tray) {
      obs.observe(tray, { attributes: true, attributeFilter: ['class'] });
      syncTrayAria();
    }
  });
})();
