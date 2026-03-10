import React, { useEffect, useState } from 'react';
import axios from 'axios';
import './App.css';

function App() {
  const [data, setData] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    const apiBase = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    axios.get(`${apiBase}/user-stats`)
      .then(res => setData(res.data))
      .catch(err => setError(err.message || 'Failed to load stats'));
  }, []);

  return (
    <div className="app">
      <h1 className="page-title">Twitter User Statistics</h1>
      {error && <p className="error">{error}</p>}
      <div className="user-lines">
        {!error && data.length === 0 && <p className="line">Loading…</p>}
        {data.map(user => (
          <React.Fragment key={user.id}>
            <p className="line">{user.id} has {user.followers} followers</p>
            <p className="line">{user.id} has {user.followees} followees</p>
          </React.Fragment>
        ))}
      </div>
    </div>
  );
}
export default App;