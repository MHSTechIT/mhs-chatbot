import React, { useState, useEffect } from 'react';

interface Document {
  id: string;
  title: string;
  url?: string;
  file_name?: string;
  type: 'document' | 'link';
  uploaded_at: string;
}

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

export const AdminPage: React.FC<AdminPageProps> = ({ onBackClick }) => {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [leads, setLeads] = useState<Lead[]>([]);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<'upload' | 'leads'>('leads');

  // Upload form
  const [file, setFile] = useState<File | null>(null);
  const [fileName, setFileName] = useState('');

  // Link form
  const [linkTitle, setLinkTitle] = useState('');
  const [linkUrl, setLinkUrl] = useState('');

  const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

  // Fetch documents
  const fetchDocuments = async () => {
    try {
      const response = await fetch(`${API_BASE}/admin/documents`);
      const data = await response.json();
      setDocuments(data.documents || []);
    } catch (error) {
      console.error('Error fetching documents:', error);
    }
  };

  // Fetch leads
  const fetchLeads = async () => {
    try {
      const response = await fetch(`${API_BASE}/admin/leads`);
      const data = await response.json();
      setLeads(data.leads || []);
    } catch (error) {
      console.error('Error fetching leads:', error);
    }
  };

  useEffect(() => {
    fetchDocuments();
    fetchLeads();
  }, []);

  // Handle file upload
  const handleFileUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file || !fileName.trim()) {
      alert('Please select file and enter title');
      return;
    }

    setLoading(true);
    const formData = new FormData();
    formData.append('file', file);
    formData.append('title', fileName);

    try {
      const response = await fetch(`${API_BASE}/admin/upload`, {
        method: 'POST',
        body: formData,
      });

      if (response.ok) {
        alert('✅ Document uploaded successfully');
        setFile(null);
        setFileName('');
        fetchDocuments();
      } else {
        alert('❌ Upload failed');
      }
    } catch (error) {
      alert('Error uploading: ' + error);
    } finally {
      setLoading(false);
    }
  };

  // Handle link submission
  const handleLinkSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!linkTitle.trim() || !linkUrl.trim()) {
      alert('Please enter both title and URL');
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/admin/add-link`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: linkTitle,
          url: linkUrl,
        }),
      });

      if (response.ok) {
        alert('✅ Link added successfully');
        setLinkTitle('');
        setLinkUrl('');
        fetchDocuments();
      } else {
        alert('❌ Failed to add link');
      }
    } catch (error) {
      alert('Error adding link: ' + error);
    } finally {
      setLoading(false);
    }
  };

  // Delete document
  const deleteDocument = async (id: string) => {
    if (!confirm('Delete this document?')) return;

    try {
      const response = await fetch(`${API_BASE}/admin/documents/${id}`, {
        method: 'DELETE',
      });

      if (response.ok) {
        alert('✅ Deleted');
        fetchDocuments();
      }
    } catch (error) {
      alert('Error deleting: ' + error);
    }
  };

  return (
    <div className="h-screen w-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 text-white flex overflow-hidden">
      {/* Sidebar */}
      <div className="w-64 bg-slate-800 border-r border-purple-500/30 p-6 flex flex-col gap-4 overflow-y-auto flex-shrink-0">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold">📚 Admin</h2>
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

        {/* Upload button hidden - documents managed via database only */}

        <button
          onClick={() => setActiveTab('leads')}
          className={`px-6 py-3 rounded-lg font-semibold transition text-left ${
            activeTab === 'leads'
              ? 'bg-purple-600 text-white shadow-lg'
              : 'bg-slate-700 text-gray-200 hover:bg-slate-600'
          }`}
        >
          👥 Leads
        </button>
      </div>

      {/* Main Content */}
      <div className="flex-1 p-6 overflow-y-auto overflow-x-hidden">
        <div className="max-w-3xl">
          {/* Header */}
          <div className="mb-8">
            <h1 className="text-4xl font-bold mb-2">📚 Admin Dashboard</h1>
            <p className="text-gray-300">
              {activeTab === 'upload' ? 'Upload documents and links for AI training' : 'View enrollment leads'}
            </p>
          </div>

          {/* Upload Tab Hidden - Documents managed via database directly */}
          {/* All upload UI removed. Backend code remains for AI to access documents */}

          {/* Leads Tab */}
          {activeTab === 'leads' && (
            <div className="bg-slate-800 rounded-xl p-8 border border-purple-500/30 overflow-x-auto">
              <h2 className="text-2xl font-bold mb-6">👥 Enrollment Leads ({leads.length})</h2>

              {leads.length === 0 ? (
                <p className="text-gray-400 text-center py-8">No enrollment leads yet</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-slate-600">
                        <th className="text-left py-3 px-4 font-semibold">Name</th>
                        <th className="text-left py-3 px-4 font-semibold">Phone Number</th>
                        <th className="text-left py-3 px-4 font-semibold">Blood Sugar Level</th>
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
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
