import React from 'react';
import ReactDOM from 'react-dom/client';
import { App } from './App';
import { SelectedFeatureProvider } from './context/SelectedFeatureContext';
import './index.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <SelectedFeatureProvider>
      <App />
    </SelectedFeatureProvider>
  </React.StrictMode>
);
