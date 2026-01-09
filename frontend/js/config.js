// API Configuration
const API_CONFIG = {
    BASE_URL: 'http://localhost:8000',
    ENDPOINTS: {
        UPLOAD: '/api/upload/',
        EXTRACT: '/api/extract/',
        CHAT: '/api/chat/',
        CHAT_HISTORY: '/api/chat/history/',
        EXPORT: '/api/export/',
        HEALTH: '/health'
    },
    TIMEOUT: 600000, // 10 minutes for extraction
    POLL_INTERVAL: 2000 // 2 seconds
};

// Application State
const APP_STATE = {
    currentDocId: null,
    currentSessionId: null,
    extractionData: null,
    currentFilter: 'all'
};

// Risk Level Configuration
const RISK_CONFIG = {
    HIGH: {
        min: 60,
        max: 100,
        color: '#ef4444',
        label: 'HIGH RISK'
    },
    MEDIUM: {
        min: 30,
        max: 59,
        color: '#f59e0b',
        label: 'MEDIUM RISK'
    },
    LOW: {
        min: 0,
        max: 29,
        color: '#10b981',
        label: 'LOW RISK'
    }
};

// Processing Steps
const PROCESSING_STEPS = [
    { id: 'step1', label: 'Uploading', duration: 2000 },
    { id: 'step2', label: 'Extracting Text', duration: 5000 },
    { id: 'step3', label: 'Analyzing Clauses', duration: 600000 }, // Most time here
    { id: 'step4', label: 'Calculating Risk', duration: 3000 },
    { id: 'step5', label: 'Complete', duration: 1000 }
];

// Utility Functions
const Utils = {
    // Generate unique session ID
    generateSessionId: () => {
        return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    },
    
    // Format file size
    formatFileSize: (bytes) => {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
    },
    
    // Get risk level from score
    getRiskLevel: (score) => {
        if (score >= RISK_CONFIG.HIGH.min) return 'HIGH';
        if (score >= RISK_CONFIG.MEDIUM.min) return 'MEDIUM';
        return 'LOW';
    },
    
    // Get risk color
    getRiskColor: (level) => {
        return RISK_CONFIG[level]?.color || '#6b7280';
    },
    
    // Truncate text
    truncateText: (text, maxLength) => {
        if (!text || text.length <= maxLength) return text;
        return text.substring(0, maxLength) + '...';
    },
    
    // Format timestamp
    formatTimestamp: (timestamp) => {
        const date = new Date(timestamp);
        return date.toLocaleTimeString('en-US', { 
            hour: '2-digit', 
            minute: '2-digit' 
        });
    }
};

// Export for use in other files
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { API_CONFIG, APP_STATE, RISK_CONFIG, PROCESSING_STEPS, Utils };
}
