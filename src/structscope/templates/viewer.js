/* StructScope viewer — no dependencies, no network. */
(function () {
  "use strict";

  var data = JSON.parse(document.getElementById("payload").textContent);
  var svg = document.getElementById("canvas");
  var panel = document.getElementById("panel");
  var filters = document.getElementById("filters");

  var nodes = Array.prototype.slice.call(svg.querySelectorAll(".node"));
  var links = Array.prototype.slice.call(svg.querySelectorAll(".link"));

  function nodeOf(el) {
    return el && el.closest ? el.closest(".node") : null;
  }

  function clearHot() {
    svg.classList.remove("dimmed");
    Array.prototype.forEach.call(svg.querySelectorAll(".hot"), function (el) {
      el.classList.remove("hot");
    });
  }

  function setHot(pair) {
    if (!pair) return;
    svg.classList.add("dimmed");
    Array.prototype.forEach.call(
      svg.querySelectorAll('[data-pair="' + pair + '"]'),
      function (el) {
        el.classList.add("hot");
      }
    );
  }

  svg.addEventListener("mouseover", function (event) {
    var node = nodeOf(event.target);
    if (!node) return;
    if (nodeOf(event.relatedTarget) === node) return;
    setHot(node.getAttribute("data-pair"));
  });

  svg.addEventListener("mouseout", function (event) {
    var node = nodeOf(event.target);
    if (!node) return;
    if (nodeOf(event.relatedTarget) === node) return;
    clearHot();
  });

  svg.addEventListener("click", function (event) {
    var node = nodeOf(event.target);
    if (node) openPanel(node.getAttribute("data-pair"));
  });

  /* ------------------------------------------------------------ panel */

  function openPanel(pair) {
    var item = data.panels[pair];
    if (!item) return;

    panel.innerHTML = "";
    panel.scrollTop = 0;

    var head = document.createElement("div");
    head.className = "p-head";

    var title = document.createElement("div");
    title.className = "p-title";

    var chip = document.createElement("span");
    chip.className = "chip st-" + item.status;
    chip.textContent = item.status;

    var heading = document.createElement("h2");
    heading.textContent = item.name;

    title.appendChild(chip);
    title.appendChild(heading);

    var close = document.createElement("button");
    close.type = "button";
    close.className = "p-close";
    close.setAttribute("aria-label", "Close");
    close.textContent = "\u00d7";
    close.addEventListener("click", closePanel);

    head.appendChild(title);
    head.appendChild(close);

    var metrics = document.createElement("div");
    metrics.className = "p-metrics";
    item.metrics.forEach(function (text) {
      var span = document.createElement("span");
      span.textContent = text;
      metrics.appendChild(span);
    });
    head.appendChild(metrics);

    if (item.note) {
      var note = document.createElement("p");
      note.className = "p-note";
      note.textContent = item.note;
      head.appendChild(note);
    }

    panel.appendChild(head);
    panel.appendChild(buildSource(item.rows));
    panel.hidden = false;
  }

  function buildSource(rows) {
    var wrap = document.createElement("div");
    wrap.className = "src";

    rows.forEach(function (row) {
      var line = document.createElement("div");
      line.className = "srow " + row[4];

      line.appendChild(cell("ln old", row[0]));
      line.appendChild(cell("code c-old", row[1]));
      line.appendChild(cell("ln new", row[2]));
      line.appendChild(cell("code c-new", row[3]));

      wrap.appendChild(line);
    });

    return wrap;
  }

  function cell(className, text) {
    var span = document.createElement("span");
    span.className = className;
    span.textContent = text === null || text === undefined ? "" : text;
    return span;
  }

  function closePanel() {
    panel.hidden = true;
    panel.innerHTML = "";
  }

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape") closePanel();
  });

  /* ----------------------------------------------------------- filter */

  function visible(status) {
    var mode = filters.getAttribute("data-mode") || "all";
    if (mode === "all") return true;
    if (mode === "changed") return status !== "unchanged";
    return status === mode;
  }

  function applyFilter(mode) {
    filters.setAttribute("data-mode", mode);
    nodes.forEach(function (node) {
      node.classList.toggle("is-hidden", !visible(node.getAttribute("data-status")));
    });
    links.forEach(function (link) {
      link.classList.toggle("is-hidden", !visible(link.getAttribute("data-status")));
    });
    clearHot();
  }

  filters.addEventListener("click", function (event) {
    var button = event.target.closest("button[data-filter]");
    if (!button) return;
    Array.prototype.forEach.call(
      filters.querySelectorAll("button"),
      function (item) {
        item.classList.toggle("is-active", item === button);
      }
    );
    applyFilter(button.getAttribute("data-filter"));
  });
})();
