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
    }
});

function createHotspots() {
    return ghanaRegions.map((region, index) => {
        // Approximate positions (adjust based on your image size)
        const positions = [
            {x: 15, y: 15},   // Upper West
            {x: 35, y: 12},   // Upper East
            {x: 55, y: 15},   // North East
            {x: 40, y: 25},   // Northern
            {x: 25, y: 32},   // Savannah
            {x: 22, y: 48},   // Bono
            {x: 45, y: 48},   // Bono East
            {x: 30, y: 55},   // Ahafo
            {x: 42, y: 65},   // Ashanti
            {x: 45, y: 75},   // Central
            {x: 18, y: 68},   // Western
            {x: 22, y: 62},   // Western North
            {x: 65, y: 65},   // Eastern
            {x: 85, y: 60},   // Volta
            {x: 68, y: 80},   // Greater Accra
            {x: 72, y: 48}    // Oti
        ];
        
        return `<div class="region-hotspot" data-region="${region}" 
                    style="left:${positions[index].x}%;top:${positions[index].y}%;"
                    title="${region}"></div>`;
    }).join('');
}

function addMapInteractions() {
    document.querySelectorAll('.region-hotspot').forEach(hotspot => {
        hotspot.addEventListener('click', () => {
            const regionName = hotspot.getAttribute('data-region');
            
            // Highlight hotspot
            document.querySelectorAll('.region-hotspot').forEach(h => h.style.opacity = '0');
            hotspot.style.opacity = '1';
            
            // Search for region
            filterRegions(regionName);
        });
    });
}

// Load Regions Data
async function loadRegions(showAll = false) {
    try {
        const response = await fetch(API_URL);
        const regions = await response.json();
        
        if (showAll && regions.length > 0) {
            renderRegions(regions);
        } else {
            document.getElementById('regions-grid-section').style.display = 'none';
        }
    } catch (error) {
        console.error('Error loading regions:', error);
    }
}

function renderRegions(regions) {
    const section = document.getElementById('regions-grid-section');
    const grid = document.getElementById('regions-grid');
    
    section.style.display = 'block';
    grid.innerHTML = '';
    
    if (!regions || regions.length === 0) {
        grid.innerHTML = '<p>No regions found.</p>';
        return;
    }
    
    regions.forEach(region => {
        const card = document.createElement('div');
        card.className = 'region-card';
        card.onclick = () => window.location.href = `/regions/${region.name.toLowerCase().replace(/\s+/g, '-')}.html`;
        
        card.innerHTML = `
            <h3>${region.name}</h3>
            <p>${region.overview || 'Click to explore...'}</p>
        `;
        
        grid.appendChild(card);
    });
}

// Search Functionality
document.getElementById('search-bar').addEventListener('input', async function(e) {
    const searchTerm = e.target.value.trim();
    
    if (searchTerm.length >= 2) {
        await filterRegions(searchTerm);
    } else {
        document.getElementById('regions-grid-section').style.display = 'none';
    }
});

async function filterRegions(term) {
    try {
        const response = await fetch(API_URL);
        const allRegions = await response.json();
        const filtered = allRegions.filter(r => 
            r.name.toLowerCase().includes(term.toLowerCase()) ||
            (r.overview && r.overview.toLowerCase().includes(term.toLowerCase()))
        );
        renderRegions(filtered);
    } catch (error) {
        console.error('Filter error:', error);
    }
}
