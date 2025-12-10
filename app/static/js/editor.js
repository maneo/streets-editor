// Editor JavaScript for managing streets

// Map management globals
let streetMap = null;
let streetMapMarker = null;
let isMapExpanded = false;

// Initialize Leaflet map
function initializeMap(lat, lng, streetName = '') {
    // Clean up existing map if it exists
    if (streetMap) {
        streetMap.remove();
        streetMap = null;
        streetMapMarker = null;
    }

    // Create map instance
    try {
        streetMap = L.map('mapPreview').setView([lat, lng], 15);

        // Add OpenStreetMap tile layer
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
            maxZoom: 19
        }).addTo(streetMap);

        // Add marker with popup
        streetMapMarker = L.marker([lat, lng]).addTo(streetMap);
        if (streetName) {
            streetMapMarker.bindPopup(streetName).openPopup();
        }

        return true;
    } catch (error) {
        console.error('Error initializing map:', error);
        return false;
    }
}

// Update map location and marker
function updateMapLocation(lat, lng, streetName = '') {
    if (!lat || !lng || isNaN(lat) || isNaN(lng)) {
        hideMapPreview();
        return false;
    }

    const latitude = parseFloat(lat);
    const longitude = parseFloat(lng);

    // Validate coordinates range
    if (latitude < -90 || latitude > 90 || longitude < -180 || longitude > 180) {
        console.warn('Invalid coordinates range');
        hideMapPreview();
        return false;
    }

    // Show map section
    showMapPreview();

    // If map doesn't exist or container is hidden, initialize it
    if (!streetMap || !isMapExpanded) {
        // If not expanded, expand it first
        if (!isMapExpanded) {
            toggleMapSection();
        }
        // Wait a bit for the container to be visible, then initialize
        setTimeout(() => {
            initializeMap(latitude, longitude, streetName);
        }, 100);
    } else {
        // Update existing map
        streetMap.setView([latitude, longitude], 15);

        // Update marker
        if (streetMapMarker) {
            streetMapMarker.setLatLng([latitude, longitude]);
            if (streetName) {
                streetMapMarker.bindPopup(streetName).openPopup();
            }
        } else {
            streetMapMarker = L.marker([latitude, longitude]).addTo(streetMap);
            if (streetName) {
                streetMapMarker.bindPopup(streetName).openPopup();
            }
        }
    }

    return true;
}

// Show map preview section
function showMapPreview() {
    const mapSection = document.getElementById('mapPreviewSection');
    if (mapSection) {
        mapSection.style.display = 'block';
    }
}

// Hide map preview section
function hideMapPreview() {
    const mapSection = document.getElementById('mapPreviewSection');
    const mapContainer = document.getElementById('mapPreviewContainer');

    if (mapSection) {
        mapSection.style.display = 'none';
    }

    if (mapContainer) {
        mapContainer.style.display = 'none';
        isMapExpanded = false;
    }

    // Clean up map
    if (streetMap) {
        streetMap.remove();
        streetMap = null;
        streetMapMarker = null;
    }

    // Reset toggle icon
    const toggleIcon = document.getElementById('mapToggleIcon');
    if (toggleIcon) {
        toggleIcon.innerHTML = '<i class="fas fa-chevron-down"></i>';
    }
}

// Toggle map section expand/collapse
function toggleMapSection() {
    const mapContainer = document.getElementById('mapPreviewContainer');
    const toggleIcon = document.getElementById('mapToggleIcon');

    if (!mapContainer || !toggleIcon) return;

    isMapExpanded = !isMapExpanded;

    if (isMapExpanded) {
        mapContainer.style.display = 'block';
        toggleIcon.innerHTML = '<i class="fas fa-chevron-up"></i>';

        // Get current coordinates
        const lat = document.getElementById('contentLatitude').value;
        const lng = document.getElementById('contentLongitude').value;
        const streetName = document.getElementById('newStreetName').value;

        // Initialize map with current coordinates
        if (lat && lng) {
            setTimeout(() => {
                initializeMap(parseFloat(lat), parseFloat(lng), streetName);
            }, 100);
        }
    } else {
        mapContainer.style.display = 'none';
        toggleIcon.innerHTML = '<i class="fas fa-chevron-down"></i>';

        // Clean up map when collapsed
        if (streetMap) {
            streetMap.remove();
            streetMap = null;
            streetMapMarker = null;
        }
    }
}

