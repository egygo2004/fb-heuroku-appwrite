import React, { useState, useEffect } from 'react';
import { client, databases, CONFIG } from '../lib/appwrite';
import { Query } from 'appwrite';
import { Activity, CheckCircle, Clock, AlertTriangle, Search, ExternalLink } from 'lucide-react';
import { Link } from 'react-router-dom';

const Dashboard = () => {
    const [stats, setStats] = useState({
        pending: 0,
        processing: 0,
        completed: 0,
        failed: 0
    });
    const [activeWorkers, setActiveWorkers] = useState([]);
    const [recentLogs, setRecentLogs] = useState([]);

    const fetchStats = async () => {
        try {
            // Using listDocuments total count for stats is efficient enough for small scale
            const [pending, processing, completed, failed] = await Promise.all([
                databases.listDocuments(CONFIG.DATABASE_ID, CONFIG.COLLECTION_NUMBERS, [Query.equal('status', 'pending'), Query.limit(1)]),
                databases.listDocuments(CONFIG.DATABASE_ID, CONFIG.COLLECTION_NUMBERS, [Query.equal('status', 'processing'), Query.limit(100)]),
                databases.listDocuments(CONFIG.DATABASE_ID, CONFIG.COLLECTION_NUMBERS, [Query.equal('status', 'completed'), Query.limit(1)]),
                databases.listDocuments(CONFIG.DATABASE_ID, CONFIG.COLLECTION_NUMBERS, [Query.equal('status', 'failed'), Query.limit(1)])
            ]);

            setStats({
                pending: pending.total,
                processing: processing.total,
                completed: completed.total,
                failed: failed.total
            });
            setActiveWorkers(processing.documents);

        } catch (error) {
            console.error(error);
        }
    };

    const fetchRecentLogs = async () => {
        try {
            const logs = await databases.listDocuments(
                CONFIG.DATABASE_ID,
                CONFIG.COLLECTION_LOGS,
                [Query.orderDesc('timestamp'), Query.limit(10)]
            );
            setRecentLogs(logs.documents);
        } catch (e) { console.error(e); }
    };

    useEffect(() => {
        fetchStats();
        fetchRecentLogs();

        // Subscribe to numbers collection for live stats
        const unsubNumbers = client.subscribe(
            `databases.${CONFIG.DATABASE_ID}.collections.${CONFIG.COLLECTION_NUMBERS}.documents`,
            () => fetchStats()
        );

        // Subscribe to logs for live ticker
        const unsubLogs = client.subscribe(
            `databases.${CONFIG.DATABASE_ID}.collections.${CONFIG.COLLECTION_LOGS}.documents`,
            (response) => {
                if (response.events.includes('databases.*.collections.*.documents.*.create')) {
                    setRecentLogs(prev => [response.payload, ...prev].slice(0, 10));
                }
            }
        );

        return () => {
            unsubNumbers();
            unsubLogs();
        };
    }, []);

    return (
        <div className="p-6 max-w-7xl mx-auto space-y-6">
            <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
                Live Overview
            </h1>

            {/* Stats Cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <Card icon={<Clock size={24} />} color="blue" label="Pending" value={stats.pending} />
                <Card icon={<Activity size={24} />} color="yellow" label="Processing" value={stats.processing} />
                <Card icon={<CheckCircle size={24} />} color="green" label="Completed" value={stats.completed} />
                <Card icon={<AlertTriangle size={24} />} color="red" label="Failed" value={stats.failed} />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Active Workers */}
                <div className="lg:col-span-2 bg-gray-900 border border-gray-800 rounded-xl overflow-hidden flex flex-col h-[500px]">
                    <div className="p-4 border-b border-gray-800 flex justify-between items-center bg-gray-900/50 backdrop-blur">
                        <h2 className="text-xl font-semibold flex items-center gap-2">
                            <Activity size={20} className="text-green-500" />
                            Active Workers ({activeWorkers.length})
                        </h2>
                    </div>
                    <div className="overflow-y-auto flex-1 p-2 space-y-2">
                        {activeWorkers.length === 0 ? (
                            <div className="flex flex-col items-center justify-center h-full text-gray-500">
                                <Clock size={48} className="mb-4 opacity-50" />
                                <p>No active processing tasks.</p>
                            </div>
                        ) : (
                            activeWorkers.map(doc => (
                                <div key={doc.$id} className="p-4 bg-gray-950 border border-gray-800 rounded-lg hover:border-blue-500/50 transition flex justify-between items-center">
                                    <div className="flex items-center space-x-4">
                                        <div className="relative">
                                            <div className="w-3 h-3 bg-green-500 rounded-full animate-ping absolute inset-0 opacity-75"></div>
                                            <div className="w-3 h-3 bg-green-500 rounded-full relative"></div>
                                        </div>
                                        <div>
                                            <p className="font-mono font-bold text-lg">{doc.phone}</p>
                                            <p className="text-xs text-gray-500 font-mono">Worker: {doc.worker_id || 'Unknown'}</p>
                                        </div>
                                    </div>
                                    <Link to={`/logs?q=${doc.phone}`} className="p-2 hover:bg-gray-800 rounded-full text-blue-400 transition">
                                        <ExternalLink size={20} />
                                    </Link>
                                </div>
                            ))
                        )}
                    </div>
                </div>

                {/* Recent Logs Ticker */}
                <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden flex flex-col h-[500px]">
                    <div className="p-4 border-b border-gray-800 bg-gray-900/50 backdrop-blur">
                        <h2 className="text-xl font-semibold">Live Logs</h2>
                    </div>
                    <div className="overflow-y-auto flex-1 p-2 font-mono text-xs space-y-1">
                        {recentLogs.map((log) => (
                            <div key={log.$id} className={`p-2 rounded border border-gray-800/50 ${getLogColor(log.level)}`}>
                                <div className="flex justify-between opacity-50 mb-1">
                                    <span>{new Date(log.timestamp).toLocaleTimeString()}</span>
                                </div>
                                <p className="break-words">{log.message}</p>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
};

const Card = ({ icon, color, label, value }) => {
    const colors = {
        blue: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
        yellow: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20',
        green: 'bg-green-500/10 text-green-400 border-green-500/20',
        red: 'bg-red-500/10 text-red-400 border-red-500/20',
    };

    return (
        <div className={`border p-4 rounded-xl flex items-center space-x-4 ${colors[color].replace('text-', 'border-')}`}>
            <div className={`p-3 rounded-lg ${colors[color]}`}>{icon}</div>
            <div>
                <p className="text-gray-400 text-sm">{label}</p>
                <p className="text-2xl font-bold font-mono">{value}</p>
            </div>
        </div>
    );
}

const getLogColor = (level) => {
    switch (level?.toLowerCase()) {
        case 'error': return 'bg-red-950/30 text-red-200 border-red-900/50';
        case 'warning': return 'bg-yellow-950/30 text-yellow-200 border-yellow-900/50';
        case 'success': return 'bg-green-950/30 text-green-200 border-green-900/50';
        default: return 'bg-gray-950 text-gray-400';
    }
}

export default Dashboard;
