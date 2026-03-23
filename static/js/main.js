/*
 * ============================================================================
 *   main.js  –  Healthcare Data Analysis  (Enhanced Edition)
 * ============================================================================
 *   • Dark mode toggle & persistence
 *   • Dashboard charts (doughnut + timeline)
 *   • Result page charts
 *   • Analytics page charts (6 chart types)
 *   • BMI Calculator & Health Score
 *   • Password strength meter
 *   • History search/filter
 *   • Scroll-to-top button
 *   • Flash message auto-dismiss
 * ============================================================================
 */

// ═══════════════════════════════════════════════════════════════════════════
//  SIDEBAR
// ═══════════════════════════════════════════════════════════════════════════
function openSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebar-overlay');
    if (sidebar) sidebar.classList.add('open');
    if (overlay) overlay.classList.add('active');
    document.body.style.overflow = 'hidden';
}
function closeSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebar-overlay');
    if (sidebar) sidebar.classList.remove('open');
    if (overlay) overlay.classList.remove('active');
    document.body.style.overflow = '';
}
document.addEventListener('keydown', e => { if (e.key === 'Escape') closeSidebar(); });

// ═══════════════════════════════════════════════════════════════════════════
//  DARK MODE
// ═══════════════════════════════════════════════════════════════════════════
function initDarkMode() {
    const saved = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', saved);
    updateThemeIcon(saved);
}

function toggleDarkMode() {
    const current = document.documentElement.getAttribute('data-theme');
    const next = current === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('theme', next);
    updateThemeIcon(next);
}

function updateThemeIcon(theme) {
    const btn = document.getElementById('theme-toggle-btn');
    if (btn) btn.textContent = theme === 'dark' ? '☀️' : '🌙';
}

// ═══════════════════════════════════════════════════════════════════════════
//  INIT ON DOM READY
// ═══════════════════════════════════════════════════════════════════════════
document.addEventListener('DOMContentLoaded', () => {
    initDarkMode();
    initFlashMessages();
    initBMICalculator();
    initLoadingOverlay();
    initPasswordStrength();
    initHistorySearch();
    initDiseaseSelector();
    initScrollTop();

    // Dashboard charts
    if (document.getElementById('riskPieChart')) {
        loadDashboardCharts();
    }

    // Analytics page
    if (document.getElementById('analyticsRiskChart')) {
        loadAnalyticsCharts();
    }

    // BMI Calculator page
    if (document.getElementById('bmiCalcForm')) {
        initBMICalcPage();
    }
});

// ═══════════════════════════════════════════════════════════════════════════
//  FLASH MESSAGES
// ═══════════════════════════════════════════════════════════════════════════
function initFlashMessages() {
    document.querySelectorAll('.alert').forEach(alert => {
        setTimeout(() => {
            alert.style.opacity = '0';
            alert.style.transform = 'translateY(-10px)';
            setTimeout(() => alert.remove(), 300);
        }, 6000);
    });
    document.querySelectorAll('.alert-close').forEach(btn => {
        btn.addEventListener('click', () => {
            const a = btn.closest('.alert');
            a.style.opacity = '0';
            a.style.transform = 'translateY(-10px)';
            setTimeout(() => a.remove(), 300);
        });
    });
}

function showToast(message, type = 'info') {
    let container = document.querySelector('.flash-messages');
    if (!container) {
        container = document.createElement('div');
        container.className = 'flash-messages';
        const main = document.querySelector('.container') || document.body;
        main.prepend(container);
    }
    const alert = document.createElement('div');
    alert.className = `alert alert-${type}`;
    alert.innerHTML = `${message} <button class="alert-close" onclick="this.closest('.alert').remove()">&times;</button>`;
    container.appendChild(alert);
    setTimeout(() => { alert.style.opacity = '0'; setTimeout(() => alert.remove(), 300); }, 5000);
}

