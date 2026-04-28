import React from 'react';
import InteractionForm from './components/InteractionForm';
import AIChatAssistant from './components/AIChatAssistant';
import './App.css';

function App() {
  return (
    <div className="app-container">
      <header className="app-header">
        <h1>Log HCP Interaction</h1>
      </header>
      <main className="main-content">
        {/* Left Side: Structured Form */}
        <section className="form-section">
          <InteractionForm />
        </section>

        {/* Right Side: AI Assistant Chat */}
        <section className="chat-section">
          <AIChatAssistant />
        </section>
      </main>
    </div>
  );
}

export default App;