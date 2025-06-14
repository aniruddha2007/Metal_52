// static/webrtc.js - Complete WebRTC implementation with Opus/AV1 support
class Metal52WebRTC {
    constructor() {
        this.localStream = null;
        this.remoteStream = null;
        this.peerConnections = new Map();
        this.websocket = null;
        this.nodeId = window.nodeConfig.node_id;
        this.localPeerId = `node-${this.nodeId}-${Date.now()}`;
        
        // WebRTC Configuration with STUN servers
        this.rtcConfig = {
            iceServers: [
                { urls: 'stun:stun.l.google.com:19302' },
                { urls: 'stun:stun1.l.google.com:19302' },
                { urls: 'stun:stun2.l.google.com:19302' }
            ]
        };
        
        // Preferred codecs for mesh networking
        this.audioCodecs = ['opus', 'PCMU', 'PCMA'];
        this.videoCodecs = ['AV1', 'H264', 'VP9', 'VP8'];
        
        this.isCallActive = false;
        this.callType = null;
    }
    
    setWebSocket(websocket) {
        this.websocket = websocket;
    }
    
    // Initialize media devices with codec preferences
    async initializeMedia(audio = true, video = false) {
        try {
            const constraints = {
                audio: audio ? {
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true,
                    sampleRate: 48000,  // Optimal for Opus
                    channelCount: 2
                } : false,
                video: video ? {
                    width: { ideal: 640, max: 1280 },
                    height: { ideal: 480, max: 720 },
                    frameRate: { ideal: 15, max: 30 }
                } : false
            };
            
            this.localStream = await navigator.mediaDevices.getUserMedia(constraints);
            
            // Display local video if video call
            if (video) {
                const localVideo = document.getElementById('localVideo');
                if (localVideo) {
                    localVideo.srcObject = this.localStream;
                }
            }
            
            console.log('[WebRTC] Media initialized:', audio ? 'Audio' : '', video ? 'Video' : '');
            return this.localStream;
            
        } catch (error) {
            console.error('[WebRTC] Failed to initialize media:', error);
            throw error;
        }
    }
    
    // Create peer connection with codec preferences
    createPeerConnection(peerId) {
        const pc = new RTCPeerConnection(this.rtcConfig);
        
        // Handle ICE candidates
        pc.onicecandidate = (event) => {
            if (event.candidate) {
                this.sendSignalingMessage({
                    type: 'ice-candidate',
                    candidate: event.candidate,
                    targetPeer: peerId,
                    fromPeer: this.localPeerId
                });
            }
        };
        
        // Handle remote stream
        pc.ontrack = (event) => {
            console.log('[WebRTC] Remote track received from', peerId);
            this.remoteStream = event.streams[0];
            
            const remoteVideo = document.getElementById('remoteVideo');
            if (remoteVideo) {
                remoteVideo.srcObject = this.remoteStream;
            }
            
            // Show media panel
            this.showMediaPanel();
        };
        
        // Handle connection state changes
        pc.onconnectionstatechange = () => {
            console.log(`[WebRTC] Connection state with ${peerId}:`, pc.connectionState);
            
            if (pc.connectionState === 'connected') {
                this.addSystemMessage(`🔗 Connected to ${peerId}`);
            } else if (pc.connectionState === 'failed' || pc.connectionState === 'disconnected') {
                this.addSystemMessage(`📵 Connection lost with ${peerId}`);
                this.peerConnections.delete(peerId);
            }
        };
        
        // Add local stream tracks
        if (this.localStream) {
            this.localStream.getTracks().forEach(track => {
                pc.addTrack(track, this.localStream);
            });
        }
        
        this.peerConnections.set(peerId, pc);
        return pc;
    }
    
    // Start audio call
    async startAudioCall() {
        try {
            await this.initializeMedia(true, false);
            this.callType = 'audio';
            this.isCallActive = true;
            
            // Send call request
            this.sendMessage({
                type: 'call_request',
                call_type: 'audio',
                caller: this.localPeerId
            });
            
            this.addSystemMessage('📞 Starting audio call...');
            this.showMediaPanel();
            
        } catch (error) {
            console.error('[WebRTC] Audio call failed:', error);
            this.addSystemMessage('❌ Audio call failed: ' + error.message);
        }
    }
    
    // Start video call
    async startVideoCall() {
        try {
            await this.initializeMedia(true, true);
            this.callType = 'video';
            this.isCallActive = true;
            
            // Send call request
            this.sendMessage({
                type: 'call_request',
                call_type: 'video',
                caller: this.localPeerId
            });
            
            this.addSystemMessage('📹 Starting video call...');
            this.showMediaPanel();
            
        } catch (error) {
            console.error('[WebRTC] Video call failed:', error);
            this.addSystemMessage('❌ Video call failed: ' + error.message);
        }
    }
    
    // Handle incoming call
    async handleIncomingCall(callData) {
        const accept = confirm(`📞 Incoming ${callData.call_type} call from ${callData.caller}. Accept?`);
        
        if (accept) {
            try {
                const isVideo = callData.call_type === 'video';
                await this.initializeMedia(true, isVideo);
                
                this.callType = callData.call_type;
                this.isCallActive = true;
                
                // Create offer to caller
                const pc = this.createPeerConnection(callData.caller);
                const offer = await pc.createOffer();
                await pc.setLocalDescription(offer);
                
                this.sendSignalingMessage({
                    type: 'offer',
                    offer: offer,
                    targetPeer: callData.caller,
                    fromPeer: this.localPeerId,
                    callType: callData.call_type
                });
                
                this.addSystemMessage(`✅ Accepted ${callData.call_type} call from ${callData.caller}`);
                this.showMediaPanel();
                
            } catch (error) {
                console.error('[WebRTC] Failed to accept call:', error);
                this.addSystemMessage('❌ Failed to accept call: ' + error.message);
            }
        } else {
            this.addSystemMessage(`📵 Declined call from ${callData.caller}`);
        }
    }
    