// Open street modal for adding or editing
async function openStreetModal(streetId) {
    const modal = document.getElementById('streetModal');
    if (!modal) return;

    // Reset form
    document.getElementById('streetForm').reset();
    document.getElementById('streetId').value = '';
    document.getElementById('isDefaultStreet').value = 'false';
    clearStreetModalStatus();

    // Hide extended fields by default
    document.getElementById('defaultStreetFields').style.display = 'none';

    if (!streetId || streetId === 'null') {
        // Add new street mode
        document.getElementById('streetModalTitle').textContent = 'Add New Street';
        document.getElementById('submitButton').textContent = 'Add Street';
        modal.classList.add('is-active');
        return;
    }

    // Edit existing street mode
    try {
        // Fetch street data
        const response = await fetch(`/api/streets/${streetId}`);
        if (!response.ok) {
            showStreetModalStatus('Failed to load street data.', 'error');
            return;
        }

        const streetData = await response.json();

        // Fill basic form fields
        document.getElementById('streetId').value = streetId;
        document.getElementById('newPrefix').value = streetData.prefix || 'ul.';
        document.getElementById('newStreetName').value = streetData.main_name_cs || '';
        document.getElementById('newDistrict').value = streetData.district || '';

        // Convert arrays back to comma-separated strings
        const variantsStr = streetData.variants ? streetData.variants.join(', ') : '';
        const misspellingsStr = streetData.misspellings ? streetData.misspellings.join(', ') : '';

        document.getElementById('newVariants').value = variantsStr;
        document.getElementById('newMisspellings').value = misspellingsStr;

        // Set modal title with street name
        const prefixDisplay = streetData.prefix && streetData.prefix !== '-' ? `${streetData.prefix} ` : '';
        document.getElementById('streetModalTitle').textContent = `Edit Street: ${prefixDisplay}${streetData.main_name_cs}`;
        document.getElementById('submitButton').textContent = 'Save Changes';

        // Check if this is a default street
        const isDefault = streetData.is_default_street || false;
        document.getElementById('isDefaultStreet').value = isDefault.toString();

        if (isDefault) {
            // Show extended fields
            document.getElementById('defaultStreetFields').style.display = 'block';

            // Fetch content if it exists
            try {
                const contentResponse = await fetch(`/api/street-content/${streetId}`);
                if (contentResponse.ok || contentResponse.status === 404) {
                    const contentData = await contentResponse.json();
                    const content = contentData.content || {};

                    // Fill extended fields
                    document.getElementById('contentLatitude').value = content.latitude || '';
                    document.getElementById('contentLongitude').value = content.longitude || '';
                    document.getElementById('contentPostalCode').value = content.postal_code || '';

                    const linksStr = content.external_links ? content.external_links.join(', ') : '';
                    document.getElementById('contentExternalLinks').value = linksStr;

                    document.getElementById('contentHistoricalInfo').value = content.historical_info || '';

                    // Check if coordinates exist and update map
                    if (content.latitude && content.longitude) {
                        const streetName = streetData.prefix && streetData.prefix !== '-'
                            ? `${streetData.prefix} ${streetData.main_name_cs}`
                            : streetData.main_name_cs;
                        updateMapLocation(content.latitude, content.longitude, streetName);
                    }
                }
            } catch (error) {
                console.error('Error loading street content:', error);
                // Continue without content data
            }
        }

        // Show modal
        modal.classList.add('is-active');
    } catch (error) {
        console.error('Error loading street data:', error);
        showStreetModalStatus('An error occurred while loading street data.', 'error');
    }
}

