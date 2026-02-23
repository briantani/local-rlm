import './ReportCanvas.css';
import { DownloadCloud, ExternalLink, FileText } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

export default function ReportCanvas({ reportHtml, taskId }) {
  const handleExport = (format) => {
    if (!taskId) return;
    const url = `/api/tasks/${taskId}/export/${format}`;
    const link = document.createElement('a');
    link.href = url;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleOpenTab = () => {
    if (!taskId) return;
    // For a new tab, we ideally want a route, but since we are a SPA without routing currently,
    // we can simply open the backend's export PDF route or a quick blob print out.
    // Given the prompt, let's open the markdown endpoint in a new tab for now.
    // Or, we render the HTML to a blob and open it.
    const url = `/report/${taskId}`;
    window.open(url, '_blank');
  };

  return (
    <aside className="pane report-canvas">
      <div className="report-header">
        <div className="report-title">
          <FileText size={16} color="var(--accent-primary)" />
          <h3>Report Canvas</h3>
        </div>

        <div className="report-actions">
          <button
            className="btn btn-secondary action-btn"
            disabled={!taskId}
            onClick={() => handleExport('markdown')}
            title="Export Markdown"
          >
            <DownloadCloud size={14} /> <span>MD</span>
          </button>

          <button
            className="btn btn-secondary action-btn"
            disabled={!taskId}
            onClick={() => handleExport('pdf')}
            title="Export PDF"
          >
            <DownloadCloud size={14} /> <span>PDF</span>
          </button>

          <button
            className="btn btn-secondary action-btn"
            disabled={!taskId}
            onClick={handleOpenTab}
            title="Open in new tab"
          >
            <ExternalLink size={14} />
          </button>
        </div>
      </div>

      <div className="report-content">
        {reportHtml ? (
           <div className="report-markdown prose">
             <ReactMarkdown remarkPlugins={[remarkGfm]}>{reportHtml}</ReactMarkdown>
           </div>
        ) : (
           <div className="report-empty">
             <FileText size={48} className="empty-icon-subtle" />
             <p>No report generated yet.</p>
             <span className="empty-subtext">Run a task to see results here.</span>
           </div>
        )}
      </div>
    </aside>
  );
}