// ═══════════════════════════════════════════════════════════════════════════
//  BMI AUTO-CALCULATOR (Health form)
// ═══════════════════════════════════════════════════════════════════════════
function initBMICalculator() {
    const h = document.getElementById('height');
    const w = document.getElementById('weight');
    const d = document.getElementById('bmi-display');
    if (h && w) {
        const calc = () => {
            const hv = parseFloat(h.value), wv = parseFloat(w.value);
            if (hv > 0 && wv > 0) {
                const bmi = (wv / ((hv / 100) ** 2)).toFixed(1);
                if (d) {
                    d.textContent = `BMI: ${bmi}`;
                    d.style.color = bmi > 30 ? '#dc3545' : bmi > 25 ? '#ffc107' : '#198754';
                }
            }
        };
        h.addEventListener('input', calc);
        w.addEventListener('input', calc);
    }
}

// ═══════════════════════════════════════════════════════════════════════════
//  LOADING OVERLAY
// ═══════════════════════════════════════════════════════════════════════════
function initLoadingOverlay() {
    const form = document.getElementById('health-form');
    if (form) {
        form.addEventListener('submit', (e) => {
            const age = document.getElementById('age');
            const bp = document.getElementById('blood_pressure');
            const sugar = document.getElementById('sugar_level');
            if (age && (age.value < 1 || age.value > 120)) { e.preventDefault(); showToast('Valid age: 1-120.', 'danger'); return; }
            if (bp && (bp.value < 60 || bp.value > 250)) { e.preventDefault(); showToast('Valid BP: 60-250.', 'danger'); return; }
            if (sugar && (sugar.value < 50 || sugar.value > 500)) { e.preventDefault(); showToast('Valid sugar: 50-500.', 'danger'); return; }
            showLoading('Analyzing your health data...');
        });
    }
}

function showLoading(msg = 'Processing...') {
    const o = document.createElement('div');
    o.className = 'loading-overlay'; o.id = 'loading-overlay';
    o.innerHTML = `<div class="spinner"></div><p class="loading-text">${msg}</p>`;
    document.body.appendChild(o);
}
function hideLoading() { const o = document.getElementById('loading-overlay'); if (o) o.remove(); }

// ═══════════════════════════════════════════════════════════════════════════
//  PASSWORD STRENGTH METER
// ═══════════════════════════════════════════════════════════════════════════
function initPasswordStrength() {
    const pw = document.getElementById('password');
    const meter = document.getElementById('password-strength');
    if (!pw || !meter) return;

    pw.addEventListener('input', () => {
        const val = pw.value;
        let score = 0;
        if (val.length >= 8)              score++;
        if (/[A-Z]/.test(val))            score++;
        if (/[a-z]/.test(val))            score++;
        if (/\d/.test(val))               score++;
        if (/[^a-zA-Z0-9]/.test(val))     score++;

        const classes = ['', 'strength-weak', 'strength-fair', 'strength-fair', 'strength-good', 'strength-strong'];
        const labels  = ['', 'Weak', 'Fair', 'Fair', 'Good', 'Strong'];
        const colors  = ['', '#dc3545', '#ffc107', '#ffc107', '#0dcaf0', '#198754'];

        meter.className = 'password-strength ' + (classes[score] || '');
        const text = meter.querySelector('.strength-text');
        if (text) { text.textContent = labels[score] || ''; text.style.color = colors[score] || ''; }
    });
}

// ═══════════════════════════════════════════════════════════════════════════
//  DISEASE TYPE SELECTOR (Health form)
// ═══════════════════════════════════════════════════════════════════════════
function initDiseaseSelector() {
    document.querySelectorAll('.disease-option').forEach(opt => {
        opt.addEventListener('click', () => {
            document.querySelectorAll('.disease-option').forEach(o => o.classList.remove('selected'));
            opt.classList.add('selected');
            opt.querySelector('input').checked = true;
        });
    });
}

// ═══════════════════════════════════════════════════════════════════════════
//  HISTORY SEARCH / FILTER
// ═══════════════════════════════════════════════════════════════════════════
function initHistorySearch() {
    const search = document.getElementById('history-search');
    const filter = document.getElementById('history-filter');
    const table  = document.querySelector('.data-table tbody');
    if (!search || !table) return;

    const doFilter = () => {
        const q = search.value.toLowerCase();
        const f = filter ? filter.value : 'all';
        table.querySelectorAll('tr').forEach(row => {
            const text   = row.textContent.toLowerCase();
            const result = row.querySelector('.badge') ? row.querySelector('.badge').textContent.trim() : '';
            const matchQ = !q || text.includes(q);
            const matchF = f === 'all' || result.toLowerCase().includes(f.toLowerCase());
            row.style.display = (matchQ && matchF) ? '' : 'none';
        });
    };
    search.addEventListener('input', doFilter);
    if (filter) filter.addEventListener('change', doFilter);
}

