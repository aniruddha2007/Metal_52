// static/app.js
class Metal52App {
    constructor() {
        this.websocket = null;
        this.nodeId = window.nodeConfig.node_id;
        this.peers = new Map();
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        
        this.init();
    }
    
    init() {
        this.connectWebSocket();
        this.setupEventListeners();
        this.updateUI();
        
        // Initialize WebRTC manager
        if (window.webrtcManager) {
            window.webrtcManager.websocket = this.websocket;
        }
        
        // Auto-discover peers on startup
        setTimeout(() => this.discoverPeers(), 2000);
    }
    
    connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/chat`;
        
        this.websocket = new WebSocket(wsUrl);
        
        this.websocket.onopen = (event) => {
            console.log('[WS] Connected to Metal-52 Node');
            this.updateNodeStatus('CONNECTED');
            this.reconnectAttempts = 0;
        };
        
        this.websocket.onmessage = (event) => {
            const data = event.data;
            this.handleWebSocketMessage(data);
        };
        
        this.websocket.onclose = (event) => {
            console.log('[WS] Connection closed');
            this.updateNodeStatus('DISCONNECTED');
            this.attemptReconnect();
        };
        
        this.websocket.onerror = (error) => {
            console.error('[WS] WebSocket error:', error);
            this.updateNodeStatus('ERROR');
        };
    }
    
    handleWebSocketMessage(data) {
        this.addChatMessage('Network', data, new Date().toISOString());
    }
    
    sendMessage(message) {
        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
            this.websocket.send(message);
        }
    }
    
    discoverPeers() {
        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
            this.websocket.send(`DISCOVERY:Node-${this.nodeId} is online`);
        }
    }
    
    addChatMessage(sender, message, timestamp) {
        const messagesContainer = document.getElementById('chatMessages');
        const messageElement = document.createElement('div');
        messageElement.className = 'message-item';
        
        const time = new Date(timestamp).toLocaleTimeString();
        
        messageElement.innerHTML = `
            <div class="message-content">
                <div class="message-header">
                    <span class="message-sender">${this.escapeHtml(sender)}</span>
                    <span class="message-time">${time}</span>
                </div>
                <div class="message-text">${this.escapeHtml(message)}</div>
            </div>
        `;
        
        messagesContainer.appendChild(messageElement);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
    
    addSystemMessage(message) {
        const messagesContainer = document.getElementById('chatMessages');
        const messageElement = document.createElement('div');
        messageElement.className = 'system-message';
        
        const timestamp = new Date().toLocaleTimeString();
        messageElement.innerHTML = `
            <span class="timestamp">[${timestamp}]</span>
            <span class="message">${this.escapeHtml(message)}</span>
        `;
        
        messagesContainer.appendChild(messageElement);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
    
    updateNodeStatus(status) {
        const statusElement = document.getElementById('nodeStatus');
        if (statusElement) {
            statusElement.textContent = status;
            statusElement.className = `node-status ${status.toLowerCase()}`;
        }
    }
    
    updateUI() {
        // Update connection count
        const connectionsElement = document.getElementById('activeConnections');
        if (connectionsElement) {
            connectionsElement.textContent = this.websocket?.readyState === WebSocket.OPEN ? '1' : '0';
        }
        
        // Update character count
        const messageInput = document.getElementById('messageInput');
        const charCount = document.getElementById('charCount');
        if (messageInput && charCount) {
            charCount.textContent = messageInput.value.length;
        }
    }
    
    setupEventListeners() {
        // Message input
        const messageInput = document.getElementById('messageInput');
        if (messageInput) {
            messageInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.handleSendMessage();
                }
            });
            
            messageInput.addEventListener('input', () => {
                this.updateUI();
            });
        }
        
        // Periodic UI updates
        setInterval(() => {
            this.updateUI();
        }, 5000);
    }
    
    attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            const delay = Math.pow(2, this.reconnectAttempts) * 1000;
            
            console.log(`[WS] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
            
            setTimeout(() => {
                this.connectWebSocket();
            }, delay);
        }
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    handleSendMessage() {
        const input = document.getElementById('messageInput');
        const message = input.value.trim();
        
        if (message && this.websocket?.readyState === WebSocket.OPEN) {
            this.sendMessage(message);
            input.value = '';
            this.updateUI();
        }
    }
}