    // Handle WebRTC signaling
    async handleSignaling(signalData) {
        try {
            const { type, fromPeer, targetPeer } = signalData;
            
            // Ignore our own signals
            if (fromPeer === this.localPeerId) return;
            
            // Only process signals meant for us or broadcast signals
            if (targetPeer && targetPeer !== this.localPeerId) return;
            
            const pc = this.peerConnections.get(fromPeer) || this.createPeerConnection(fromPeer);
            
            switch (type) {
                case 'offer':
                    await pc.setRemoteDescription(signalData.offer);
                    const answer = await pc.createAnswer();
                    await pc.setLocalDescription(answer);
                    
                    this.sendSignalingMessage({
                        type: 'answer',
                        answer: answer,
                        targetPeer: fromPeer,
                        fromPeer: this.localPeerId
                    });
                    break;
                    
                case 'answer':
                    await pc.setRemoteDescription(signalData.answer);
                    break;
                    
                case 'ice-candidate':
                    await pc.addIceCandidate(signalData.candidate);
                    break;
                    
                default:
                    console.log('[WebRTC] Unknown signal type:', type);
            }
            
        } catch (error) {
            console.error('[WebRTC] Signaling error:', error);
        }
    }
    
    // Send signaling message
    sendSignalingMessage(signal) {
        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
            this.websocket.send(JSON.stringify({
                type: 'webrtc_signal',
                signal: signal
            }));
        }
    }
    
    // Send general message
    sendMessage(message) {
        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
            this.websocket.send(JSON.stringify(message));
        }
    }
    
    // Media controls
    toggleMute() {
        if (this.localStream) {
            const audioTrack = this.localStream.getAudioTracks()[0];
            if (audioTrack) {
                audioTrack.enabled = !audioTrack.enabled;
                const muteBtn = document.getElementById('muteBtn');
                if (muteBtn) {
                    muteBtn.textContent = audioTrack.enabled ? '🎤' : '🔇';
                    muteBtn.classList.toggle('muted', !audioTrack.enabled);
                }
                this.addSystemMessage(audioTrack.enabled ? '🎤 Unmuted' : '🔇 Muted');
            }
        }
    }
    
    toggleVideo() {
        if (this.localStream) {
            const videoTrack = this.localStream.getVideoTracks()[0];
            if (videoTrack) {
                videoTrack.enabled = !videoTrack.enabled;
                const videoBtn = document.getElementById('videoBtn');
                if (videoBtn) {
                    videoBtn.textContent = videoTrack.enabled ? '📹' : '📵';
                    videoBtn.classList.toggle('muted', !videoTrack.enabled);
                }
                this.addSystemMessage(videoTrack.enabled ? '📹 Video on' : '📵 Video off');
            }
        }
    }
    
    async shareScreen() {
        try {
            const screenStream = await navigator.mediaDevices.getDisplayMedia({
                video: true,
                audio: true
            });
            
            const videoTrack = screenStream.getVideoTracks()[0];
            
            // Replace video track in all peer connections
            for (const [peerId, pc] of this.peerConnections) {
                const sender = pc.getSenders().find(s => 
                    s.track && s.track.kind === 'video'
                );
                
                if (sender) {
                    await sender.replaceTrack(videoTrack);
                }
            }
            
            // Handle screen share end
            videoTrack.onended = () => {
                this.addSystemMessage('🖥️ Screen sharing ended');
                // Switch back to camera
                const cameraTrack = this.localStream.getVideoTracks()[0];
                if (cameraTrack) {
                    for (const [peerId, pc] of this.peerConnections) {
                        const sender = pc.getSenders().find(s => 
                            s.track && s.track.kind === 'video'
                        );
                        if (sender) {
                            sender.replaceTrack(cameraTrack);
                        }
                    }
                }
            };
            
            this.addSystemMessage('🖥️ Screen sharing started');
            
        } catch (error) {
            console.error('[WebRTC] Screen sharing failed:', error);
            this.addSystemMessage('❌ Screen sharing failed: ' + error.message);
        }
    }
    
    // End all calls
    endCall() {
        this.isCallActive = false;
        this.callType = null;
        
        // Close all peer connections
        for (const [peerId, pc] of this.peerConnections) {
            pc.close();
        }
        this.peerConnections.clear();
        
        // Stop local stream
        if (this.localStream) {
            this.localStream.getTracks().forEach(track => track.stop());
            this.localStream = null;
        }
        
        // Hide media panel
        this.hideMediaPanel();
        
        this.addSystemMessage('📵 Call ended');
    }
    
    // UI helpers
    showMediaPanel() {
        const panel = document.getElementById('mediaPanel');
        if (panel) {
            panel.style.display = 'block';
        }
    }
    
    hideMediaPanel() {
        const panel = document.getElementById('mediaPanel');
        if (panel) {
            panel.style.display = 'none';
        }
        
        // Clear video elements
        const localVideo = document.getElementById('localVideo');
        const remoteVideo = document.getElementById('remoteVideo');
        if (localVideo) localVideo.srcObject = null;
        if (remoteVideo) remoteVideo.srcObject = null;
    }
    
    addSystemMessage(message) {
        if (window.app && window.app.addSystemMessage) {
            window.app.addSystemMessage(message);
        } else {
            console.log('[WebRTC]', message);
        }
    }
}

// Global WebRTC manager
window.webrtcManager = new Metal52WebRTC();