// ═══════════════════════════════════════════════════════════════════════════
//  SCROLL-TO-TOP
// ═══════════════════════════════════════════════════════════════════════════
function initScrollTop() {
    const btn = document.getElementById('scroll-top-btn');
    if (!btn) return;
    window.addEventListener('scroll', () => {
        btn.classList.toggle('visible', window.scrollY > 300);
    });
    btn.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));
}

// ═══════════════════════════════════════════════════════════════════════════
//  DASHBOARD CHARTS
// ═══════════════════════════════════════════════════════════════════════════
async function loadDashboardCharts() {
    try {
        const res = await fetch('/api/chart-data');
        if (!res.ok) return;
        const data = await res.json();
        const colors = getChartColors();

        // Risk pie
        const pie = document.getElementById('riskPieChart');
        if (pie && data.risk_distribution) {
            new Chart(pie.getContext('2d'), {
                type: 'doughnut',
                data: {
                    labels: ['Low Risk', 'High Risk'],
                    datasets: [{ data: [data.risk_distribution.low, data.risk_distribution.high],
                        backgroundColor: ['#198754', '#dc3545'], borderWidth: 2, borderColor: colors.bg }]
                },
                options: { responsive: true, maintainAspectRatio: false,
                    plugins: { legend: { position: 'bottom', labels: { padding: 20, font: { size: 13 }, color: colors.text } } }, cutout: '65%' }
            });
        }

        // Timeline
        const line = document.getElementById('timelineChart');
        if (line && data.timeline && data.timeline.length > 0) {
            new Chart(line.getContext('2d'), {
                type: 'line',
                data: {
                    labels: data.timeline.map(d => d.date),
                    datasets: [{
                        label: 'Risk Probability (%)', data: data.timeline.map(d => d.probability),
                        borderColor: '#0d6efd', backgroundColor: 'rgba(13,110,253,0.1)', fill: true,
                        tension: 0.4,
                        pointBackgroundColor: data.timeline.map(d => d.result === 'High Risk' ? '#dc3545' : '#198754'),
                        pointRadius: 6, pointHoverRadius: 8
                    }]
                },
                options: {
                    responsive: true, maintainAspectRatio: false,
                    scales: {
                        y: { beginAtZero: true, max: 100, title: { display: true, text: 'Probability (%)', color: colors.text }, ticks: { color: colors.text }, grid: { color: colors.grid } },
                        x: { title: { display: true, text: 'Date', color: colors.text }, ticks: { color: colors.text }, grid: { color: colors.grid } }
                    },
                    plugins: { legend: { display: true, position: 'top', labels: { color: colors.text } } }
                }
            });
        }
    } catch (e) { console.error('Chart error:', e); }
}

// ═══════════════════════════════════════════════════════════════════════════
//  RESULT PAGE CHARTS
// ═══════════════════════════════════════════════════════════════════════════
function initResultCharts(inputData, probability, result) {
    const colors = getChartColors();

    const riskCtx = document.getElementById('resultRiskChart');
    if (riskCtx) {
        new Chart(riskCtx.getContext('2d'), {
            type: 'doughnut',
            data: {
                labels: ['Risk', 'Safe'],
                datasets: [{ data: [probability, 100 - probability],
                    backgroundColor: [result === 'High Risk' ? '#dc3545' : '#198754', colors.grid], borderWidth: 0 }]
            },
            options: { responsive: true, maintainAspectRatio: false, cutout: '70%',
                plugins: { legend: { position: 'bottom', labels: { color: colors.text } } } }
        });
    }

    const barCtx = document.getElementById('resultBarChart');
    if (barCtx) {
        new Chart(barCtx.getContext('2d'), {
            type: 'bar',
            data: {
                labels: ['Age', 'Blood Pressure', 'Sugar Level', 'BMI'],
                datasets: [{
                    label: 'Your Values',
                    data: [inputData.age || 0, inputData.blood_pressure || 0, inputData.sugar_level || 0, inputData.bmi || 0],
                    backgroundColor: ['rgba(13,110,253,0.7)', 'rgba(220,53,69,0.7)', 'rgba(255,193,7,0.7)', 'rgba(25,135,84,0.7)'],
                    borderColor: ['#0d6efd', '#dc3545', '#ffc107', '#198754'], borderWidth: 2, borderRadius: 6
                }, {
                    label: 'Normal Range',
                    data: [50, 120, 100, 24],
                    backgroundColor: 'rgba(108,117,125,0.2)', borderColor: '#6c757d', borderWidth: 1, borderRadius: 6
                }]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                scales: { y: { beginAtZero: true, title: { display: true, text: 'Value', color: colors.text }, ticks: { color: colors.text }, grid: { color: colors.grid } },
                    x: { ticks: { color: colors.text }, grid: { color: colors.grid } } },
                plugins: { legend: { position: 'top', labels: { color: colors.text } } }
            }
        });
    }
}

