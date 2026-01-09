// API Service
const API = {
    // Upload PDF file
    uploadFile: async (file) => {
        try {
            const formData = new FormData();
            formData.append('file', file);
            
            const response = await fetch(`${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.UPLOAD}`, {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Upload failed');
            }
            
            return await response.json();
        } catch (error) {
            console.error('Upload error:', error);
            throw error;
        }
    },
    
    // Extract clauses from uploaded document
    extractClauses: async (docId) => {
        try {
            const response = await fetch(
                `${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.EXTRACT}${docId}`,
                {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                }
            );
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Extraction failed');
            }
            
            return await response.json();
        } catch (error) {
            console.error('Extraction error:', error);
            throw error;
        }
    },
    
    // Send chat message
    sendChatMessage: async (sessionId, docId, query) => {
        try {
            const response = await fetch(`${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.CHAT}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    session_id: sessionId,
                    doc_id: docId,
                    query: query
                })
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Chat request failed');
            }
            
            return await response.json();
        } catch (error) {
            console.error('Chat error:', error);
            throw error;
        }
    },
    
    // Get chat history
    getChatHistory: async (sessionId, limit = 10) => {
        try {
            const response = await fetch(
                `${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.CHAT_HISTORY}${sessionId}?limit=${limit}`
            );
            
            if (!response.ok) {
                throw new Error('Failed to fetch chat history');
            }
            
            return await response.json();
        } catch (error) {
            console.error('Chat history error:', error);
            throw error;
        }
    },
    
    // Clear chat session
    clearChatSession: async (sessionId) => {
        try {
            const response = await fetch(
                `${API_CONFIG.BASE_URL}/api/chat/session/${sessionId}`,
                {
                    method: 'DELETE'
                }
            );
            
            if (!response.ok) {
                throw new Error('Failed to clear chat session');
            }
            
            return await response.json();
        } catch (error) {
            console.error('Clear session error:', error);
            throw error;
        }
    },
    
    // Export to Excel
    exportToExcel: async (docId) => {
        try {
            const response = await fetch(
                `${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.EXPORT}${docId}`
            );
            
            if (!response.ok) {
                throw new Error('Export failed');
            }
            
            // Download file
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `contract_analysis_${docId}.xlsx`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            
            return true;
        } catch (error) {
            console.error('Export error:', error);
            throw error;
        }
    },
    
    // Health check
    healthCheck: async () => {
        try {
            const response = await fetch(`${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.HEALTH}`);
            return response.ok;
        } catch (error) {
            return false;
        }
    }
};

// Toast Notification System
const Toast = {
    show: (message, type = 'info') => {
        const container = document.getElementById('toastContainer');
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        
        const icon = type === 'success' ? 'check-circle' : 
                     type === 'error' ? 'exclamation-circle' : 
                     'info-circle';
        
        toast.innerHTML = `
            <i class="fas fa-${icon}"></i>
            <span>${message}</span>
        `;
        
        container.appendChild(toast);
        
        // Remove after 5 seconds
        setTimeout(() => {
            toast.style.animation = 'slideOutRight 0.3s ease';
            setTimeout(() => {
                container.removeChild(toast);
            }, 300);
        }, 5000);
    },
    
    success: (message) => Toast.show(message, 'success'),
    error: (message) => Toast.show(message, 'error'),
    info: (message) => Toast.show(message, 'info')
};
