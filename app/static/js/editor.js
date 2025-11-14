// Editor JavaScript for managing streets

// Add new street
document.getElementById('addStreetForm').addEventListener('submit', async function(e) {
    e.preventDefault();

    const prefix = document.getElementById('newPrefix').value;
    const mainName = document.getElementById('newStreetName').value.trim();

    if (!mainName) {
        alert('Please enter a street name.');
        return;
    }

    try {
        const response = await fetch('/api/streets', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                city: CITY,
                decade: DECADE,
                prefix: prefix,
                main_name: mainName
            })
        });

        const data = await response.json();

        if (response.ok) {
            // Reload page to show new street
            window.location.reload();
        } else {
            alert(data.error || 'Failed to add street.');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('An error occurred while adding the street.');
    }
});

// Edit street
function editStreet(id, prefix, name) {
    document.getElementById('editStreetId').value = id;
    document.getElementById('editPrefix').value = prefix;
    document.getElementById('editStreetName').value = name;
    document.getElementById('editModal').classList.remove('hidden');
}

// Close edit modal
function closeEditModal() {
    document.getElementById('editModal').classList.add('hidden');
}

// Handle edit form submission
document.getElementById('editStreetForm').addEventListener('submit', async function(e) {
    e.preventDefault();

    const id = document.getElementById('editStreetId').value;
    const prefix = document.getElementById('editPrefix').value;
    const mainName = document.getElementById('editStreetName').value.trim();

    if (!mainName) {
        alert('Please enter a street name.');
        return;
    }

    try {
        const response = await fetch(`/api/streets/${id}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                prefix: prefix,
                main_name: mainName
            })
        });

        const data = await response.json();

        if (response.ok) {
            // Reload page to show updated street
            window.location.reload();
        } else {
            alert(data.error || 'Failed to update street.');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('An error occurred while updating the street.');
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
