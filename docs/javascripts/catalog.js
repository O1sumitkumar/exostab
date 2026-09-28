// Sort the catalog table by clicking a column header, and filter rows by system name.
// Works with Material for MkDocs instant navigation (document$) and with plain page loads.
(function () {
  function setup() {
    var table = document.getElementById("catalog-table");
    if (!table || table.dataset.ready) return;
    table.dataset.ready = "1";
    var tbody = table.tBodies[0];
    var headers = table.tHead.rows[0].cells;
    Array.prototype.forEach.call(headers, function (th, col) {
      th.setAttribute("role", "button");
      th.setAttribute("tabindex", "0");
      th.setAttribute("aria-sort", "none");
      function sort() {
        var asc = th.getAttribute("aria-sort") !== "ascending";
        Array.prototype.forEach.call(headers, function (h) { h.setAttribute("aria-sort", "none"); });
        th.setAttribute("aria-sort", asc ? "ascending" : "descending");
        var rows = Array.prototype.slice.call(tbody.rows);
        rows.sort(function (a, b) {
          var x = a.cells[col].dataset.sort, y = b.cells[col].dataset.sort;
          var nx = parseFloat(x), ny = parseFloat(y);
          var cmp = (!isNaN(nx) && !isNaN(ny)) ? nx - ny : x.localeCompare(y);
          return asc ? cmp : -cmp;
        });
        rows.forEach(function (r) { tbody.appendChild(r); });
      }
      th.addEventListener("click", sort);
      th.addEventListener("keydown", function (e) { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); sort(); } });
    });
    var filter = document.getElementById("catalog-filter");
    if (filter) {
      filter.addEventListener("input", function () {
        var q = filter.value.trim().toLowerCase();
        Array.prototype.forEach.call(tbody.rows, function (r) {
          r.style.display = r.cells[0].textContent.toLowerCase().indexOf(q) === -1 ? "none" : "";
        });
      });
    }
  }
  if (typeof document$ !== "undefined") { document$.subscribe(setup); } else { document.addEventListener("DOMContentLoaded", setup); }
})();
