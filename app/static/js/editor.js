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

// Close modal when clicking outside
document.getElementById('editModal').addEventListener('click', function(e) {
    if (e.target === this) {
        closeEditModal();
    }
});