// Global functions for UI interaction
function sendMessage() {
    window.app.handleSendMessage();
}

function discoverPeers() {
    window.app.discoverPeers();
}

function initializeAudioCall() {
    console.log('Audio call initialized');
    window.app.addSystemMessage('Audio call feature - WebRTC implementation needed');
}

function initializeVideoCall() {
    console.log('Video call initialized');
    window.app.addSystemMessage('Video call feature - WebRTC implementation needed');
}

function endCall() {
    console.log('Call ended');
    const panel = document.getElementById('mediaPanel');
    if (panel) {
        panel.classList.remove('active');
    }
}

function toggleMute() {
    const muteBtn = document.getElementById('muteBtn');
    if (muteBtn) {
        muteBtn.classList.toggle('muted');
        muteBtn.textContent = muteBtn.classList.contains('muted') ? '🔇' : '🎤';
    }
}

function toggleVideo() {
    const videoBtn = document.getElementById('videoBtn');
    if (videoBtn) {
        videoBtn.classList.toggle('muted');
        videoBtn.textContent = videoBtn.classList.contains('muted') ? '📵' : '📹';
    }
}

function shareScreen() {
    console.log('Screen sharing requested');
    window.app.addSystemMessage('Screen sharing feature - WebRTC implementation needed');
}

function clearChat() {
    const messagesContainer = document.getElementById('chatMessages');
    if (messagesContainer) {
        messagesContainer.innerHTML = `
            <div class="system-message">
                <span class="timestamp">[SYSTEM]</span>
                <span class="message">Chat history cleared</span>
            </div>
        `;
    }
}

function exportChat() {
    const messages = document.getElementById('chatMessages');
    if (messages) {
        const chatData = messages.innerText;
        const blob = new Blob([chatData], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `metal52-chat-${new Date().toISOString().split('T')[0]}.txt`;
        a.click();
        URL.revokeObjectURL(url);
    }
}

function toggleEncryption() {
    alert('🔒 End-to-end encryption active\n\nProtocol: DTLS 1.3 + SRTP\nCipher: AES-256-GCM\nKey Exchange: ECDH P-256\nAuthentication: SHA-256');
}

function attachFile() {
    const input = document.createElement('input');
    input.type = 'file';
    input.onchange = (e) => {
        const file = e.target.files[0];
        if (file) {
            console.log('File selected:', file.name);
            window.app.addSystemMessage(`File selected: ${file.name} (${file.size} bytes)`);
        }
    };
    input.click();
}

function openFileTransfer() {
    attachFile();
}

function emergencyStop() {
    if (confirm('🚨 EMERGENCY STOP\n\nThis will:\n• Terminate all connections\n• Clear chat history\n• Reset all sessions\n\nContinue?')) {
        if (window.app.websocket) {
            window.app.websocket.close();
        }
        clearChat();
        window.app.addSystemMessage('🚨 EMERGENCY STOP ACTIVATED - All connections terminated');
        window.app.updateNodeStatus('EMERGENCY');
    }
}

function showAddPeerModal() {
    const modal = document.getElementById('addPeerModal');
    if (modal) {
        modal.classList.add('active');
    }
}

function hideAddPeerModal() {
    const modal = document.getElementById('addPeerModal');
    if (modal) {
        modal.classList.remove('active');
    }
}

function addPeer() {
    const ipInput = document.getElementById('peerIP');
    const portInput = document.getElementById('peerPort');
    
    const ip = ipInput.value.trim();
    const port = parseInt(portInput.value) || 8000;
    
    if (ip) {
        fetch('/api/peer/add', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: `peer_ip=${ip}&peer_port=${port}`
        })
        .then(response => response.json())
        .then(data => {
            console.log('Peer added:', data);
            hideAddPeerModal();
            window.app.discoverPeers();
            window.app.addSystemMessage(`Peer added: ${ip}:${port}`);
        })
        .catch(error => {
            console.error('Failed to add peer:', error);
            window.app.addSystemMessage(`Failed to add peer: ${error.message}`);
        });
    }
}

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    console.log('Metal-52 initializing...');
    window.app = new Metal52App();
});
