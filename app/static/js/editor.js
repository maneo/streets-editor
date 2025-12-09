// Editor JavaScript for managing streets

// Edit street in form
async function editStreetInForm(streetId) {
    try {
        // Fetch street data
        const response = await fetch(`/api/streets/${streetId}`);
        if (!response.ok) {
            alert('Failed to load street data.');
            return;
        }

        const streetData = await response.json();

        // Fill form fields
        document.getElementById('editingStreetId').value = streetId;
        document.getElementById('newPrefix').value = streetData.prefix;
        document.getElementById('newStreetName').value = streetData.main_name_cs;
        document.getElementById('newDistrict').value = streetData.district || '';

        // Convert arrays back to comma-separated strings
        const variantsStr = streetData.variants ? streetData.variants.join(', ') : '';
        const misspellingsStr = streetData.misspellings ? streetData.misspellings.join(', ') : '';

        document.getElementById('newVariants').value = variantsStr;
        document.getElementById('newMisspellings').value = misspellingsStr;

        // Update form UI for editing
        document.getElementById('formTitle').textContent = 'Edit Street';
        document.getElementById('submitButton').textContent = 'Save Changes';

        // Add cancel button if it doesn't exist
        const formButtons = document.getElementById('formButtons');
        if (!document.getElementById('cancelEditButton')) {
            const cancelButton = document.createElement('button');
            cancelButton.type = 'button';
            cancelButton.id = 'cancelEditButton';
            cancelButton.className = 'px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50 mr-3';
            cancelButton.textContent = 'Cancel Edit';
            cancelButton.onclick = cancelEdit;
            formButtons.insertBefore(cancelButton, formButtons.firstChild);
        }

        // Scroll to form
        document.getElementById('addStreetForm').scrollIntoView({ behavior: 'smooth' });
    } catch (error) {
        console.error('Error loading street data:', error);
        alert('An error occurred while loading street data.');
    }
}

// Cancel editing and reset form
function cancelEdit() {
    // Clear form
    document.getElementById('addStreetForm').reset();
    document.getElementById('editingStreetId').value = '';

    // Reset UI
    document.getElementById('formTitle').textContent = 'Add New Street';
    document.getElementById('submitButton').textContent = 'Add Street';

    // Remove cancel button
    const cancelButton = document.getElementById('cancelEditButton');
    if (cancelButton) {
        cancelButton.remove();
    }
}

// Handle form submission (add or edit street)
document.getElementById('addStreetForm').addEventListener('submit', async function(e) {
    e.preventDefault();

    const editingStreetId = document.getElementById('editingStreetId').value;
    const prefix = document.getElementById('newPrefix').value;
    const mainName = document.getElementById('newStreetName').value.trim();
    const district = document.getElementById('newDistrict').value.trim();
    const variantsText = document.getElementById('newVariants').value.trim();
    const misspellingsText = document.getElementById('newMisspellings').value.trim();

    if (!mainName) {
        alert('Please enter a street name.');
        return;
    }

    // Parse comma-separated values into arrays
    const variants = variantsText ? variantsText.split(',').map(v => v.trim()).filter(v => v) : [];
    const misspellings = misspellingsText ? misspellingsText.split(',').map(m => m.trim()).filter(m => m) : [];

    const isEditing = editingStreetId !== '';

    try {
        let response;
        if (isEditing) {
            // Update existing street
            response = await fetch(`/api/streets/${editingStreetId}`, {
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

        if (response.ok) {
            if (isEditing) {
                // Reset form to add mode and reload page
                cancelEdit();
            } else {
                // Clear form and reload page to show new street
                document.getElementById('addStreetForm').reset();
            }
            window.location.reload();
        } else {
            alert(data.error || `Failed to ${isEditing ? 'update' : 'add'} street.`);
        }
    } catch (error) {
        console.error('Error:', error);
        alert(`An error occurred while ${isEditing ? 'updating' : 'adding'} the street.`);
    }
});


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
