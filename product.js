// API_BASE is inherited from index.js

document.addEventListener('DOMContentLoaded', async () => {
    const urlParams = new URLSearchParams(window.location.search);
    const productId = urlParams.get('id');

    if (!productId) {
        document.getElementById('pdpTitle').textContent = 'Product Not Found';
        document.getElementById('pdpTitle').classList.remove('skeleton');
        document.querySelector('.pdp-price-card').style.display = 'none';
        document.querySelector('.pdp-chart-section').style.display = 'none';
        document.querySelector('.pdp-actions').style.display = 'none';
        return;
    }

    await loadProductDetails(productId);
});

async function loadProductDetails(id) {
    try {
        const res = await fetch(`${API_BASE}/products/${id}`);
        if (!res.ok) throw new Error('Product not found');
        
        const p = await res.json();

        // Update basic info and remove skeletons
        document.title = `${p.title} – TheMaskMan`;
        
        const titleEl = document.getElementById('pdpTitle');
        titleEl.textContent = p.title;
        titleEl.classList.remove('skeleton');
        
        const descEl = document.getElementById('pdpDesc');
        descEl.textContent = p.description || 'Premium deal with real-time price monitoring and historical analysis.';
        descEl.classList.remove('skeleton');
        
        const catEl = document.getElementById('pdpCat');
        catEl.textContent = p.category;
        catEl.classList.remove('skeleton');

        // Price Formatting
        const priceEl = document.getElementById('pdpPrice');
        priceEl.textContent = p.price_new || 'N/A';
        priceEl.classList.remove('skeleton');
        
        if (p.price_old) {
            document.getElementById('pdpMrp').textContent = p.price_old;
        }
        
        const discEl = document.getElementById('pdpDisc');
        if (p.price_discount && p.price_discount !== '0% OFF') {
            discEl.textContent = p.price_discount;
            discEl.style.display = 'inline-flex';
        }

        // Deal Button
        const dealBtn = document.getElementById('pdpDealBtn');
        dealBtn.href = p.deal_url || '#';
        dealBtn.classList.remove('skeleton');
        
        // Lowest Price Badge
        const lowestBadge = document.getElementById('pdpLowestBadge');
        if (p.lowest_price && p.price_new && p.price_new.includes(parseFloat(p.lowest_price).toLocaleString('en-IN'))) {
            lowestBadge.style.display = 'inline-flex';
        }

        // Setup Main Image
        const mainImg = document.getElementById('mainImg');
        const imgWrap = document.getElementById('mainImgWrap');
        mainImg.src = p.image_src || 'https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=600&q=80';
        mainImg.onload = () => imgWrap.classList.remove('skeleton');
        
        // Render gallery
        const gallery = [p.image_src, ...(p.image_gallery || [])].filter(Boolean).slice(0, 6);
        const galleryContainer = document.getElementById('gallery');
        
        if (gallery.length > 0) {
            galleryContainer.innerHTML = gallery.map((img, i) => `
                <img src="${img}" class="pdp-thumb ${i === 0 ? 'active' : ''}" 
                     onclick="document.getElementById('mainImg').src='${img}'; document.querySelectorAll('.pdp-thumb').forEach(t=>t.classList.remove('active')); this.classList.add('active');"
                     onerror="this.style.display='none'"/>
            `).join('');
        } else {
            galleryContainer.style.display = 'none';
        }

        // Load Chart
        await loadResponsiveChart(id);

    } catch (error) {
        console.error('Error loading product:', error);
        document.getElementById('pdpTitle').textContent = 'Product Not Found';
        document.getElementById('pdpTitle').classList.remove('skeleton');
        document.querySelector('.pdp-price-card').style.display = 'none';
        document.querySelector('.pdp-chart-section').style.display = 'none';
        document.querySelector('.pdp-actions').style.display = 'none';
        document.getElementById('mainImgWrap').classList.remove('skeleton');
    }
}

async function loadResponsiveChart(productId) {
    const canvas = document.getElementById('pdpChart');
    const container = document.getElementById('chartTarget');
    
    // Set height based on width
    function updateChartSize() {
        if (!container) return;
        const width = container.offsetWidth;
        let height = width * 0.45;
        if (width < 600) height = width * 0.7;
        container.style.height = height + 'px';
    }
    
    updateChartSize();
    window.addEventListener('resize', updateChartSize);

    try {
        const res = await fetch(`${API_BASE}/products/${productId}/price-history`);
        if (!res.ok) throw new Error('History fetch failed');
        const data = await res.json();

        container.classList.remove('skeleton');

        if (!data || data.length < 2) {
            document.getElementById('pdpStatus').textContent = 'Insufficient data';
            document.getElementById('pdpStatus').style.background = 'rgba(255,255,255,0.05)';
            return;
        }

        const mn = Math.min(...data.map(d => d.price));
        const mx = Math.max(...data.map(d => d.price));

        new Chart(canvas, {
            type: 'line',
            data: {
                labels: data.map(d => d.date),
                datasets: [{
                    data: data.map(d => d.price),
                    borderColor: '#A3FF12', // Gold standard accent
                    backgroundColor: ctx => {
                        const c = ctx.chart.ctx.canvas;
                        const g = ctx.chart.ctx.createLinearGradient(0, 0, 0, c.height);
                        g.addColorStop(0, 'rgba(163, 255, 18, 0.4)');
                        g.addColorStop(1, 'rgba(163, 255, 18, 0.0)');
                        return g;
                    },
                    borderWidth: 3,
                    pointRadius: 0,
                    pointHoverRadius: 6,
                    pointBackgroundColor: '#A3FF12',
                    pointBorderColor: '#0a0a0a',
                    pointBorderWidth: 2,
                    fill: true,
                    tension: 0.4 // Smooth curves
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    intersect: false,
                    mode: 'index',
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: 'rgba(10,10,10,0.95)',
                        borderColor: '#A3FF12',
                        borderWidth: 1,
                        padding: 16,
                        titleFont: { size: 13, weight: '600', family: 'Inter' },
                        titleColor: '#888',
                        bodyFont: { size: 16, weight: '800', family: 'JetBrains Mono' },
                        bodyColor: '#A3FF12',
                        displayColors: false,
                        callbacks: {
                            label: ctx => '₹' + ctx.parsed.y.toLocaleString('en-IN'),
                            title: items => {
                                const d = new Date(items[0].label);
                                return d.toLocaleDateString('en-US', { day: 'numeric', month: 'short', year: 'numeric' });
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        ticks: { color: '#666', font: { size: 11, family: 'Inter' }, maxTicksLimit: 6, maxRotation: 0 },
                        grid: { display: false },
                        border: { display: false }
                    },
                    y: {
                        ticks: { 
                            color: '#666', 
                            font: { size: 11, family: 'Inter' },
                            callback: v => '₹' + (v >= 1000 ? (v/1000).toFixed(1) + 'k' : v)
                        },
                        grid: { color: 'rgba(255,255,255,0.05)', drawTicks: false },
                        border: { display: false },
                        min: Math.max(0, Math.floor(mn * 0.95)),
                        max: Math.ceil(mx * 1.05)
                    }
                }
            }
        });

    } catch (error) {
        console.error('Error loading chart:', error);
        container.classList.remove('skeleton');
        document.getElementById('pdpStatus').textContent = 'Analysis Unavailable';
    }
}
