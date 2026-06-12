/**
 * WebSocket Hook for real-time collaboration
 *
 * Connects to FastAPI WebSocket backend at:
 * ws://host:port/api/v1/ws/collaboration/{roomId}/{userId}?user_name=xxx&user_color=xxx
 */

import { useEffect, useRef, useState, useCallback } from 'react';

export interface Collaborator {
  id: string;
  name: string;
  color: string;
  cursor?: { x: number; y: number; documentId: string };
  selection?: { start: number; end: number; documentId: string };
  lastSeen: number;
}

interface ChatMessage {
  userId: string;
  userName: string;
  color?: string;
  content: string;
  timestamp: number;
}

export interface UseWebSocketReturn {
  isConnected: boolean;
  collaborators: Collaborator[];
  messages: ChatMessage[];
  updateCursor: (x: number, y: number, documentId: string) => void;
  updateSelection: (start: number, end: number, documentId: string) => void;
  sendUpdate: (operation: string, position: number, text: string, documentId: string) => void;
  sendChat: (content: string) => void;
  reconnect: () => void;
}

const USER_COLORS = [
  '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FECA57',
  '#FF9FF3', '#54A0FF', '#48DBFB', '#1DD1A1', '#FFC048'
];

const WS_BASE_URL = typeof window !== 'undefined'
  ? (process.env.NEXT_PUBLIC_WS_URL || 'ws://127.0.0.1:8000/api/v1')
  : '';

const RECONNECT_DELAY = 3000;
const MAX_RECONNECT_ATTEMPTS = 5;