// Close street modal
function closeStreetModal() {
    const modal = document.getElementById('streetModal');
    if (modal) {
        modal.classList.remove('is-active');
    }
    document.getElementById('streetForm').reset();
    document.getElementById('streetId').value = '';
    document.getElementById('isDefaultStreet').value = 'false';
    clearStreetModalStatus();

    // Clean up map
    hideMapPreview();
}


// Delete street
async function deleteStreet(id) {
    if (!confirm('Are you sure you want to delete this street?')) {
        return;
    }

    try {
        const response = await fetch(`/api/streets/${id}`, {
            method: 'DELETE',
        });

        const data = await response.json();

        if (response.ok) {
            // Remove row from table
            const row = document.querySelector(`tr[data-street-id="${id}"]`);
            if (row) {
                row.remove();
            }
        } else {
            alert(data.error || 'Failed to delete street.');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('An error occurred while deleting the street.');
    }
}

// Mapping modal state
let currentMappingStreetId = null;
let selectedDefaultStreetId = null;
let originalMappingId = null; // Store original mapping to compare changes
let allDefaultStreets = [];

// Open mapping modal
async function openMappingModal(streetId, currentMappingId, currentMappingName) {
    currentMappingStreetId = streetId;
    originalMappingId = currentMappingId ? parseInt(currentMappingId) : null;
    selectedDefaultStreetId = originalMappingId;

    const modal = document.getElementById('mappingModal');
    if (!modal) return;

    // Show current mapping if exists
    const currentMappingDiv = document.getElementById('currentMapping');
    const currentMappingText = document.getElementById('currentMappingText');
    const removeMappingBtn = document.getElementById('removeMappingBtn');
    const saveBtn = document.getElementById('saveMappingBtn');

    if (currentMappingId && currentMappingName) {
        currentMappingDiv.style.display = 'block';
        currentMappingText.textContent = currentMappingName;
        removeMappingBtn.style.display = 'block';
    } else {
        currentMappingDiv.style.display = 'none';
        removeMappingBtn.style.display = 'none';
    }

    // Reset search and load streets
    document.getElementById('mappingSearch').value = '';
    await loadDefaultStreets();

    // Update save button state
    if (saveBtn) {
        saveBtn.disabled = !selectedDefaultStreetId || selectedDefaultStreetId === originalMappingId;
    }

    // Show modal
    modal.classList.add('is-active');
}

// Close mapping modal
function closeMappingModal() {
    const modal = document.getElementById('mappingModal');
    if (modal) {
        modal.classList.remove('is-active');
    }
    currentMappingStreetId = null;
    selectedDefaultStreetId = null;
    originalMappingId = null;
}

// Load default streets
async function loadDefaultStreets(searchQuery = '') {
    const listDiv = document.getElementById('mappingStreetsList');
    if (!listDiv) return;

    try {
        const url = `/api/default-streets/${encodeURIComponent(CITY)}${searchQuery ? `?search=${encodeURIComponent(searchQuery)}` : ''}`;
        const response = await fetch(url);

        if (!response.ok) {
            listDiv.innerHTML = '<p class="has-text-danger">Failed to load default streets.</p>';
            return;
        }

        const data = await response.json();
        allDefaultStreets = data.streets || [];

        if (allDefaultStreets.length === 0) {
            listDiv.innerHTML = '<p class="has-text-grey has-text-centered">No default streets found.</p>';
            return;
        }

        // Render streets list
        let html = '<div class="content">';
        allDefaultStreets.forEach(street => {
            const isSelected = selectedDefaultStreetId == street.id;
            html += `
                <div class="box mb-2 ${isSelected ? 'has-background-info-light' : ''}"
                     onclick="selectDefaultStreet(${street.id}, '${street.display_name.replace(/'/g, "\\'")}')"
                     style="cursor: pointer; ${isSelected ? 'border: 2px solid #3273dc;' : ''}">
                    <div class="level">
                        <div class="level-left">
                            <div>
                                <strong>${street.display_name}</strong>
                            </div>
                        </div>
                        <div class="level-right">
                            ${isSelected ? '<span class="tag is-info"><i class="fas fa-check"></i> Selected</span>' : ''}
                        </div>
                    </div>
                </div>
            `;
        });
        html += '</div>';
        listDiv.innerHTML = html;

        // Update save button state
        const saveBtn = document.getElementById('saveMappingBtn');
        if (saveBtn) {
            saveBtn.disabled = !selectedDefaultStreetId || selectedDefaultStreetId === originalMappingId;
        }
    } catch (error) {
        console.error('Error loading default streets:', error);
        listDiv.innerHTML = '<p class="has-text-danger">An error occurred while loading default streets.</p>';
    }
}

// Search default streets
function searchDefaultStreets() {
    const searchQuery = document.getElementById('mappingSearch').value.trim();
    loadDefaultStreets(searchQuery);
}

// Select default street
function selectDefaultStreet(streetId, streetName) {
    selectedDefaultStreetId = parseInt(streetId);

    // Update UI - highlight selected street
    const listDiv = document.getElementById('mappingStreetsList');
    const boxes = listDiv.querySelectorAll('.box');
    boxes.forEach(box => {
        const onclickAttr = box.getAttribute('onclick') || '';
        const isSelected = onclickAttr.includes(`selectDefaultStreet(${streetId},`);

        if (isSelected) {
            box.classList.add('has-background-info-light');
            box.style.border = '2px solid #3273dc';
            // Add selected indicator
            const levelRight = box.querySelector('.level-right');
            if (levelRight) {
                levelRight.innerHTML = '<span class="tag is-info"><i class="fas fa-check"></i> Selected</span>';
            }
        } else {
            box.classList.remove('has-background-info-light');
            box.style.border = '';
            const levelRight = box.querySelector('.level-right');
            if (levelRight) {
                const tag = levelRight.querySelector('.tag');
                if (tag) tag.remove();
            }
        }
    });

    // Update save button
    const saveBtn = document.getElementById('saveMappingBtn');
    if (saveBtn) {
        // Enable button if a street is selected and it's different from original mapping
        saveBtn.disabled = !selectedDefaultStreetId || selectedDefaultStreetId === originalMappingId;
    }
}

// Save mapping
async function saveMapping() {
    if (!currentMappingStreetId || !selectedDefaultStreetId) {
        alert('Please select a default street.');
        return;
    }

    try {
        const response = await fetch(`/api/streets/${currentMappingStreetId}/map-to-default`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                default_street_id: selectedDefaultStreetId
            })
        });

        const data = await response.json();

        if (response.ok) {
            closeMappingModal();
            window.location.reload();
        } else {
            alert(data.error || 'Failed to save mapping.');
        }
    } catch (error) {
        console.error('Error saving mapping:', error);
        alert('An error occurred while saving the mapping.');
    }
}

