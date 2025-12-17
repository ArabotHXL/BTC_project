import React from 'react';

interface AlertProps {
  type: 'success' | 'error' | 'warning' | 'info';
  message: string;
  onClose?: () => void;
}

export const Alert: React.FC<AlertProps> = ({ type, message, onClose }) => {
  const typeClasses = {
    success: 'bg-green-900 border-green-500 text-green-200',
    error: 'bg-red-900 border-red-500 text-red-200',
    warning: 'bg-yellow-900 border-yellow-500 text-yellow-200',
    info: 'bg-blue-900 border-blue-500 text-blue-200',
  };

  return (
    <div className={`border-l-4 p-4 mb-4 ${typeClasses[type]}`}>
      <div className="flex justify-between items-center">
        <p>{message}</p>
        {onClose && (
          <button
            onClick={onClose}
            className="ml-4 text-xl font-bold hover:opacity-75"
          >
            ×
          </button>
        )}
      </div>
    </div>
  );
};
