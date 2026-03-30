/**
 * ToastNotification — Slide-in toast container + individual toast.
 * @spec docs/spec/07_FRONTEND_SPEC.md#toast-notifications
 */
import { useEffect } from "react";
import { X, Info, CheckCircle, AlertTriangle, XCircle } from "lucide-react";
import { useSimulationStore } from "../../store/simulationStore";

export default function ToastContainer() {
  const toasts = useSimulationStore((s) => s.toasts);
  const removeToast = useSimulationStore((s) => s.removeToast);

  return (
    <div
      aria-live="polite"
      className="fixed top-4 right-4 z-[9999] flex flex-col gap-2 pointer-events-none"
    >
      {toasts.map((t) => (
        <Toast key={t.id} toast={t} onDismiss={() => removeToast(t.id)} />
      ))}
    </div>
  );
}

interface ToastItem {
  id: string;
  type: "info" | "success" | "warning" | "error";
  message: string;
}

function Toast({ toast, onDismiss }: { toast: ToastItem; onDismiss: () => void }) {
  useEffect(() => {
    const timer = setTimeout(onDismiss, 5000);
    return () => clearTimeout(timer);
  }, [onDismiss]);

  const config = {
    info: {
      icon: <Info className="w-4 h-4 shrink-0" />,
      classes: "border-blue-500/40 bg-blue-500/10 text-blue-400",
    },
    success: {
      icon: <CheckCircle className="w-4 h-4 shrink-0" />,
      classes: "border-green-500/40 bg-green-500/10 text-green-400",
    },
    warning: {
      icon: <AlertTriangle className="w-4 h-4 shrink-0" />,
      classes: "border-yellow-500/40 bg-yellow-500/10 text-yellow-400",
    },
    error: {
      icon: <XCircle className="w-4 h-4 shrink-0" />,
      classes: "border-red-500/40 bg-red-500/10 text-red-400",
    },
  }[toast.type];

  return (
    <div
      className={`pointer-events-auto flex items-start gap-2.5 min-w-[280px] max-w-sm px-3.5 py-3 rounded-lg border shadow-lg backdrop-blur-sm animate-slide-in-right text-sm ${config.classes}`}
    >
      {config.icon}
      <span className="flex-1 leading-snug">{toast.message}</span>
      <button
        onClick={onDismiss}
        className="shrink-0 opacity-60 hover:opacity-100 transition-opacity mt-0.5"
        aria-label="Dismiss"
      >
        <X className="w-3.5 h-3.5" />
      </button>
    </div>
  );
}
