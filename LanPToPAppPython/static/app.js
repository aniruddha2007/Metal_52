// static/app.js - Complete working implementation
class Metal52App {
    constructor() {
        this.websocket = null;
        this.nodeId = window.nodeConfig ? window.nodeConfig.node_id : 1;
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
        setTimeout(() => {
            if (window.webrtcManager) {
                window.webrtcManager.setWebSocket(this.websocket);
            }
        }, 1000);
    }

    connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/chat`;

        this.websocket = new WebSocket(wsUrl);

        this.websocket.onopen = (event) => {
            console.log('[WS] Connected to Metal-52 Node');
            this.updateNodeStatus('CONNECTED');
            this.reconnectAttempts = 0;
            
            // Connect WebRTC manager
            if (window.webrtcManager) {
                window.webrtcManager.setWebSocket(this.websocket);
            }
        };

        this.websocket.onmessage = (event) => {
            this.handleWebSocketMessage(event.data);
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
        try {
            const message = JSON.parse(data);
            
            switch (message.type) {
                case 'chat':
                    this.addChatMessage(message.sender, message.message, message.timestamp);
                    break;
                case 'udp_message':
                    this.addChatMessage(message.sender, message.message, message.timestamp);
                    break;
                case 'system':
                    this.addSystemMessage(message.message);
                    break;
                case 'call_request':
                    console.log('[WS] Call request received:', message);
                    if (window.webrtcManager) {
                        window.webrtcManager.handleIncomingCall(message);
                    }
                    break;
                case 'webrtc_signal':
                    console.log('[WS] WebRTC signal received:', message.signal?.type);
                    if (window.webrtcManager) {
                        window.webrtcManager.handleWebRTCSignaling(message.signal);
                    }
                    break;
                default:
                    this.addChatMessage('Network', data, new Date().toISOString());
            }
        } catch (error) {
            console.error('[WS] Message parse error:', error);
            this.addChatMessage('Network', data, new Date().toISOString());
        }
    }

    sendMessage(message) {
        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
            this.websocket.send(message);
        }
    }

    addChatMessage(sender, message, timestamp) {
        const messagesContainer = document.getElementById('chatMessages');
        if (!messagesContainer) return;
        
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
        if (!messagesContainer) return;
        
        const messageElement = document.createElement('div');
        messageElement.className = 'system-message';
        
        const timestamp = new Date().toLocaleTimeString();
        messageElement.innerHTML = `
            <span class="timestamp">[${timestamp}]</span> ${this.escapeHtml(message)}
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
        const connectionsElement = document.getElementById('activeConnections');
        if (connectionsElement) {
            connectionsElement.textContent = this.websocket?.readyState === WebSocket.OPEN ? '1' : '0';
        }

        const messageInput = document.getElementById('messageInput');
        const charCount = document.getElementById('charCount');
        if (messageInput && charCount) {
            charCount.textContent = messageInput.value.length;
        }
    }

    setupEventListeners() {
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

        setInterval(() => {
            this.updateUI();
        }, 5000);
    }

    attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            const delay = Math.pow(2, this.reconnectAttempts) * 1000;
            console.log(`[WS] Reconnecting in ${delay}ms`);
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

function initializeAudioCall() {
    console.log('[APP] Starting audio call');
    if (window.webrtcManager) {
        window.webrtcManager.startAudioCall();
    } else {
        window.app.addSystemMessage('❌ WebRTC not ready');
    }
}

function initializeVideoCall() {
    console.log('[APP] Starting video call');
    if (window.webrtcManager) {
        window.webrtcManager.startVideoCall();
    } else {
        window.app.addSystemMessage('❌ WebRTC not ready');
    }
}

function endCall() {
    if (window.webrtcManager) {
        window.webrtcManager.endCall();
    }
}

function toggleMute() {
    if (window.webrtcManager) {
        window.webrtcManager.toggleMute();
    }
}

function toggleVideo() {
    if (window.webrtcManager) {
        window.webrtcManager.toggleVideo();
    }
}

function acceptCall() {
    if (window.webrtcManager) {
        window.webrtcManager.acceptIncomingCall();
    }
}

function declineCall() {
    if (window.webrtcManager) {
        window.webrtcManager.pendingCall = null;
        window.webrtcManager.hideCallModal();
        window.app.addSystemMessage('📵 Call declined');
    }
}

function clearChat() {
    const messagesContainer = document.getElementById('chatMessages');
    if (messagesContainer) {
        messagesContainer.innerHTML = `
            <div class="system-message">
                <span class="timestamp">[SYSTEM]</span> Chat history cleared
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

function attachFile() {
    const input = document.createElement('input');
    input.type = 'file';
    input.onchange = (e) => {
        const file = e.target.files[0];
        if (file) {
            window.app.addSystemMessage(`File selected: ${file.name} (${file.size} bytes)`);
        }
    };
    input.click();
}

function emergencyStop() {
    if (confirm('🚨 EMERGENCY STOP\n\nThis will terminate all connections. Continue?')) {
        if (window.webrtcManager) window.webrtcManager.endCall();
        if (window.app.websocket) window.app.websocket.close();
        clearChat();
        window.app.addSystemMessage('🚨 EMERGENCY STOP ACTIVATED');
        window.app.updateNodeStatus('EMERGENCY');
    }
}

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    console.log('Metal-52 initializing...');
    
    // Create node configuration if missing
    if (!window.nodeConfig) {
        window.nodeConfig = {
            node_id: 1,
            local_ip: '127.0.0.1',
            ports: { web: 8001, udp: 9002, audio: 5061, video: 5057 }
        };
    }
    
    window.app = new Metal52App();
});
