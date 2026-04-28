import React, { useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { syncFromAI } from '../store/interactionSlice';
import { sendChatMessage } from '../api/chatApi';

const AIChatAssistant = () => {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState([{ role: 'ai', content: 'Hello! I can help you log your latest HCP interaction. Just describe what happened.' }]);
  const dispatch = useDispatch();
  const currentData = useSelector(state => state.interaction);

  const handleSend = async () => {
    if (!input.trim()) return;
    const userMsg = { role: 'user', content: input };
    setMessages(prev => [...prev, userMsg]);
    setInput('');

    try {
      const data = await sendChatMessage(input, currentData);
      if (data.updated_data) dispatch(syncFromAI(data.updated_data));
      setMessages(prev => [...prev, { role: 'ai', content: data.response }]);
    } catch (err) {
      setMessages(prev => [...prev, { role: 'ai', content: 'Sorry, I encountered an error connecting to the agent.' }]);
    }
  };

  return (
    <div className="chat-section">
      <div className="chat-history">
        {messages.map((m, i) => (
          <div key={i} className={`message ${m.role}`}>{m.content}</div>
        ))}
      </div>
      <div className="chat-input-area">
        <input 
          value={input} 
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type interaction details..."
          onKeyPress={(e) => e.key === 'Enter' && handleSend()}
        />
        <button 
          onClick={handleSend}
          style={{ background: 'var(--primary)', color: 'white', border: 'none', padding: '10px 20px', borderRadius: '8px', cursor: 'pointer' }}
        >
          Send
        </button>
      </div>
    </div>
  );
};

export default AIChatAssistant;