// Report tree: classification → variant type → record, with pagination
// on the record list. Search and paging share one pass so a page change
// cannot resurrect rows the filter has excluded.
(function () {
  "use strict";

  const PAGE_SIZE_WIDE = 25;
  const PAGE_SIZE_NARROW = 12;

  const root = document.querySelector("[data-report-filter]");
  if (!root) return;

  const searchInput = root.querySelector("[data-search-input]");
  const starFilter = root.querySelector("[data-star-filter]");
  const statusEl = document.querySelector("[data-filter-status]");
  const expandGroups = document.querySelector("[data-expand-groups]");
  const collapseAll = document.querySelector("[data-collapse-all]");

  function pageSize() {
    return window.matchMedia("(max-width: 40rem)").matches ? PAGE_SIZE_NARROW : PAGE_SIZE_WIDE;
  }

  const groups = Array.prototype.map.call(
    document.querySelectorAll("[data-group]"),
    function (groupEl) {
      const types = Array.prototype.map.call(
        groupEl.querySelectorAll("[data-type-block]"),
        function (details) {
          return {
            details: details,
            items: Array.prototype.slice.call(details.querySelectorAll("[data-variant]")),
            pager: details.querySelector("[data-pager]"),
            pageStatus: details.querySelector("[data-page-status]"),
            first: details.querySelector("[data-page-first]"),
            prev: details.querySelector("[data-page-prev]"),
            next: details.querySelector("[data-page-next]"),
            last: details.querySelector("[data-page-last]"),
            emptyNote: details.querySelector("[data-empty-note]"),
            countEl: details.querySelector("[data-type-count]"),
            total: parseInt(details.dataset.total, 10) || details.querySelectorAll("[data-variant]").length,
            page: 1,
            matches: []
          };
        }
      );
      return {
        el: groupEl,
        countEl: groupEl.querySelector("[data-group-count]"),
        total: parseInt(groupEl.dataset.total, 10) || 0,
        types: types
      };
    }
  );

  function currentQuery() {
    return {
      term: (searchInput.value || "").trim().toLowerCase(),
      minStars: parseInt(starFilter.value, 10) || 0
    };
  }

  function matches(item, query) {
    if (query.minStars > 0) {
      if ((parseInt(item.dataset.stars, 10) || 0) < query.minStars) return false;
    }
    if (!query.term) return true;
    return (item.dataset.haystack || "").toLowerCase().indexOf(query.term) !== -1;
  }

  function renderType(type, query, filtering, size) {
    type.matches = type.items.filter(function (item) {
      return matches(item, query);
    });

    const pageCount = Math.max(1, Math.ceil(type.matches.length / size));
    if (type.page > pageCount) type.page = pageCount;
    if (type.page < 1) type.page = 1;

    const start = (type.page - 1) * size;
    const end = start + size;
    const visible = type.matches.slice(start, end);
    const visibleSet = new Set(visible);

    type.items.forEach(function (item) {
      item.hidden = !visibleSet.has(item);
    });

    const hasMatches = type.matches.length > 0;
    type.emptyNote.hidden = hasMatches;
    type.pager.hidden = type.matches.length <= size;
    type.details.hidden = filtering && !hasMatches;

    if (!type.pager.hidden) {
      type.first.disabled = type.prev.disabled = type.page === 1;
      type.next.disabled = type.last.disabled = type.page === pageCount;
      type.pageStatus.textContent =
        "Showing " + (start + 1).toLocaleString() + "\u2013" +
        Math.min(end, type.matches.length).toLocaleString() +
        " of " + type.matches.length.toLocaleString() +
        " \u00b7 page " + type.page + " of " + pageCount;
    }

    if (type.countEl) {
      type.countEl.textContent = filtering
        ? type.matches.length.toLocaleString() + " of " + type.total.toLocaleString()
        : String(type.total.toLocaleString());
    }

    if (filtering) {
      type.details.open = hasMatches;
    }

    type.details.dataset.hasMatches = hasMatches ? "true" : "false";
    return type.matches.length;
  }

  function render() {
    const query = currentQuery();
    const filtering = Boolean(query.term) || query.minStars > 0;
    const size = pageSize();

    let totalMatches = 0;
    let totalItems = 0;

    groups.forEach(function (group) {
      let groupMatches = 0;
      group.types.forEach(function (type) {
        groupMatches += renderType(type, query, filtering, size);
        totalItems += type.total;
      });
      totalMatches += groupMatches;

      const hasMatches = groupMatches > 0;
      group.el.hidden = filtering && !hasMatches;
      if (filtering && hasMatches) {
        group.el.open = true;
      }
      if (group.countEl) {
        group.countEl.textContent = filtering
          ? groupMatches.toLocaleString() + " of " + group.total.toLocaleString() + " records"
          : group.total.toLocaleString() + " records";
      }
    });

    if (statusEl) {
      statusEl.textContent = filtering
        ? "Showing " + totalMatches.toLocaleString() + " of " +
          totalItems.toLocaleString() + " records."
        : "";
    }
  }

  groups.forEach(function (group) {
    group.types.forEach(function (type) {
      type.first.addEventListener("click", function () {
        type.page = 1;
        render();
      });
      type.prev.addEventListener("click", function () {
        type.page -= 1;
        render();
      });
      type.next.addEventListener("click", function () {
        type.page += 1;
        render();
      });
      type.last.addEventListener("click", function () {
        type.page = Math.ceil(type.matches.length / pageSize()) || 1;
        render();
      });
    });
  });

  function resetPages() {
    groups.forEach(function (group) {
      group.types.forEach(function (type) {
        type.page = 1;
      });
    });
  }

  let debounce;
  searchInput.addEventListener("input", function () {
    window.clearTimeout(debounce);
    debounce = window.setTimeout(function () {
      resetPages();
      render();
    }, 140);
  });

  starFilter.addEventListener("change", function () {
    resetPages();
    render();
  });

  if (expandGroups) {
    expandGroups.addEventListener("click", function () {
      groups.forEach(function (group) {
        if (!group.el.hidden) group.el.open = true;
      });
    });
  }

  if (collapseAll) {
    collapseAll.addEventListener("click", function () {
      groups.forEach(function (group) {
        group.el.open = false;
        group.types.forEach(function (type) {
          type.details.open = false;
          type.items.forEach(function (item) {
            const inner = item.querySelector("[data-variant-details]");
            if (inner) inner.open = false;
          });
        });
      });
    });
  }

  let resizeTimer;
  window.addEventListener("resize", function () {
    window.clearTimeout(resizeTimer);
    resizeTimer = window.setTimeout(render, 160);
  });

  render();
})();
