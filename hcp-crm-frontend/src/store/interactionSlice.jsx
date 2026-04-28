import { createSlice } from '@reduxjs/toolkit';

// Initial state matches the requirements of the "Log Interaction Screen" [cite: 21-51]
const initialState = {
  hcp_name: '',           // [cite: 22]
  interaction_type: 'Meeting', // [cite: 25-26]
  date: new Date().toISOString().split('T')[0], // [cite: 24, 35]
  time: '19:36',          // [cite: 27-28]
  attendees: '',          // [cite: 36]
  topics: '',             // [cite: 38]
  sentiment: 'Neutral',   // [cite: 43-44]
  outcomes: '',           // [cite: 45-46]
  follow_ups: [],         // [cite: 47, 49]
};

const interactionSlice = createSlice({
  name: 'interaction',
  initialState,
  reducers: {
    // Used for manual typing in the form fields [cite: 10]
    updateField: (state, action) => {
      const { field, value } = action.payload;
      state[field] = value;
    },
    
    // The "Magic" action: Merges structured data from the LangGraph Agent [cite: 13, 60]
    syncFromAI: (state, action) => {
      const aiData = action.payload;
      
      // We map the backend keys to our frontend state keys
      if (aiData.hcp_name) state.hcp_name = aiData.hcp_name;
      if (aiData.sentiment) state.sentiment = aiData.sentiment;
      if (aiData.topics) state.topics = Array.isArray(aiData.topics) ? aiData.topics.join(', ') : aiData.topics;
      if (aiData.follow_ups) state.follow_ups = aiData.follow_ups;
      if (aiData.interaction_type) state.interaction_type = aiData.interaction_type;
    },

    // Resets the form after a successful submission [cite: 4, 125]
    resetForm: () => initialState,
  },
});

export const { updateField, syncFromAI, resetForm } = interactionSlice.actions;
export default interactionSlice.reducer;