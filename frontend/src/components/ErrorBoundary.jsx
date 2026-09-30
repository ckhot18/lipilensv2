import { Component } from 'react'

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError() {
    return { hasError: true }
  }

  reload = () => {
    window.location.reload()
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="error-boundary">
          <div className="error-boundary-card">
            <span className="error-boundary-icon" aria-hidden="true">✦</span>
            <h2>Something went wrong</h2>
            <p className="error-boundary-message">
              The application encountered an unexpected error.
            </p>
            <button className="btn" onClick={this.reload}>
              Reload
            </button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}