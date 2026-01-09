// Chat Module
const Chat = {
    isProcessing: false,
    
    init: () => {
        const chatInput = document.getElementById('chatInput');
        const sendBtn = document.getElementById('sendBtn');
        const clearBtn = document.getElementById('clearChatBtn');
        
        // Send message on button click
        sendBtn?.addEventListener('click', () => Chat.sendMessage());
        
        // Send message on Enter key
        chatInput?.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                Chat.sendMessage();
            }
        });
        
        // Clear chat
        clearBtn?.addEventListener('click', () => Chat.clearChat());
        
        // Suggested questions
        document.querySelectorAll('.suggested-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                if (chatInput) {
                    chatInput.value = btn.textContent;
                    Chat.sendMessage();
                }
            });
        });
    },
    
    sendMessage: async () => {
        const chatInput = document.getElementById('chatInput');
        const sendBtn = document.getElementById('sendBtn');
        
        if (!chatInput || !sendBtn) return;
        
        const query = chatInput.value.trim();
        
        if (!query) {
            Toast.error('Please enter a question');
            return;
        }
        
        if (!APP_STATE.currentDocId) {
            Toast.error('No document loaded');
            return;
        }
        
        if (Chat.isProcessing) {
            return;
        }
        
        Chat.isProcessing = true;
        sendBtn.disabled = true;
        
        // Add user message to chat
        Chat.addMessage(query, 'user');
        
        // Clear input
        chatInput.value = '';
        
        // Show typing indicator
        const typingId = Chat.addTypingIndicator();
        
        try {
            // Send to API
            const response = await API.sendChatMessage(
                APP_STATE.currentSessionId,
                APP_STATE.currentDocId,
                query
            );
            
            // Remove typing indicator
            Chat.removeTypingIndicator(typingId);
            
            // Add AI response
            Chat.addMessage(response.answer, 'ai', response.sources);
            
        } catch (error) {
            Chat.removeTypingIndicator(typingId);
            Toast.error('Failed to get response: ' + error.message);
            Chat.addMessage('Sorry, I encountered an error processing your question. Please try again.', 'ai');
        } finally {
            Chat.isProcessing = false;
            sendBtn.disabled = false;
            chatInput.focus();
        }
    },
    
    addMessage: (text, sender, sources = []) => {
        const chatMessages = document.getElementById('chatMessages');
        if (!chatMessages) return;
        
        // Remove welcome message if exists
        const welcome = chatMessages.querySelector('.chat-welcome');
        if (welcome) {
            welcome.remove();
        }
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `chat-message message-${sender}`;
        
        const avatarIcon = sender === 'ai' ? 'robot' : 'user';
        
        // Sources display (for AI messages)
        let sourcesHTML = '';
        if (sender === 'ai' && sources && sources.length > 0) {
            const sourcesList = sources.map(s => {
                if (s.clause_type) {
                    return `${s.clause_type} (${s.risk_level})`;
                }
                return 'Contract text';
            }).join(', ');
            
            sourcesHTML = `<div class="message-sources"><i class="fas fa-info-circle"></i> Sources: ${sourcesList}</div>`;
        }
        
        messageDiv.innerHTML = `
            <div class="message-avatar">
                <i class="fas fa-${avatarIcon}"></i>
            </div>
            <div class="message-content">
                <div class="message-bubble">${Chat.formatMessageText(text)}</div>
                ${sourcesHTML}
            </div>
        `;
        
        chatMessages.appendChild(messageDiv);
        
        // Scroll to bottom
        chatMessages.scrollTop = chatMessages.scrollHeight;
    },
    
    formatMessageText: (text) => {
        // Convert newlines to <br>
        return text.replace(/\n/g, '<br>');
    },
    
    addTypingIndicator: () => {
        const chatMessages = document.getElementById('chatMessages');
        if (!chatMessages) return null;
        
        const typingDiv = document.createElement('div');
        typingDiv.className = 'chat-message message-ai';
        typingDiv.id = 'typing-indicator';
        
        typingDiv.innerHTML = `
            <div class="message-avatar">
                <i class="fas fa-robot"></i>
            </div>
            <div class="message-content">
                <div class="message-bubble">
                    <i class="fas fa-circle-notch fa-spin"></i> Thinking...
                </div>
            </div>
        `;
        
        chatMessages.appendChild(typingDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        
        return 'typing-indicator';
    },
    
    removeTypingIndicator: (id) => {
        const indicator = document.getElementById(id);
        if (indicator) {
            indicator.remove();
        }
    },
    
    clearChat: async () => {
        if (!APP_STATE.currentSessionId) return;
        
        try {
            await API.clearChatSession(APP_STATE.currentSessionId);
            
            // Clear messages
            const chatMessages = document.getElementById('chatMessages');
            if (chatMessages) {
                chatMessages.innerHTML = `
                    <div class="chat-welcome">
                        <i class="fas fa-robot"></i>
                        <p>Ask me anything about this contract. I can help you understand clauses, risks, and specific terms.</p>
                        <div class="suggested-questions">
                            <p class="suggested-label">Suggested questions:</p>
                            <button class="suggested-btn">What is the termination notice period?</button>
                            <button class="suggested-btn">What are the high-risk clauses?</button>
                            <button class="suggested-btn">Is there a liability cap?</button>
                        </div>
                    </div>
                `;
                
                // Re-attach suggested button listeners
                chatMessages.querySelectorAll('.suggested-btn').forEach(btn => {
                    btn.addEventListener('click', () => {
                        const chatInput = document.getElementById('chatInput');
                        if (chatInput) {
                            chatInput.value = btn.textContent;
                            Chat.sendMessage();
                        }
                    });
                });
            }
            
            Toast.success('Chat cleared');
        } catch (error) {
            Toast.error('Failed to clear chat');
        }
    }
};

// Initialize chat when dashboard loads
document.addEventListener('DOMContentLoaded', () => {
    Chat.init();
});
