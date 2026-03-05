const API_URL = 'https://echo-stack-ghana.onrender.com/api/regions';

async function loadRegions() {
    try {
        const response = await fetch(API_URL);
        const regions = await response.json();
        renderRegions(regions);
    } catch (error) {
        console.error('Error loading regions:', error);
        // Show default regions if API fails
        renderRegions([
            { id: 1, name: 'Ashanti', overview: 'Heart of the Ashanti Kingdom' },
            { id: 2, name: 'Eastern', overview: 'Sixth largest region by area' },
            { id: 3, name: 'Savannah', overview: "Ghana's largest region by land" },
            { id: 4, name: 'North East', overview: 'Northern Ghana landscapes' }
        ]);
    }
}

function renderRegions(regions) {
    const grid = document.getElementById('regions-grid');
    
    if (!regions || regions.length === 0) {
        grid.innerHTML = '<p>No regions available. Please check back soon!</p>';
        return;
    }
    
    grid.innerHTML = '';
    
    regions.forEach(region => {
        const card = document.createElement('div');
        card.className = 'region-card';
        card.onclick = () => window.location.href = `/regions/${region.name.toLowerCase()}.html`;
        
        card.innerHTML = `
            <h3>${region.name}</h3>
            <p>${region.overview || 'Click to explore this region...'}</p>
        `;
        
        grid.appendChild(card);
    });
}

// Search functionality
document.getElementById('search-bar').addEventListener('input', function(e) {
    const searchTerm = e.target.value.toLowerCase();
    const cards = document.querySelectorAll('.region-card');
    
    cards.forEach(card => {
        const regionName = card.querySelector('h3').textContent.toLowerCase();
        const regionDesc = card.querySelector('p').textContent.toLowerCase();
        
        if (regionName.includes(searchTerm) || regionDesc.includes(searchTerm)) {
            card.style.display = 'block';
        } else {
            card.style.display = 'none';
        }
    });
});

// Load regions when page loads
loadRegions();
