import React, { useState, useEffect } from 'react';
import { databases, storage, CONFIG } from '../lib/appwrite';
import { Query } from 'appwrite';
import { Search, Image, FileText } from 'lucide-react';
import { useSearchParams } from 'react-router-dom';

const Logs = () => {
    const [searchParams] = useSearchParams();
    const [query, setQuery] = useState(searchParams.get('q') || '');
    const [logs, setLogs] = useState([]);
    const [loading, setLoading] = useState(false);
    const [selectedNumber, setSelectedNumber] = useState(null);

    const searchLogs = async (phoneQuery) => {
        if (!phoneQuery) return;
        setLoading(true);
        try {
            // 1. Find the number ID first (assuming search is by phone)
            // Appwrite doesn't support deep join queries easily, so 2 steps
            const numberDocs = await databases.listDocuments(
                CONFIG.DATABASE_ID,
                CONFIG.COLLECTION_NUMBERS,
                [Query.equal('phone', phoneQuery)]
            );

            if (numberDocs.total === 0) {
                setLogs([]);
                setSelectedNumber(null);
                setLoading(false);
                return;
            }

            const numberDoc = numberDocs.documents[0];
            setSelectedNumber(numberDoc);

            // 2. Fetch logs for this number ID
            const logDocs = await databases.listDocuments(
                CONFIG.DATABASE_ID,
                CONFIG.COLLECTION_LOGS,
                [
                    Query.equal('number_id', numberDoc.$id),
                    Query.orderAsc('timestamp'), // Chronological order
                    Query.limit(100)
                ]
            );
            setLogs(logDocs.documents);

        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (query) {
            searchLogs(query);
        }
    }, []);

    const handleSearch = (e) => {
        e.preventDefault();
        searchLogs(query);
    }

    const getScreenshotUrl = (fileId) => {
        return storage.getFileView(CONFIG.BUCKET_ID, fileId);
    }

    return (
        <div className="p-6 max-w-7xl mx-auto space-y-6">
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-8">
                <form onSubmit={handleSearch} className="flex gap-4">
                    <div className="relative flex-1">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={20} />
                        <input
                            type="text"
                            value={query}
                            onChange={e => setQuery(e.target.value)}
                            placeholder="Search by phone number (e.g. +1234567890)"
                            className="w-full bg-gray-950 border border-gray-800 rounded-lg py-3 pl-10 pr-4 focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                        />
                    </div>
                    <button type="submit" className="bg-blue-600 hover:bg-blue-500 text-white px-6 py-2 rounded-lg font-medium transition">
                        Search Log
                    </button>
                </form>
            </div>

            {selectedNumber && (
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    <div className="lg:col-span-3">
                        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 flex justify-between items-center">
                            <div>
                                <p className="text-gray-400 text-sm">Status</p>
                                <span className={`inline-block px-3 py-1 rounded-full text-sm font-medium mt-1 ${selectedNumber.status === 'completed' ? 'bg-green-500/20 text-green-400' :
                                        selectedNumber.status === 'failed' ? 'bg-red-500/20 text-red-400' :
                                            selectedNumber.status === 'processing' ? 'bg-yellow-500/20 text-yellow-400' : 'bg-gray-700 text-gray-300'
                                    }`}>
                                    {selectedNumber.status?.toUpperCase()}
                                </span>
                            </div>
                            <div className="text-right">
                                <p className="text-gray-400 text-sm">Result</p>
                                <p className="font-mono">{selectedNumber.result || '-'}</p>
                            </div>
                        </div>
                    </div>

                    <div className="lg:col-span-3 bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
                        <div className="p-4 border-b border-gray-800">
                            <h2 className="text-lg font-semibold flex items-center gap-2">
                                <FileText size={20} className="text-blue-500" />
                                Execution Timeline
                            </h2>
                        </div>
                        <div className="divide-y divide-gray-800">
                            {logs.length === 0 ? (
                                <div className="p-8 text-center text-gray-500">No logs found for this number.</div>
                            ) : (
                                logs.map((log) => (
                                    <div key={log.$id} className="p-4 hover:bg-gray-800/30 transition">
                                        <div className="flex gap-4">
                                            <div className="flex flex-col items-center">
                                                <div className="h-full w-px bg-gray-800 my-1"></div>
                                            </div>
                                            <div className="flex-1 space-y-2">
                                                <div className="flex justify-between items-start">
                                                    <p className={`font-mono text-sm ${log.level === 'error' ? 'text-red-400' :
                                                            log.level === 'success' ? 'text-green-400' : 'text-gray-300'
                                                        }`}>
                                                        {log.message}
                                                    </p>
                                                    <span className="text-xs text-gray-500 whitespace-nowrap ml-4">
                                                        {new Date(log.timestamp).toLocaleTimeString()}
                                                    </span>
                                                </div>
                                                {log.screenshot_id && (
                                                    <div className="mt-2">
                                                        <a href={getScreenshotUrl(log.screenshot_id)} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-2 px-3 py-2 bg-gray-950 border border-gray-800 rounded-lg hover:border-blue-500 transition group">
                                                            <Image size={16} className="text-blue-400" />
                                                            <span className="text-xs text-gray-400 group-hover:text-white">View Screenshot</span>
                                                        </a>
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                ))
                            )}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default Logs;
