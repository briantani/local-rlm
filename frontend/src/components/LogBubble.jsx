import './LogBubble.css';
import { Loader2, Terminal, Code2, Play } from 'lucide-react';

export default function LogBubble({ steps, statusMessage, isRunning }) {
  if (!isRunning && steps.length === 0) return null;

  // The latest step
  const lastStep = steps[steps.length - 1];
  const stepCount = steps.length;

  return (
    <div className="log-bubble">
      <div className="log-bubble-header">
        <div className="log-bubble-status">
          {isRunning ? <Loader2 size={16} className="spinner" /> : <Terminal size={16} />}
          <span>{statusMessage || 'Thinking...'}</span>
        </div>
        <div className="log-bubble-step-count">
          {stepCount > 0 ? `Step ${stepCount}` : ''}
        </div>
      </div>

      {lastStep && (
        <div className="log-bubble-content">
           <div className="step-action">
             <Code2 size={14} /> Action: {lastStep.action}
           </div>

           {lastStep.code && (
             <div className="step-code">
               <pre><code>{lastStep.code}</code></pre>
             </div>
           )}

           {lastStep.output && (
             <div className="step-output">
               <div className="output-label"><Play size={12} /> Output</div>
               <pre><code>{lastStep.output}</code></pre>
             </div>
           )}
        </div>
      )}
    </div>
  );
}