// ═══════════════════════════════════════════════════════════════════════════
//  ANALYTICS PAGE CHARTS
// ═══════════════════════════════════════════════════════════════════════════
async function loadAnalyticsCharts() {
    try {
        const res = await fetch('/api/analytics-data');
        if (!res.ok) return;
        const data = await res.json();
        if (data.empty) return;
        const c = getChartColors();

        // Update stat values
        const setVal = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
        setVal('stat-total', data.total_records);
        setVal('stat-avg-bp', data.averages.bp);
        setVal('stat-avg-sugar', data.averages.sugar);
        setVal('stat-avg-bmi', data.averages.bmi);
        setVal('stat-avg-score', data.averages.score);

        // 1) Risk distribution pie
        const pie = document.getElementById('analyticsRiskChart');
        if (pie) {
            new Chart(pie.getContext('2d'), {
                type: 'doughnut',
                data: { labels: ['Low Risk', 'High Risk'],
                    datasets: [{ data: [data.risk_distribution.low, data.risk_distribution.high],
                        backgroundColor: ['#198754', '#dc3545'], borderWidth: 2, borderColor: c.bg }] },
                options: { responsive: true, maintainAspectRatio: false, cutout: '60%',
                    plugins: { legend: { position: 'bottom', labels: { color: c.text, padding: 16 } } } }
            });
        }

        // 2) Blood Pressure Trend
        const bpCtx = document.getElementById('analyticsBPChart');
        if (bpCtx && data.bp_trend.length) {
            new Chart(bpCtx.getContext('2d'), {
                type: 'line',
                data: { labels: data.bp_trend.map(d => d.date),
                    datasets: [{
                        label: 'Blood Pressure', data: data.bp_trend.map(d => d.value),
                        borderColor: '#dc3545', backgroundColor: 'rgba(220,53,69,0.1)', fill: true, tension: 0.4, pointRadius: 4
                    }, {
                        label: 'Normal (120)', data: Array(data.bp_trend.length).fill(120),
                        borderColor: '#6c757d', borderDash: [5, 5], pointRadius: 0, fill: false
                    }]
                },
                options: chartLineOptions(c, 'mm Hg')
            });
        }

        // 3) Sugar Level Trend
        const sugarCtx = document.getElementById('analyticsSugarChart');
        if (sugarCtx && data.sugar_trend.length) {
            new Chart(sugarCtx.getContext('2d'), {
                type: 'line',
                data: { labels: data.sugar_trend.map(d => d.date),
                    datasets: [{
                        label: 'Sugar Level', data: data.sugar_trend.map(d => d.value),
                        borderColor: '#ffc107', backgroundColor: 'rgba(255,193,7,0.1)', fill: true, tension: 0.4, pointRadius: 4
                    }, {
                        label: 'Normal (100)', data: Array(data.sugar_trend.length).fill(100),
                        borderColor: '#6c757d', borderDash: [5, 5], pointRadius: 0, fill: false
                    }]
                },
                options: chartLineOptions(c, 'mg/dl')
            });
        }

        // 4) BMI Trend
        const bmiCtx = document.getElementById('analyticsBMIChart');
        if (bmiCtx && data.bmi_trend.length) {
            new Chart(bmiCtx.getContext('2d'), {
                type: 'line',
                data: { labels: data.bmi_trend.map(d => d.date),
                    datasets: [{
                        label: 'BMI', data: data.bmi_trend.map(d => d.value),
                        borderColor: '#198754', backgroundColor: 'rgba(25,135,84,0.1)', fill: true, tension: 0.4, pointRadius: 4
                    }, {
                        label: 'Normal (24)', data: Array(data.bmi_trend.length).fill(24),
                        borderColor: '#6c757d', borderDash: [5, 5], pointRadius: 0, fill: false
                    }]
                },
                options: chartLineOptions(c, 'BMI')
            });
        }

        // 5) Health Score Trend
        const scoreCtx = document.getElementById('analyticsScoreChart');
        if (scoreCtx && data.score_trend.length) {
            new Chart(scoreCtx.getContext('2d'), {
                type: 'bar',
                data: { labels: data.score_trend.map(d => d.date),
                    datasets: [{
                        label: 'Health Score', data: data.score_trend.map(d => d.value),
                        backgroundColor: data.score_trend.map(d =>
                            d.value >= 80 ? 'rgba(25,135,84,0.7)' :
                            d.value >= 60 ? 'rgba(13,110,253,0.7)' :
                            d.value >= 40 ? 'rgba(255,193,7,0.7)' : 'rgba(220,53,69,0.7)'
                        ),
                        borderRadius: 6
                    }]
                },
                options: {
                    responsive: true, maintainAspectRatio: false,
                    scales: { y: { beginAtZero: true, max: 100, title: { display: true, text: 'Score', color: c.text }, ticks: { color: c.text }, grid: { color: c.grid } },
                        x: { ticks: { color: c.text }, grid: { color: c.grid } } },
                    plugins: { legend: { labels: { color: c.text } } }
                }
            });
        }

        // 6) Lifestyle Radar
        const lifeCtx = document.getElementById('analyticsLifestyleChart');
        if (lifeCtx && data.lifestyle) {
            const l = data.lifestyle;
            new Chart(lifeCtx.getContext('2d'), {
                type: 'radar',
                data: {
                    labels: ['Smoking', 'Exercise', 'Alcohol', 'Healthy BP', 'Healthy Sugar'],
                    datasets: [{
                        label: 'Your Profile',
                        data: [
                            Math.round(l.smoking / l.total * 100),
                            Math.round(l.exercise / l.total * 100),
                            Math.round(l.alcohol / l.total * 100),
                            Math.round((data.averages.bp <= 130 ? 80 : data.averages.bp <= 140 ? 50 : 20)),
                            Math.round((data.averages.sugar <= 110 ? 80 : data.averages.sugar <= 140 ? 50 : 20))
                        ],
                        backgroundColor: 'rgba(13,110,253,0.15)',
                        borderColor: '#0d6efd', pointBackgroundColor: '#0d6efd'
                    }]
                },
                options: {
                    responsive: true, maintainAspectRatio: false,
                    scales: { r: { beginAtZero: true, max: 100, ticks: { color: c.text }, grid: { color: c.grid }, pointLabels: { color: c.text } } },
                    plugins: { legend: { labels: { color: c.text } } }
                }
            });
        }

    } catch (e) { console.error('Analytics error:', e); }
}

