// static/webrtc.js - Complete working implementation
class Metal52WebRTC {
    constructor() {
        this.localStream = null;
        this.remoteStream = null;
        this.peerConnection = null;
        this.websocket = null;
        this.nodeId = window.nodeConfig ? window.nodeConfig.node_id : 1;
        this.localPeerId = `node-${this.nodeId}`;
        
        this.rtcConfig = {
            iceServers: [
                { urls: 'stun:stun.l.google.com:19302' },
                { urls: 'stun:stun1.l.google.com:19302' }
            ]
        };
        
        this.isCallActive = false;
        this.callType = null;
        this.pendingCall = null;
        this.isCaller = false;
        this.signalingQueue = [];
        
        console.log('[WebRTC] Manager initialized for Node', this.nodeId);
    }
    
    setWebSocket(websocket) {
        this.websocket = websocket;
        console.log('[WebRTC] WebSocket connected');
        this.processSignalingQueue();
    }
    
    createPeerConnection() {
        if (this.peerConnection) {
            this.peerConnection.close();
        }
        
        this.peerConnection = new RTCPeerConnection(this.rtcConfig);
        
        // CRITICAL: Enhanced ontrack handler (from search result [4])
        this.peerConnection.ontrack = (event) => {
            console.log('[WebRTC] 🎉 ONTRACK EVENT FIRED!');
            console.log('[WebRTC] Track details:', {
                kind: event.track.kind,
                enabled: event.track.enabled,
                readyState: event.track.readyState,
                muted: event.track.muted,  // Check muted state (search result [5])
                streams: event.streams.length
            });
            
            if (event.streams && event.streams[0]) {
                this.remoteStream = event.streams[0];
                console.log('[WebRTC] Remote stream assigned');
                this.assignRemoteMedia();
            }
        };
        
        this.peerConnection.onicecandidate = (event) => {
            if (event.candidate) {
                console.log('[WebRTC] 📡 Sending ICE candidate:', event.candidate.type);
                this.sendSignalingMessage({
                    type: 'ice-candidate',
                    candidate: event.candidate,
                    from: this.localPeerId
                });
            } else {
                console.log('[WebRTC] ✅ ICE gathering complete');
            }
        };
        
        this.peerConnection.onconnectionstatechange = () => {
            const state = this.peerConnection.connectionState;
            console.log('[WebRTC] 🔄 Connection state changed to:', state);
            
            if (state === 'connected') {
                this.addSystemMessage('🔗 WebRTC connected successfully');
                this.debugConnectionState();
            } else if (state === 'failed') {
                this.addSystemMessage('❌ WebRTC connection failed');
            }
        };
        
        this.peerConnection.oniceconnectionstatechange = () => {
            console.log('[WebRTC] 🧊 ICE connection state:', this.peerConnection.iceConnectionState);
        };
        
        this.peerConnection.onsignalingstatechange = () => {
            console.log('[WebRTC] 📡 Signaling state:', this.peerConnection.signalingState);
        };
        
        console.log('[WebRTC] ✅ Peer connection created with enhanced handlers');
    }
    
    // Enhanced debugging method
    debugConnectionState() {
        console.log('[WebRTC] 🔍 Connection Debug:');
        console.log('- Local stream tracks:', this.localStream ? this.localStream.getTracks().length : 0);
        console.log('- Remote stream tracks:', this.remoteStream ? this.remoteStream.getTracks().length : 0);
        
        if (this.localStream) {
            this.localStream.getTracks().forEach((track, i) => {
                console.log(`  Local track ${i}:`, {
                    kind: track.kind,
                    enabled: track.enabled,
                    readyState: track.readyState,
                    muted: track.muted
                });
            });
        }
        
        if (this.remoteStream) {
            this.remoteStream.getTracks().forEach((track, i) => {
                console.log(`  Remote track ${i}:`, {
                    kind: track.kind,
                    enabled: track.enabled,
                    readyState: track.readyState,
                    muted: track.muted
                });
            });
        }
    }
    
