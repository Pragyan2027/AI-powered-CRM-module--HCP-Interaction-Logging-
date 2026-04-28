import React from 'react';
import { useSelector, useDispatch } from 'react-redux';
import { updateField } from '../store/interactionSlice';

const InteractionForm = () => {
  const formData = useSelector((state) => state.interaction);
  const dispatch = useDispatch();

  const handleUpdate = (field, value) => {
    dispatch(updateField({ field, value }));
  };

  return (
    <div className="form-section">
      <h3>Interaction Summary</h3>
      
      <div className="form-group">
        <label>Healthcare Professional (HCP)</label>
        <input 
          placeholder="e.g. Dr. Das"
          value={formData.hcp_name}
          onChange={(e) => handleUpdate('hcp_name', e.target.value)}
        />
      </div>

      <div className="form-row">
        <div className="form-group" style={{ flex: 1 }}>
          <label>Date of Interaction</label>
          <input type="date" value={formData.date} onChange={(e) => handleUpdate('date', e.target.value)} />
        </div>
        <div className="form-group" style={{ flex: 1 }}>
          <label>Interaction Type</label>
          <select value={formData.interaction_type} onChange={(e) => handleUpdate('interaction_type', e.target.value)}>
            <option>Meeting</option>
            <option>Email</option>
            <option>Phone Call</option>
          </select>
        </div>
      </div>

      <div className="form-group">
        <label>Discussion Topics</label>
        <textarea 
          rows="4"
          placeholder="Mention products, feedback, or clinical trial data..."
          value={formData.topics}
          onChange={(e) => handleUpdate('topics', e.target.value)}
        />
      </div>

      <div className="form-group">
  <label>HCP Sentiment</label>
  <div className="sentiment-options" style={{ display: 'flex', marginTop: '10px' }}>
    {['Positive', 'Neutral', 'Negative'].map((s) => (
      <div
        key={s}
        // This line dynamically adds the 'active' class based on Redux state
        className={`sentiment-chip ${formData.sentiment === s ? `active ${s}` : ''}`}
        onClick={() => dispatch(updateField({ field: 'sentiment', value: s }))}
      >
        {s}
      </div>
    ))}
  </div>
</div>
      </div>
  );
};

export default InteractionForm;