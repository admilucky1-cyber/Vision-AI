(function () {
  function token() {
    return localStorage.getItem("vision_ai_access_token") || localStorage.getItem("vision_ai_access") || localStorage.getItem("access_token") || "";
  }
  async function api(path, opts) {
    opts = opts || {};
    const headers = Object.assign({ Accept: "application/json" }, opts.headers || {});
    if (token()) headers.Authorization = "Bearer " + token();
    if (opts.body && typeof opts.body === "object" && !(opts.body instanceof FormData)) {
      headers["Content-Type"] = "application/json";
      opts.body = JSON.stringify(opts.body);
    }
    const res = await fetch(path, Object.assign({}, opts, { headers }));
    let data = {};
    try { data = await res.json(); } catch (e) {}
    if (!res.ok) {
      const d = data.detail;
      let msg = res.statusText;
      if (typeof d === "string") msg = d;
      else if (d && d.message) msg = d.message;
      else if (d && d.code) msg = d.code + ": " + (d.message || "");
      else if (data.error && data.error.message) msg = data.error.message;
      throw new Error(msg || ("HTTP " + res.status));
    }
    return data;
  }
  function $(id) { return document.getElementById(id); }
  function show(el, text, ok) {
    if (!el) return;
    el.textContent = text || "";
    el.className = "msg " + (ok ? "ok" : "err");
  }
  function capsText(m) {
    const c = (m && m.capabilities) || {};
    return Object.keys(c).filter(function (k) { return c[k]; }).join(", ") || "—";
  }

  document.querySelectorAll(".tabs button").forEach(function (btn) {
    btn.onclick = function () {
      document.querySelectorAll(".tabs button").forEach(function (b) { b.classList.remove("active"); });
      document.querySelectorAll(".panel").forEach(function (p) { p.classList.remove("active"); });
      btn.classList.add("active");
      var p = $("panel-" + btn.getAttribute("data-tab"));
      if (p) p.classList.add("active");
      var tab = btn.getAttribute("data-tab");
      if (tab === "jobs") loadJobs();
      if (tab === "models") loadModels();
      if (tab === "workers") loadWorkers();
    };
  });

  async function loadModels() {
    try {
      const data = await api("/api/studio/models");
      const models = data.models || [];
      const imgSel = $("imgModel"), vidSel = $("vidModel"), trainSel = $("trainBase"), grid = $("modelGrid");
      [imgSel, vidSel, trainSel].forEach(function (s) { if (s) s.innerHTML = ""; });
      if (grid) grid.innerHTML = "";
      models.forEach(function (m) {
        const opt = document.createElement("option");
        opt.value = m.id;
        opt.textContent = m.name + " (" + m.type + ")";
        if (m.type === "image") {
          if (imgSel) imgSel.appendChild(opt.cloneNode(true));
          if (trainSel && (m.capabilities || {}).lora) trainSel.appendChild(opt.cloneNode(true));
        }
        if (m.type === "video" && vidSel) vidSel.appendChild(opt.cloneNode(true));
        if (grid) {
          const card = document.createElement("div");
          card.className = "card";
          card.innerHTML = "<strong>" + (m.name || m.id) + "</strong><br>VRAM ~" + (m.vram_gb || "?") + "GB<br>" +
            capsText(m) + "<br><span style='opacity:.7'>" + (m.notes || m.license || "") + "</span>";
          grid.appendChild(card);
        }
      });
      updateImgCaps();
      const loras = await api("/api/studio/loras");
      const ls = $("imgLora");
      if (ls) {
        ls.innerHTML = '<option value="">None</option>';
        (loras.loras || []).forEach(function (l) {
          const o = document.createElement("option");
          o.value = l.id;
          o.textContent = l.name || l.id;
          ls.appendChild(o);
        });
      }
    } catch (e) {
      if ($("modelGrid")) $("modelGrid").innerHTML = "<div class='card'>" + e.message + "</div>";
    }
  }
  function updateImgCaps() {
    const sel = $("imgModel");
    if (!sel || !sel.options.length) return;
    api("/api/studio/models").then(function (data) {
      const m = (data.models || []).find(function (x) { return x.id === sel.value; });
      if ($("imgCaps")) $("imgCaps").textContent = m ? ("Capabilities: " + capsText(m)) : "";
    }).catch(function () {});
  }
  if ($("imgModel")) $("imgModel").onchange = updateImgCaps;

  async function loadJobs() {
    try {
      const data = await api("/api/studio/jobs");
      const grid = $("jobGrid");
      if (!grid) return;
      grid.innerHTML = "";
      (data.jobs || []).forEach(function (j) {
        const card = document.createElement("div");
        card.className = "card";
        card.innerHTML = "<strong>" + (j.type || "job") + "</strong> · " + (j.status || "") +
          "<br>" + (j.model_id || j.base_model || "") +
          "<br>" + String(j.prompt || j.dataset_id || j.id || "").slice(0, 90);
        grid.appendChild(card);
      });
      if (!(data.jobs || []).length) grid.innerHTML = "<div class='card'>No jobs yet</div>";
    } catch (e) {
      if ($("jobGrid")) $("jobGrid").innerHTML = "<div class='card'>" + e.message + "</div>";
    }
  }
  async function loadWorkers() {
    try {
      const data = await api("/api/workers");
      const grid = $("workerGrid");
      grid.innerHTML = "";
      const list = (data.workers || data.items || []);
      if (Array.isArray(list)) {
        list.forEach(function (w) {
          const card = document.createElement("div");
          card.className = "card";
          card.innerHTML = "<strong>" + (w.kind || "worker") + "</strong><br>" + (w.url || "").slice(0, 60) +
            "<br>status: " + (w.status || "—");
          grid.appendChild(card);
        });
      }
      $("workerHint").textContent = data.live_ok ? "At least one worker appears live." : "No live worker — open Boost / Colab and register.";
      if (!list.length) grid.innerHTML = "<div class='card'>No registered workers</div>";
    } catch (e) {
      $("workerGrid").innerHTML = "<div class='card'>" + e.message + "</div>";
    }
  }

  $("imgGen").onclick = async function () {
    show($("imgMsg"), "Generating…", true);
    $("imgPreview").innerHTML = "";
    $("imgGen").disabled = true;
    try {
      const body = {
        prompt: $("imgPrompt").value,
        negative_prompt: $("imgNeg").value || "",
        model_id: $("imgModel").value || "sdxl-turbo",
        lora_id: $("imgLora").value || null,
        lora_weight: Number($("imgLoraW").value || 1),
        width: Number($("imgW").value || 512),
        height: Number($("imgH").value || 512),
        steps: Number($("imgSteps").value || 4),
        guidance: Number($("imgGuid").value || 1),
        seed: $("imgSeed").value === "" ? null : Number($("imgSeed").value)
      };
      const data = await api("/api/studio/generate", { method: "POST", body: body });
      show($("imgMsg"), "OK · " + (data.provider || "") + " · job " + (data.job_id || ""), true);
      (data.images || []).forEach(function (im) {
        var url = im.url;
        var raw = im.image_data || im.image || im.data;
        if (!url && raw) url = raw.indexOf("data:") === 0 ? raw : ("data:image/png;base64," + raw);
        if (url) {
          var img = document.createElement("img");
          img.src = url;
          $("imgPreview").appendChild(img);
        }
      });
    } catch (e) {
      show($("imgMsg"), e.message, false);
    }
    $("imgGen").disabled = false;
  };

  $("vidGen").onclick = async function () {
    try {
      const data = await api("/api/studio/video", {
        method: "POST",
        body: {
          prompt: $("vidPrompt").value,
          mode: $("vidMode").value || "i2v",
          model_id: $("vidModel").value || "svd-xt",
          input_image: $("vidInput").value || null,
          frames: Number($("vidFrames").value || 14),
          fps: Number($("vidFps").value || 7)
        }
      });
      show($("vidMsg"), "Queued " + ((data.job && data.job.id) || "") + " — worker must claim", true);
    } catch (e) { show($("vidMsg"), e.message, false); }
  };

  $("trainStart").onclick = async function () {
    try {
      const data = await api("/api/studio/train", {
        method: "POST",
        body: {
          dataset_id: $("trainDs").value,
          base_model: $("trainBase").value || "flux-schnell",
          rank: Number($("trainRank").value || 16),
          epochs: Number($("trainEpochs").value || 10)
        }
      });
      show($("trainMsg"), "Queued " + ((data.job && data.job.id) || ""), true);
    } catch (e) { show($("trainMsg"), e.message, false); }
  };

  $("dsReg").onclick = async function () {
    try {
      const data = await api("/api/studio/datasets", {
        method: "POST",
        body: { name: $("dsName").value, drive_path: $("dsPath").value }
      });
      show($("dsMsg"), "Registered " + ((data.dataset && data.dataset.id) || ""), true);
      if (data.dataset && data.dataset.id) $("trainDs").value = data.dataset.id;
    } catch (e) { show($("dsMsg"), e.message, false); }
  };

  loadModels();
})();
