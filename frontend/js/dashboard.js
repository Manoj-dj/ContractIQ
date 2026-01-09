// Dashboard Module
const Dashboard = {
    render: (data) => {
        console.log('Rendering dashboard with data:', data);
        
        // Update document name
        const filenameElement = document.getElementById('dashboardFileName');
        if (filenameElement) {
            filenameElement.textContent = data.filename;
        }
        
        // Render risk overview
        Dashboard.renderRiskOverview(data);
        
        // Render clauses list
        Dashboard.renderClausesList(data.clauses);
        
        // Setup filters
        Dashboard.setupFilters();
    },
    
    renderRiskOverview: (data) => {
        // Overall risk score with gauge
        const scoreElement = document.getElementById('overallScore');
        const levelElement = document.getElementById('overallRiskLevel');
        const gaugeFill = document.getElementById('gaugeFill');
        
        if (scoreElement) {
            scoreElement.textContent = Math.round(data.overall_risk_score);
        }
        
        if (levelElement) {
            levelElement.textContent = data.risk_level;
            levelElement.style.color = Utils.getRiskColor(data.risk_level);
        }
        
        // Animate gauge
        if (gaugeFill) {
            const percentage = data.overall_risk_score / 100;
            const offset = 251.2 - (251.2 * percentage);
            
            setTimeout(() => {
                gaugeFill.style.strokeDashoffset = offset;
                gaugeFill.style.stroke = Utils.getRiskColor(data.risk_level);
            }, 300);
        }
        
        // Risk counts
        document.getElementById('highRiskCount').textContent = data.high_risk_count;
        document.getElementById('mediumRiskCount').textContent = data.medium_risk_count;
        document.getElementById('lowRiskCount').textContent = data.low_risk_count;
        document.getElementById('missingCriticalCount').textContent = data.missing_critical_count;
    },
    
    renderClausesList: (clauses) => {
        const clausesList = document.getElementById('clausesList');
        if (!clausesList) return;
        
        clausesList.innerHTML = '';
        
        // Sort clauses: HIGH risk first, then MEDIUM, then LOW, then NOT_FOUND
        const sortedClauses = [...clauses].sort((a, b) => {
            const order = { 'HIGH': 0, 'MEDIUM': 1, 'LOW': 2, 'NOT_FOUND': 3 };
            return order[a.risk_level] - order[b.risk_level];
        });
        
        sortedClauses.forEach(clause => {
            const clauseElement = Dashboard.createClauseElement(clause);
            clausesList.appendChild(clauseElement);
        });
    },
    
    createClauseElement: (clause) => {
        const div = document.createElement('div');
        div.className = 'clause-item';
        div.dataset.riskLevel = clause.risk_level.toLowerCase();
        
        // Risk badge HTML
        let riskBadgeClass = 'risk-not-found';
        if (clause.risk_level === 'HIGH') riskBadgeClass = 'risk-high';
        else if (clause.risk_level === 'MEDIUM') riskBadgeClass = 'risk-medium';
        else if (clause.risk_level === 'LOW') riskBadgeClass = 'risk-low';
        
        // Confidence badge (only if found)
        const confidenceBadge = clause.found ? 
            `<span class="confidence-badge">${Math.round(clause.confidence * 100)}% confidence</span>` : 
            '';
        
        // Clause text
        const clauseText = clause.found && clause.extracted_text ? 
            Utils.truncateText(clause.extracted_text, 200) : 
            'Clause not found in contract';
        
        const textClass = clause.found ? 'clause-text' : 'clause-text not-found';
        
        // Page and location info
        const metaInfo = clause.found ? `
            <div class="clause-meta">
                ${clause.page_number ? `<span><i class="fas fa-file"></i> Page ${clause.page_number}</span>` : ''}
                ${clause.char_start !== null ? `<span><i class="fas fa-map-marker-alt"></i> Position ${clause.char_start}-${clause.char_end}</span>` : ''}
            </div>
        ` : '';
        
        // Reliability warning
        const reliabilityWarning = clause.reliability_flag ? `
            <div class="reliability-warning">
                <i class="fas fa-exclamation-triangle"></i>
                <span>${clause.reliability_flag === 'REQUIRES_HUMAN_VERIFICATION' ? 
                    'Low confidence - Requires human verification' : 
                    'Critical clause missing - Review required'}</span>
            </div>
        ` : '';
        
        div.innerHTML = `
            <div class="clause-header">
                <h4 class="clause-title">${clause.clause_type}</h4>
                <div class="clause-badges">
                    <span class="risk-badge ${riskBadgeClass}">${clause.risk_level} (${clause.risk_score}/100)</span>
                    ${confidenceBadge}
                </div>
            </div>
            <p class="${textClass}">${clauseText}</p>
            ${metaInfo}
            ${reliabilityWarning}
        `;
        
        return div;
    },
    
    setupFilters: () => {
        const filterButtons = document.querySelectorAll('.filter-btn');
        
        filterButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                // Update active state
                filterButtons.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                
                // Get filter value
                const filter = btn.dataset.filter;
                APP_STATE.currentFilter = filter;
                
                // Filter clauses
                Dashboard.filterClauses(filter);
            });
        });
    },
    
    filterClauses: (filter) => {
        const clauseItems = document.querySelectorAll('.clause-item');
        
        clauseItems.forEach(item => {
            const riskLevel = item.dataset.riskLevel;
            
            if (filter === 'all') {
                item.classList.remove('hidden');
            } else if (filter === 'high') {
                item.classList.toggle('hidden', riskLevel !== 'high');
            } else if (filter === 'medium') {
                item.classList.toggle('hidden', riskLevel !== 'medium');
            } else if (filter === 'low') {
                item.classList.toggle('hidden', riskLevel !== 'low');
            } else if (filter === 'missing') {
                item.classList.toggle('hidden', riskLevel !== 'not_found');
            }
        });
    }
};