function chartLineOptions(c, yLabel) {
    return {
        responsive: true, maintainAspectRatio: false,
        scales: {
            y: { beginAtZero: false, title: { display: true, text: yLabel, color: c.text }, ticks: { color: c.text }, grid: { color: c.grid } },
            x: { ticks: { color: c.text, maxRotation: 45 }, grid: { color: c.grid } }
        },
        plugins: { legend: { position: 'top', labels: { color: c.text } } }
    };
}

// ═══════════════════════════════════════════════════════════════════════════
//  BMI CALCULATOR PAGE
// ═══════════════════════════════════════════════════════════════════════════
function initBMICalcPage() {
    const form = document.getElementById('bmiCalcForm');
    form.addEventListener('submit', (e) => {
        e.preventDefault();
        const height = parseFloat(document.getElementById('calc-height').value);
        const weight = parseFloat(document.getElementById('calc-weight').value);
        const age    = parseInt(document.getElementById('calc-age').value) || 30;
        const bp     = parseInt(document.getElementById('calc-bp').value) || 120;
        const sugar  = parseInt(document.getElementById('calc-sugar').value) || 100;
        const smoking  = document.getElementById('calc-smoking')?.checked;
        const exercise = document.getElementById('calc-exercise')?.checked;
        const alcohol  = document.getElementById('calc-alcohol')?.checked;

        if (!height || !weight || height <= 0 || weight <= 0) {
            showToast('Please enter valid height and weight.', 'danger');
            return;
        }

        const bmi = (weight / ((height / 100) ** 2)).toFixed(1);
        let cat, color;
        if (bmi < 18.5) { cat = 'Underweight'; color = '#0dcaf0'; }
        else if (bmi < 25) { cat = 'Normal Weight'; color = '#198754'; }
        else if (bmi < 30) { cat = 'Overweight'; color = '#ffc107'; }
        else { cat = 'Obese'; color = '#dc3545'; }

        document.getElementById('bmi-result-value').textContent = bmi;
        document.getElementById('bmi-result-value').style.color = color;
        document.getElementById('bmi-result-category').textContent = cat;
        document.getElementById('bmi-result-category').style.color = color;
        document.getElementById('bmi-result-section').style.display = 'block';

        // BMI indicator position
        const indicator = document.getElementById('bmi-indicator');
        if (indicator) {
            const pct = Math.min(100, Math.max(0, (bmi - 10) / 35 * 100));
            indicator.style.left = pct + '%';
        }

        // Health score via API
        const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;
        fetch('/api/health-score', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrfToken || '' },
            body: JSON.stringify({ age, blood_pressure: bp, sugar_level: sugar, bmi: parseFloat(bmi), smoking, exercise, alcohol })
        })
        .then(r => r.json())
        .then(d => {
            document.getElementById('health-score-value').textContent = d.score;
            document.getElementById('health-score-grade').textContent = d.grade + ' – ' + d.description;
            const sc = document.getElementById('health-score-circle');
            if (sc) {
                sc.className = 'score-circle ' + (d.score >= 80 ? 'excellent' : d.score >= 60 ? 'good' : d.score >= 40 ? 'fair' : 'poor');
            }
            document.getElementById('health-score-section').style.display = 'block';
        })
        .catch(e => console.error('Health score error:', e));
    });
}

