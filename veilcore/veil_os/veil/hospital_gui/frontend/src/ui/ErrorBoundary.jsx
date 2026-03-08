import React from "react";

export class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, message: "" };
  }

  static getDerivedStateFromError() {
    return { hasError: true, message: "Dashboard error. Refresh the page." };
  }

  componentDidCatch(err) {
    // Don’t show stack traces to users
    console.error("Dashboard error:", err?.message || err);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: 16, color: "#e6edf3", fontFamily: "system-ui" }}>
          <h2 style={{ margin: 0 }}>Something went wrong</h2>
          <p style={{ opacity: 0.85 }}>{this.state.message}</p>
          <button onClick={() => window.location.reload()}>Refresh</button>
        </div>
      );
    }
    return this.props.children;
  }
}
