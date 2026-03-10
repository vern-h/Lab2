import React, { useEffect, useState } from 'react';
import axios from 'axios';
import './App.css';

function App() {
  const [data, setData] = useState([]);
  const targetUsers = ["214328887", "107830991"];

  useEffect(() => {
    const apiBase = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    axios.get(`${apiBase}/user-stats`)
      .then(res => setData(res.data));
  }, []);

  return (
    <div className="app">
      <h1 className="page-title">Twitter User Statistics</h1>
      <div className="user-lines">
        {data.filter(u => targetUsers.includes(u.id)).map(user => (
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