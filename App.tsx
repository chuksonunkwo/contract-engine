
import React, { useState, useCallback, useEffect } from 'react';
import { Upload, Zap, FileCheck, Gavel, FileText, Shield, MessageSquareText, CheckCircle2, Briefcase, Search, PieChart, Settings, Github } from 'lucide-react';
import { analyzeContract } from './services/geminiService';
import { AnalysisState, AnalysisStatus, ContractFile } from './types';
import AnalysisResult from './components/AnalysisResult';
import GumroadOverlay from './components/GumroadOverlay';

declare global {
    interface Window {
        mammoth: any;
    }
}

const MAX_FILE_SIZE_MB = 25;
const MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024;

export const App: React.FC = () => {
  // Verification State
  const [isVerified, setIsVerified] = useState(false);
  const [isCheckingLicense, setIsCheckingLicense] = useState(true);

  // Check for existing license on mount
  useEffect(() => {
    const savedKey = localStorage.getItem('contract_engine_license');
    if (savedKey) {
        setIsVerified(true);
    }
    setIsCheckingLicense(false);
  }, []);

  const [contractFile, setContractFile] = useState<ContractFile | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  
  const [analysis, setAnalysis] = useState<AnalysisState>({
    status: AnalysisStatus.IDLE,
    result: null,
    error: null,
  });

  const handleAnalyze = async () => {
    if (!contractFile) return;

    setAnalysis({ status: AnalysisStatus.ANALYZING, result: null, error: null });

    try {
      const result = await analyzeContract(contractFile);
      setAnalysis({
        status: AnalysisStatus.COMPLETE,
        result: result,
        error: null,
      });
    } catch (error) {
      setAnalysis({
        status: AnalysisStatus.ERROR,
        result: null,
        error: "Failed to analyze contract. Please try again later or check your connection.",
      });
    }
  };

  const fileToBase64 = (file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.readAsDataURL(file);
        reader.onload = () => {
            const result = reader.result as string;
            // Remove the data URL prefix (e.g., "data:application/pdf;base64,")
            const base64 = result.split(',')[1];
            resolve(base64);
        };
        reader.onerror = error => reject(error);
    });
  };

  const processFile = async (file: File) => {
      // Reset analysis when new file is loaded
    setAnalysis({ status: AnalysisStatus.IDLE, result: null, error: null });

    if (file.size > MAX_FILE_SIZE_BYTES) {
        setAnalysis({
            status: AnalysisStatus.ERROR,
            result: null,
            error: `File is too large (over ${MAX_FILE_SIZE_MB}MB). Analysis may fail or be incomplete. Please upload a smaller document.`
        });
        return;
    }

    try {
        if (file.type === 'application/pdf') {
            const base64Data = await fileToBase64(file);
            setContractFile({
                type: 'pdf',
                content: base64Data,
                name: file.name,
                mimeType: 'application/pdf'
            });
        } else if (file.name.endsWith('.docx')) {
             // Use Mammoth to extract text
             const arrayBuffer = await file.arrayBuffer();
             if (window.mammoth) {
                 const result = await window.mammoth.extractRawText({ arrayBuffer: arrayBuffer });
                 setContractFile({
                     type: 'docx',
                     content: result.value,
                     name: file.name
                 });
             } else {
                 throw new Error("Docx parser not loaded");
             }
        } else {
            // Assume text
            const text = await file.text();
             setContractFile({
                type: 'text',
                content: text,
                name: file.name
            });
        }
    } catch (err) {
        console.error("File load error", err);
        setAnalysis({
            status: AnalysisStatus.ERROR,
            result: null,
            error: "Could not read file. Please upload a valid PDF, DOCX, or TXT file."
        });
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    await processFile(file);
  };

  const handleTextChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      setContractFile({
          type: 'text',
          content: e.target.value,
          name: 'Manual Entry'
      });
  };

  const handleDragOver = useCallback((e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback(async (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
  }, []);

  const handleDrop = useCallback(async (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      const file = e.dataTransfer.files?.[0];
      if (file) {
          await processFile(file);
      }
  }, []);

  const resetView = () => {
    setAnalysis({ status: AnalysisStatus.IDLE, result: null, error: null });
    setContractFile(null);
  };

  // If initial check is still running, show nothing or a loader
  if (isCheckingLicense) return null;

  return (
    <div className="min-h-screen bg-[#f8fafc] font-sans text-slate-800 flex flex-col relative">
      
      {/* Gumroad Login Gate */}
      {!isVerified && (
        <GumroadOverlay onVerified={() => setIsVerified(true)} />
      )}

      {/* Navigation Bar */}
      <nav className="border-b border-slate-200 bg-white px-8 py-4 flex items-center justify-between sticky top-0 z-20 shadow-sm/50">
        <div className="flex items-center gap-4 cursor-pointer group" onClick={resetView}>
            <div className="relative w-11 h-11 flex items-center justify-center">
                {/* Composite Logo Icon (Gear + Search) */}
                <Settings className="text-corporate-900 absolute" size={40} strokeWidth={1.5} />
                <div className="absolute -bottom-1 -right-1 bg-white rounded-full p-0.5 border-2 border-white">
                    <Search className="text-amber-600" size={18} strokeWidth={3} />
                </div>
            </div>
            <div className="flex flex-col">
                <span className="font-bold text-2xl text-corporate-900 tracking-tight font-serif leading-none">Contract Engine</span>
                <span className="text-xs font-bold text-amber-600 uppercase tracking-[0.2em] mt-1">Oil & Gas Edition</span>
            </div>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto px-6 py-12 pb-32 flex-grow">
        
        {analysis.status === AnalysisStatus.IDLE || analysis.status === AnalysisStatus.ANALYZING || analysis.status === AnalysisStatus.ERROR ? (
            <>
                {/* Hero Section */}
                <div className="text-center max-w-3xl mx-auto mb-12">
                    <h1 className="text-4xl md:text-5xl font-bold text-corporate-900 mb-6 tracking-tight leading-tight font-serif">
                        The AI Co-Pilot for Independent Oil & Gas Consultants
                    </h1>
                    <p className="text-lg text-slate-600 leading-relaxed font-normal">
                        Review Contracts in Seconds, Not Hours.
                    </p>
                </div>

                {/* Main Input Card */}
                <div 
                    className={`bg-white rounded-xl shadow-lg border overflow-hidden max-w-4xl mx-auto mb-16 relative transition-all duration-300 ${
                        isDragging ? 'border-accent-500 ring-4 ring-accent-100 scale-[1.01]' : 'border-slate-200'
                    }`}
                    onDragOver={handleDragOver}
                    onDragLeave={handleDragLeave}
                    onDrop={handleDrop}
                >
                    <div className="px-8 py-6 border-b border-slate-100 bg-slate-50/50 flex items-center justify-between">
                        <div>
                            <h3 className="font-semibold text-lg text-corporate-900">Contract Input</h3>
                            <p className="text-sm text-slate-500">Paste text or drag & drop a document (PDF, DOCX) - max {MAX_FILE_SIZE_MB}MB</p>
                        </div>
                    </div>

                    <div className="p-8 relative">
                         {isDragging && (
                             <div className="absolute inset-0 z-20 bg-accent-50/90 flex flex-col items-center justify-center backdrop-blur-sm">
                                 <Upload size={48} className="text-accent-600 mb-4 animate-bounce" />
                                 <p className="text-2xl font-semibold text-accent-700">Drop document to analyze</p>
                             </div>
                         )}

                         {contractFile?.type === 'pdf' ? (
                            <div className="w-full h-64 bg-slate-50 border-2 border-dashed border-slate-200 rounded-lg flex flex-col items-center justify-center text-slate-500 relative group transition-colors hover:border-accent-300 hover:bg-slate-100/50">
                                <FileText size={48} className="text-accent-500 mb-3" />
                                <p className="font-semibold text-corporate-900 text-lg mb-1">{contractFile.name}</p>
                                <p className="text-sm font-medium text-slate-500">PDF Ready for Analysis</p>
                                <button 
                                    onClick={() => setContractFile(null)}
                                    className="absolute top-4 right-4 p-2 bg-white border border-slate-200 rounded-full shadow-sm hover:bg-red-50 hover:text-red-500 hover:border-red-200 transition-colors"
                                >
                                    <Zap size={18} /> 
                                </button>
                            </div>
                         ) : (
                            <textarea
                                className="w-full h-64 p-5 bg-slate-50 border border-slate-200 rounded-lg focus:ring-2 focus:ring-accent-500 focus:border-transparent outline-none resize-none text-slate-900 placeholder-slate-400 transition-all font-mono text-lg leading-relaxed"
                                placeholder="Paste contract clauses here, or drag and drop a PDF/DOCX file..."
                                value={contractFile?.content || ''}
                                onChange={handleTextChange}
                                disabled={analysis.status === AnalysisStatus.ANALYZING}
                            ></textarea>
                         )}

                         {/* Loading Overlay */}
                         {analysis.status === AnalysisStatus.ANALYZING && (
                            <div className="absolute inset-0 bg-white/95 backdrop-blur-[2px] z-10 flex flex-col items-center justify-center">
                                <div className="w-16 h-16 border-4 border-slate-100 border-t-accent-600 rounded-full animate-spin mb-6"></div>
                                <h3 className="text-2xl font-bold text-corporate-900 animate-pulse">Analyzing Contract...</h3>
                                <p className="text-slate-500 font-medium mt-2 text-lg">Performing 360° Risk, Scope & Compliance Review</p>
                            </div>
                         )}

                         {/* Error Message */}
                         {analysis.status === AnalysisStatus.ERROR && (
                            <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm flex items-center gap-3 font-medium">
                                <Zap size={18} />
                                {analysis.error}
                            </div>
                         )}
                    </div>

                    <div className="px-8 py-6 border-t border-slate-100 flex items-center justify-between bg-white">
                         <label className="flex items-center gap-2 px-6 py-3 bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 font-medium rounded-lg cursor-pointer transition-all shadow-sm text-lg">
                            <Upload size={20} />
                            <span>Upload Document</span>
                            <input 
                                type="file" 
                                accept=".txt,.pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document" 
                                onChange={handleFileUpload} 
                                className="hidden" 
                            />
                        </label>
                        
                        <button
                            onClick={handleAnalyze}
                            disabled={!contractFile || analysis.status === AnalysisStatus.ANALYZING}
                            className="flex items-center gap-2 px-10 py-3 bg-corporate-900 hover:bg-corporate-800 text-white font-semibold rounded-lg shadow-md hover:shadow-lg hover:-translate-y-0.5 transition-all disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none text-lg"
                        >
                            <span>Analyze Contract</span>
                        </button>
                    </div>
                </div>

                {/* Analysis Engine Capabilities */}
                <div className="max-w-7xl mx-auto">
                   <div className="text-center mb-10">
                      <h4 className="text-sm font-bold text-slate-400 uppercase tracking-widest">Analysis Engine Capabilities</h4>
                   </div>
                   <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                      
                      {/* Card 1 */}
                      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm hover:shadow-md transition-shadow group">
                         <div className="w-12 h-12 bg-blue-50 text-blue-600 rounded-lg flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                            <Search size={24} />
                         </div>
                         <h3 className="font-semibold text-corporate-900 text-xl mb-2">Automated Risk Review</h3>
                         <p className="text-lg text-slate-700 leading-relaxed">
                            Instantly reads PDF & Word contracts to identify high-risk clauses, missing terms, and deviations from standard positions.
                         </p>
                      </div>

                      {/* Card 2 */}
                      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm hover:shadow-md transition-shadow group">
                         <div className="w-12 h-12 bg-purple-50 text-purple-600 rounded-lg flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                            <MessageSquareText size={24} />
                         </div>
                         <h3 className="font-semibold text-corporate-900 text-xl mb-2">Negotiation Coach</h3>
                         <p className="text-lg text-slate-700 leading-relaxed">
                            Interactive AI assistant helps you draft counter-clauses, explain legal jargon, and strategize your negotiation approach.
                         </p>
                      </div>

                      {/* Card 3 */}
                      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm hover:shadow-md transition-shadow group">
                         <div className="w-12 h-12 bg-green-50 text-green-600 rounded-lg flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                            <Shield size={24} />
                         </div>
                         <h3 className="font-semibold text-corporate-900 text-xl mb-2">Vendor Intelligence</h3>
                         <p className="text-lg text-slate-700 leading-relaxed">
                            Performs background checks using live Google Search to flag sanctions, financial instability, or reputational risks.
                         </p>
                      </div>

                      {/* Card 4 */}
                      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm hover:shadow-md transition-shadow group">
                         <div className="w-12 h-12 bg-orange-50 text-orange-600 rounded-lg flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                            <PieChart size={24} />
                         </div>
                         <h3 className="font-semibold text-corporate-900 text-xl mb-2">Executive Insights</h3>
                         <p className="text-lg text-slate-700 leading-relaxed">
                            Transforms complex legal documents into clear, data-driven executive summaries and visual risk matrices.
                         </p>
                      </div>

                   </div>
                </div>
            </>
        ) : (
            /* Analysis Results View */
            <div className="animate-in fade-in slide-in-from-bottom-8 duration-500">
                <div className="flex items-center justify-between mb-8">
                    <div>
                        <h2 className="text-3xl font-bold text-corporate-900 flex items-center gap-3 font-serif">
                            {contractFile?.name || 'Contract'} Analysis
                            <CheckCircle2 size={24} className="text-green-600" />
                        </h2>
                        <p className="text-slate-500 font-medium text-lg mt-1">Comprehensive Assessment</p>
                    </div>
                </div>
                
                {analysis.result && <AnalysisResult data={analysis.result} contractFile={contractFile} />}
                
                <div className="mt-12 flex justify-center">
                    <button 
                        onClick={resetView}
                        className="px-6 py-3 text-slate-600 hover:text-corporate-900 font-semibold transition-colors text-lg hover:bg-slate-100 rounded-lg"
                    >
                        Analyze Another Contract
                    </button>
                </div>
            </div>
        )}

      </main>

      {/* Disclaimer Footer */}
      <footer className="border-t border-slate-200 bg-white py-8 mt-auto">
          <div className="max-w-7xl mx-auto px-6 flex flex-col items-center gap-4 text-center">
              <p className="text-slate-500 text-sm font-medium">
                  Zero-Retention Policy - AI Co-Pilot, not a law firm. Results should be verified by a qualified attorney.
              </p>
              <a 
                href="https://github.com/chuksonunkwo/contract-engine" 
                target="_blank" 
                rel="noopener noreferrer"
                className="flex items-center gap-2 text-slate-400 hover:text-slate-700 transition-colors"
              >
                  <Github size={20} />
                  <span className="text-xs font-semibold">View on GitHub</span>
              </a>
          </div>
      </footer>
    </div>
  );
};
