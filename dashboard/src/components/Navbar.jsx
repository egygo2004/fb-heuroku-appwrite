import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { LayoutDashboard, UploadCloud, Search, Smartphone } from 'lucide-react';

const Navbar = () => {
    const location = useLocation();

    const isActive = (path) => location.pathname === path ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-white hover:bg-gray-800';

    return (
        <nav className="border-b border-gray-800 bg-gray-950 sticky top-0 z-50">
            <div className="max-w-7xl mx-auto px-4">
                <div className="flex items-center justify-between h-16">
                    <div className="flex items-center space-x-2">
                        <div className="p-2 bg-blue-600 rounded-lg">
                            <Smartphone size={20} className="text-white" />
                        </div>
                        <span className="text-xl font-bold bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
                            FB OTP Bot
                        </span>
                    </div>

                    <div className="flex items-center space-x-4">
                        <Link to="/" className={`px-3 py-2 rounded-md text-sm font-medium transition flex items-center space-x-2 ${isActive('/')}`}>
                            <LayoutDashboard size={18} />
                            <span>Dashboard</span>
                        </Link>
                        <Link to="/upload" className={`px-3 py-2 rounded-md text-sm font-medium transition flex items-center space-x-2 ${isActive('/upload')}`}>
                            <UploadCloud size={18} />
                            <span>Upload</span>
                        </Link>
                        <Link to="/logs" className={`px-3 py-2 rounded-md text-sm font-medium transition flex items-center space-x-2 ${isActive('/logs')}`}>
                            <Search size={18} />
                            <span>Logs</span>
                        </Link>
                    </div>
                </div>
            </div>
        </nav>
    );
};

export default Navbar;
