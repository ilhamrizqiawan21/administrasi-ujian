import { Component, type ErrorInfo, type ReactNode } from "react";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  message: string;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, message: "" };

  static getDerivedStateFromError(error: Error): State {
    return {
      hasError: true,
      message: error.message || "Terjadi kesalahan pada antarmuka.",
    };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    if (import.meta.env.DEV) {
      console.error("UI ErrorBoundary:", error, info);
    }
  }

  render() {
    if (this.state.hasError) {
      return (
        <main className="spike-shell">
          <section className="panel error-panel" role="alert">
            <h1>Antarmuka Mengalami Gangguan</h1>
            <p>{this.state.message}</p>
            <button
              type="button"
              className="btn-primary"
              onClick={() => window.location.reload()}
            >
              Muat Ulang
            </button>
          </section>
        </main>
      );
    }
    return this.props.children;
  }
}
