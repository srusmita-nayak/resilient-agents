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
  const intentionalCloseRef = useRef(false);

  // Keep latest onEvent callback in a ref to avoid reconnecting when callback reference changes
  const onEventRef = useRef(onEvent);
  useEffect(() => {
    onEventRef.current = onEvent;
  }, [onEvent]);

  // Keep latest runId & fromSeq in refs
  const runIdRef = useRef(runId);
  const fromSeqRef = useRef(fromSeq);
  useEffect(() => {
    runIdRef.current = runId;
    fromSeqRef.current = fromSeq;
    // Send subscription over existing open connection if runId changes dynamically
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN && runId) {
      wsRef.current.send(JSON.stringify({ action: 'subscribe', run_id: runId, from_seq: fromSeq }));
    }
  }, [runId, fromSeq]);

  const connect = useCallback(() => {
    // Clear any pending reconnect timer
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    // Guard against duplicate concurrent sockets
    if (
      wsRef.current &&
      (wsRef.current.readyState === WebSocket.OPEN || wsRef.current.readyState === WebSocket.CONNECTING)
    ) {
      return;
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const wsUrl = `${protocol}//${host}/ws/events`;

    intentionalCloseRef.current = false;

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        if (runIdRef.current) {
          ws.send(JSON.stringify({ action: 'subscribe', run_id: runIdRef.current, from_seq: fromSeqRef.current }));
        }

        if (pingIntervalRef.current) clearInterval(pingIntervalRef.current);
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
            if (onEventRef.current) onEventRef.current(ev);
          }
        } catch {
          // ignore malformed frame
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
        if (pingIntervalRef.current) clearInterval(pingIntervalRef.current);
        // Only schedule auto-reconnect if close was unexpected (not intentional cleanup)
        if (!intentionalCloseRef.current) {
          reconnectTimeoutRef.current = window.setTimeout(connect, 3000);
        }
      };

      ws.onerror = () => {
        ws.close();
      };
    } catch {
      if (!intentionalCloseRef.current) {
        reconnectTimeoutRef.current = window.setTimeout(connect, 3000);
      }
    }
  }, []);

  useEffect(() => {
    connect();
    return () => {
      intentionalCloseRef.current = true;
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
      if (pingIntervalRef.current) {
        clearInterval(pingIntervalRef.current);
        pingIntervalRef.current = null;
      }
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [connect]);

  const clearEvents = useCallback(() => setEvents([]), []);

  return { isConnected, lastEvent, events, clearEvents };
}
