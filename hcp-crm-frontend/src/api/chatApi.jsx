import axios from 'axios';

const API_URL = 'http://localhost:8000';

// Ensure the 'export' keyword is right here!
export const sendChatMessage = async (message, currentData) => {
  try {
    const response = await axios.post(`${API_URL}/chat`, {
      message: message,
      current_data: currentData 
    });
    return response.data; 
  } catch (error) {
    console.error("API Error:", error);
    throw error;
  }
};