import { BrowserRouter as Router, Routes, Route, useParams } from 'react-router-dom';
import { useState, useEffect } from 'react';
import './index.css';
import Sidebar from './components/Sidebar';
import ChatPane from './components/ChatPane';
import ReportCanvas from './components/ReportCanvas';

function AppLayout() {
  const [sessionId, setSessionId] = useState(null);
  const [selectedConfig, setSelectedConfig] = useState('');

  const [reportMarkdown, setReportMarkdown] = useState('');
  const [reportTaskId, setReportTaskId] = useState('');

  // Initialize Session
  useEffect(() => {
    fetch('/api/sessions', { method: 'POST', headers: { 'Content-Type': 'application/json' } })
      .then(res => res.json())
      .then(data => {
        setSessionId(data.session_id);
      })
      .catch(err => console.error("Could not create session", err));
  }, []);

  const handleReportGenerated = (taskId, taskData) => {
    setReportTaskId(taskId);
    // Use the `answer` if available, or fetch full markdown from backend
    if (taskData.answer) {
      setReportMarkdown(taskData.answer);
    } else {
      fetch(`/api/tasks/${taskId}`)
        .then(res => res.json())
        .then(data => setReportMarkdown(data.result?.answer || ''))
        .catch(err => console.error(err));
    }
  };

  return (
    <div className="app-container">
      <Sidebar
        sessionId={sessionId}
        selectedConfig={selectedConfig}
        onConfigChange={setSelectedConfig}
      />

      <ChatPane
        sessionId={sessionId}
        selectedConfig={selectedConfig}
        onReportGenerated={handleReportGenerated}
      />

      <ReportCanvas
        reportHtml={reportMarkdown}
        taskId={reportTaskId}
      />
    </div>
  );
}

function ReportViewer() {
  const { taskId } = useParams();
  const [reportMarkdown, setReportMarkdown] = useState('');

  useEffect(() => {
    fetch(`/api/tasks/${taskId}/export/markdown`)
      .then(res => {
        if (!res.ok) throw new Error('Report not found');
        return res.text();
      })
      .then(text => setReportMarkdown(text))
      .catch(err => console.error("Error loading task markdown:", err));
  }, [taskId]);

  return (
    <div className="app-container" style={{ display: 'flex', flexDirection: 'column', width: '100vw' }}>
      <div style={{ padding: '16px 24px', background: 'var(--bg-secondary)', borderBottom: '1px solid var(--border-color)', display: 'flex', alignItems: 'center', gap: '16px' }}>
         <button onClick={() => window.close()} className="btn btn-secondary" style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '14px', flexShrink: 0, border: 'none', background: 'transparent' }}>
           <span style={{ fontSize: '18px' }}>✕</span> Close Tab
         </button>
         <h2 style={{ fontSize: '16px', margin: 0, color: 'var(--text-primary)' }}>Report Viewer: Task {taskId?.substring(0,8)}...</h2>
      </div>
      <div style={{ display: 'flex', justifyContent: 'center', flex: 1, overflowY: 'auto' }}>
        <ReportCanvas
          reportHtml={reportMarkdown}
          taskId={taskId}
          style={{ width: '100%', maxWidth: '800px', margin: '0 auto', border: 'none', boxShadow: 'none' }}
        />
      </div>
    </div>
  );
}

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<AppLayout />} />
        <Route path="/report/:taskId" element={<ReportViewer />} />
      </Routes>
    </Router>
  );
}

export default App;
