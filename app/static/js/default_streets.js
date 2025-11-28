// JavaScript for managing default streets content

// Edit content for a street
async function editContent(streetId) {
    try {
        // Fetch existing content if it exists
        const response = await fetch(`/api/street-content/${streetId}`);
        if (!response.ok && response.status !== 404) {
            alert('Failed to load street content.');
            return;
        }

        const data = await response.json();
        const content = data.content || {};

        // Fill form fields
        document.getElementById('contentStreetId').value = streetId;
        document.getElementById('contentLatitude').value = content.latitude || '';
        document.getElementById('contentLongitude').value = content.longitude || '';
        document.getElementById('contentDistrict').value = content.district || '';
        document.getElementById('contentPostalCode').value = content.postal_code || '';

        const linksStr = content.external_links ? content.external_links.join(', ') : '';
        document.getElementById('contentExternalLinks').value = linksStr;

        document.getElementById('contentHistoricalInfo').value = content.historical_info || '';

        // Update modal title
        const modalTitle = document.getElementById('modalTitle');
        modalTitle.textContent = content.id ? 'Edit Street Content' : 'Add Street Content';

        // Show modal
        document.getElementById('contentModal').classList.add('is-active');
    } catch (error) {
        console.error('Error loading street content:', error);
        alert('An error occurred while loading street content.');
    }
}

// Close content modal
function closeContentModal() {
    document.getElementById('contentModal').classList.remove('is-active');
    document.getElementById('contentForm').reset();
    document.getElementById('contentStreetId').value = '';
}

// Handle form submission
document.getElementById('contentForm').addEventListener('submit', async function(e) {
    e.preventDefault();

    const streetId = document.getElementById('contentStreetId').value;
    const latitude = document.getElementById('contentLatitude').value.trim();
    const longitude = document.getElementById('contentLongitude').value.trim();
    const district = document.getElementById('contentDistrict').value.trim();
    const postalCode = document.getElementById('contentPostalCode').value.trim();
    const linksText = document.getElementById('contentExternalLinks').value.trim();
    const historicalInfo = document.getElementById('contentHistoricalInfo').value.trim();

    // Parse comma-separated links into array
    const externalLinks = linksText ? linksText.split(',').map(l => l.trim()).filter(l => l) : [];

    const payload = {
        district: district || null,
        postal_code: postalCode || null,
        external_links: externalLinks,
        historical_info: historicalInfo || null,
    };

    // Add geolocation if provided
    if (latitude) {
        payload.latitude = parseFloat(latitude);
    }
    if (longitude) {
        payload.longitude = parseFloat(longitude);
    }

    try {
        const response = await fetch(`/api/street-content/${streetId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(payload)
        });

        const data = await response.json();

        if (response.ok) {
            closeContentModal();
            window.location.reload();
        } else {
            alert(data.error || 'Failed to save street content.');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('An error occurred while saving street content.');
    }
});
