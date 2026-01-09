// Contract Facts and Legal Tips
const CONTRACT_FACTS = [
    {
        title: "Did you know?",
        text: "The average commercial contract contains 50-70 pages and takes legal professionals 2-4 hours to review thoroughly."
    },
    {
        title: "Legal Insight",
        text: "Indemnity clauses are among the most negotiated terms in contracts. One-sided indemnity can expose you to unlimited liability."
    },
    {
        title: "Contract Tip",
        text: "Always check the governing law clause. Different jurisdictions have vastly different legal interpretations and enforcement mechanisms."
    },
    {
        title: "Risk Factor",
        text: "Contracts without a liability cap can expose your company to financial risks far exceeding the contract value."
    },
    {
        title: "Fun Fact",
        text: "The longest contract ever written was an insurance policy with over 40,000 words - longer than many novels!"
    },
    {
        title: "Legal Wisdom",
        text: "Termination for convenience clauses give you the flexibility to exit a contract early, but they're often missing from vendor agreements."
    },
    {
        title: "Contract Insight",
        text: "Auto-renewal clauses with short notice periods are a common trap. Some require 180+ days notice to cancel!"
    },
    {
        title: "Did you know?",
        text: "IP ownership clauses determine who owns work created during the contract. Ambiguous language can lead to expensive disputes."
    },
    {
        title: "Legal Tip",
        text: "Non-compete clauses lasting more than 2 years are often considered unreasonable and may not be enforceable in court."
    },
    {
        title: "Industry Standard",
        text: "Best-in-class SaaS contracts include a liability cap of 12 months of fees paid. Anything less is considered vendor-friendly."
    },
    {
        title: "Risk Alert",
        text: "Audit rights clauses without time limits or advance notice requirements can disrupt your business operations."
    },
    {
        title: "Contract Wisdom",
        text: "Force majeure clauses became crucial during COVID-19. They excuse performance during unforeseeable events."
    },
    {
        title: "Legal Insight",
        text: "Confidentiality clauses typically last 3-5 years post-termination. Perpetual confidentiality is rare and hard to enforce."
    },
    {
        title: "Fun Fact",
        text: "Studies show that 60% of contracts contain at least one clause that contradicts another clause in the same document."
    },
    {
        title: "Best Practice",
        text: "Notice periods for termination should match payment cycles. Monthly payments should have monthly notice periods."
    },
    {
        title: "Did you know?",
        text: "The CUAD dataset (Contract Understanding Atticus Dataset) contains 510 contracts with over 13,000 expert annotations."
    },
    {
        title: "Contract Fact",
        text: "Most Favored Nation clauses ensure you get the best pricing. They're powerful negotiating tools but hard to enforce."
    },
    {
        title: "Legal Standard",
        text: "Liquidated damages must be a reasonable estimate of actual losses. Excessive amounts may be deemed unenforceable penalties."
    },
    {
        title: "Risk Insight",
        text: "Change of control clauses can give vendors the right to terminate if your company is acquired. Review these carefully."
    },
    {
        title: "Contract Tip",
        text: "Anti-assignment clauses prevent you from transferring the contract. This can complicate mergers and reorganizations."
    },
    {
        title: "Industry Data",
        text: "Legal AI tools can reduce contract review time by 60-80%, from hours to minutes, while improving accuracy."
    },
    {
        title: "Legal Fact",
        text: "Delaware law is chosen in 60%+ of US corporate contracts due to its well-developed business court system."
    },
    {
        title: "Best Practice",
        text: "Warranties should have defined durations. Unlimited warranty periods create indefinite liability exposure."
    },
    {
        title: "Did you know?",
        text: "Third-party beneficiary clauses can give non-signatories the right to enforce contract terms. Use them carefully."
    },
    {
        title: "Contract Wisdom",
        text: "Post-termination services clauses ensure smooth transitions. They're critical for mission-critical systems."
    }
];

// Facts Manager
const FactsManager = {
    currentIndex: 0,
    intervalId: null,
    
    // Get random fact
    getRandomFact: () => {
        const randomIndex = Math.floor(Math.random() * CONTRACT_FACTS.length);
        return CONTRACT_FACTS[randomIndex];
    },
    
    // Display fact
    displayFact: (fact) => {
        const titleElement = document.getElementById('factTitle');
        const textElement = document.getElementById('factText');
        
        if (titleElement && textElement) {
            // Fade out
            titleElement.style.opacity = '0';
            textElement.style.opacity = '0';
            
            setTimeout(() => {
                titleElement.textContent = fact.title;
                textElement.textContent = fact.text;
                
                // Fade in
                titleElement.style.transition = 'opacity 0.5s ease';
                textElement.style.transition = 'opacity 0.5s ease';
                titleElement.style.opacity = '1';
                textElement.style.opacity = '1';
            }, 300);
        }
    },
    
    // Start rotating facts
    startRotation: () => {
        // Display first fact immediately
        FactsManager.displayFact(FactsManager.getRandomFact());
        
        // Rotate every 8 seconds
        FactsManager.intervalId = setInterval(() => {
            FactsManager.displayFact(FactsManager.getRandomFact());
        }, 8000);
    },
    
    // Stop rotating facts
    stopRotation: () => {
        if (FactsManager.intervalId) {
            clearInterval(FactsManager.intervalId);
            FactsManager.intervalId = null;
        }
    }
};
