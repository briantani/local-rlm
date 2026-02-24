import { useState, useEffect } from 'react';
import './LogBubble.css';
import { Loader2, Terminal, Code2, Play, ChevronDown, ChevronRight } from 'lucide-react';

export default function LogBubble({ step, stepNumber, statusMessage, isRunning }) {
  const [isExpanded, setIsExpanded] = useState(false);

  useEffect(() => {
    if (isRunning) {
      setIsExpanded(true);
    }
  }, [isRunning]);

  if (!step) return null;

  return (
    <div className="log-bubble">
      <div
        className="log-bubble-header"
        onClick={() => setIsExpanded(!isExpanded)}
        style={{ cursor: 'pointer', userSelect: 'none' }}
      >
        <div className="log-bubble-status">
          {isExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
          {isRunning ? <Loader2 size={16} className="spinner" /> : <Terminal size={16} />}
          <span>{statusMessage || step.action || 'Executing...'}</span>
        </div>
        <div className="log-bubble-step-count">
          Step {stepNumber}
        </div>
      </div>

      {isExpanded && (
        <div className="log-bubble-content">
           <div className="step-action">
             <Code2 size={14} /> Action: {step.action}
           </div>

           {step.code && (
             <div className="step-code">
               <pre><code>{step.code}</code></pre>
             </div>
           )}

           {step.output && (
             <div className="step-output">
               <div className="output-label"><Play size={12} /> Output</div>
               <pre><code>{step.output}</code></pre>
             </div>
           )}
        </div>
      )}
    </div>
  );
}
