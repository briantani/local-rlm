import { useState, useEffect } from 'react';
import './index.css';
import Sidebar from './components/Sidebar';
import ChatPane from './components/ChatPane';
import ReportCanvas from './components/ReportCanvas';

function App() {
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

export default App;
