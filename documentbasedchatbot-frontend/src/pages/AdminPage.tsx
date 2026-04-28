import React, { useState, useEffect, useCallback } from 'react';

interface Lead {
  id: string;
  name: string;
  phone: string;
  sugar_level: string;
  created_at: string;
}

interface AdminPageProps {
  onBackClick?: () => void;
}

const SESSION_KEY = 'admin_api_key';

export const AdminPage: React.FC<AdminPageProps> = ({ onBackClick }) => {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [activeTab, setActiveTab] = useState<'upload' | 'leads'>('leads');
  const [adminKey, setAdminKey] = useState<string>(() => sessionStorage.getItem(SESSION_KEY) || '');
  const [keyInput, setKeyInput] = useState('');
  const [authError, setAuthError] = useState('');
  const [page, setPage] = useState(1);
  const [totalLeads, setTotalLeads] = useState(0);
  const PAGE_SIZE = 20;

  const API_BASE = (import.meta.env.VITE_API_URL || 'http://localhost:8000').trim();

  const adminHeaders = useCallback(() => ({
    'Content-Type': 'application/json',
    'X-Admin-Key': adminKey,
  }), [adminKey]);

  const fetchLeads = useCallback(async (pageNum: number) => {
    if (!adminKey) return;
    try {
      const offset = (pageNum - 1) * PAGE_SIZE;
      const response = await fetch(
        `${API_BASE}/admin/leads?limit=${PAGE_SIZE}&offset=${offset}`,
        { headers: adminHeaders() }
      );
      if (response.status === 401) {
        setAdminKey('');
        sessionStorage.removeItem(SESSION_KEY);
        setAuthError('Invalid admin key. Please try again.');
        return;
      }
      const data = await response.json();
      setLeads(data.leads || []);
      setTotalLeads(data.total ?? data.count ?? 0);
    } catch (error) {
      console.error('Error fetching leads:', error);
    }
  }, [adminKey, adminHeaders, API_BASE]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (adminKey) fetchLeads(page);
  }, [adminKey, page, fetchLeads]);

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = keyInput.trim();
    if (!trimmed) return;
    sessionStorage.setItem(SESSION_KEY, trimmed);
    setAdminKey(trimmed);
    setAuthError('');
    setKeyInput('');
  };

  const handleLogout = () => {
    sessionStorage.removeItem(SESSION_KEY);
    setAdminKey('');
    setLeads([]);
  };

  const totalPages = Math.ceil(totalLeads / PAGE_SIZE) || 1;

  // — Key entry screen —
  if (!adminKey) {
    return (
      <div className="h-screen w-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex items-center justify-center">
        <form
          onSubmit={handleLogin}
          className="bg-slate-800 border border-purple-500/30 rounded-xl p-8 w-full max-w-sm flex flex-col gap-4"
        >
          <h2 className="text-2xl font-bold text-white text-center">Admin Access</h2>
          {authError && <p className="text-red-400 text-sm text-center">{authError}</p>}
          <input
            type="password"
            value={keyInput}
            onChange={(e) => setKeyInput(e.target.value)}
            placeholder="Enter admin key"
            className="bg-slate-700 text-white rounded-lg px-4 py-3 outline-none focus:ring-2 focus:ring-purple-500"
            autoFocus
          />
          <button
            type="submit"
            className="bg-purple-600 hover:bg-purple-700 text-white font-semibold py-3 rounded-lg transition"
          >
            Unlock
          </button>
          {onBackClick && (
            <button
              type="button"
              onClick={onBackClick}
              className="text-gray-400 hover:text-white text-sm text-center transition"
            >
              ← Back to chat
            </button>
          )}
        </form>
      </div>
    );
  }

  return (
    <div className="h-screen w-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 text-white flex overflow-hidden">
      {/* Sidebar */}
      <div className="w-64 bg-slate-800 border-r border-purple-500/30 p-6 flex flex-col gap-4 overflow-y-auto flex-shrink-0">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold">Admin</h2>
          {onBackClick && (
            <button
              onClick={onBackClick}
              className="p-2 hover:bg-slate-700 rounded-lg transition"
              title="Back to Chat"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </button>
          )}
        </div>

        <button
          onClick={() => setActiveTab('leads')}
          className={`px-6 py-3 rounded-lg font-semibold transition text-left ${
            activeTab === 'leads'
              ? 'bg-purple-600 text-white shadow-lg'
              : 'bg-slate-700 text-gray-200 hover:bg-slate-600'
          }`}
        >
          Leads
        </button>

        <button
          onClick={handleLogout}
          className="mt-auto px-6 py-3 rounded-lg font-semibold bg-slate-700 text-gray-300 hover:bg-red-900/40 hover:text-red-300 transition text-left"
        >
          Sign out
        </button>
      </div>

      {/* Main Content */}
      <div className="flex-1 p-6 overflow-y-auto overflow-x-hidden">
        <div className="max-w-3xl">
          <div className="mb-8">
            <h1 className="text-4xl font-bold mb-2">Admin Dashboard</h1>
            <p className="text-gray-300">View enrollment leads</p>
          </div>

          {activeTab === 'leads' && (
            <div className="bg-slate-800 rounded-xl p-8 border border-purple-500/30 overflow-x-auto">
              <h2 className="text-2xl font-bold mb-6">
                Enrollment Leads ({totalLeads})
              </h2>

              {leads.length === 0 ? (
                <p className="text-gray-400 text-center py-8">No enrollment leads yet</p>
              ) : (
                <>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-slate-600">
                          <th className="text-left py-3 px-4 font-semibold">Name</th>
                          <th className="text-left py-3 px-4 font-semibold">Phone</th>
                          <th className="text-left py-3 px-4 font-semibold">Blood Sugar</th>
                          <th className="text-left py-3 px-4 font-semibold">Date</th>
                        </tr>
                      </thead>
                      <tbody>
                        {leads.map((lead) => (
                          <tr key={lead.id} className="border-b border-slate-700 hover:bg-slate-700/50 transition">
                            <td className="py-3 px-4 text-white">{lead.name}</td>
                            <td className="py-3 px-4 text-white">{lead.phone}</td>
                            <td className="py-3 px-4 text-white">{lead.sugar_level || 'Not provided'}</td>
                            <td className="py-3 px-4 text-gray-400">{new Date(lead.created_at).toLocaleDateString()}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  {/* Pagination */}
                  {totalPages > 1 && (
                    <div className="flex items-center justify-between mt-6 pt-4 border-t border-slate-600">
                      <button
                        onClick={() => setPage((p) => Math.max(1, p - 1))}
                        disabled={page === 1}
                        className="px-4 py-2 rounded-lg bg-slate-700 hover:bg-slate-600 disabled:opacity-40 disabled:cursor-not-allowed transition"
                      >
                        Previous
                      </button>
                      <span className="text-gray-400 text-sm">
                        Page {page} of {totalPages}
                      </span>
                      <button
                        onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                        disabled={page === totalPages}
                        className="px-4 py-2 rounded-lg bg-slate-700 hover:bg-slate-600 disabled:opacity-40 disabled:cursor-not-allowed transition"
                      >
                        Next
                      </button>
                    </div>
                  )}
                </>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
