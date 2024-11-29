function initModal(modalId, csrfToken, showModal, triggerButtonId, savePreferenceUrl) {
    const modalElement = document.getElementById(modalId);
    // Check if the modal element exists
    if (!modalElement) return;

    const modalInstance = new bootstrap.Modal(modalElement);

    // Only show the modal on page load if the condition is true
    if (showModal) {
        modalInstance.show();

        // Add an event listener to the save button
        const saveButton = document.getElementById('savePreference');
        if (saveButton) {
            saveButton.addEventListener('click', () => {
                const dontShowAgain = document.getElementById('dontShowAgain').checked;
                if (dontShowAgain) {
                    // Send a POST request to save the user's preference
                    fetch(savePreferenceUrl, {
                        method: "POST",
                        headers: {
                            "X-CSRFToken": csrfToken,
                            "Content-Type": "application/json"
                        },
                        body: JSON.stringify({
                            modal_name: modalId,
                            show_modal: false
                        })
                    }).then(response => {
                        if (response.ok) {
                            console.log(`Preference for ${modalId} saved`);
                        } else {
                            console.error(`Failed to save preference for ${modalId}`);
                        }
                    });
                }

                // Hide the modal after preference saved
                modalInstance.hide();
            });
        } 
    } else {
        // Hide the modal on page load
        modalInstance.hide();
    }

    // Add event listener to the trigger button if provided
    if (triggerButtonId) {
        const triggerButton = document.getElementById(triggerButtonId);
        if (triggerButton) {
            triggerButton.addEventListener('click', () => {
                modalInstance.show();
            });
        }
    }

    
}