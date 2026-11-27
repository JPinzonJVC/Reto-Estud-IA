import React from 'react';
import { createRoot } from 'react-dom/client';
import { App } from './App';
import { MlDashboard } from './pages/MlDashboard';
import './styles.css';
import './ml.css';

const rootElement = document.getElementById('root');

if (!rootElement) {
  throw new Error('No se encontró el nodo raíz de la aplicación.');
}

createRoot(rootElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);

const mlRoot = document.getElementById('ml-react-root');
if (mlRoot) {
  createRoot(mlRoot).render(
    <React.StrictMode>
      <MlDashboard />
    </React.StrictMode>,
  );
}