    assignRemoteMedia() {
        const remoteVideo = document.getElementById('remoteVideo');
        if (!remoteVideo || !this.remoteStream) {
            console.error('[WebRTC] Missing video element or stream');
            return;
        }
        
        console.log('[WebRTC] 📺 Assigning remote stream');
        
        // Debug stream contents
        const videoTracks = this.remoteStream.getVideoTracks();
        const audioTracks = this.remoteStream.getAudioTracks();
        
        console.log(`[WebRTC] Remote stream: ${videoTracks.length} video, ${audioTracks.length} audio tracks`);
        
        // Check for muted tracks (search result [5])
        videoTracks.forEach((track, i) => {
            console.log(`[WebRTC] Video track ${i}:`, {
                enabled: track.enabled,
                readyState: track.readyState,
                muted: track.muted,
                label: track.label
            });
            
            // Ensure track is enabled and not muted
            if (track.muted) {
                console.warn('[WebRTC] Video track is muted!');
            }
        });
        
        audioTracks.forEach((track, i) => {
            console.log(`[WebRTC] Audio track ${i}:`, {
                enabled: track.enabled,
                readyState: track.readyState,
                muted: track.muted,
                label: track.label
            });
            
            // CRITICAL: Check if audio track is muted (search result [5])
            if (track.muted) {
                console.warn('[WebRTC] Audio track is muted!');
            }
        });
        
        // Modern srcObject assignment
        remoteVideo.srcObject = this.remoteStream;
        remoteVideo.muted = false; // CRITICAL: Don't mute remote video for audio
        
        // Enhanced play handling
        remoteVideo.play().then(() => {
            console.log('[WebRTC] ✅ Remote video playing');
            this.addSystemMessage('📹 Remote video connected');
            if (audioTracks.length > 0) {
                this.addSystemMessage('🔊 Remote audio connected');
            }
        }).catch(error => {
            console.error('[WebRTC] ❌ Remote video play failed:', error);
            this.addSystemMessage('❌ Video play failed');
        });
    }
    
    // FIXED: Complete audio call implementation
    async startAudioCall() {
        try {
            console.log('[WebRTC] 🚀 Starting audio call...');
            this.createPeerConnection();
            await this.initializeMedia(true, false); // Audio only
            
            this.callType = 'audio';
            this.isCallActive = true;
            this.isCaller = true;
            
            console.log('[WebRTC] 📤 Sending audio call request');
            this.sendMessage({
                type: 'call_request',
                call_type: 'audio',
                caller: this.localPeerId
            });
            
            this.addSystemMessage('📞 Starting audio call...');
            this.showMediaPanel();
            
        } catch (error) {
            console.error('[WebRTC] ❌ Audio call failed:', error);
            this.addSystemMessage('❌ Audio call failed: ' + error.message);
        }
    }
    
    async startVideoCall() {
        try {
            console.log('[WebRTC] 🚀 Starting video call...');
            this.createPeerConnection();
            await this.initializeMedia(true, true); // Both audio and video
            
            this.callType = 'video';
            this.isCallActive = true;
            this.isCaller = true;
            
            console.log('[WebRTC] 📤 Sending video call request');
            this.sendMessage({
                type: 'call_request',
                call_type: 'video',
                caller: this.localPeerId
            });
            
            this.addSystemMessage('📹 Starting video call...');
            this.showMediaPanel();
            
        } catch (error) {
            console.error('[WebRTC] ❌ Video call failed:', error);
            this.addSystemMessage('❌ Video call failed: ' + error.message);
        }
    }
    
    async acceptIncomingCall() {
        if (!this.pendingCall) return;
        
        try {
            const callData = this.pendingCall;
            this.pendingCall = null;
            
            console.log('[WebRTC] ✅ Accepting call from:', callData.caller);
            this.createPeerConnection();
            
            const isVideo = callData.call_type === 'video';
            await this.initializeMedia(true, isVideo);
            
            this.callType = callData.call_type;
            this.isCallActive = true;
            this.isCaller = false;
            
            console.log('[WebRTC] 📤 Sending call-accepted signal');
            this.sendSignalingMessage({
                type: 'call-accepted',
                from: this.localPeerId,
                to: callData.caller,
                call_type: callData.call_type
            });
            
            this.addSystemMessage(`✅ Accepted ${callData.call_type} call`);
            this.showMediaPanel();
            this.hideCallModal();
            
        } catch (error) {
            console.error('[WebRTC] ❌ Accept call failed:', error);
            this.addSystemMessage('❌ Failed to accept call');
        }
    }
    