// Remove mapping
async function removeMapping() {
    if (!currentMappingStreetId) {
        return;
    }

    if (!confirm('Are you sure you want to remove the mapping?')) {
        return;
    }

    try {
        const response = await fetch(`/api/streets/${currentMappingStreetId}/map-to-default`, {
            method: 'DELETE',
        });

        const data = await response.json();

        if (response.ok) {
            closeMappingModal();
            window.location.reload();
        } else {
            alert(data.error || 'Failed to remove mapping.');
        }
    } catch (error) {
        console.error('Error removing mapping:', error);
        alert('An error occurred while removing the mapping.');
    }
}

// Show status message in street modal
function showStreetModalStatus(message, type = 'info') {
    const statusDiv = document.getElementById('streetModalStatus');
    const statusMessage = document.getElementById('streetModalStatusMessage');

    // Remove existing type classes
    statusDiv.classList.remove('is-success', 'is-danger', 'is-warning', 'is-info');

    // Add appropriate type class
    if (type === 'success') {
        statusDiv.classList.add('is-success');
    } else if (type === 'error') {
        statusDiv.classList.add('is-danger');
    } else if (type === 'warning') {
        statusDiv.classList.add('is-warning');
    } else {
        statusDiv.classList.add('is-info');
    }

    statusMessage.textContent = message;
    statusDiv.style.display = 'block';

    // Auto-hide success messages after 5 seconds
    if (type === 'success') {
        setTimeout(() => {
            clearStreetModalStatus();
        }, 5000);
    }
}

