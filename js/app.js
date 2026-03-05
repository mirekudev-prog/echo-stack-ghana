const API_URL = 'https://echo-stack-ghana.onrender.com/api/regions';

// All 16 Official Regions with PINPOINT CENTER positions
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
        // REFINED PINPOINT positions - each circle in CENTER of region
        const positions = [
            {x: 20, y: 30},   // Upper West      ← Top-left green region
            {x: 55, y: 18},   // Upper East      ← Top-right grey region  
            {x: 68, y: 22},   // North East      ← Purple top-right corner
            {x: 62, y: 35},   // Northern        ← Brown large center-top
            {x: 38, y: 45},   // Savannah        ← Pink left-center
            {x: 25, y: 60},   // Bono            ← Orange mid-left
            {x: 50, y: 58},   // Bono East       ← Green center
            {x: 38, y: 68},   // Ahafo           ← Dark blue small area
            {x: 48, y: 78},   // Ashanti         ← Light blue bottom-center
            {x: 58, y: 92},   // Central         ← Light green south
            {x: 15, y: 85},   // Western         ← Blue bottom-left corner
            {x: 22, y: 75},   // Western North   ← Light blue above Western
            {x: 72, y: 80},   // Eastern         ← Red right-bottom area
            {x: 90, y: 70},   // Volta           ← Yellow-green far right
            {x: 75, y: 95},   // Greater Accra   ← Purple tiny coastal spot
            {x: 62, y: 55}    // Oti             ← Pink between Eastern/Northern
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
                c.style.transform = 'translate(-50%, -50%) scale(1)';
            });
            
            // Highlight selected
            e.currentTarget.classList.add('selected');
            e.currentTarget.style.transform = 'translate(-50%, -50%) scale(1.3)';
            
            // Search for this region
            await filterRegions(regionName);
            
            // Scroll to results
            document.getElementById('regions-grid-section')?.scrollIntoView({ behavior: 'smooth' });
        });
        
        // Hover effects
        circle.addEventListener('mouseenter', () => {
            circle.style.transform = 'translate(-50%, -50%) scale(1.2)';
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

console.log('✅ Interactive pin-point map loaded!');