// ═══════════════════════════════════════════════════════════════════════════
//  SYMPTOM CHIPS - Interactive Selection Styling
// ═══════════════════════════════════════════════════════════════════════════
function initSymptomChips() {
    const chips = document.querySelectorAll('.symptom-chip');
    
    chips.forEach(chip => {
        const checkbox = chip.querySelector('input[type="checkbox"]');
        
        if (checkbox) {
            // Apply checked state on page load
            if (checkbox.checked) {
                chip.classList.add('checked');
            }
            
            // Handle change events
            checkbox.addEventListener('change', function() {
                if (this.checked) {
                    chip.classList.add('checked');
                } else {
                    chip.classList.remove('checked');
                }
            });
            
            // Handle keyboard interaction
            chip.addEventListener('keydown', function(e) {
                if (e.code === 'Space' || e.code === 'Enter') {
                    e.preventDefault();
                    checkbox.checked = !checkbox.checked;
                    checkbox.dispatchEvent(new Event('change'));
                    chip.focus();
                }
            });
        }
    });
}

// Initialize symptom chips when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initSymptomChips);
} else {
    initSymptomChips();
}

// ═══════════════════════════════════════════════════════════════════════════
//  UTILITY: Chart color helper for dark mode
// ═══════════════════════════════════════════════════════════════════════════
function getChartColors() {
    const dark = document.documentElement.getAttribute('data-theme') === 'dark';
    return {
        text: dark ? '#a8adb5' : '#212529',
        grid: dark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)',
        bg:   dark ? '#22262d' : '#ffffff'
    };
}

// ═══════════════════════════════════════════════════════════════════════════
//  SMOOTH SCROLLING
// ═══════════════════════════════════════════════════════════════════════════
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const t = document.querySelector(this.getAttribute('href'));
        if (t) t.scrollIntoView({ behavior: 'smooth' });
    });
});
