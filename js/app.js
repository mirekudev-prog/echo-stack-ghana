const API_URL = 'https://echo-stack-ghana.onrender.com/api/regions';

// All 16 Official Regions with CENTER POINT positions
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
        // Circle center positions (X%, Y%) based on your map image
        const positions = [
            {x: 18, y: 25},   // Upper West      ← Top-left corner
            {x: 52, y: 15},   // Upper East      ← Top-center
            {x: 65, y: 18},   // North East      ← Top-right
            {x: 55, y: 30},   // Northern        ← Center-top (large region)
            {x: 35, y: 40},   // Savannah        ← Left-center
            {x: 22, y: 55},   // Bono            ← Mid-left
            {x: 45, y: 55},   // Bono East       ← Center
            {x: 32, y: 62},   // Ahafo           ← Small, near Bono
            {x: 42, y: 72},   // Ashanti         ← Center-bottom
            {x: 52, y: 85},   // Central         ← South-center
            {x: 12, y: 75},   // Western         ← Bottom-left
            {x: 18, y: 68},   // Western North   ← Above Western
            {x: 72, y: 72},   // Eastern         ← Right side
            {x: 88, y: 65},   // Volta           ← Long eastern strip
            {x: 70, y: 90},   // Greater Accra   ← Small coastal city
            {x: 58, y: 50}    // Oti             ← Between Eastern/Northern
        ];
        
        return `<div class="region-circle" data-region="${region}" 
                    style="left:${positions[index].x}%;top:${positions[index].y}%;"
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
                c.style.transform = 'scale(1)';
            });
            
            // Highlight selected
            e.currentTarget.classList.add('selected');
            e.currentTarget.style.transform = 'scale(1.5)';
            
            // Search for this region
            await filterRegions(regionName);
            
            // Scroll to results
            document.getElementById('regions-grid-section')?.scrollIntoView({ behavior: 'smooth' });
        });
        
        // Hover effects
        circle.addEventListener('mouseenter', () => {
            circle.style.transform = 'scale(1.2)';
            circle.querySelector('.circle-label').style.opacity = '1';
        });
        
        circle.addEventListener('mouseleave', () => {
            if (!circle.classList.contains('selected')) {
                circle.style.transform = 'scale(1)';
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

console.log('✅ Interactive circular hotspot map loaded!');
