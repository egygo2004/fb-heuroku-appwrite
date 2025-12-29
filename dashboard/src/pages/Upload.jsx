import React, { useState } from 'react';
import { databases, CONFIG } from '../lib/appwrite';
import { ID } from 'appwrite';
import { UploadCloud, Check, AlertCircle } from 'lucide-react';

const Upload = () => {
    const [text, setText] = useState('');
    const [loading, setLoading] = useState(false);
    const [status, setStatus] = useState(null); // { type: 'success'|'error', msg: '' }

    const handleUpload = async () => {
        if (!text.trim()) return;
        setLoading(true);
        setStatus(null);

        const lines = text.split('\n').map(l => l.trim()).filter(l => l);
        let count = 0;
        let errors = 0;

        try {
            // Batch creation (in parallel)
            const promises = lines.map(phone =>
                databases.createDocument(
                    CONFIG.DATABASE_ID,
                    CONFIG.COLLECTION_NUMBERS,
                    ID.unique(),
                    {
                        phone: phone,
                        status: 'pending'
                    }
                ).then(() => count++).catch(() => errors++)
            );

            await Promise.all(promises);

            setStatus({
                type: 'success',
                msg: `Successfully uploaded ${count} numbers. ${errors > 0 ? `(${errors} failed)` : ''}`
            });
            setText('');
        } catch (e) {
            console.error(e);
            setStatus({ type: 'error', msg: `Upload failed: ${e.message} (Code: ${e.code})` });
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="max-w-4xl mx-auto p-6">
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-8">
                <h1 className="text-2xl font-bold mb-6 flex items-center space-x-2">
                    <UploadCloud className="text-blue-500" />
                    <span>Upload Numbers</span>
                </h1>

                <div className="space-y-4">
                    <div className="space-y-2">
                        <label className="text-sm text-gray-400">Paste Numbers (One per line)</label>
                        <textarea
                            value={text}
                            onChange={(e) => setText(e.target.value)}
                            className="w-full h-64 bg-gray-950 border border-gray-800 rounded-lg p-4 font-mono text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none resize-none placeholder-gray-700"
                            placeholder="+1234567890&#10;+0987654321"
                        />
                    </div>

                    <div className="flex items-center justify-between">
                        <div className="text-sm text-gray-500">
                            {text.split('\n').filter(l => l.trim()).length} numbers detected
                        </div>
                        <button
                            onClick={handleUpload}
                            disabled={loading || !text.trim()}
                            className={`px-6 py-2 rounded-lg font-medium flex items-center space-x-2 transition ${loading || !text.trim()
                                ? 'bg-gray-800 text-gray-500 cursor-not-allowed'
                                : 'bg-blue-600 hover:bg-blue-500 text-white'
                                }`}
                        >
                            {loading && <div className="w-4 h-4 border-2 border-white/20 border-t-white rounded-full animate-spin" />}
                            <span>{loading ? 'Uploading...' : 'Upload Numbers'}</span>
                        </button>
                    </div>

                    {status && (
                        <div className={`p-4 rounded-lg flex items-center space-x-2 ${status.type === 'success' ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'
                            }`}>
                            {status.type === 'success' ? <Check size={20} /> : <AlertCircle size={20} />}
                            <span>{status.msg}</span>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default Upload;
