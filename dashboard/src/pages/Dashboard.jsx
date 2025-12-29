import React, { useState, useEffect } from 'react';
import { client, databases, storage, CONFIG } from '../lib/appwrite';
import { Query } from 'appwrite';
import { Activity, CheckCircle, Clock, AlertTriangle, ExternalLink, Image, ChevronDown, ChevronUp } from 'lucide-react';
import { Link } from 'react-router-dom';

const Dashboard = () => {
    const [stats, setStats] = useState({
        pending: 0,
        processing: 0,
        completed: 0,
        failed: 0
    });
    const [allNumbers, setAllNumbers] = useState([]);
    const [expandedRow, setExpandedRow] = useState(null);
    const [numberLogs, setNumberLogs] = useState({});

    const fetchStats = async () => {
        try {
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
        } catch (error) {
            console.error(error);
        }
    };

    const fetchAllNumbers = async () => {
        try {
            const result = await databases.listDocuments(
                CONFIG.DATABASE_ID,
                CONFIG.COLLECTION_NUMBERS,
                [Query.orderDesc('$createdAt'), Query.limit(50)]
            );
            setAllNumbers(result.documents);
        } catch (e) { console.error(e); }
    };

    const fetchLogsForNumber = async (numberId) => {
        if (numberLogs[numberId]) return; // Already fetched
        try {
            const logs = await databases.listDocuments(
                CONFIG.DATABASE_ID,
                CONFIG.COLLECTION_LOGS,
                [Query.equal('number_id', numberId), Query.orderAsc('$createdAt'), Query.limit(100)]
            );
            setNumberLogs(prev => ({ ...prev, [numberId]: logs.documents }));
        } catch (e) { console.error(e); }
    };

    const toggleRow = (numberId) => {
        if (expandedRow === numberId) {
            setExpandedRow(null);
        } else {
            setExpandedRow(numberId);
            fetchLogsForNumber(numberId);
        }
    };

    const getScreenshotUrl = (fileId) => {
        return storage.getFileView(CONFIG.BUCKET_ID, fileId);
    };

    useEffect(() => {
        fetchStats();
        fetchAllNumbers();

        const unsubNumbers = client.subscribe(
            `databases.${CONFIG.DATABASE_ID}.collections.${CONFIG.COLLECTION_NUMBERS}.documents`,
            () => {
                fetchStats();
                fetchAllNumbers();
            }
        );

        const unsubLogs = client.subscribe(
            `databases.${CONFIG.DATABASE_ID}.collections.${CONFIG.COLLECTION_LOGS}.documents`,
            (response) => {
                if (response.events.includes('databases.*.collections.*.documents.*.create')) {
                    const log = response.payload;
                    if (log.number_id) {
                        setNumberLogs(prev => {
                            if (prev[log.number_id]) {
                                return { ...prev, [log.number_id]: [...prev[log.number_id], log] };
                            }
                            return prev;
                        });
                    }
                }
            }
        );

        return () => {
            unsubNumbers();
            unsubLogs();
        };
    }, []);

    const getStatusBadge = (status) => {
        const styles = {
            pending: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
            processing: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
            completed: 'bg-green-500/20 text-green-400 border-green-500/30',
            failed: 'bg-red-500/20 text-red-400 border-red-500/30'
        };
        return (
            <span className={`px-2 py-1 text-xs font-medium rounded border ${styles[status] || styles.pending}`}>
                {status?.toUpperCase()}
            </span>
        );
    };

    return (
        <div className="p-6 max-w-7xl mx-auto space-y-6">
            <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
                Live Overview
            </h1>

            {/* Stats Cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <Card icon={<Clock size={24} />} color="blue" label="Pending" value={stats.pending} />
                <Card icon={<Activity size={24} />} color="yellow" label="Processing" value={stats.processing} />
                <Card icon={<CheckCircle size={24} />} color="green" label="Completed" value={stats.completed} />
                <Card icon={<AlertTriangle size={24} />} color="red" label="Failed" value={stats.failed} />
            </div>

            {/* Numbers Table */}
            <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
                <div className="p-4 border-b border-gray-800 bg-gray-900/50">
                    <h2 className="text-xl font-semibold">All Numbers</h2>
                </div>
                <div className="overflow-x-auto">
                    <table className="w-full">
                        <thead className="bg-gray-950 text-left text-sm text-gray-400">
                            <tr>
                                <th className="p-3">Phone</th>
                                <th className="p-3">Status</th>
                                <th className="p-3">Steps</th>
                                <th className="p-3">Result</th>
                                <th className="p-3"></th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-800">
                            {allNumbers.map((num) => (
                                <React.Fragment key={num.$id}>
                                    <tr className="hover:bg-gray-800/50 cursor-pointer" onClick={() => toggleRow(num.$id)}>
                                        <td className="p-3 font-mono font-bold">{num.phone}</td>
                                        <td className="p-3">{getStatusBadge(num.status)}</td>
                                        <td className="p-3 text-sm text-gray-400">
                                            {numberLogs[num.$id]?.length || 0} steps
                                        </td>
                                        <td className="p-3 text-sm text-gray-400 max-w-[200px] truncate">
                                            {num.result || '-'}
                                        </td>
                                        <td className="p-3 text-gray-500">
                                            {expandedRow === num.$id ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
                                        </td>
                                    </tr>
                                    {expandedRow === num.$id && (
                                        <tr>
                                            <td colSpan="5" className="p-0 bg-gray-950">
                                                <div className="p-4 space-y-3 max-h-[400px] overflow-y-auto">
                                                    {numberLogs[num.$id]?.length === 0 && (
                                                        <p className="text-gray-500 text-sm">No logs yet...</p>
                                                    )}
                                                    {numberLogs[num.$id]?.map((log, idx) => (
                                                        <div key={log.$id} className="flex gap-4 items-start border-l-2 border-gray-700 pl-4">
                                                            <div className="flex-1">
                                                                <div className="flex items-center gap-2 mb-1">
                                                                    <span className="text-xs text-gray-500">{idx + 1}.</span>
                                                                    <span className={`text-sm ${log.level === 'error' ? 'text-red-400' :
                                                                            log.level === 'success' ? 'text-green-400' : 'text-gray-300'
                                                                        }`}>
                                                                        {log.message}
                                                                    </span>
                                                                </div>
                                                                {log.screenshot_id && (
                                                                    <a
                                                                        href={getScreenshotUrl(log.screenshot_id)}
                                                                        target="_blank"
                                                                        rel="noopener noreferrer"
                                                                        className="inline-flex items-center gap-1 mt-1 px-2 py-1 bg-gray-800 border border-gray-700 rounded text-xs text-blue-400 hover:bg-gray-700"
                                                                    >
                                                                        <Image size={12} /> Screenshot
                                                                    </a>
                                                                )}
                                                            </div>
                                                        </div>
                                                    ))}
                                                </div>
                                            </td>
                                        </tr>
                                    )}
                                </React.Fragment>
                            ))}
                        </tbody>
                    </table>
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
};

export default Dashboard;
