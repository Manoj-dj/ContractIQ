// Main Application
const App = {
    init: () => {
        console.log('Initializing ContractIQ...');
        
        // Check backend health
        App.checkBackendHealth();
        
        // Setup event listeners
        App.setupEventListeners();
        
        // Initialize session ID
        APP_STATE.currentSessionId = Utils.generateSessionId();
        
        console.log('ContractIQ initialized successfully');
    },
    
    checkBackendHealth: async () => {
        const isHealthy = await API.healthCheck();
        if (!isHealthy) {
            Toast.error('Backend server is not responding. Please ensure it is running on port 8000.');
        }
    },
    
    setupEventListeners: () => {
        // File upload
        const uploadArea = document.getElementById('uploadArea');
        const fileInput = document.getElementById('fileInput');
        const browseBtn = document.getElementById('browseBtn');
        
        // Click to browse
        browseBtn?.addEventListener('click', () => fileInput?.click());
        uploadArea?.addEventListener('click', () => fileInput?.click());
        
        // File input change
        fileInput?.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                App.handleFileUpload(e.target.files[0]);
            }
        });
        
        // Drag and drop
        uploadArea?.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('drag-over');
        });
        
        uploadArea?.addEventListener('dragleave', () => {
            uploadArea.classList.remove('drag-over');
        });
        
        uploadArea?.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('drag-over');
            
            if (e.dataTransfer.files.length > 0) {
                App.handleFileUpload(e.dataTransfer.files[0]);
            }
        });
        
        // Navigation
        document.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const page = link.dataset.page;
                
                if (page === 'docs') {
                    window.open(`${API_CONFIG.BASE_URL}/docs`, '_blank');
                    return;
                }
                
                if (page === 'upload') {
                    App.showSection('upload-section');
                }
            });
        });
        
        // New analysis button
        document.getElementById('newAnalysisBtn')?.addEventListener('click', () => {
            App.resetApplication();
        });
        
        // Export button
        document.getElementById('exportBtn')?.addEventListener('click', () => {
            App.handleExport();
        });
    },
    
    handleFileUpload: async (file) => {
        // Validate file
        if (!file.name.toLowerCase().endsWith('.pdf')) {
            Toast.error('Please upload a PDF file');
            return;
        }
        
        if (file.size > 10 * 1024 * 1024) {
            Toast.error('File size must be less than 10MB');
            return;
        }
        
        console.log('Uploading file:', file.name);
        
        // Show processing section
        App.showSection('processing-section');
        App.updateProcessingStep(0);
        App.updateProcessingInfo(file.name, null);
        
        // Start facts rotation
        FactsManager.startRotation();
        
        try {
            // Step 1: Upload
            App.updateProcessingStep(1);
            const uploadResult = await API.uploadFile(file);
            console.log('Upload result:', uploadResult);
            
            APP_STATE.currentDocId = uploadResult.doc_id;
            App.updateProcessingInfo(uploadResult.filename, uploadResult.num_pages);
            
            Toast.success('File uploaded successfully');
            
            // Wait a bit before extraction
            await App.delay(1000);
            
            // Step 2: Extract text
            App.updateProcessingStep(2);
            await App.delay(2000);
            
            // Step 3: Extract clauses (long process)
            App.updateProcessingStep(3);
            const extractionResult = await API.extractClauses(uploadResult.doc_id);
            console.log('Extraction result:', extractionResult);
            
            APP_STATE.extractionData = extractionResult;
            
            // Step 4: Calculate risk
            App.updateProcessingStep(4);
            await App.delay(2000);
            
            // Step 5: Complete
            App.updateProcessingStep(5);
            await App.delay(1000);
            
            // Stop facts rotation
            FactsManager.stopRotation();
            
            Toast.success('Analysis complete!');
            
            // Show dashboard
            App.showSection('dashboard-section');
            Dashboard.render(extractionResult);
            
        } catch (error) {
            console.error('Upload/Extraction error:', error);
            FactsManager.stopRotation();
            Toast.error(error.message || 'An error occurred during processing');
            
            // Go back to upload
            setTimeout(() => {
                App.showSection('upload-section');
            }, 3000);
        }
    },
    
    updateProcessingStep: (stepNumber) => {
        // Update progress bar
        const progressFill = document.getElementById('progressFill');
        const percentage = (stepNumber / 5) * 100;
        if (progressFill) {
            progressFill.style.width = `${percentage}%`;
        }
        
        // Update steps
        for (let i = 1; i <= 5; i++) {
            const stepElement = document.getElementById(`step${i}`);
            if (stepElement) {
                stepElement.classList.remove('active', 'completed');
                
                if (i < stepNumber) {
                    stepElement.classList.add('completed');
                } else if (i === stepNumber) {
                    stepElement.classList.add('active');
                }
            }
        }
        
        // Update status
        const statusElement = document.getElementById('processingStatus');
        if (statusElement) {
            if (stepNumber === 5) {
                statusElement.textContent = 'Complete';
                statusElement.className = 'status-badge status-complete';
            } else {
                statusElement.textContent = 'Processing';
                statusElement.className = 'status-badge status-processing';
            }
        }
    },
    
    updateProcessingInfo: (filename, pages) => {
        const filenameElement = document.getElementById('processingFileName');
        const pagesElement = document.getElementById('processingPages');
        
        if (filenameElement) {
            filenameElement.textContent = filename;
        }
        
        if (pagesElement && pages) {
            pagesElement.textContent = pages;
        }
    },
    
    showSection: (sectionId) => {
        // Hide all sections
        document.querySelectorAll('.section').forEach(section => {
            section.classList.remove('active');
        });
        
        // Show target section
        const targetSection = document.getElementById(sectionId);
        if (targetSection) {
            targetSection.classList.add('active');
        }
        
        // Update nav
        document.querySelectorAll('.nav-link').forEach(link => {
            link.classList.remove('active');
        });
    },
    
    handleExport: async () => {
        if (!APP_STATE.currentDocId) {
            Toast.error('No document to export');
            return;
        }
        
        try {
            Toast.info('Generating Excel file...');
            await API.exportToExcel(APP_STATE.currentDocId);
            Toast.success('Excel file downloaded successfully');
        } catch (error) {
            Toast.error('Failed to export: ' + error.message);
        }
    },
    
    resetApplication: () => {
        APP_STATE.currentDocId = null;
        APP_STATE.extractionData = null;
        APP_STATE.currentSessionId = Utils.generateSessionId();
        APP_STATE.currentFilter = 'all';
        
        // Reset file input
        const fileInput = document.getElementById('fileInput');
        if (fileInput) fileInput.value = '';
        
        // Show upload section
        App.showSection('upload-section');
        
        Toast.info('Ready for new analysis');
    },
    
    delay: (ms) => new Promise(resolve => setTimeout(resolve, ms))
};

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    App.init();
});
