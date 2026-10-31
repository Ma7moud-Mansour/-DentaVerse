import { useCallback, useEffect, useRef, useState } from 'react';

export function useWorkbench() {
  const [state, setState] = useState(null);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState('');
  const socket = useRef(null);
  const current = useRef(null);
  useEffect(() => {
    let stopped = false, retry;
    function connect() {
      const ws = new WebSocket(`${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws`);
      socket.current = ws;
      ws.onmessage = ({ data }) => {
        if (stopped) return;
        try {
          const message = JSON.parse(data);
          if (message.type === 'state') {
            current.current = message.state;
            setState(message.state);
            setConnected(true); // Authoritative snapshot, not just an open transport.
          } else if (message.type === 'error') setError(message.error);
        } catch { setError('Received an unreadable server message. Reconnect the workspace.'); }
      };
      ws.onclose = () => {
        if (stopped) return;
        setConnected(false);
        retry = setTimeout(connect, 1500);
      };
      ws.onerror = () => ws.close();
    }
    connect();
    return () => { stopped = true; clearTimeout(retry); socket.current?.close(); };
  }, []);
  const send = useCallback((type, payload = {}) => {
    if (socket.current?.readyState !== WebSocket.OPEN || !current.current) {
      setError('Reconnect the coordinator before changing the workspace.');
      return;
    }
    socket.current.send(JSON.stringify({ version: 1, source: 'ui', type, payload,
      session_id: current.current.session.id, event_id: crypto.randomUUID(), timestamp: Date.now() / 1000 }));
  }, []);
  return { state, connected, send, error, clearError: () => setError('') };
}
