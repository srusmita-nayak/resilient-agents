import { useEffect, useRef, useState, useCallback } from 'react';
import { SimEvent } from '../api/types';

interface UseWebSocketOptions {
  runId?: string | null;
  fromSeq?: number;
  onEvent?: (event: SimEvent) => void;
}

export function useWebSocket({ runId, fromSeq = 0, onEvent }: UseWebSocketOptions = {}) {
  const [isConnected, setIsConnected] = useState(false);
  const [lastEvent, setLastEvent] = useState<SimEvent | null>(null);
  const [events, setEvents] = useState<SimEvent[]>([]);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const pingIntervalRef = useRef<number | null>(null);

  const connect = useCallback(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const wsUrl = `${protocol}//${host}/ws/events`;

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        // Subscribe to run if provided
        if (runId) {
          ws.send(JSON.stringify({ action: 'subscribe', run_id: runId, from_seq: fromSeq }));
        }

        // Start ping interval
        pingIntervalRef.current = window.setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ action: 'ping', timestamp: Date.now() }));
          }
        }, 15000);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'EVENT_LIVE' || data.type === 'EVENT_REPLAY') {
            const ev: SimEvent = data.event;
            setLastEvent(ev);
            setEvents((prev) => [...prev.slice(-499), ev]);
            if (onEvent) onEvent(ev);
          }
        } catch {
          // ignore
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
        if (pingIntervalRef.current) clearInterval(pingIntervalRef.current);
        reconnectTimeoutRef.current = window.setTimeout(connect, 3000);
      };

      ws.onerror = () => {
        ws.close();
      };
    } catch {
      reconnectTimeoutRef.current = window.setTimeout(connect, 3000);
    }
  }, [runId, fromSeq, onEvent]);

  useEffect(() => {
    connect();
    return () => {
      if (wsRef.current) wsRef.current.close();
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (pingIntervalRef.current) clearInterval(pingIntervalRef.current);
    };
  }, [connect]);

  const clearEvents = useCallback(() => setEvents([]), []);

  return { isConnected, lastEvent, events, clearEvents };
}