// Clear status message in street modal
function clearStreetModalStatus() {
    const statusDiv = document.getElementById('streetModalStatus');
    statusDiv.style.display = 'none';
    statusDiv.classList.remove('is-success', 'is-danger', 'is-warning', 'is-info');
}

// Enrich street with geolocation
async function enrichStreetGeo() {
    const streetId = document.getElementById('streetId').value;

    if (!streetId) {
        showStreetModalStatus('No street selected for enrichment.', 'error');
        return;
    }

    const enrichButton = document.getElementById('enrichGeoButton');
    const originalButtonContent = enrichButton.innerHTML;

    // Disable button and show loading state
    enrichButton.disabled = true;
    enrichButton.innerHTML = '<span class="icon is-small"><i class="fas fa-spinner fa-spin"></i></span><span>Enriching...</span>';

    try {
        const response = await fetch(`/api/streets/geolocations/${streetId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });

        const data = await response.json();

        if (response.ok && data.success) {
            // Populate form fields with geolocation data
            document.getElementById('contentLatitude').value = data.latitude;
            document.getElementById('contentLongitude').value = data.longitude;

            // Update map with new coordinates
            const streetName = document.getElementById('newStreetName').value;
            const prefix = document.getElementById('newPrefix').value;
            const fullStreetName = prefix && prefix !== '-' ? `${prefix} ${streetName}` : streetName;
            updateMapLocation(data.latitude, data.longitude, fullStreetName);

            // Show success message
            showStreetModalStatus(
                `Geolocation enriched successfully! Latitude: ${data.latitude}, Longitude: ${data.longitude}`,
                'success'
            );
        } else {
            // Handle error or already has geolocation
            if (data.latitude && data.longitude) {
                // Street already has geolocation
                document.getElementById('contentLatitude').value = data.latitude;
                document.getElementById('contentLongitude').value = data.longitude;
                showStreetModalStatus(data.message || 'Street already has geolocation data.', 'info');
            } else {
                showStreetModalStatus(
                    data.message || 'Failed to enrich geolocation. Street may not be found in OpenStreetMap.',
                    'error'
                );
            }
        }
    } catch (error) {
        console.error('Error enriching geolocation:', error);
        showStreetModalStatus('An error occurred while enriching geolocation.', 'error');
    } finally {
        // Restore button state
        enrichButton.disabled = false;
        enrichButton.innerHTML = originalButtonContent;
    }
}

// Handle unified street form submission
const streetForm = document.getElementById('streetForm');
if (streetForm) {
    streetForm.addEventListener('submit', async function(e) {
        e.preventDefault();

        const streetId = document.getElementById('streetId').value;
        const prefix = document.getElementById('newPrefix').value;
        const mainName = document.getElementById('newStreetName').value.trim();
        const district = document.getElementById('newDistrict').value.trim();
        const variantsText = document.getElementById('newVariants').value.trim();
        const misspellingsText = document.getElementById('newMisspellings').value.trim();
        const isDefault = document.getElementById('isDefaultStreet').value === 'true';

        if (!mainName) {
            showStreetModalStatus('Please enter a street name.', 'error');
            return;
        }

        // Parse comma-separated values into arrays
        const variants = variantsText ? variantsText.split(',').map(v => v.trim()).filter(v => v) : [];
        const misspellings = misspellingsText ? misspellingsText.split(',').map(m => m.trim()).filter(m => m) : [];

        const isEditing = streetId !== '';

        try {
            // Save street data
            let response;
            if (isEditing) {
                // Update existing street
                response = await fetch(`/api/streets/${streetId}`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        prefix: prefix,
                        main_name_cs: mainName,
                        district: district || null,
                        variants: variants,
                        misspellings: misspellings
                    })
                });
            } else {
                // Add new street
                response = await fetch('/api/streets', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        city: CITY,
                        decade: DECADE,
                        prefix: prefix,
                        main_name_cs: mainName,
                        district: district || null,
                        variants: variants,
                        misspellings: misspellings
                    })
                });
            }

            const data = await response.json();

            if (!response.ok) {
                showStreetModalStatus(data.error || `Failed to ${isEditing ? 'update' : 'add'} street.`, 'error');
                return;
            }

            // Get the street ID (either from editing or from creation response)
            const savedStreetId = isEditing ? streetId : data.id;

            // If this is a default street, save content data
            if (isDefault && savedStreetId) {
                const latitude = document.getElementById('contentLatitude').value.trim();
                const longitude = document.getElementById('contentLongitude').value.trim();
                const postalCode = document.getElementById('contentPostalCode').value.trim();
                const linksText = document.getElementById('contentExternalLinks').value.trim();
                const historicalInfo = document.getElementById('contentHistoricalInfo').value.trim();

                // Parse comma-separated links into array
                const externalLinks = linksText ? linksText.split(',').map(l => l.trim()).filter(l => l) : [];

                const contentPayload = {
                    postal_code: postalCode || null,
                    external_links: externalLinks,
                    historical_info: historicalInfo || null,
                };

                // Add geolocation if provided
                if (latitude) {
                    contentPayload.latitude = parseFloat(latitude);
                }
                if (longitude) {
                    contentPayload.longitude = parseFloat(longitude);
                }

                try {
                    const contentResponse = await fetch(`/api/street-content/${savedStreetId}`, {
                        method: 'PUT',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify(contentPayload)
                    });

                    if (!contentResponse.ok) {
                        const contentData = await contentResponse.json();
                        showStreetModalStatus(
                            `Street saved but content update failed: ${contentData.error || 'Unknown error'}`,
                            'warning'
                        );
                        // Still reload to show the street was saved
                        setTimeout(() => {
                            window.location.reload();
                        }, 2000);
                        return;
                    }
                } catch (error) {
                    console.error('Error saving street content:', error);
                    showStreetModalStatus('Street saved but content update failed.', 'warning');
                    setTimeout(() => {
                        window.location.reload();
                    }, 2000);
                    return;
                }
            }

            // Success - show message and reload
            showStreetModalStatus(
                `Street ${isEditing ? 'updated' : 'created'} successfully!`,
                'success'
            );
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        } catch (error) {
            console.error('Error:', error);
            showStreetModalStatus(`An error occurred while ${isEditing ? 'updating' : 'adding'} the street.`, 'error');
        }
    });
}

// Add event listeners for coordinate input fields to update map on manual changes
const latitudeInput = document.getElementById('contentLatitude');
const longitudeInput = document.getElementById('contentLongitude');

if (latitudeInput && longitudeInput) {
    // Debounce function to avoid too many updates while typing
    let coordinateUpdateTimeout = null;

    const handleCoordinateChange = () => {
        clearTimeout(coordinateUpdateTimeout);
        coordinateUpdateTimeout = setTimeout(() => {
            const lat = latitudeInput.value.trim();
            const lng = longitudeInput.value.trim();

            if (lat && lng) {
                const streetName = document.getElementById('newStreetName').value;
                const prefix = document.getElementById('newPrefix').value;
                const fullStreetName = prefix && prefix !== '-' ? `${prefix} ${streetName}` : streetName;
                updateMapLocation(lat, lng, fullStreetName);
            } else {
                // If either coordinate is empty, hide the map
                hideMapPreview();
            }
        }, 500); // Wait 500ms after user stops typing
    };

    latitudeInput.addEventListener('input', handleCoordinateChange);
    longitudeInput.addEventListener('input', handleCoordinateChange);
}