export function useWebSocket(
  roomId: string,
  userId: string,
  userName: string
): UseWebSocketReturn {
  const [isConnected, setIsConnected] = useState(false);
  const [collaborators, setCollaborators] = useState<Collaborator[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const [userColor] = useState(() => USER_COLORS[Math.floor(Math.random() * USER_COLORS.length)]);
  const isConnectingRef = useRef(false);
  const connectRef = useRef<() => void>(() => {});

  const handleMessage = useCallback((msg: Record<string, unknown>) => {
    const type = msg.type as string;

    switch (type) {
      case 'init': {
        const cols = (msg.collaborators as Collaborator[]) || [];
        setCollaborators(cols);
        break;
      }

      case 'presence': {
        const event = msg.event as string;
        const user = msg.user as Collaborator | undefined;
        if (!user) break;

        if (event === 'join') {
          setCollaborators((prev) => {
            if (prev.find((c) => c.id === user.id)) return prev;
            return [...prev, user];
          });
        } else if (event === 'leave') {
          setCollaborators((prev) => prev.filter((c) => c.id !== user.id));
        }
        break;
      }

      case 'cursor': {
        const uid = msg.userId as string;
        const data = msg.data as { x?: number; y?: number; documentId?: string } | undefined;
        if (!data) break;
        setCollaborators((prev) =>
          prev.map((c) =>
            c.id === uid
              ? {
                  ...c,
                  cursor: {
                    x: data.x ?? 0,
                    y: data.y ?? 0,
                    documentId: data.documentId ?? '',
                  },
                  lastSeen: Date.now(),
                }
              : c
          )
        );
        break;
      }

      case 'selection': {
        const sUid = msg.userId as string;
        const sData = msg.data as { start?: number; end?: number; documentId?: string } | undefined;
        if (!sData) break;
        setCollaborators((prev) =>
          prev.map((c) =>
            c.id === sUid
              ? {
                  ...c,
                  selection: {
                    start: sData.start ?? 0,
                    end: sData.end ?? 0,
                    documentId: sData.documentId ?? '',
                  },
                  lastSeen: Date.now(),
                }
              : c
          )
        );
        break;
      }

      case 'chat': {
        const chatMsg: ChatMessage = {
          userId: (msg.userId as string) || '',
          userName: (msg.userName as string) || 'Unknown',
          color: (msg.color as string) || undefined,
          content: (msg.content as string) || '',
          timestamp: (msg.timestamp as number) || Date.now(),
        };
        setMessages((prev) => [...prev, chatMsg]);
        break;
      }

      case 'update': {
        // Document update broadcast — consumer decides what to do
        // For now, just update lastSeen of the sender
        const uUid = msg.userId as string;
        setCollaborators((prev) =>
          prev.map((c) => (c.id === uUid ? { ...c, lastSeen: Date.now() } : c))
        );
        break;
      }

      case 'ping': {
        // Respond with pong
        wsRef.current?.send(JSON.stringify({ type: 'pong' }));
        break;
      }
    }
  }, []);

  const connect = useCallback(() => {
    if (isConnectingRef.current) return;
    if (wsRef.current?.readyState === WebSocket.OPEN) return;
    if (!roomId || !userId) return;

    isConnectingRef.current = true;

    try {
      const wsUrl = `${WS_BASE_URL}/ws/collaboration/${encodeURIComponent(roomId)}/${encodeURIComponent(userId)}?user_name=${encodeURIComponent(userName)}&user_color=${encodeURIComponent(userColor)}`;

      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        reconnectAttemptsRef.current = 0;
        isConnectingRef.current = false;
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          handleMessage(msg);
        } catch {
          // ignore non-JSON messages
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
        wsRef.current = null;
        isConnectingRef.current = false;

        // Auto-reconnect if not maxed out
        if (reconnectAttemptsRef.current < MAX_RECONNECT_ATTEMPTS) {
          reconnectAttemptsRef.current += 1;
          reconnectTimerRef.current = setTimeout(() => {
            connectRef.current();
          }, RECONNECT_DELAY * reconnectAttemptsRef.current);
        }
      };

      ws.onerror = () => {
        isConnectingRef.current = false;
      };
    } catch {
      isConnectingRef.current = false;
      setIsConnected(false);
    }
  }, [roomId, userId, userName, userColor, handleMessage]);

  // Keep connectRef in sync to break self-reference dead zone
  useEffect(() => {
    connectRef.current = connect;
  }, [connect]);

  const disconnect = useCallback(() => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }

    if (wsRef.current) {
      // Prevent auto-reconnect on manual disconnect
      reconnectAttemptsRef.current = MAX_RECONNECT_ATTEMPTS;
      wsRef.current.close();
      wsRef.current = null;
    }

    setIsConnected(false);
    setCollaborators([]);
  }, []);

  const reconnect = useCallback(() => {
    disconnect();
    reconnectAttemptsRef.current = 0;
    setTimeout(connect, 500);
  }, [disconnect, connect]);

  const sendMessage = useCallback((msg: Record<string, unknown>) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      try {
        wsRef.current.send(JSON.stringify(msg));
      } catch {
        // ignore send errors
      }
    }
  }, []);

  const updateCursor = useCallback((x: number, y: number, documentId: string) => {
    sendMessage({
      type: 'cursor',
      data: { x, y, documentId },
    });
  }, [sendMessage]);

  const updateSelection = useCallback((start: number, end: number, documentId: string) => {
    sendMessage({
      type: 'selection',
      data: { start, end, documentId },
    });
  }, [sendMessage]);

  const sendUpdate = useCallback((operation: string, position: number, text: string, documentId: string) => {
    sendMessage({
      type: 'update',
      data: { operation, position, text, documentId },
    });
  }, [sendMessage]);

  const sendChat = useCallback((content: string) => {
    const timestamp = Date.now();
    // Add to local messages immediately for instant feedback
    setMessages((prev) => [
      ...prev,
      { userId, userName, content, timestamp },
    ]);
    sendMessage({
      type: 'chat',
      content,
      timestamp,
    });
  }, [sendMessage, userId, userName]);

  // Connect on mount / params change
  useEffect(() => {
    connect();

    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  return {
    isConnected,
    collaborators,
    messages,
    updateCursor,
    updateSelection,
    sendUpdate,
    sendChat,
    reconnect,
  };
}

export default useWebSocket;
