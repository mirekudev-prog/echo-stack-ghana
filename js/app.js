const API_URL = 'https://echo-stack-ghana.onrender.com/api/regions';

// All 16 Official Regions
const ghanaRegions = [
    "Upper West", "Upper East", "North East", "Northern", 
    "Savannah", "Bono", "Bono East", "Ahafo",
    "Ashanti", "Central", "Western", "Western North",
    "Eastern", "Volta", "Greater Accra", "Oti"
];

// DEBUG: Test API Connection First
console.log('🧪 Testing API...');
fetch(API_URL)
    .then(response => response.json())
    .then(data => {
        console.log('✅ API Connected! Got', data.length, 'regions:', data);
    })
    .catch(error => {
        console.error('❌ API Error:', error);
        alert('API Connection Failed! Check your database.');
    });

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
        // Position percentages (will adjust after seeing real results)
        const positions = [
            {x: 10, y: 12},   // Upper West
            {x: 45, y: 8},    // Upper East
            {x: 58, y: 12},   // North East
            {x: 45, y: 25},   // Northern
            {x: 28, y: 30},   // Savannah
            {x: 20, y: 48},   // Bono
            {x: 50, y: 48},   // Bono East
            {x: 32, y: 58},   // Ahafo
            {x: 42, y: 68},   // Ashanti
            {x: 48, y: 80},   // Central
            {x: 15, y: 70},   // Western
            {x: 22, y: 65},   // Western North
            {x: 68, y: 68},   // Eastern
            {x: 85, y: 60},   // Volta
            {x: 68, y: 85},   // Greater Accra
            {x: 75, y: 48}    // Oti
        ];
        
        return `<div class="region-hotspot" data-region="${region}" 
                    style="left:${positions[index].x}%;top:${positions[index].y}%;"
                    title="Click ${region}"></div>`;
    }).join('');
}

function addMapInteractions() {
    console.log('🎯 Adding interactions to', document.querySelectorAll('.region-hotspot').length, 'hotspots');
    
    document.querySelectorAll('.region-hotspot').forEach((hotspot, i) => {
        hotspot.addEventListener('click', async (e) => {
            const regionName = e.target.getAttribute('data-region');
            
            console.log('✅ Clicked:', regionName);
            
            // Highlight selected
            document.querySelectorAll('.region-hotspot').forEach(h => h.style.opacity = '0.3');
            e.target.style.opacity = '1';
            e.target.style.boxShadow = '0 0 10px #0077b6';
            
            // Search for this region
            await filterRegions(regionName);
            
            // Scroll to results
            document.getElementById('regions-grid-section')?.scrollIntoView({ behavior: 'smooth' });
        });
    });
}

async function filterRegions(term) {
    try {
        console.log('🔍 Searching for:', term);
        
        const response = await fetch(API_URL);
        const allRegions = await response.json();
        console.log('📦 Total regions in DB:', allRegions.length);
        
        const filtered = allRegions.filter(r => 
            r.name.toLowerCase().includes(term.toLowerCase()) ||
            (r.overview && r.overview.toLowerCase().includes(term.toLowerCase()))
        );
        
        console.log('📋 Filtered results:', filtered.length);
        
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
    
    console.log('📱 Creating', regions.length, 'region cards');
    
    regions.forEach(region => {
        const card = document.createElement('div');
        card.className = 'region-card';
        card.onclick = () => {
            alert('Coming soon: /regions/' + region.name.replace(/\s+/g, '-').toLowerCase() + '.html');
            // window.location.href = `/regions/${region.name.toLowerCase().replace(/\s+/g, '-')}.html`;
        };
        
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

console.log('✅ Script loaded successfully!');
