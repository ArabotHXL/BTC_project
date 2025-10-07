import { Routes, Route } from 'react-router-dom';

function App() {
  return (
    <div className="min-h-screen bg-gray-50">
      <Routes>
        <Route path="/" element={<HomePage />} />
      </Routes>
    </div>
  );
}

function HomePage() {
  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-4xl font-bold text-gray-900 mb-4">
        Welcome to CRM Platform
      </h1>
      <p className="text-lg text-gray-600">
        Enterprise-level Customer Relationship Management System
      </p>
    </div>
  );
}

export default App;
