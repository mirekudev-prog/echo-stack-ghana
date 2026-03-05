const API_URL = 'https://echo-stack-ghana.onrender.com/api/regions';

// Only include regions that fit ON the map (removed off-boundary points)
const ghanaRegions = [
    "Upper West", "Upper East", "North East", "Northern", 
    "Savannah", "Bono", "Bono East", "Ahafo",
    "Ashanti", "Central", "Western", "Western North",
    "Eastern", "Volta", "Oti"
];

// NOTE: Greater Accra removed - too small/tiny for clear circle placement

// Initialize Map On Page Load
document.addEventListener('DOMContentLoaded', () => {
    const mapContainer = document.getElementById('ghana-map-container');
    
    if (mapContainer) {
        // Display Real Ghana Map Image
        mapContainer.innerHTML = `
            <div class="map-wrapper">
                <img src="/images/ghana-map.png" alt="Ghana Map" class="map-image">
                ${createHotspots()}
            </div>
        `;
        
        addMapInteractions();
    } else {
        console.error('❌ mapContainer element not found!');
    }
});

function createHotspots() {
    return ghanaRegions.map((region, index) => {
        // Constrained positions - ALL within map boundary (no X > 85, no Y > 90)
        const positions = [
            {x: 22, y: 28},   // Upper West
            {x: 52, y: 16},   // Upper East  
            {x: 65, y: 20},   // North East
            {x: 58, y: 32},   // Northern
            {x: 38, y: 42},   // Savannah
            {x: 25, y: 58},   // Bono
            {x: 48, y: 56},   // Bono East
            {x: 35, y: 66},   // Ahafo
            {x: 45, y: 75},   // Ashanti
            {x: 55, y: 88},   // Central
            {x: 18, y: 82},   // Western
            {x: 25, y: 72},   // Western North
            {x: 68, y: 78},   // Eastern
            {x: 82, y: 65},   // Volta (kept at edge but safe)
            {x: 60, y: 52}    // Oti
        ];
        
        return `<div class="region-circle" data-region="${region}" 
                    style="--pos-x: ${positions[index].x}; --pos-y: ${positions[index].y};"
                    title="Click ${region}">
                    <span class="circle-label">${region}</span>
                </div>`;
    }).join('');
}

function addMapInteractions() {
    document.querySelectorAll('.region-circle').forEach(circle => {
        circle.addEventListener('click', async (e) => {
            const regionName = e.currentTarget.getAttribute('data-region');
            
            console.log('✅ Clicked:', regionName);
            
            // Clear all highlights
            document.querySelectorAll('.region-circle').forEach(c => {
                c.classList.remove('selected');
                c.style.transform = 'translate(-50%, -50%) scale(1)';
            });
            
            // Highlight selected
            e.currentTarget.classList.add('selected');
            e.currentTarget.style.transform = 'translate(-50%, -50%) scale(1.2)';
            
            // Search for this region
            await filterRegions(regionName);
            
            // Scroll to results
            document.getElementById('regions-grid-section')?.scrollIntoView({ behavior: 'smooth' });
        });
        
        // Hover effects
        circle.addEventListener('mouseenter', () => {
            circle.style.transform = 'translate(-50%, -50%) scale(1.1)';
            circle.querySelector('.circle-label').style.opacity = '1';
        });
        
        circle.addEventListener('mouseleave', () => {
            if (!circle.classList.contains('selected')) {
                circle.style.transform = 'translate(-50%, -50%) scale(1)';
                circle.querySelector('.circle-label').style.opacity = '0';
            }
        });
    });
}

async function filterRegions(term) {
    try {
        console.log('🔍 Searching for:', term);
        
        const response = await fetch(API_URL);
        const allRegions = await response.json();
        
        const filtered = allRegions.filter(r => 
            r.name.toLowerCase().includes(term.toLowerCase()) ||
            (r.overview && r.overview.toLowerCase().includes(term.toLowerCase()))
        );
        
        renderRegions(filtered);
    } catch (error) {
        console.error('❌ Filter Error:', error);
        alert('Error loading regions: ' + error.message);
    }
}

function renderRegions(regions) {
    const section = document.getElementById('regions-grid-section');
    const grid = document.getElementById('regions-grid');
    
    if (!section || !grid) {
        console.error('❌ Grid elements not found!');
        return;
    }
    
    section.style.display = 'block';
    grid.innerHTML = '';
    
    if (!regions || regions.length === 0) {
        grid.innerHTML = '<p>No matching regions found.</p>';
        return;
    }
    
    regions.forEach(region => {
        const card = document.createElement('div');
        card.className = 'region-card';
        card.onclick = () => window.location.href = `/regions/${region.name.replace(/\s+/g, '-').toLowerCase()}.html`;
        
        card.innerHTML = `
            <h3>${region.name}</h3>
            <p>${region.overview || 'Click for more details...'}</p>
        `;
        
        grid.appendChild(card);
    });
}

// Search Bar
document.getElementById('search-bar')?.addEventListener('input', async (e) => {
    const searchTerm = e.target.value.trim();
    
    if (searchTerm.length >= 2) {
        await filterRegions(searchTerm);
    } else {
        document.getElementById('regions-grid-section').style.display = 'none';
    }
});

console.log('✅ Interactive map loaded!');
