from typing import List, Dict, Set
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        # active_connections maps client_id to WebSocket
        self.active_connections: Dict[str, WebSocket] = {}
        # user_connections maps user_id to set of client_ids
        self.user_connections: Dict[int, Set[str]] = {}
        # role_connections maps role to set of client_ids
        self.role_connections: Dict[str, Set[str]] = {}

    async def connect(self, client_id: str, websocket: WebSocket, user_id: int = None, role: str = None):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        
        if user_id:
            # Check if this was the first connection for this user
            is_first = user_id not in self.user_connections or not self.user_connections[user_id]
            
            if user_id not in self.user_connections:
                self.user_connections[user_id] = set()
            self.user_connections[user_id].add(client_id)
            
            if is_first:
                await self.broadcast({"type": "presence", "user_id": user_id, "status": "online"})
            
        if role:
            if role not in self.role_connections:
                self.role_connections[role] = set()
            self.role_connections[role].add(client_id)

    async def disconnect(self, client_id: str):
        user_id_to_notify = None
        if client_id in self.active_connections:
            del self.active_connections[client_id]
        
        # Clean up user mapping
        for uid in list(self.user_connections.keys()):
            if client_id in self.user_connections[uid]:
                self.user_connections[uid].remove(client_id)
                if not self.user_connections[uid]:
                    del self.user_connections[uid]
                    user_id_to_notify = uid
                    
        # Clean up role mapping
        for role in list(self.role_connections.keys()):
            if client_id in self.role_connections[role]:
                self.role_connections[role].remove(client_id)
                if not self.role_connections[role]:
                    del self.role_connections[role]

        if user_id_to_notify:
            await self.broadcast({"type": "presence", "user_id": user_id_to_notify, "status": "offline"})

    async def broadcast_to_client(self, client_id: str, message: dict):
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_json(message)
            except Exception:
                self.disconnect(client_id)

    async def broadcast_to_user(self, user_id: int, message: dict):
        if user_id in self.user_connections:
            for client_id in list(self.user_connections[user_id]):
                await self.broadcast_to_client(client_id, message)

    async def broadcast_to_role(self, role: str, message: dict):
        if role in self.role_connections:
            for client_id in list(self.role_connections[role]):
                await self.broadcast_to_client(client_id, message)

    async def broadcast(self, message: dict):
        for client_id in list(self.active_connections.keys()):
            await self.broadcast_to_client(client_id, message)

manager = ConnectionManager()