    async handleCallAccepted(data) {
        if (!this.isCaller || !this.isCallActive) {
            console.log('[WebRTC] Ignoring call-accepted - not caller or inactive');
            return;
        }
        
        try {
            console.log('[WebRTC] 📡 Call accepted! Creating offer...');
            
            // CRITICAL: Create offer with proper options (search result [6])
            const offerOptions = {
                offerToReceiveAudio: true,
                offerToReceiveVideo: this.callType === 'video'
            };
            
            const offer = await this.peerConnection.createOffer(offerOptions);
            await this.peerConnection.setLocalDescription(offer);
            
            console.log('[WebRTC] 📤 Sending offer');
            this.sendSignalingMessage({
                type: 'offer',
                offer: offer,
                from: this.localPeerId,
                to: data.from
            });
            
            this.addSystemMessage('📞 Negotiating connection...');
            
        } catch (error) {
            console.error('[WebRTC] ❌ Failed to create offer:', error);
            this.addSystemMessage('❌ Failed to create offer');
        }
    }
    
    async handleWebRTCSignaling(data) {
        if (!this.peerConnection) {
            console.warn('[WebRTC] No peer connection, queuing signaling message');
            this.signalingQueue.push(data);
            return;
        }
        
        console.log('[WebRTC] 📡 Processing signaling:', data.type);
        
        try {
            switch (data.type) {
                case 'offer':
                    console.log('[WebRTC] 📥 Processing offer');
                    
                    await this.peerConnection.setRemoteDescription(data.offer);
                    console.log('[WebRTC] ✅ Remote description set from offer');
                    
                    // Create and send answer (search result [6])
                    const answerOptions = {
                        offerToReceiveAudio: true,
                        offerToReceiveVideo: this.callType === 'video'
                    };
                    
                    const answer = await this.peerConnection.createAnswer(answerOptions);
                    await this.peerConnection.setLocalDescription(answer);
                    
                    console.log('[WebRTC] 📤 Sending answer');
                    this.sendSignalingMessage({
                        type: 'answer',
                        answer: answer,
                        from: this.localPeerId,
                        to: data.from
                    });
                    
                    break;
                    
                case 'answer':
                    console.log('[WebRTC] 📥 Processing answer');
                    
                    if (this.peerConnection.signalingState === 'have-local-offer') {
                        await this.peerConnection.setRemoteDescription(data.answer);
                        console.log('[WebRTC] ✅ Answer processed successfully');
                    } else {
                        console.error('[WebRTC] ❌ Invalid signaling state for answer:', this.peerConnection.signalingState);
                    }
                    break;
                    
                case 'ice-candidate':
                    console.log('[WebRTC] 📥 Processing ICE candidate');
                    
                    if (this.peerConnection.remoteDescription) {
                        await this.peerConnection.addIceCandidate(data.candidate);
                        console.log('[WebRTC] ✅ ICE candidate added');
                    } else {
                        console.log('[WebRTC] ⏳ Queuing ICE candidate - no remote description');
                        this.signalingQueue.push(data);
                    }
                    break;
                    
                case 'call-accepted':
                    await this.handleCallAccepted(data);
                    break;
                    
                default:
                    console.log('[WebRTC] ❓ Unknown signaling type:', data.type);
            }
        } catch (error) {
            console.error('[WebRTC] ❌ Signaling error:', error);
            console.error('[WebRTC] Error details:', {
                type: data.type,
                signalingState: this.peerConnection.signalingState,
                error: error.message
            });
            this.addSystemMessage('❌ Signaling error: ' + error.message);
        }
    }
    
    processSignalingQueue() {
        console.log(`[WebRTC] Processing ${this.signalingQueue.length} queued signaling messages`);
        
        while (this.signalingQueue.length > 0) {
            const data = this.signalingQueue.shift();
            this.handleWebRTCSignaling(data);
        }
    }
    
