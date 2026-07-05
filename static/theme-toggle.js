(function () {
  var saved = localStorage.getItem("sept-theme") || "dark";
  document.documentElement.setAttribute("data-theme", saved);

  function makeThemeButton() {
    var btn = document.createElement("button");
    btn.className = "theme-toggle-btn";
    btn.type = "button";
    btn.title = "Switch theme";
    btn.textContent = saved === "light" ? "🌙" : "☀️";
    btn.addEventListener("click", function () {
      var current = document.documentElement.getAttribute("data-theme") || "dark";
      var next = current === "light" ? "dark" : "light";
      document.documentElement.setAttribute("data-theme", next);
      localStorage.setItem("sept-theme", next);
      btn.textContent = next === "light" ? "🌙" : "☀️";
    });
    document.body.appendChild(btn);
  }

  // ---------------------------------------------------------
  // HAMBURGER MENU (for pages with a .sidebar + .topbar layout)
  // ---------------------------------------------------------
  function initHamburger() {
    var sidebar = document.querySelector(".sidebar");
    var topbar = document.querySelector(".topbar");
    if (!sidebar || !topbar) return;

    var overlay = document.createElement("div");
    overlay.className = "sept-sidebar-overlay";
    document.body.appendChild(overlay);

    var hamburger = document.createElement("button");
    hamburger.type = "button";
    hamburger.className = "sept-hamburger-btn";
    hamburger.setAttribute("aria-label", "Toggle menu");
    hamburger.innerHTML = "<span></span><span></span><span></span>";

    var left = topbar.querySelector(".topbar-left") || topbar.firstElementChild;
    topbar.insertBefore(hamburger, left || topbar.firstChild);

    function closeSidebar() {
      sidebar.classList.remove("sept-open");
      overlay.classList.remove("sept-visible");
      hamburger.classList.remove("sept-active");
    }
    function toggleSidebar() {
      var isOpen = sidebar.classList.toggle("sept-open");
      overlay.classList.toggle("sept-visible", isOpen);
      hamburger.classList.toggle("sept-active", isOpen);
    }

    hamburger.addEventListener("click", toggleSidebar);
    overlay.addEventListener("click", closeSidebar);
    sidebar.querySelectorAll("a").forEach(function (link) {
      link.addEventListener("click", closeSidebar);
    });
    window.addEventListener("resize", function () {
      if (window.innerWidth > 900) closeSidebar();
    });
  }

  // ---------------------------------------------------------
  // NOTIFICATION BELL (for pages with a .topbar-right, i.e. logged-in dashboards)
  // ---------------------------------------------------------
  function initNotificationBell() {
    var topbarRight = document.querySelector(".topbar-right");
    if (!topbarRight) return;

    var wrap = document.createElement("div");
    wrap.className = "sept-notif-wrap";

    var bellBtn = document.createElement("button");
    bellBtn.type = "button";
    bellBtn.className = "sept-notif-btn";
    bellBtn.setAttribute("aria-label", "Notifications");
    bellBtn.innerHTML = '<i class="fa-solid fa-bell"></i><span class="sept-notif-badge" style="display:none;">0</span>';

    var dropdown = document.createElement("div");
    dropdown.className = "sept-notif-dropdown";
    dropdown.innerHTML =
      '<div class="sept-notif-header">Notifications</div>' +
      '<div class="sept-notif-list"><div class="sept-notif-empty">No new notifications</div></div>' +
      '<a class="sept-notif-viewall" href="/notifications">View all</a>';

    wrap.appendChild(bellBtn);
    wrap.appendChild(dropdown);
    topbarRight.insertBefore(wrap, topbarRight.firstChild);

    var badge = bellBtn.querySelector(".sept-notif-badge");
    var list = dropdown.querySelector(".sept-notif-list");

    function escapeHtml(str) {
      var div = document.createElement("div");
      div.textContent = str || "";
      return div.innerHTML;
    }

    function renderNotifications(notifs) {
      if (!notifs || notifs.length === 0) {
        badge.style.display = "none";
        list.innerHTML = '<div class="sept-notif-empty">No new notifications</div>';
        return;
      }
      badge.style.display = "flex";
      badge.textContent = notifs.length > 9 ? "9+" : notifs.length;
      list.innerHTML = notifs
        .slice(0, 6)
        .map(function (n) {
          return (
            '<div class="sept-notif-item">' +
            '<div class="sept-notif-title">' + escapeHtml(n.title) + "</div>" +
            (n.body ? '<div class="sept-notif-body">' + escapeHtml(n.body) + "</div>" : "") +
            "</div>"
          );
        })
        .join("");
    }

    function fetchNotifications() {
      fetch("/get_notifications", { credentials: "same-origin" })
        .then(function (res) {
          return res.ok ? res.json() : [];
        })
        .then(renderNotifications)
        .catch(function () {});
    }

    bellBtn.addEventListener("click", function (e) {
      e.stopPropagation();
      var isOpen = dropdown.classList.toggle("sept-visible");
      if (isOpen) fetchNotifications();
    });
    document.addEventListener("click", function (e) {
      if (!wrap.contains(e.target)) dropdown.classList.remove("sept-visible");
    });

    fetchNotifications();
    setInterval(fetchNotifications, 30000);
  }

  function initAll() {
    makeThemeButton();
    initHamburger();
    initNotificationBell();
  }

  if (document.body) {
    initAll();
  } else {
    document.addEventListener("DOMContentLoaded", initAll);
  }
})();
