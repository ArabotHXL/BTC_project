import { Outlet } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { LoadingSpinner } from './ui/LoadingSpinner';

export const PrivateRoute = () => {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-900">
        <LoadingSpinner />
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-900">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-white mb-4">需要登录</h2>
          <p className="text-gray-400 mb-6">请先在主应用登录后再访问 CRM 系统</p>
          <a 
            href="/" 
            className="inline-block px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            返回主页登录
          </a>
        </div>
      </div>
    );
  }

  return <Outlet />;
};
