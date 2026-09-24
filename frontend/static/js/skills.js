
(function () {
  var STORAGE_KEY = "vision_ai_custom_skills_v1";
  var BUILTIN = [
    { id: "summarize", name: "Summarize", description: "Condense long text into bullet points", builtin: true },
    { id: "urdu_hint", name: "Urdu Hint", description: "Prepare a clear Urdu translation prompt", builtin: true },
    { id: "exam_steps", name: "Exam Steps", description: "Structure exam answers step by step", builtin: true },
    { id: "code_review", name: "Code Review", description: "Checklist-driven code review framing", builtin: true }
  ];

  function loadCustom() {
    try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]"); } catch (e) { return []; }
  }
  function saveCustom(list) {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(list)); } catch (e) {}
  }
  function allSkills() {
    var custom = loadCustom().map(function (s) {
      return { id: s.id, name: s.name, description: s.description || "", builtin: false };
    });
    return BUILTIN.concat(custom);
  }

  function render() {
    var grid = document.getElementById("skillsGrid");
    if (!grid) return;
    var skills = allSkills();
    grid.innerHTML = skills.map(function (s) {
      return (
        '<div class="skill-card" data-id="' + s.id + '">' +
        "<h3>" + escapeHtml(s.name) + "</h3>" +
        "<p>" + escapeHtml(s.description || "") + "</p>" +
        '<div class="skill-actions">' +
        (s.builtin
          ? '<button type="button" class="btn" disabled>Built-in</button>'
          : '<button type="button" class="btn" data-remove="' + s.id + '">Remove</button>') +
        '<button type="button" class="btn btn-primary" data-use="' + s.id + '">Use in chat</button>' +
        "</div></div>"
      );
    }).join("");

    grid.querySelectorAll("[data-remove]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var id = btn.getAttribute("data-remove");
        saveCustom(loadCustom().filter(function (s) { return s.id !== id; }));
        render();
      });
    });
    grid.querySelectorAll("[data-use]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var id = btn.getAttribute("data-use");
        try { localStorage.setItem("vision_ai_pending_skill", id); } catch (e) {}
        window.location.href = "/";
      });
    });
  }

  function escapeHtml(t) {
    var d = document.createElement("div");
    d.textContent = t || "";
    return d.innerHTML;
  }

  function openModal(open) {
    var m = document.getElementById("skillModal");
    if (!m) return;
    m.classList.toggle("open", !!open);
  }

  function installFromForm() {
    var name = (document.getElementById("skillName").value || "").trim();
    var desc = (document.getElementById("skillDesc").value || "").trim();
    var code = (document.getElementById("skillCode").value || "").trim();
    if (!name || !code) { alert("Name and code are required"); return; }
    if (/\bimport\b|__|open\s*\(|exec\s*\(|eval\s*\(/.test(code)) {
      alert("Unsafe code rejected");
      return;
    }
    if (!/def\s+run\s*\(/.test(code)) {
      alert("Code must define run(prompt, context)");
      return;
    }
    var id = name.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "") || "custom";
    var list = loadCustom().filter(function (s) { return s.id !== id; });
    list.push({ id: id, name: name, description: desc, code: code });
    saveCustom(list);
    openModal(false);
    render();
  }

  document.addEventListener("DOMContentLoaded", function () {
    render();
    var add = document.getElementById("btnAddSkill");
    var cancel = document.getElementById("btnCancelSkill");
    var save = document.getElementById("btnSaveSkill");
    if (add) add.onclick = function () { openModal(true); };
    if (cancel) cancel.onclick = function () { openModal(false); };
    if (save) save.onclick = installFromForm;
  });
})();
