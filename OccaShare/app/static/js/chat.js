/**
 * OccaShare Real-time Chat System
 * Handles WebSocket messaging and Chat UI updates.
 */

class OccaChat {
    constructor(options = {}) {
        this.userId = options.userId;
        this.userRole = options.userRole;
        this.peerId = options.peerId || null;
        this.websocketUrl = options.websocketUrl;
        this.socket = null;
        this.onMessageReceived = options.onMessageReceived || null;
        
        this.initWebSocket();
    }

    initWebSocket() {
        const clientId = `chat_${this.userId}_${Math.random().toString(36).substr(2, 9)}`;
        const wsUrl = `${this.websocketUrl}/${clientId}`;
        
        console.log(`Connecting to WebSocket: ${wsUrl}`);
        this.socket = new WebSocket(wsUrl);

        this.socket.onopen = () => {
            console.log("Chat WebSocket Connected");
        };

        this.socket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            
            // Handle Chat Messages
            if (data.type === 'chat_message') {
                this.handleIncomingMessage(data);
            } else if (data.type === 'message_edit') {
                this.handleMessageEdit(data);
            } else if (data.type === 'message_delete') {
                this.handleMessageDelete(data);
            } else if (data.type === 'presence') {
                this.handlePresenceUpdate(data);
            } 
            
            // Handle Generic Notifications
            else if (data.type === 'new_notification' || data.type === 'dashboard_update') {
                if (window.showToast && data.message) {
                    window.showToast(data.message, 'info');
                }
                if (window.OccaEvents) window.OccaEvents.publish('notification', data);
            }
            
            // Handle Payment/Booking events
            else if (data.type === 'payment_rejected' || data.type === 'booking_update') {
                if (window.showToast && data.message) {
                    window.showToast(data.message, data.type === 'payment_rejected' ? 'warning' : 'info');
                }
                
                // If on a specific booking management page, reload to show changes
                if (window.location.pathname.includes('/bookings/manage/') || window.location.pathname.includes('/caterer/bookings')) {
                   // Optional: Use OccaEvents to trigger a more subtle refresh if implemented
                   if (window.OccaEvents) window.OccaEvents.publish('booking_status_changed', data);
                   
                   // For now, force reload after a short delay so the toast stays visible
                   setTimeout(() => {
                       window.location.reload();
                   }, 2000);
                }
            }
        };

        this.socket.onclose = () => {
            console.log("Chat WebSocket Disconnected. Reconnecting...");
            setTimeout(() => this.initWebSocket(), 3000);
        };

        this.socket.onerror = (error) => {
            console.error("WebSocket Error:", error);
        };
    }

    async editMessage(messageId, newContent) {
        try {
            const response = await fetch(`/api/chat/edit/${messageId}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ content: newContent })
            });
            if (!response.ok) throw new Error("Failed to edit message");
            return await response.json();
        } catch (error) {
            console.error("Edit Error:", error);
            return null;
        }
    }

    async deleteMessage(messageId) {
        try {
            const response = await fetch(`/api/chat/delete/${messageId}`, {
                method: 'DELETE'
            });
            if (!response.ok) throw new Error("Failed to delete message");
            return await response.json();
        } catch (error) {
            console.error("Delete Error:", error);
            return null;
        }
    }

    handleMessageEdit(data) {
        console.log("Message Edited:", data);
        if (this.onMessageEdited) {
            this.onMessageEdited(data);
        }
    }

    handleMessageDelete(data) {
        console.log("Message Deleted:", data);
        if (this.onMessageDeleted) {
            this.onMessageDeleted(data);
        }
    }

    handlePresenceUpdate(data) {
        console.log("Presence Update:", data);
        if (this.onPresenceUpdate) {
            this.onPresenceUpdate(data);
        }
    }

    async sendMessage(receiverId, content, extraData = {}) {
        // Validation: Must have either content or file data
        if (!content && !extraData.file_url) return;

        try {
            const payload = {
                receiver_id: receiverId,
                content: content || "",
                message_type: extraData.message_type || "text",
                file_url: extraData.file_url || null,
                file_name: extraData.file_name || null
            };

            const response = await fetch('/api/chat/send', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!response.ok) throw new Error("Failed to send message");
            
            const msg = await response.json();
            return msg;
        } catch (error) {
            console.error("Send Error:", error);
            return null;
        }
    }

    handleIncomingMessage(data) {
        console.log("New Message:", data);
        
        // If the message is from the person we are currently chatting with, mark as read
        if (this.peerId && data.sender_id === this.peerId) {
            this.markAsRead(data.id);
        }

        // Trigger callback for UI update
        if (this.onMessageReceived) {
            this.onMessageReceived(data);
        }

        // Show browser notification or play sound if not on the chat page
        if (!this.peerId || data.sender_id !== this.peerId) {
            this.notifyUser(data);
        }
    }

    async markAsRead(messageId) {
        try {
            await fetch(`/api/chat/read/${messageId}`, { method: 'POST' });
        } catch (e) {}
    }

    async markAllAsRead(peerId) {
        try {
            await fetch(`/api/chat/read-all/${peerId}`, { method: 'POST' });
        } catch (e) {}
    }

    notifyUser(data) {
        // Play subtle sound
        const audio = new Audio('/static/sounds/notification.mp3');
        audio.play().catch(() => {}); // Browser might block auto-play

        // Show Toast (using SweetAlert2 which is already available in the project)
        if (window.Swal) {
            const Toast = Swal.mixin({
                toast: true,
                position: 'top-end',
                showConfirmButton: false,
                timer: 3000,
                timerProgressBar: true
            });
            let notifyText = data.content;
            if (data.message_type === 'image') notifyText = "Sent a photo";
            else if (data.message_type === 'file') notifyText = "Sent a file: " + (data.file_name || "");

            Toast.fire({
                icon: 'info',
                title: `New message from ${data.sender_name}`,
                text: notifyText && notifyText.length > 30 ? notifyText.substring(0, 30) + '...' : notifyText
            });
        }
    }

    static formatTime(dateStr) {
        const date = new Date(dateStr);
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }
}

// Global helper to load chat history
async function loadChatHistory(peerId) {
    try {
        const response = await fetch(`/api/chat/history/${peerId}`);
        if (!response.ok) return [];
        return await response.json();
    } catch (e) {
        return [];
    }
}

// Global helper to load conversations
async function loadConversations() {
    try {
        const response = await fetch('/api/chat/conversations');
        if (!response.ok) return [];
        return await response.json();
    } catch (e) {
        return [];
    }
}
