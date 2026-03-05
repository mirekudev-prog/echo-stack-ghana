const API_URL = 'https://echo-stack-ghana.onrender.com/api/regions';

// All 16 Official Regions
const ghanaRegions = [
    "Upper West", "Upper East", "North East", "Northern", 
    "Savannah", "Bono", "Bono East", "Ahafo",
    "Ashanti", "Central", "Western", "Western North",
    "Eastern", "Volta", "Greater Accra", "Oti"
];

// Initialize Map On Page Load
document.addEventListener('DOMContentLoaded', () => {
    const mapContainer = document.getElementById('ghana-map-container');
    
    if (mapContainer) {
        // Display Real Ghana Map Image
        mapContainer.innerHTML = `
            <img src="/images/ghana-map.png" alt="Ghana Map" class="map-image">
            ${createHotspots()}
        `;
        
        addMapInteractions();
    } else {
        console.error('❌ mapContainer element not found!');
    }
});

function createHotspots() {
    return ghanaRegions.map((region, index) => {
        // REFINED positions based on visual map layout
        const positions = [
            {x: 8, y: 10, w: 15, h: 12},   // Upper West      ← Top-left area
            {x: 48, y: 8, w: 12, h: 10},   // Upper East      ← Top-center
            {x: 60, y: 12, w: 12, h: 10},  // North East      ← Top-right
            {x: 45, y: 22, w: 20, h: 15},  // Northern        ← Large central-top
            {x: 25, y: 30, w: 25, h: 18},  // Savannah        ← Left-center
            {x: 15, y: 45, w: 15, h: 14},  // Bono            ← Mid-left
            {x: 40, y: 48, w: 18, h: 14},  // Bono East       ← Center
            {x: 30, y: 56, w: 10, h: 10},  // Ahafo           ← Small, near Bono
            {x: 35, y: 65, w: 20, h: 14},  // Ashanti         ← Center-bottom
            {x: 48, y: 78, w: 15, h: 10},  // Central         ← South-center
            {x: 5, y: 65, w: 12, h: 18},   // Western         ← Bottom-left
            {x: 12, y: 60, w: 8, h: 10},   // Western North   ← Above Western
            {x: 65, y: 65, w: 18, h: 16},  // Eastern         ← Right side
            {x: 82, y: 55, w: 12, h: 30},  // Volta           ← Long eastern strip
            {x: 68, y: 82, w: 8, h: 8},    // Greater Accra   ← Small coastal
            {x: 55, y: 42, w: 10, h: 10}   // Oti             ← Between Eastern/Northern
        ];
        
        return `<div class="region-hotspot" data-region="${region}" 
                    style="left:${positions[index].x}%;top:${positions[index].y}%;width:${positions[index].w}%;height:${positions[index].h}%;"
                    title="Click ${region}"></div>`;
    }).join('');
}

function addMapInteractions() {
    document.querySelectorAll('.region-hotspot').forEach(hotspot => {
        hotspot.addEventListener('click', async (e) => {
            const regionName = e.target.getAttribute('data-region');
            
            console.log('✅ Clicked:', regionName);
            
            // Clear all highlights
            document.querySelectorAll('.region-hotspot').forEach(h => {
                h.classList.remove('selected');
                h.style.opacity = '0.3';
            });
            
            // Highlight selected
            e.target.classList.add('selected');
            e.target.style.opacity = '1';
            
            // Search for this region
            await filterRegions(regionName);
            
            // Scroll to results
            document.getElementById('regions-grid-section')?.scrollIntoView({ behavior: 'smooth' });
        });
        
        // Hover effects
        hotspot.addEventListener('mouseenter', () => {
            hotspot.style.opacity = '0.7';
        });
        
        hotspot.addEventListener('mouseleave', () => {
            if (!hotspot.classList.contains('selected')) {
                hotspot.style.opacity = '0.3';
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
        card.onclick = () => alert('Coming soon: ' + region.name + ' details page');
        
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
