import { useState, useRef, useEffect } from 'react';
import './ChatPane.css';
import LogBubble from './LogBubble';
import { Send, SquareSquare } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

export default function ChatPane({ sessionId, selectedConfig, onReportGenerated }) {
  const [taskText, setTaskText] = useState('');
  const [messages, setMessages] = useState([]);
  const [isRunning, setIsRunning] = useState(false);
  const [statusMessage, setStatusMessage] = useState('');
  const [currentSteps, setCurrentSteps] = useState([]);

  const wsRef = useRef(null);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, currentSteps]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!taskText.trim() || !selectedConfig || isRunning) return;

    const content = taskText;
    setTaskText('');
    setIsRunning(true);
    setStatusMessage('Queuing task...');
    setCurrentSteps([]);

    setMessages(prev => [...prev, { role: 'user', content }]);

    try {
      const res = await fetch('/api/tasks', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Session-ID': sessionId
        },
        body: JSON.stringify({
          task: content,
          config_name: selectedConfig
        })
      });

      if (!res.ok) throw new Error('Failed to start task');

      const data = await res.json();
      connectWebSocket(data.task_id);
    } catch (err) {
      setMessages(prev => [...prev, { role: 'assistant', content: `**Error:** ${err.message}` }]);
      setIsRunning(false);
    }
  };

  const connectWebSocket = (taskId) => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/tasks/${taskId}`;

    wsRef.current = new WebSocket(wsUrl);

    wsRef.current.onmessage = (event) => {
      const update = JSON.parse(event.data);
      handleWsUpdate(update, taskId);
    };

    wsRef.current.onerror = () => {
      setStatusMessage('Connection error');
    };

    wsRef.current.onclose = () => {
      if (isRunning) setStatusMessage('Connection closed unexpectedly');
    };
  };

  const handleWsUpdate = (update, taskId) => {
    switch (update.type) {
      case 'status':
        setStatusMessage(update.data.status);
        break;
      case 'step':
        setCurrentSteps(prev => [...prev, {
          action: update.data.action,
          input: update.data.input,
          code: null,
          output: update.data.output
        }]);
        setStatusMessage(update.data.action);
        break;
      case 'code':
        setCurrentSteps(prev => [...prev, {
          action: 'CODE',
          input: update.data.code,
          code: update.data.code,
          output: null
        }]);
        setStatusMessage('Executing code...');
        break;
      case 'output':
        setCurrentSteps(prev => {
          const newSteps = [...prev];
          for (let i = newSteps.length - 1; i >= 0; i--) {
            if (newSteps[i].action === 'CODE') {
              newSteps[i].output = update.data.output;
              break;
            }
          }
          return newSteps;
        });
        break;
      case 'complete':
        setIsRunning(false);
        if (wsRef.current) wsRef.current.close();

        const finalAnswer = update.data.answer || `Task completed in ${update.data.duration_seconds?.toFixed(1) || 0}s`;
        setMessages(prev => [...prev, { role: 'assistant', content: finalAnswer }]);

        // Push the full report up to App/ReportCanvas
        // We will pass the taskId to fetch the Markdown output
        onReportGenerated(taskId, update.data);
        break;
      case 'error':
        setIsRunning(false);
        if (wsRef.current) wsRef.current.close();
        setMessages(prev => [...prev, { role: 'assistant', content: `**Error:** ${update.data.error}` }]);
        break;
      default:
        break;
    }
  };

  const stopTask = () => {
    if (wsRef.current) wsRef.current.close();
    setIsRunning(false);
    setMessages(prev => [...prev, { role: 'assistant', content: '_Task stopped by user_' }]);
  };

  return (
    <main className="pane chat-pane">
      <div className="chat-history">
        {messages.length === 0 && !isRunning && (
          <div className="chat-empty">
            <span className="empty-icon">🚀</span>
            <h3>Ready to start</h3>
            <p>Enter a task below to get started</p>
          </div>
        )}

        {messages.map((msg, idx) => (
          <div key={idx} className={`message-row ${msg.role === 'user' ? 'user-row' : 'assistant-row'}`}>
            <div className={`message-bubble ${msg.role === 'user' ? 'user-msg' : 'assistant-msg'}`}>
              <div className="message-role">{msg.role === 'user' ? 'You' : 'RLM Agent'}</div>
              <div className="message-content">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
              </div>
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      <LogBubble steps={currentSteps} statusMessage={statusMessage} isRunning={isRunning} />

      <div className="chat-input-area">
        <form onSubmit={handleSubmit} className="chat-form">
          <textarea
            value={taskText}
            onChange={(e) => setTaskText(e.target.value)}
            disabled={isRunning || !sessionId}
            placeholder="Describe your task... (Cmd/Ctrl + Enter to send)"
            className="chat-textarea"
            rows={2}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
                handleSubmit(e);
              }
            }}
          />

          <button
            type="submit"
            className="btn btn-primary send-btn"
            disabled={!taskText.trim() || isRunning || !sessionId || !selectedConfig}
          >
            {isRunning ? <SquareSquare size={18} className="spinner" onClick={(e) => { e.preventDefault(); stopTask(); }} /> : <Send size={18} />}
          </button>
        </form>
      </div>
    </main>
  );
}