    sendSignalingMessage(data) {
        console.log('[WebRTC] 📤 Sending signaling message:', data.type);
        
        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
            this.websocket.send(JSON.stringify({
                type: 'webrtc_signal',
                signal: data
            }));
        } else {
            console.error('[WebRTC] ❌ WebSocket not ready for signaling');
            this.addSystemMessage('❌ Connection not ready');
        }
    }
    
    sendMessage(message) {
        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
            this.websocket.send(JSON.stringify(message));
        }
    }
    
    // ENHANCED: Media initialization with better error handling (search result [3])
    async initializeMedia(audio = true, video = false) {
        try {
            const constraints = {
                audio: audio ? {
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true,
                    sampleRate: 48000
                } : false,
                video: video ? {
                    width: { ideal: 640 },
                    height: { ideal: 480 },
                    frameRate: { ideal: 15 }
                } : false
            };
            
            console.log('[WebRTC] 📸 Requesting media access with constraints:', constraints);
            
            // Check available devices first (search result [3])
            const devices = await navigator.mediaDevices.enumerateDevices();
            const audioDevices = devices.filter(device => device.kind === 'audioinput');
            const videoDevices = devices.filter(device => device.kind === 'videoinput');
            
            console.log(`[WebRTC] Available devices: ${audioDevices.length} audio, ${videoDevices.length} video`);
            
            if (audio && audioDevices.length === 0) {
                throw new Error('No audio input devices found');
            }
            
            if (video && videoDevices.length === 0) {
                throw new Error('No video input devices found');
            }
            
            this.localStream = await navigator.mediaDevices.getUserMedia(constraints);
            
            // Debug local stream
            console.log('[WebRTC] ✅ Media access granted');
            const audioTracks = this.localStream.getAudioTracks();
            const videoTracks = this.localStream.getVideoTracks();
            
            console.log(`[WebRTC] Local stream: ${audioTracks.length} audio, ${videoTracks.length} video tracks`);
            
            audioTracks.forEach((track, i) => {
                console.log(`[WebRTC] Local audio track ${i}:`, {
                    enabled: track.enabled,
                    readyState: track.readyState,
                    label: track.label
                });
            });
            
            videoTracks.forEach((track, i) => {
                console.log(`[WebRTC] Local video track ${i}:`, {
                    enabled: track.enabled,
                    readyState: track.readyState,
                    label: track.label
                });
            });
            
            // Display local video
            const localVideo = document.getElementById('localVideo');
            if (localVideo && this.localStream) {
                localVideo.srcObject = this.localStream;
                localVideo.muted = true; // Prevent feedback
                localVideo.play().catch(e => console.error('[WebRTC] Local video play error:', e));
            }
            
            // Add tracks to peer connection
            if (this.peerConnection) {
                this.localStream.getTracks().forEach(track => {
                    console.log('[WebRTC] ➕ Adding track to peer connection:', track.kind);
                    this.peerConnection.addTrack(track, this.localStream);
                });
            }
            
            return this.localStream;
        } catch (error) {
            console.error('[WebRTC] ❌ Media access failed:', error);
            console.error('[WebRTC] Error details:', {
                name: error.name,
                message: error.message,
                constraint: error.constraint
            });
            this.addSystemMessage('❌ Camera/microphone access failed: ' + error.message);
            throw error;
        }
    }
    
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
                console.log('[WebRTC] Audio track toggled:', audioTrack.enabled);
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
                console.log('[WebRTC] Video track toggled:', videoTrack.enabled);
            }
        }
    }
    
    endCall() {
        this.isCallActive = false;
        this.callType = null;
        this.pendingCall = null;
        this.isCaller = false;
        this.signalingQueue = [];
        
        if (this.peerConnection) {
            this.peerConnection.close();
            this.peerConnection = null;
        }
        
        if (this.localStream) {
            this.localStream.getTracks().forEach(track => track.stop());
            this.localStream = null;
        }
        
        this.hideMediaPanel();
        this.hideCallModal();
        this.addSystemMessage('📵 Call ended');
    }
    
    showMediaPanel() {
        const panel = document.getElementById('mediaPanel');
        if (panel) panel.classList.add('active');
    }
    
    hideMediaPanel() {
        const panel = document.getElementById('mediaPanel');
        if (panel) panel.classList.remove('active');
    }
    
    showCallModal(callData) {
        const modal = document.getElementById('callModal');
        const message = document.getElementById('callModalMessage');
        if (modal && message) {
            message.textContent = `Incoming ${callData.call_type} call from ${callData.caller}`;
            modal.classList.add('active');
        }
    }
    
    hideCallModal() {
        const modal = document.getElementById('callModal');
        if (modal) modal.classList.remove('active');
    }
    
    addSystemMessage(message) {
        if (window.app && window.app.addSystemMessage) {
            window.app.addSystemMessage(message);
        } else {
            console.log('[WebRTC]', message);
        }
    }
    
    handleIncomingCall(callData) {
        if (this.isCallActive) {
            this.addSystemMessage('📵 Call declined - already in call');
            return;
        }
        
        this.pendingCall = callData;
        this.showCallModal(callData);
    }
}

window.webrtcManager = new Metal52WebRTC();
