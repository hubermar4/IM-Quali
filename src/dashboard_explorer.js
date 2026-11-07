    // ---- Race Explorer: overview, filters, ranks and athlete drill-down ----
    // Inlined into the app script by build_html() (the DASHBOARD_EXPLORER placeholder), so it
    // shares DATASETS, dataset(), duration(), metric() and the year selection.
    // All statistics here are descriptive, all-athlete statistics; they belong to
    // neither qualification objective.
    const explorerFilters = { gender: "", division: "", country: "" };
    let explorerSort = { key: "overall", direction: 1 };
    const EXPLORER_PAGE = 250;
    let explorerLimit = EXPLORER_PAGE;
    let explorerSelected = null;
    let explorerOverviewGender = false;
    const explorerRankCache = new WeakMap();
    const explorerFieldCache = new WeakMap();
    let explorerIdentityIndex = null;
    const explorerSplitKeys = [["swim", "Swim"], ["t1", "T1"], ["bike", "Bike"], ["t2", "T2"], ["run", "Run"]];
    const explorerGenderColors = { Male: "#277da1", Female: "#d1495b" };

    function explorerNormalizedDivision(row) {
      return String(row.division).trim().toUpperCase();
    }
    function explorerMatches(row) {
      if (explorerFilters.gender && row.gender !== explorerFilters.gender) return false;
      if (explorerFilters.division && explorerNormalizedDivision(row) !== explorerFilters.division) return false;
      if (explorerFilters.country && row.country !== explorerFilters.country) return false;
      return true;
    }
    // Overall place within the race-year (all finishers, including professionals)
    // and age-group place within the division.
    function explorerRanks(records) {
      if (explorerRankCache.has(records)) return explorerRankCache.get(records);
      const ranks = new Map();
      const byYear = new Map();
      records.forEach(row => {
        if (!byYear.has(row.year)) byYear.set(row.year, []);
        byYear.get(row.year).push(row);
      });
      byYear.forEach(rows => {
        const ordered = [...rows].sort((left, right) => left.overall - right.overall);
        const divisionPlaces = new Map();
        const divisionSizes = new Map();
        ordered.forEach(row => {
          const division = explorerNormalizedDivision(row);
          divisionSizes.set(division, (divisionSizes.get(division) || 0) + 1);
        });
        ordered.forEach((row, index) => {
          const division = explorerNormalizedDivision(row);
          const place = (divisionPlaces.get(division) || 0) + 1;
          divisionPlaces.set(division, place);
          ranks.set(row, { place: index + 1, field: ordered.length, divisionPlace: place, divisionField: divisionSizes.get(division) });
        });
      });
      explorerRankCache.set(records, ranks);
      return ranks;
    }
    const explorerSortValue = {
      year: row => Number(row.year), name: row => row.name.toLocaleLowerCase(), division: explorerNormalizedDivision,
      place: row => row.overall, overall: row => row.overall, swim: row => row.swim, t1: row => row.t1,
      bike: row => row.bike, t2: row => row.t2, run: row => row.run,
    };
    function explorerCompare(left, right) {
      const value = explorerSortValue[explorerSort.key] || explorerSortValue.overall;
      const a = value(left), b = value(right);
      const order = a < b ? -1 : a > b ? 1 : 0;
      return order * explorerSort.direction || left.overall - right.overall || left.name.localeCompare(right.name);
    }

    // Sorted split times per race-year (and per division) for percentiles.
    function explorerField(records, year, division, key) {
      if (!explorerFieldCache.has(records)) explorerFieldCache.set(records, new Map());
      const cache = explorerFieldCache.get(records);
      const cacheKey = `${year}|${division || ""}|${key}`;
      if (!cache.has(cacheKey)) {
        cache.set(cacheKey, records
          .filter(row => row.year === year && (!division || explorerNormalizedDivision(row) === division) && row[key] > 0)
          .map(row => row[key]).sort((a, b) => a - b));
      }
      return cache.get(cacheKey);
    }
    // Share of the field strictly slower than `value` (higher is better).
    function explorerFasterThan(sorted, value) {
      if (!sorted.length || !(value > 0)) return null;
      let low = 0, high = sorted.length;
      while (low < high) {
        const middle = (low + high) >> 1;
        if (sorted[middle] <= value) low = middle + 1; else high = middle;
      }
      return (sorted.length - low) / sorted.length;
    }
    function explorerMedian(values) {
      const sorted = values.filter(Number.isFinite).sort((a, b) => a - b);
      if (!sorted.length) return null;
      const middle = Math.floor(sorted.length / 2);
      return sorted.length % 2 ? sorted[middle] : (sorted[middle - 1] + sorted[middle]) / 2;
    }
    function explorerVisibleRecords() {
      return dataset().records.filter(row => compareYearVisible(row.year));
    }

    // ---- Athletes & Splits table ----
    function populateExplorerFilters() {
      const divisionSelect = document.getElementById("explorerDivision");
      const countrySelect = document.getElementById("explorerCountry");
      if (!divisionSelect) return;
      const records = dataset().records;
      const divisions = [...new Set(records.map(explorerNormalizedDivision))].sort((a, b) => {
        const pro = value => /PRO$/.test(value) ? 0 : 1;
        return pro(a) - pro(b) || a.localeCompare(b);
      });
      const countries = [...new Set(records.map(row => row.country).filter(Boolean))].sort((a, b) => a.localeCompare(b));
      if (explorerFilters.division && !divisions.includes(explorerFilters.division)) explorerFilters.division = "";
      if (explorerFilters.country && !countries.includes(explorerFilters.country)) explorerFilters.country = "";
      divisionSelect.innerHTML = `<option value="">All age groups</option>${divisions.map(value => `<option value="${escapeHtml(value)}">${escapeHtml(value)}</option>`).join("")}`;
      countrySelect.innerHTML = `<option value="">All countries</option>${countries.map(value => `<option value="${escapeHtml(value)}">${escapeHtml(value)}</option>`).join("")}`;
      divisionSelect.value = explorerFilters.division;
      countrySelect.value = explorerFilters.country;
      document.getElementById("explorerGender").value = explorerFilters.gender;
    }
    function explorerFullRange() {
      const times = dataset().records.map(row => row.overall);
      return times.length ? [Math.min(...times), Math.max(...times)] : [0, 0];
    }
    function explorerActiveFilterText(rows) {
      const parts = [];
      if (explorerFilters.gender) parts.push(explorerFilters.gender === "Male" ? "men" : "women");
      if (explorerFilters.division) parts.push(explorerFilters.division);
      if (explorerFilters.country) parts.push(explorerFilters.country);
      if (searchInput.value.trim()) parts.push(`“${searchInput.value.trim()}”`);
      const years = compareYears.filter(year => compareYearVisible(year) && dataset().records.some(row => row.year === year)).length;
      return `${rows.length.toLocaleString()} finishers · ${years} race year${years === 1 ? "" : "s"}${parts.length ? ` · ${parts.join(" · ")}` : ""}`;
    }
    function renderExplorerFinishers(rows) {
      const body = document.getElementById("finishersBody");
      document.querySelectorAll("#finishersTable th[data-sort]").forEach(header => {
        const active = header.dataset.sort === explorerSort.key;
        header.setAttribute("aria-sort", active ? (explorerSort.direction > 0 ? "ascending" : "descending") : "none");
      });
      const status = document.getElementById("explorerTableStatus");
      if (status) status.textContent = explorerActiveFilterText(rows);
      if (!rows.length) {
        body.innerHTML = `<tr><td colspan="11" class="empty">No finishers match these filters. Widen the time range or clear a filter.</td></tr>`;
        body.explorerRows = [];
        const emptyMore = document.getElementById("explorerMore");
        if (emptyMore) emptyMore.hidden = true;
        return;
      }
      const ranks = explorerRanks(dataset().records);
      const shown = rows.slice(0, explorerLimit);
      body.innerHTML = shown.map((row, index) => {
        const rank = ranks.get(row) || {};
        const bars = splits.map(([, key]) => `<span class="${key}" style="width:${100 * row[key] / row.overall}%"></span>`).join("");
        const selected = row === explorerSelected ? ' class="explorer-selected"' : "";
        return `<tr${selected}><td>${yearCell(eventSelect.value, row.year)}</td><td><button type="button" class="athlete-link" data-explorer-row="${index}" aria-label="Show details for ${escapeHtml(row.name)}, ${row.year}"><strong>${escapeHtml(row.name)}</strong></button><br><small>${escapeHtml(row.country)} · #${escapeHtml(row.bib)}</small></td><td>${escapeHtml(row.division)}</td><td>${rank.place ?? "—"}<small class="of"> / ${rank.field ?? "—"}</small><br><small>AG ${rank.divisionPlace ?? "—"} / ${rank.divisionField ?? "—"}</small></td><td><strong>${duration(row.overall)}</strong></td><td><div class="split-bar">${bars}</div></td><td>${withMetric("swim", row.swim)}</td><td>${duration(row.t1)}</td><td>${withMetric("bike", row.bike)}</td><td>${duration(row.t2)}</td><td>${withMetric("run", row.run)}</td></tr>`;
      }).join("");
      body.explorerRows = shown;
      const more = document.getElementById("explorerMore");
      if (!more) return;
      more.hidden = rows.length <= explorerLimit;
      more.textContent = `Show ${Math.min(EXPLORER_PAGE, rows.length - explorerLimit).toLocaleString()} more (${shown.length.toLocaleString()} of ${rows.length.toLocaleString()} shown)`;
    }

    // ---- Athlete detail ----
    function explorerIdentity(row) {
      return identityKey(row.name, row.gender, row.country);
    }
    function explorerOtherResults(row) {
      if (!explorerIdentityIndex) {
        explorerIdentityIndex = new Map();
        Object.entries(DATASETS).forEach(([eventId, entry]) => (entry.records || []).forEach(record => {
          const key = explorerIdentity(record);
          if (!key) return;
          if (!explorerIdentityIndex.has(key)) explorerIdentityIndex.set(key, []);
          explorerIdentityIndex.get(key).push({ eventId, row: record });
        }));
      }
      return (explorerIdentityIndex.get(explorerIdentity(row)) || [])
        .slice().sort((left, right) => Number(right.row.year) - Number(left.row.year) || DATASETS[left.eventId].name.localeCompare(DATASETS[right.eventId].name));
    }
    function explorerPercentileCell(label, fraction) {
      if (fraction === null) return `<div class="pct-row"><span class="pct-bar"><i style="width:0"></i></span><span>—</span></div>`;
      const percent = Math.round(100 * fraction);
      return `<div class="pct-row"><span class="pct-bar" role="img" aria-label="${escapeHtml(label)}: faster than ${percent}%"><i style="width:${percent}%"></i></span><span>${percent}%</span></div>`;
    }
    function renderExplorerAthlete() {
      const panel = document.getElementById("explorerAthlete");
      if (!panel) return;
      const row = explorerSelected;
      if (!row || !dataset().records.includes(row)) {
        explorerSelected = null;
        panel.hidden = true;
        return;
      }
      const records = dataset().records;
      const rank = explorerRanks(records).get(row) || {};
      const division = explorerNormalizedDivision(row);
      const splitRows = explorerSplitKeys.map(([key, label]) => {
        const field = explorerField(records, row.year, null, key);
        const group = explorerField(records, row.year, division, key);
        const groupMedian = explorerMedian(group);
        const delta = Number.isFinite(groupMedian) ? row[key] - groupMedian : null;
        const deltaText = delta === null ? "—" : `${delta <= 0 ? "−" : "+"}${duration(Math.abs(delta))}`;
        return `<tr><th scope="row"><i class="split-dot ${key}"></i>${label}</th><td>${withMetric(key, row[key])}</td><td>${explorerPercentileCell("Field", explorerFasterThan(field, row[key]))}</td><td>${explorerPercentileCell(division, explorerFasterThan(group, row[key]))}</td><td class="${delta !== null && delta <= 0 ? "faster" : "slower"}">${deltaText}</td></tr>`;
      }).join("");
      const overallField = explorerFasterThan(explorerField(records, row.year, null, "overall"), row.overall);
      const overallGroup = explorerFasterThan(explorerField(records, row.year, division, "overall"), row.overall);
      const others = explorerOtherResults(row);
      const otherRows = others.map(({ eventId, row: other }) => {
        const current = other === row;
        const otherRank = explorerRanks(DATASETS[eventId].records).get(other) || {};
        const action = current ? "<small>shown</small>" : `<button type="button" class="context-action" data-explorer-open="${escapeHtml(eventId)}|${other.year}|${escapeHtml(other.bib)}">Open</button>`;
        return `<tr${current ? ' class="explorer-selected"' : ""}><td>${other.year}</td><td>${escapeHtml(DATASETS[eventId].name)}</td><td>${escapeHtml(other.division)}</td><td>${duration(other.overall)}</td><td>${otherRank.divisionPlace ?? "—"} / ${otherRank.divisionField ?? "—"}</td><td>${duration(other.swim)}</td><td>${duration(other.bike)}</td><td>${duration(other.run)}</td><td>${action}</td></tr>`;
      }).join("");
      panel.innerHTML = `<div class="athlete-head"><div><span class="eyebrow">${escapeHtml(dataset().name)} · ${row.year}</span><h2>${escapeHtml(row.name)}</h2><p class="note">${escapeHtml(row.country)} · ${escapeHtml(row.division)} · bib #${escapeHtml(row.bib)}</p></div><button type="button" class="context-action" id="explorerAthleteClose" aria-label="Close athlete details">Close ✕</button></div>
        <div class="metrics athlete-metrics">
          <div class="metric"><span>Finish time</span><strong>${duration(row.overall)}</strong></div>
          <div class="metric"><span>Overall place</span><strong>${rank.place ?? "—"} <small>of ${rank.field ?? "—"}</small></strong></div>
          <div class="metric"><span>${escapeHtml(division)} place</span><strong>${rank.divisionPlace ?? "—"} <small>of ${rank.divisionField ?? "—"}</small></strong></div>
          <div class="metric"><span>Faster than</span><strong>${overallField === null ? "—" : `${Math.round(100 * overallField)}%`} <small>of field · ${overallGroup === null ? "—" : `${Math.round(100 * overallGroup)}%`} of AG</small></strong></div>
        </div>
        <div class="split-bar athlete-split-bar">${splits.map(([, key]) => `<span class="${key}" style="width:${100 * row[key] / row.overall}%" title="${key}: ${duration(row[key])}"></span>`).join("")}</div>
        <div class="table-wrap" style="max-height:none"><table class="athlete-splits"><thead><tr><th>Split</th><th>Time</th><th>Faster than · field ${row.year}</th><th>Faster than · ${escapeHtml(division)}</th><th>vs. ${escapeHtml(division)} median</th></tr></thead><tbody>${splitRows}</tbody></table></div>
        <p class="note">Percentiles compare this split with every finisher of the same race-year (and the same age group). Course and conditions differ between race-years; use Course Analysis for standard-course comparisons.</p>
        <h3>All results of this athlete in the data</h3>
        <div class="table-wrap" style="max-height:340px"><table><thead><tr><th>Year</th><th>Race</th><th>Division</th><th>Finish</th><th>AG place</th><th>Swim</th><th>Bike</th><th>Run</th><th></th></tr></thead><tbody>${otherRows}</tbody></table></div>
        <p class="note">Matched by name, gender and country, so namesakes can appear and changed spellings are missed.</p>`;
      panel.hidden = false;
    }
    function explorerShowAthlete(row, scroll = true) {
      explorerSelected = row;
      renderExplorerAthlete();
      render();
      if (scroll) document.getElementById("explorerAthlete").scrollIntoView({ block: "start", behavior: "smooth" });
    }

    // ---- Drill-down from the overview into the athlete table ----
    function explorerDrill({ from, to, division = "", country = "", gender = "" } = {}) {
      const [minimum, maximum] = explorerFullRange();
      fromInput.value = duration(Number.isFinite(from) ? from : minimum);
      toInput.value = duration(Number.isFinite(to) ? to : maximum);
      explorerFilters.division = division;
      explorerFilters.country = country;
      explorerFilters.gender = gender;
      searchInput.value = "";
      explorerLimit = EXPLORER_PAGE;
      populateExplorerFilters();
      activateDashboardView("splits");
      render();
      document.getElementById("splitsPanel").scrollIntoView({ block: "start" });
    }

    // ---- Overview ----
    function explorerDelta(current, previous, format, unit = "") {
      if (!Number.isFinite(current) || !Number.isFinite(previous)) return "";
      const change = current - previous;
      if (Math.abs(change) < 1e-9) return `<small class="delta">no change vs. previous</small>`;
      return `<small class="delta">${change > 0 ? "▲" : "▼"} ${format(Math.abs(change))}${unit} vs. previous</small>`;
    }
    function explorerKpis(records) {
      const stats = (dataset().statistics || []).filter(row => compareYearVisible(row.year)).sort((a, b) => Number(a.year) - Number(b.year));
      const latest = stats.at(-1);
      const previous = stats.at(-2);
      const latestRecords = latest ? records.filter(row => row.year === latest.year) : [];
      const previousRecords = previous ? records.filter(row => row.year === previous.year) : [];
      const medianLatest = explorerMedian(latestRecords.map(row => row.overall));
      const medianPrevious = explorerMedian(previousRecords.map(row => row.overall));
      const womenShare = row => row?.finishers ? 100 * row.female_finishers / row.finishers : null;
      const completion = row => Number.isFinite(row?.completion_rate) ? 100 * row.completion_rate : null;
      const tile = (label, value, detail) => `<div class="metric"><span>${label}</span><strong>${value}</strong>${detail}</div>`;
      return `<div class="metrics overview-metrics">
        ${tile(`Finishers ${latest?.year ?? ""}`, latest ? latest.finishers.toLocaleString() : "—", previous ? explorerDelta(latest.finishers, previous.finishers, value => Math.round(value).toLocaleString()) : "")}
        ${tile(`Median finish ${latest?.year ?? ""}`, duration(medianLatest), explorerDelta(medianLatest, medianPrevious, duration))}
        ${tile(`Completion ${latest?.year ?? ""}`, Number.isFinite(completion(latest)) ? `${completion(latest).toFixed(1)}%` : "—", explorerDelta(completion(latest), completion(previous), value => value.toFixed(1), " pp"))}
        ${tile(`Women ${latest?.year ?? ""}`, Number.isFinite(womenShare(latest)) ? `${womenShare(latest).toFixed(1)}%` : "—", explorerDelta(womenShare(latest), womenShare(previous), value => value.toFixed(1), " pp"))}
      </div>`;
    }
    function explorerHistogram(records) {
      if (!records.length) return '<p class="empty">No finishers in the selected race years.</p>';
      const binSize = dataset().group === "703" ? 600 : 900;
      const times = records.map(row => row.overall).sort((a, b) => a - b);
      const start = Math.floor(times[0] / binSize) * binSize;
      const end = Math.ceil((times.at(-1) + 1) / binSize) * binSize;
      const binCount = Math.max(1, Math.round((end - start) / binSize));
      const groups = explorerOverviewGender ? ["Male", "Female"] : ["All"];
      const bins = Array.from({ length: binCount }, () => Object.fromEntries(groups.map(group => [group, 0])));
      records.forEach(row => {
        const index = Math.min(binCount - 1, Math.floor((row.overall - start) / binSize));
        const group = explorerOverviewGender ? (row.gender === "Female" ? "Female" : "Male") : "All";
        bins[index][group]++;
      });
      const maximum = Math.max(...bins.map(bin => groups.reduce((sum, group) => sum + bin[group], 0)));
      const width = 1000, height = 300, left = 52, right = 14, top = 14, bottom = 42;
      const plotWidth = width - left - right, plotHeight = height - top - bottom;
      const barWidth = plotWidth / binCount;
      const y = value => top + plotHeight - plotHeight * value / maximum;
      const x = seconds => left + plotWidth * (seconds - start) / (end - start);
      const colors = { All: "#00796b", ...explorerGenderColors };
      let bars = "";
      bins.forEach((bin, index) => {
        let base = 0;
        const from = start + index * binSize, to = from + binSize - 1;
        const total = groups.reduce((sum, group) => sum + bin[group], 0);
        groups.forEach(group => {
          const value = bin[group];
          if (!value) return;
          bars += `<rect x="${(left + index * barWidth + 1).toFixed(1)}" y="${y(base + value).toFixed(1)}" width="${Math.max(1, barWidth - 2).toFixed(1)}" height="${(y(base) - y(base + value)).toFixed(1)}" fill="${colors[group]}" pointer-events="none"/>`;
          base += value;
        });
        const label = `${duration(from)}–${duration(to)}: ${total.toLocaleString()} finishers${explorerOverviewGender ? ` (${bin.Male.toLocaleString()} men, ${bin.Female.toLocaleString()} women)` : ""}. Select to list them.`;
        bars += `<rect class="hist-hit" x="${(left + index * barWidth).toFixed(1)}" y="${top}" width="${barWidth.toFixed(1)}" height="${plotHeight}" fill="transparent" tabindex="${total ? 0 : -1}" role="button" aria-label="${label}" data-hist-from="${from}" data-hist-to="${to}"><title>${label}</title></rect>`;
      });
      const ticks = [];
      const tickStep = (end - start) / 3600 > 8 ? 7200 : 3600;
      for (let tick = Math.ceil(start / tickStep) * tickStep; tick <= end; tick += tickStep) {
        ticks.push(`<line class="grid" x1="${x(tick)}" x2="${x(tick)}" y1="${top}" y2="${top + plotHeight}"/><text x="${x(tick)}" y="${height - 20}" text-anchor="middle">${Math.floor(tick / 3600)}:${String(Math.floor(tick % 3600 / 60)).padStart(2, "0")} h</text>`);
      }
      const yTicks = [0, 0.5, 1].map(fraction => Math.round(maximum * fraction)).map(value => `<line class="grid" x1="${left}" x2="${width - right}" y1="${y(value)}" y2="${y(value)}"/><text x="${left - 8}" y="${y(value) + 4}" text-anchor="end">${value.toLocaleString()}</text>`).join("");
      const median = explorerMedian(times);
      const quantile = q => times[Math.min(times.length - 1, Math.floor(q * times.length))];
      const markers = [[quantile(0.1), "Top 10%", "#b08900"], [median, "Median", "#15231e"]].map(([value, label, color]) =>
        `<line x1="${x(value)}" x2="${x(value)}" y1="${top}" y2="${top + plotHeight}" stroke="${color}" stroke-width="2" stroke-dasharray="5 4" pointer-events="none"/><text x="${x(value) + 5}" y="${top + 12}" fill="${color}" style="fill:${color};font-weight:700">${label} ${duration(value)}</text>`).join("");
      return `<svg class="chart histogram" viewBox="0 0 ${width} ${height}" role="group" aria-label="Finish-time distribution; each bar is selectable">${yTicks}${ticks.join("")}<line class="axis" x1="${left}" x2="${width - right}" y1="${top + plotHeight}" y2="${top + plotHeight}"/>${bars}${markers}<text x="${left + plotWidth / 2}" y="${height - 3}" text-anchor="middle">Finish time · ${binSize / 60}-minute bins</text></svg>`;
    }
    function explorerBreakdown(records) {
      const years = [...new Set(records.map(row => row.year))].sort();
      if (!years.length) return "";
      const medians = years.map(year => {
        const rows = records.filter(row => row.year === year);
        return { year, values: Object.fromEntries(explorerSplitKeys.map(([key]) => [key, explorerMedian(rows.map(row => row[key]).filter(value => value > 0))])) };
      });
      const totals = medians.map(entry => explorerSplitKeys.reduce((sum, [key]) => sum + (entry.values[key] || 0), 0));
      const maximum = Math.max(...totals);
      return medians.map((entry, index) => {
        const modification = dataset().modified_courses?.[entry.year];
        const parts = explorerSplitKeys.map(([key, label]) => {
          const value = entry.values[key] || 0;
          const showText = value / maximum > 0.12;
          return `<span class="${key}" style="width:${(100 * value / maximum).toFixed(2)}%" title="${label}: ${duration(value)}">${showText ? duration(value).replace(/^0/, "") : ""}</span>`;
        }).join("");
        return `<div class="breakdown-row"><span class="breakdown-year">${entry.year}${modification ? ` <span title="${escapeHtml(modification)}">⚠</span>` : ""}</span><div class="breakdown-bar">${parts}</div><span class="breakdown-total">${duration(totals[index])}</span></div>`;
      }).join("");
    }
    function explorerDivisionTable(records) {
      const divisions = new Map();
      records.forEach(row => {
        const division = explorerNormalizedDivision(row);
        if (!divisions.has(division)) divisions.set(division, []);
        divisions.get(division).push(row.overall);
      });
      const rows = [...divisions.entries()].map(([division, times]) => ({ division, count: times.length, median: explorerMedian(times), fastest: Math.min(...times) }))
        .sort((a, b) => {
          const pro = value => /PRO$/.test(value) ? 0 : 1;
          return pro(a.division) - pro(b.division) || a.division.localeCompare(b.division);
        });
      const maximumCount = Math.max(...rows.map(row => row.count));
      return rows.map(row => `<tr><td><button type="button" class="athlete-link" data-drill-division="${escapeHtml(row.division)}">${escapeHtml(row.division)}</button></td><td><span class="inline-bar"><i style="width:${(100 * row.count / maximumCount).toFixed(1)}%"></i></span>${row.count.toLocaleString()}</td><td>${(100 * row.count / records.length).toFixed(1)}%</td><td>${duration(row.median)}</td><td>${duration(row.fastest)}</td></tr>`).join("");
    }
    function explorerCountryList(records) {
      const counts = new Map();
      records.forEach(row => { if (row.country) counts.set(row.country, (counts.get(row.country) || 0) + 1); });
      const top = [...counts.entries()].sort((a, b) => b[1] - a[1]).slice(0, 15);
      const maximum = top[0]?.[1] || 1;
      return top.map(([country, count]) => `<li><button type="button" class="athlete-link" data-drill-country="${escapeHtml(country)}">${escapeHtml(country)}</button><span class="inline-bar"><i style="width:${(100 * count / maximum).toFixed(1)}%"></i></span><span>${count.toLocaleString()}</span><span class="note">${(100 * count / records.length).toFixed(1)}%</span></li>`).join("")
        + (counts.size > 15 ? `<li class="note">and ${(counts.size - 15).toLocaleString()} more countries</li>` : "");
    }
    function renderExplorerOverview() {
      const panel = document.getElementById("overviewPanel");
      if (!panel) return;
      const records = explorerVisibleRecords();
      panel.querySelector("#overviewKpis").innerHTML = explorerKpis(records);
      panel.querySelector("#overviewHistogram").innerHTML = explorerHistogram(records);
      panel.querySelector("#overviewHistogramNote").textContent = `${records.length.toLocaleString()} finishers in the selected race years, including professionals. Select a bar to list those finishers in Athletes & Splits.`;
      panel.querySelector("#overviewBreakdown").innerHTML = explorerBreakdown(records) || '<p class="empty">No finishers in the selected race years.</p>';
      panel.querySelector("#overviewDivisions").innerHTML = explorerDivisionTable(records) || '<tr><td colspan="5" class="empty">No finishers in the selected race years.</td></tr>';
      panel.querySelector("#overviewCountries").innerHTML = explorerCountryList(records);
    }

    function initializeExplorer() {
      const overview = document.createElement("div");
      overview.id = "overviewPanel";
      overview.className = "tab-panel";
      overview.innerHTML = `<div id="overviewKpis"></div>
        <section class="chart-panel"><div class="chart-heading"><div><h2>Finish-time distribution</h2><p id="overviewHistogramNote" class="note"></p></div><div class="chart-controls"><label class="binary-label"><input type="checkbox" id="overviewByGender"> Split by gender</label></div></div>
          <ul class="legend overview-gender-legend" hidden><li><i style="background:${explorerGenderColors.Male}"></i>Men</li><li><i style="background:${explorerGenderColors.Female}"></i>Women</li></ul>
          <div id="overviewHistogram"></div></section>
        <div class="overview-grid">
          <section class="chart-panel"><h2>Where the time goes</h2><p class="note">Median split per race year; bar length is the sum of the medians. ⚠ marks shortened or modified courses.</p>
            <div class="legend"><span><i class="swim"></i>Swim</span><span><i class="t1"></i>T1</span><span><i class="bike"></i>Bike</span><span><i class="t2"></i>T2</span><span><i class="run"></i>Run</span></div>
            <div id="overviewBreakdown" class="breakdown"></div></section>
          <section class="chart-panel"><h2>Countries</h2><p class="note">Finishers by country in the selected race years. Select one to list its athletes.</p><ol id="overviewCountries" class="country-list"></ol></section>
        </div>
        <section class="chart-panel"><h2>Age groups</h2><p class="note">Finishers per division in the selected race years. Select a division to list its athletes.</p>
          <div class="table-wrap" style="max-height:520px"><table class="division-table"><thead><tr><th>Division</th><th>Finishers</th><th>Share</th><th>Median finish</th><th>Fastest</th></tr></thead><tbody id="overviewDivisions"></tbody></table></div></section>`;
      document.getElementById("statisticsPanel").before(overview);

      const controls = document.querySelector("#splitsPanel > .controls");
      const filters = document.createElement("div");
      filters.className = "explorer-filters";
      filters.innerHTML = `<label>Gender <select id="explorerGender"><option value="">All</option><option value="Male">Men</option><option value="Female">Women</option></select></label>
        <label>Age group <select id="explorerDivision"></select></label>
        <label>Country <select id="explorerCountry"></select></label>
        <button type="button" class="context-action" id="explorerAllTimes">All finish times</button>
        <button type="button" class="context-action" id="explorerClear">Clear filters</button>`;
      controls.querySelector("#download").before(filters);

      const tableSection = document.getElementById("finishersBody").closest("section");
      tableSection.querySelector("h2").insertAdjacentHTML("afterend", '<p id="explorerTableStatus" class="note table-status" aria-live="polite"></p>');
      const athlete = document.createElement("section");
      athlete.id = "explorerAthlete";
      athlete.className = "chart-panel athlete-panel";
      athlete.hidden = true;
      tableSection.before(athlete);
      tableSection.insertAdjacentHTML("beforeend", '<button type="button" class="context-action explorer-more" id="explorerMore" hidden></button>');

      const changeFilter = (key, value) => {
        explorerFilters[key] = value;
        explorerLimit = EXPLORER_PAGE;
        render();
        updateDashboardScope();
      };
      document.getElementById("explorerGender").addEventListener("change", event => changeFilter("gender", event.target.value));
      document.getElementById("explorerDivision").addEventListener("change", event => changeFilter("division", event.target.value));
      document.getElementById("explorerCountry").addEventListener("change", event => changeFilter("country", event.target.value));
      document.getElementById("explorerAllTimes").addEventListener("click", () => {
        const [minimum, maximum] = explorerFullRange();
        fromInput.value = duration(minimum);
        toInput.value = duration(maximum);
        explorerLimit = EXPLORER_PAGE;
        render();
        updateDashboardScope();
      });
      document.getElementById("explorerClear").addEventListener("click", () => {
        explorerFilters.gender = explorerFilters.division = explorerFilters.country = "";
        searchInput.value = "";
        populateExplorerFilters();
        explorerLimit = EXPLORER_PAGE;
        render();
        updateDashboardScope();
      });
      document.getElementById("explorerMore").addEventListener("click", () => {
        explorerLimit += EXPLORER_PAGE;
        render();
      });
      [fromInput, toInput, searchInput].forEach(element => element.addEventListener("input", () => { explorerLimit = EXPLORER_PAGE; }));
      document.querySelectorAll("#finishersTable th[data-sort]").forEach(header => {
        const button = header.querySelector("button");
        button.addEventListener("click", () => {
          const key = header.dataset.sort;
          explorerSort = { key, direction: explorerSort.key === key ? -explorerSort.direction : (key === "name" || key === "division" ? 1 : key === "year" ? -1 : 1) };
          render();
        });
      });
      document.getElementById("finishersBody").addEventListener("click", event => {
        const button = event.target.closest("[data-explorer-row]");
        if (!button) return;
        const row = document.getElementById("finishersBody").explorerRows?.[Number(button.dataset.explorerRow)];
        if (row) explorerShowAthlete(row);
      });
      athlete.addEventListener("click", event => {
        if (event.target.closest("#explorerAthleteClose")) {
          explorerSelected = null;
          renderExplorerAthlete();
          render();
          return;
        }
        const open = event.target.closest("[data-explorer-open]");
        if (!open) return;
        const [eventId, year, bib] = open.dataset.explorerOpen.split("|");
        const target = DATASETS[eventId]?.records.find(row => row.year === year && String(row.bib) === bib);
        if (!target) return;
        if (eventSelect.value !== eventId) {
          eventSelect.value = eventId;
          eventSelect.dispatchEvent(new Event("change"));
        }
        if (!compareYearVisible(year)) toggleCompareYear(year);
        fromInput.value = duration(target.overall);
        toInput.value = duration(target.overall);
        explorerFilters.gender = explorerFilters.division = explorerFilters.country = "";
        searchInput.value = "";
        populateExplorerFilters();
        explorerShowAthlete(target);
      });
      overview.addEventListener("click", event => {
        const bar = event.target.closest("[data-hist-from]");
        if (bar) {
          explorerDrill({ from: Number(bar.dataset.histFrom), to: Number(bar.dataset.histTo) });
          return;
        }
        const division = event.target.closest("[data-drill-division]");
        if (division) { explorerDrill({ division: division.dataset.drillDivision }); return; }
        const country = event.target.closest("[data-drill-country]");
        if (country) explorerDrill({ country: country.dataset.drillCountry });
      });
      overview.addEventListener("keydown", event => {
        const bar = event.target.closest("[data-hist-from]");
        if (bar && (event.key === "Enter" || event.key === " ")) {
          event.preventDefault();
          bar.dispatchEvent(new MouseEvent("click", { bubbles: true }));
        }
      });
      document.getElementById("overviewByGender").addEventListener("change", event => {
        explorerOverviewGender = event.target.checked;
        overview.querySelector(".overview-gender-legend").hidden = !explorerOverviewGender;
        renderExplorerOverview();
      });
      populateExplorerFilters();
      renderExplorerOverview();
    }
