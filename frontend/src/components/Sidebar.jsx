import { useEffect, useRef, useState } from 'react';
import './Sidebar.css';
import { UploadCloud, File, Trash2, Settings } from 'lucide-react';

export default function Sidebar({ sessionId, selectedConfig, onConfigChange }) {
  const [configs, setConfigs] = useState([]);
  const [files, setFiles] = useState([]);
  const [isHovering, setIsHovering] = useState(false);
  const fileInputRef = useRef(null);

  useEffect(() => {
    fetch('/api/configs')
      .then(res => res.json())
      .then(data => {
        const profileList = data.profiles || [];
        setConfigs(profileList);
        if (profileList.length > 0 && !selectedConfig) {
          const localOnly = profileList.find(c => c.name === 'local-only');
          onConfigChange(localOnly ? 'local-only' : profileList[0].name);
        }
      })
      .catch(err => console.error('Failed to load configs:', err));
  }, []);

  useEffect(() => {
    if (!sessionId) return;

    const loadFiles = () => {
      fetch(`/api/sessions/${sessionId}/files`)
        .then(res => res.json())
        .then(data => setFiles(data.files || []))
        .catch(err => console.error('Failed to load files:', err));
    };

    loadFiles();
    // Poll loosely for simplicity in UI sync, or just rely on state changes
    const interval = setInterval(loadFiles, 5000);
    return () => clearInterval(interval);
  }, [sessionId]);

  const handleFileUpload = async (e) => {
    const uploadFiles = e.target.files || e.dataTransfer.files;
    if (!uploadFiles || uploadFiles.length === 0 || !sessionId) return;

    for (let i = 0; i < uploadFiles.length; i++) {
        const formData = new FormData();
        formData.append('file', uploadFiles[i]);

        try {
            await fetch(`/api/sessions/${sessionId}/files`, {
                method: 'POST',
                body: formData
            });
        } catch (err) {
            console.error('Error uploading file:', uploadFiles[i].name, err);
        }
    }

    // Refresh files immediately
    fetch(`/api/sessions/${sessionId}/files`)
      .then(res => res.json())
      .then(data => setFiles(data.files || []));
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsHovering(true);
  };

  const handleDragLeave = () => {
    setIsHovering(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsHovering(false);
    handleFileUpload(e);
  };

  const currentConfigDesc = configs.find(c => c.name === selectedConfig)?.description || '';

  return (
    <aside className="pane sidebar">
      <div className="sidebar-header">
        <div className="sidebar-logo">
          <span>🧠</span>
          <h2>RLM Agent</h2>
        </div>
      </div>

      <div className="sidebar-section">
        <div className="section-title">
          <Settings size={14} />
          <span>Configuration</span>
        </div>
        <select
          className="config-select"
          value={selectedConfig}
          onChange={(e) => onConfigChange(e.target.value)}
        >
          {configs.map(c => (
             <option key={c.name} value={c.name}>{c.name}</option>
          ))}
        </select>
        {currentConfigDesc && (
            <p className="config-desc">{currentConfigDesc}</p>
        )}
      </div>

      <div className="sidebar-section" style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        <div className="section-title">
          <File size={14} />
          <span>Session Workspace</span>
        </div>

        <div className="file-list">
          {files.length === 0 ? (
            <div className="empty-files">No files uploaded yet</div>
          ) : (
            files.map(f => (
              <div className="file-item" key={f.name}>
                <span className="file-name" title={f.name}>{f.name}</span>
                <span className="file-size">{(f.size / 1024).toFixed(1)} KB</span>
              </div>
            ))
          )}
        </div>

        <div
          className={`upload-zone ${isHovering ? 'hovering' : ''}`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
        >
          <UploadCloud size={24} color="var(--accent-primary)" />
          <span>Drag files here or click</span>
          <input
            type="file"
            multiple
            ref={fileInputRef}
            onChange={handleFileUpload}
            style={{ display: 'none' }}
          />
        </div>
      </div>
    </aside>
  );
}
