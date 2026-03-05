const API_URL = 'https://echo-stack-ghana.onrender.com/api/regions';

// ==========================================
// GHANA SVG MAP WITH INTERACTIVE REGIONS
// ==========================================
const ghanaMapSVG = `
<svg viewBox="0 0 400 500" xmlns="http://www.w3.org/2000/svg">
    <!-- Northern Region -->
    <path class="region-path" data-region="Northern" 
          d="M180,40 L280,45 L300,100 L280,150 L220,160 L150,140 L140,90 Z"/>
    
    <!-- Savanna Region -->
    <path class="region-path" data-region="Savannah" 
          d="M140,90 L220,160 L180,200 L120,180 L100,130 Z"/>
    
    <!-- North East Region -->
    <path class="region-path" data-region="North East" 
          d="M280,150 L340,160 L350,220 L280,200 L220,160 Z"/>
    
    <!-- Bono Region -->
    <path class="region-path" data-region="Bono" 
          d="M120,180 L180,200 L170,260 L110,250 L100,200 Z"/>
    
    <!-- Bono East Region -->
    <path class="region-path" data-region="Bono East" 
          d="M180,200 L220,220 L210,270 L170,260 Z"/>
    
    <!-- Ahafo Region -->
    <path class="region-path" data-region="Ahafo" 
          d="M110,250 L170,260 L160,300 L100,290 Z"/>
    
    <!-- Ashanti Region -->
    <path class="region-path" data-region="Ashanti" 
          d="M170,260 L210,270 L220,330 L160,350 L160,300 Z"/>
    
    <!-- Eastern Region -->
    <path class="region-path" data-region="Eastern" 
          d="M210,270 L280,280 L300,350 L220,330 Z"/>
    
    <!-- Western Region -->
    <path class="region-path" data-region="Western" 
          d="M60,300 L100,290 L160,300 L140,380 L80,360 Z"/>
    
    <!-- Western North Region -->
    <path class="region-path" data-region="Western North" 
          d="M160,300 L200,310 L190,360 L160,350 Z"/>
    
    <!-- Greater Accra Region -->
    <path class="region-path" data-region="Greater Accra" 
          d="M280,280 L320,290 L330,310 L280,310 Z"/>
    
    <!-- Volta Region -->
    <path class="region-path" data-region="Volta" 
          d="M220,330 L280,310 L330,310 L320,420 L220,400 Z"/>
    
    <!-- Oti Region -->
    <path class="region-path" data-region="Oti" 
          d="M280,280 L340,290 L320,400 L280,310 Z"/>
    
    <!-- Upper West Region -->
    <path class="region-path" data-region="Upper West" 
          d="M40,40 L140,40 L140,140 L100,180 L40,140 Z"/>
    
    <!-- Upper East Region -->
    <path class="region-path" data-region="Upper East" 
          d="M280,45 L380,50 L370,120 L340,160 L280,150 Z"/>
    
    <!-- Labels -->
    <text x="220" y="100" font-size="12" fill="#1a1e29" text-anchor="middle">Northern</text>
    <text x="150" y="230" font-size="11" fill="#1a1e29" text-anchor="middle">Ashanti</text>
    <text x="280" y="350" font-size="10" fill="#1a1e29" text-anchor="middle">Volta</text>
    <text x="300" y="300" font-size="9" fill="#1a1e29" text-anchor="middle">Accra</text>
</svg>
`;

// Render Map On Page Load
document.addEventListener('DOMContentLoaded', () => {
    const mapContainer = document.getElementById('ghana-map-container');
    if (mapContainer) {
        mapContainer.innerHTML = ghanaMapSVG;
        addMapInteractions();
    }
});

// ==========================================
// REGION DATA LOADING
// ==========================================
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
        grid.innerHTML = '<p>No regions found. Please try another search.</p>';
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

// ==========================================
// MAP INTERACTION HANDLERS
// ==========================================
function addMapInteractions() {
    document.querySelectorAll('.region-path').forEach(path => {
        path.addEventListener('click', () => {
            // Highlight selected region
            document.querySelectorAll('.region-path').forEach(p => p.style.fill = '#e0e0e0');
            path.style.fill = '#0077b6';
            
            // Search for this region
            const regionName = path.getAttribute('data-region');
            filterRegions(regionName);
        });
        
        // Add hover effect
        path.addEventListener('mouseenter', () => {
            path.style.fill = '#00b4d8';
        });
        
        path.addEventListener('mouseleave', () => {
            // Only reset if not selected
            if (path.style.fill !== 'rgb(0, 119, 182)') {
                path.style.fill = '#e0e0e0';
            }
        });
    });
}

// ==========================================
// SEARCH FUNCTIONALITY
// ==========================================
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
